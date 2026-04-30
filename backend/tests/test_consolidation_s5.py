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


# ── Apr-30 fix PR: AI synth output loss regression guards ────────────────────


def test_ai_synthesis_return_dict_matches_persistence_schema():
    """Regression guard for the schema-mismatch bug (Apr 30 fix PR).

    AI synth dict must include the schema-aligned keys
    (signal_weak, expected_move_pts, expected_move_pct) AND
    preserve the active-consumer keys (strategy_hint, source,
    sizing_modifier).

    Limitation: this is a unit test for dict shape; it does NOT
    verify the supabase insert succeeds end-to-end (would require
    integration test mocking the full run_cycle path). For the
    immediate fix's lifecycle, this guards against future regressions
    that REMOVE schema-aligned keys or that ADD unknown extras. A
    schema-driven integration test is queued for Phase 5A hardening.
    """
    from datetime import datetime, timezone
    from prediction_engine import PredictionEngine

    engine = PredictionEngine.__new__(PredictionEngine)
    synth = {
        "direction": "bull",
        "confidence": 0.62,
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

    # Required keys (must be present; persisted to schema columns):
    for key in ("p_bull", "p_bear", "p_neutral", "direction",
                "confidence", "expected_move_pts", "expected_move_pct",
                "signal_weak"):
        assert key in result, (
            f"AI synth dict missing required key {key} — would cause "
            f"non-AI-synth-shape downstream consumer to read None or "
            f"fail analytics persistence"
        )

    # Active-consumer keys (must be preserved):
    for key in ("strategy_hint", "source", "sizing_modifier"):
        assert key in result, (
            f"AI synth dict missing active-consumer key {key} — would "
            f"silently break feature flag or telemetry routing"
        )

    # Specific value assertions for high-conviction bull case:
    assert result["source"] == "ai_synthesis"
    assert result["direction"] == "bull"
    assert result["signal_weak"] is False  # 62% conf → wide spread


def test_ai_synthesis_neutral_does_not_trigger_signal_weak_gate():
    """B1 guard: AI synth direction='neutral' must NOT flag signal_weak.

    For direction='neutral' the AI synth path produces p_bull == p_bear
    by construction (both = (1 - confidence) * 0.5). A naive
    abs(p_bull - p_bear) < 0.05 check would always be True and would
    block iron_condor — the literal strategy for high-conviction
    range-bound predictions. The B1 fix guards the comparison with
    `direction != 'neutral'` so AI synth's high-conviction neutral
    predictions proceed to strategy_selector.

    This aligns with operator's "increase ROI not clamp down" rule:
    treating an actively-computed high-conviction neutral the same as
    placeholder/no-signal is exactly the failure mode to avoid.
    """
    from datetime import datetime, timezone
    from prediction_engine import PredictionEngine

    engine = PredictionEngine.__new__(PredictionEngine)
    synth = {
        "direction": "neutral",
        "confidence": 0.70,  # high conviction neutral → iron_condor candidate
        "strategy": "iron_condor",
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
    engine._direction_model = None

    result = engine._compute_direction(
        regime="pin_range", cv_stress=20.0, spx_price=5200.0,
        flip_zone=None, gex_conf=0.0,
    )

    # The dict shape contract still applies:
    assert result["source"] == "ai_synthesis"
    assert result["direction"] == "neutral"

    # Mathematical invariant: AI synth neutral has p_bull == p_bear:
    assert abs(result["p_bull"] - result["p_bear"]) < 1e-9, (
        f"AI synth neutral path expected p_bull == p_bear, got "
        f"p_bull={result['p_bull']}, p_bear={result['p_bear']}"
    )

    # B1 fix: signal_weak must be False despite zero spread,
    # because direction is 'neutral' (the spread is meaningful only
    # for directional predictions).
    assert result["signal_weak"] is False, (
        "AI synth neutral predictions must not be flagged signal_weak; "
        "doing so would block iron_condor — the intended strategy for "
        "high-conviction range-bound predictions. See B1 guard at "
        "prediction_engine.py:498-510."
    )


# ── T-ACT-041: LightGBM model loader (3-tier strategy) ──────────────────────


# Helpers shared across the 4 model-loader tests below. Producing a
# real picklable object (instead of MagicMock) avoids the well-known
# unittest.mock pickling edge cases.
class _FakeLGBM:
    """Stand-in for LGBMClassifier used by tests. Picklable because it
    is a top-level class with no closures. Tests only check that the
    loader stores it on _direction_model — they don't invoke
    predict_proba (that's covered by separate inference tests)."""
    classes_ = ["bear", "bull"]

    def predict_proba(self, X):  # noqa: ARG002
        return [[0.4, 0.6]]


def _write_pkl(path, obj):
    import pickle as _pickle
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        _pickle.dump(obj, f)


def _write_meta(path, features=None):
    if features is None:
        # Use a small but non-empty list — D3 partial-state guard
        # rejects empty features, so any non-empty list works for
        # tests that only check load success.
        features = ["return_5m", "vix_close", "rv_20d"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "model_version": "v1",
        "features": features,
        "n_features": len(features),
        "win_rate": 0.5292,
        "gate_passed": True,
    }))


