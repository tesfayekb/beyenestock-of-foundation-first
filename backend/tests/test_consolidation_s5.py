"""Consolidation Session 5 tests — event regime, synthesis fall-through,
probability simplex, War Room services, VVIX TTL.

Tests in this file cover:
  ROI-1  — _compute_regime returns "event" on catalyst/earnings days
  ROI-2  — synthesis no longer gates on macro brief alone
  ROI-4  — AI synthesis prediction includes a normalised probability simplex
  P1-15  — WarRoomPage EXPECTED_SERVICES matches HealthPage and has no
           phantom services
  P1-16  — every polygon:vvix:* write in _store_baseline uses setex
"""
import json
import os
import sys
from unittest.mock import MagicMock, patch


# Make backend/ and backend_agents/ importable, mirroring the pattern in
# test_phase_2a_agents.py. These tests run from `backend/` so the parent
# is the repo root.
_BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..")
_AGENTS_DIR = os.path.join(_BACKEND_DIR, "..", "backend_agents")
sys.path.insert(0, os.path.abspath(_BACKEND_DIR))
sys.path.insert(0, os.path.abspath(_AGENTS_DIR))


# ── ROI-1: Event regime ──────────────────────────────────────────────────────


def test_compute_regime_returns_event_on_catalyst_day():
    """When calendar:today:intel marks a major catalyst, regime is 'event'."""
    from prediction_engine import PredictionEngine

    engine = PredictionEngine.__new__(PredictionEngine)
    intel = {
        "has_major_catalyst": True,
        "has_major_earnings": False,
        "day_classification": "catalyst_major",
    }

    def mock_read(key, default=None):
        if key == "calendar:today:intel":
            return json.dumps(intel)
        return default

    engine._read_redis = mock_read
    engine.redis_client = MagicMock()

    result = engine._compute_regime()
    assert result["regime"] == "event", (
        f"Expected regime='event' on catalyst day, got '{result['regime']}'"
    )
    assert result["rcs"] == 55.0
    assert result["regime_agreement"] is True
    assert result["allocation_tier"] == "moderate"


def test_compute_regime_returns_event_on_earnings_day():
    """Major earnings day also flips regime to 'event'."""
    from prediction_engine import PredictionEngine

    engine = PredictionEngine.__new__(PredictionEngine)
    intel = {"has_major_catalyst": False, "has_major_earnings": True}

    engine._read_redis = (
        lambda k, d=None: json.dumps(intel)
        if k == "calendar:today:intel" else d
    )
    engine.redis_client = MagicMock()

    result = engine._compute_regime()
    assert result["regime"] == "event"


def test_compute_regime_normal_when_no_catalyst():
    """Quiet day → normal VVIX/GEX regime logic, never 'event'."""
    from prediction_engine import PredictionEngine

    engine = PredictionEngine.__new__(PredictionEngine)
    intel = {"has_major_catalyst": False, "has_major_earnings": False}

    def mock_read(key, default=None):
        if key == "calendar:today:intel":
            return json.dumps(intel)
        if key == "polygon:vvix:z_score":
            return "0.5"
        if key == "gex:confidence":
            return "0.2"  # below 0.3 → falls back to HMM
        return default

    engine._read_redis = mock_read
    engine.redis_client = MagicMock()

    with patch.object(engine, "_get_spx_price", return_value=5200.0):
        result = engine._compute_regime()

    assert result["regime"] != "event"


def test_compute_regime_falls_through_when_calendar_unavailable():
    """Calendar key absent → normal regime logic runs unchanged."""
    from prediction_engine import PredictionEngine

    engine = PredictionEngine.__new__(PredictionEngine)
    engine._read_redis = lambda k, d=None: d  # everything missing
    engine.redis_client = MagicMock()

    with patch.object(engine, "_get_spx_price", return_value=5200.0):
        result = engine._compute_regime()

    assert result["regime"] != "event"
    assert "regime" in result
    assert "rcs" in result


def test_compute_regime_falls_through_on_malformed_calendar_intel():
    """Garbled calendar JSON must not crash regime — fall through cleanly."""
    from prediction_engine import PredictionEngine

    engine = PredictionEngine.__new__(PredictionEngine)
    # Malformed JSON triggers the except branch in the new ROI-1 block
    engine._read_redis = (
        lambda k, d=None: "{not valid json"
        if k == "calendar:today:intel" else d
    )
    engine.redis_client = MagicMock()

    with patch.object(engine, "_get_spx_price", return_value=5200.0):
        result = engine._compute_regime()  # must not raise
    assert result["regime"] != "event"


# ── ROI-2: Synthesis fall-through ────────────────────────────────────────────


def test_synthesis_runs_without_macro_brief():
    """When macro is missing but flow exists, synthesis must NOT short-circuit
    to {} — it should call the AI provider and return a result."""
    from synthesis_agent import run_synthesis_agent

    flow_brief = {
        "flow_score": 60,
        "flow_direction": "bull",
        "flow_confidence": 0.6,
        "put_call_ratio": 0.85,
        "unusual_activity_count": 3,
    }

    def mock_get(key):
        if key == "agents:ai_synthesis:enabled":
            return b"true"
        if key == "ai:macro:brief":
            return None  # macro absent
        if key == "ai:flow:brief":
            return json.dumps(flow_brief).encode()
        if key == "ai:sentiment:brief":
            return None
        if key == "calendar:today:intel":
            return None
        return None

    redis = MagicMock()
    redis.get.side_effect = mock_get

    with patch("synthesis_agent.config") as mc:
        mc.ANTHROPIC_API_KEY = "fake-key"
        mc.OPENAI_API_KEY = ""
        mc.AI_PROVIDER = "anthropic"
        mc.AI_MODEL = "claude-sonnet-4-5"
        with patch(
            "synthesis_agent._call_ai_provider",
            return_value={
                "direction": "bull",
                "confidence": 0.7,
                "strategy": "iron_condor",
                "rationale": "test",
                "risk_level": 4,
                "sizing_modifier": 1.0,
            },
        ):
            result = run_synthesis_agent(redis)

    assert result != {}, (
        "Macro absent but flow present → synthesis must still run "
        "(prior bug: returned {} when only macro was missing)"
    )
    assert result["direction"] == "bull"


def test_synthesis_skips_when_all_signals_absent():
    """All four primary signals absent → synthesis cleanly returns {}."""
    from synthesis_agent import run_synthesis_agent

    redis = MagicMock()
    redis.get.return_value = None  # everything absent

    with patch("synthesis_agent.config") as mc:
        mc.ANTHROPIC_API_KEY = "fake-key"
        mc.OPENAI_API_KEY = ""
        mc.AI_PROVIDER = "anthropic"
        mc.AI_MODEL = "claude-sonnet-4-5"
        result = run_synthesis_agent(redis)

    assert result == {}, "All signals absent → synthesis must return {}"


# ── ROI-4: Probability simplex ───────────────────────────────────────────────


def test_probability_simplex_sums_to_one_in_ai_synthesis_branch():
    """When AI synthesis drives the prediction, p_bull + p_bear + p_neutral
    must sum to 1.0 (was previously incomplete: only p_bull + p_bear)."""
    from datetime import datetime, timezone
    from prediction_engine import PredictionEngine

    engine = PredictionEngine.__new__(PredictionEngine)
    synth = {
        "direction": "bull",
        "confidence": 0.72,
        "strategy": "debit_call_spread",
        "sizing_modifier": 1.0,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    def mock_read(key, default=None):
        if key == "ai:synthesis:latest":
            return json.dumps(synth)
        if key == "agents:ai_synthesis:enabled":
            return "true"
        return default

    engine._read_redis = mock_read
    engine.redis_client = MagicMock()
    engine._direction_model = None  # force fall-through guard

    result = engine._compute_direction(
        regime="trend", cv_stress=20.0, spx_price=5200.0,
        flip_zone=None, gex_conf=0.0,
    )
    assert result["source"] == "ai_synthesis"
    total = result["p_bull"] + result["p_bear"] + result["p_neutral"]
    assert abs(total - 1.0) < 0.001, (
        f"Probability simplex sums to {total}, expected 1.0"
    )
    assert result["p_neutral"] >= 0.0


# ── P1-15: War Room EXPECTED_SERVICES ────────────────────────────────────────


def _war_room_src() -> str:
    path = os.path.join(
        os.path.dirname(__file__), "..", "..",
        "src", "pages", "admin", "trading", "WarRoomPage.tsx",
    )
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def test_war_room_expected_services_no_phantom_services():
    """learning_engine, sentinel, cboe_feed must not appear in War Room."""
    src = _war_room_src()
    for phantom in ("learning_engine", "sentinel", "cboe_feed"):
        assert (
            f"'{phantom}'" not in src and f'"{phantom}"' not in src
        ), f"Phantom service '{phantom}' still in WarRoomPage EXPECTED_SERVICES"


def test_war_room_includes_polygon_feed_and_morning_agents():
    """War Room must list polygon_feed plus the morning AI agents that
    HealthPage tracks — they were missing from the prior 11-service list."""
    src = _war_room_src()
    for required in (
        "polygon_feed",
        "economic_calendar",
        "synthesis_agent",
        "earnings_scanner",
        "feedback_agent",
        "prediction_watchdog",
        "emergency_backstop",
        "position_reconciliation",
    ):
        assert f"'{required}'" in src, (
            f"WarRoomPage EXPECTED_SERVICES missing '{required}'"
        )


# ── P1-16: VVIX TTL ──────────────────────────────────────────────────────────


def test_vvix_writes_use_setex_not_bare_set():
    """No bare .set("polygon:vvix:...") may remain in polygon_feed.py —
    every VVIX write must carry a TTL via setex."""
    path = os.path.join(os.path.dirname(__file__), "..", "polygon_feed.py")
    with open(path, "r", encoding="utf-8") as f:
        src = f.read()
    # Bare .set( with a polygon:vvix: literal as first arg = bug
    assert '.set("polygon:vvix:' not in src, (
        "Found bare .set(\"polygon:vvix:...\") — must use setex with TTL"
    )
    # And confirm setex IS used for vvix
    assert '.setex("polygon:vvix:current"' in src, (
        "polygon:vvix:current must be written with setex"
    )