def test_direction_model_loads_from_local_cache_when_present(tmp_path):
    """T-ACT-041 Tier 1 — local cache hit. Both files present at
    the local-tree path; loader populates _direction_model and
    _direction_features without touching Supabase. Health probe
    writes 'healthy'."""
    from prediction_engine import PredictionEngine

    local_pkl  = tmp_path / "models" / "direction_lgbm_v1.pkl"
    local_meta = tmp_path / "models" / "model_metadata.json"
    cache_pkl  = tmp_path / "cache" / "direction_lgbm_v1.pkl"
    cache_meta = tmp_path / "cache" / "model_metadata.json"
    _write_pkl(local_pkl, _FakeLGBM())
    _write_meta(local_meta)

    engine = PredictionEngine.__new__(PredictionEngine)

    with patch("prediction_engine.write_health_status") as mock_health, \
         patch("prediction_engine.get_client") as mock_client:
        engine._load_direction_model(
            local_pkl=local_pkl,
            local_meta=local_meta,
            cache_pkl=cache_pkl,
            cache_meta=cache_meta,
        )

        assert engine._direction_model is not None
        assert isinstance(engine._direction_model, _FakeLGBM)
        assert engine._direction_features == [
            "return_5m", "vix_close", "rv_20d",
        ]
        # Tier 1 hit must NOT touch Supabase:
        mock_client.assert_not_called()
        # Health probe records 'healthy' once:
        mock_health.assert_called_once_with(
            "direction_model", "healthy", last_error_message=None,
        )
        # Cache path must NOT be populated when Tier 1 hits (the
        # /tmp cache is for Tier 2 spillover only):
        assert not cache_pkl.exists()
        assert not cache_meta.exists()


def test_direction_model_loads_from_supabase_when_local_missing(tmp_path):
    """T-ACT-041 Tier 2 — Supabase fallback. Local cache absent;
    storage download returns valid bytes for both files; loader
    caches them under /tmp atomically and then loads. Health probe
    writes 'degraded'."""
    import pickle as _pickle
    from prediction_engine import PredictionEngine

    local_pkl  = tmp_path / "models" / "direction_lgbm_v1.pkl"
    local_meta = tmp_path / "models" / "model_metadata.json"
    cache_pkl  = tmp_path / "cache" / "direction_lgbm_v1.pkl"
    cache_meta = tmp_path / "cache" / "model_metadata.json"
    # Note: deliberately NOT writing local files — Tier 1 must miss.

    pkl_bytes  = _pickle.dumps(_FakeLGBM())
    meta_bytes = json.dumps({
        "model_version": "v1",
        "features": ["vwap_distance", "rv_20d", "return_4h"],
        "win_rate": 0.5292,
        "gate_passed": True,
    }).encode("utf-8")

    mock_storage = MagicMock()
    mock_storage.download.side_effect = [pkl_bytes, meta_bytes]
    mock_supabase = MagicMock()
    mock_supabase.storage.from_.return_value = mock_storage

    engine = PredictionEngine.__new__(PredictionEngine)

    with patch("prediction_engine.write_health_status") as mock_health, \
         patch("prediction_engine.get_client", return_value=mock_supabase):
        engine._load_direction_model(
            local_pkl=local_pkl,
            local_meta=local_meta,
            cache_pkl=cache_pkl,
            cache_meta=cache_meta,
        )

        assert engine._direction_model is not None
        assert isinstance(engine._direction_model, _FakeLGBM)
        assert engine._direction_features == [
            "vwap_distance", "rv_20d", "return_4h",
        ]

        # Storage was called with the canonical bucket + paths:
        mock_supabase.storage.from_.assert_called_once_with("ml-models")
        mock_storage.download.assert_any_call(
            "direction/v1/direction_lgbm_v1.pkl"
        )
        mock_storage.download.assert_any_call(
            "direction/v1/model_metadata.json"
        )

        # Cache populated atomically — both files now present:
        assert cache_pkl.exists()
        assert cache_meta.exists()
        # Bytes match what storage returned:
        assert cache_pkl.read_bytes() == pkl_bytes
        assert cache_meta.read_bytes() == meta_bytes
        # No leftover staging dirs:
        leftover = list(cache_pkl.parent.glob(".staging-*"))
        assert leftover == [], (
            f"staging dir(s) leaked after successful download: {leftover}"
        )

        # Health probe records 'degraded':
        mock_health.assert_called_once()
        call_args = mock_health.call_args
        assert call_args.args[:2] == ("direction_model", "degraded")
        assert "supabase fallback" in (
            call_args.kwargs.get("last_error_message") or ""
        )


def test_direction_model_falls_through_to_gex_zg_when_both_paths_miss(tmp_path):
    """T-ACT-041 Tier 3 — total miss. Local absent; Supabase download
    raises. Loader leaves _direction_model = None so the GEX/ZG
    fallback at L545 takes over; no exception bubbles up to break
    PredictionEngine __init__. Health probe writes 'error'."""
    from prediction_engine import PredictionEngine

    local_pkl  = tmp_path / "models" / "direction_lgbm_v1.pkl"
    local_meta = tmp_path / "models" / "model_metadata.json"
    cache_pkl  = tmp_path / "cache" / "direction_lgbm_v1.pkl"
    cache_meta = tmp_path / "cache" / "model_metadata.json"

    mock_storage = MagicMock()
    mock_storage.download.side_effect = RuntimeError(
        "supabase storage: 404 not_found direction/v1/direction_lgbm_v1.pkl"
    )
    mock_supabase = MagicMock()
    mock_supabase.storage.from_.return_value = mock_storage

    engine = PredictionEngine.__new__(PredictionEngine)
    engine._direction_model = "sentinel-must-be-overwritten"
    engine._direction_features = ["sentinel"]

    with patch("prediction_engine.write_health_status") as mock_health, \
         patch("prediction_engine.get_client", return_value=mock_supabase):
        # Must NOT raise — fall-through is the contract per Q-D10.
        engine._load_direction_model(
            local_pkl=local_pkl,
            local_meta=local_meta,
            cache_pkl=cache_pkl,
            cache_meta=cache_meta,
        )

        # Final state is the documented Tier 3 silent miss:
        assert engine._direction_model is None
        assert engine._direction_features is None

        # Health probe records 'error' with informative message:
        mock_health.assert_called_once()
        call_args = mock_health.call_args
        assert call_args.args[:2] == ("direction_model", "error")
        msg = call_args.kwargs.get("last_error_message") or ""
        assert "both missed" in msg


def test_direction_model_treats_partial_local_state_as_cache_miss(tmp_path):
    """T-ACT-041 D3 partial-state guard regression. Pre-existing
    inline block at the previous prediction_engine.py:67-89 had a
    silent failure: if local direction_lgbm_v1.pkl existed but
    model_metadata.json did NOT, the model loaded but
    _direction_features stayed None, and inference at L545 short-
    circuited because of the AND check. New three-tier loader must
    treat this as a cache miss and trigger Supabase fallback."""
    import pickle as _pickle
    from prediction_engine import PredictionEngine

    local_pkl  = tmp_path / "models" / "direction_lgbm_v1.pkl"
    local_meta = tmp_path / "models" / "model_metadata.json"
    cache_pkl  = tmp_path / "cache" / "direction_lgbm_v1.pkl"
    cache_meta = tmp_path / "cache" / "model_metadata.json"

    # Local PKL present, local metadata MISSING — the partial-state
    # condition that the pre-fix code silently mishandled.
    _write_pkl(local_pkl, _FakeLGBM())
    assert local_pkl.exists()
    assert not local_meta.exists()

    # Supabase fallback returns a valid pair so we can verify Tier 2
    # actually fires (and isn't silently skipped).
    pkl_bytes  = _pickle.dumps(_FakeLGBM())
    meta_bytes = json.dumps({
        "model_version": "v1",
        "features": ["return_5m", "vix_close"],
        "win_rate": 0.5292,
        "gate_passed": True,
    }).encode("utf-8")

    mock_storage = MagicMock()
    mock_storage.download.side_effect = [pkl_bytes, meta_bytes]
    mock_supabase = MagicMock()
    mock_supabase.storage.from_.return_value = mock_storage

    engine = PredictionEngine.__new__(PredictionEngine)

    with patch("prediction_engine.write_health_status") as mock_health, \
         patch("prediction_engine.get_client", return_value=mock_supabase):
        engine._load_direction_model(
            local_pkl=local_pkl,
            local_meta=local_meta,
            cache_pkl=cache_pkl,
            cache_meta=cache_meta,
        )

        # Fix verified: Tier 1 was correctly skipped; Tier 2 fired:
        mock_supabase.storage.from_.assert_called_once_with("ml-models")
        assert mock_storage.download.call_count == 2

        # Final state reflects Supabase load (Tier 2), NOT the
        # partial local-tree state:
        assert engine._direction_model is not None
        assert engine._direction_features == ["return_5m", "vix_close"]

        # Health probe records 'degraded' (Supabase fallback), NOT
        # the misleading 'healthy' the old code would have implied:
        mock_health.assert_called_once()
        assert mock_health.call_args.args[:2] == (
            "direction_model", "degraded",
        )


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
