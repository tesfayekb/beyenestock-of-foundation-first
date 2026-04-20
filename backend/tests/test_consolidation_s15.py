"""
Consolidation Session 15 — Signal Quality.

T1-10: NFP polarity, T1-11: flow agent ET date,
T2-1:  directional accuracy uses outcome_correct,
T2-2:  ET labeling windows (no UTC-midnight boundary),
T2-4:  RTH gate in run_cycle (fail-open import),
T2-5:  minor catalyst regime override with softer RCS.

Note on test strategy:
  * surprise_detector.py has no SurpriseDetector class today — the
    NFP classifier was inline inside _detect_surprises(). S15 extracts
    it to a module-level _classify_direction() helper so we can unit-
    test the polarity fix directly without building a live Finnhub
    fixture. Tests call _classify_direction as a module function.
  * prediction_engine.run_cycle imports market_calendar.is_market_open
    method-local (critical rule #2 — must be inside try/except so a
    broken import cannot silently halt trading). Patches therefore
    target market_calendar.is_market_open, not prediction_engine.
    Same pattern as S13 T1-1.
"""
import json
import os
import sys

import pytest
from unittest.mock import MagicMock, patch

BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
AGENTS = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "backend_agents")
)
REPO_ROOT = os.path.abspath(os.path.join(BACKEND, ".."))
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)
if AGENTS not in sys.path:
    sys.path.insert(0, AGENTS)


# ═════════════════════════════════════════════════════════════════════════════
# T1-10 — NFP polarity
# ═════════════════════════════════════════════════════════════════════════════

def test_nfp_mild_beat_is_bullish():
    """NFP +7% deviation (mild jobs beat / Goldilocks) must be bullish.

    Previously fell through to the `else: direction = "bear"` branch
    because no explicit 5-10% positive elif existed.
    """
    from surprise_detector import _classify_direction
    direction = _classify_direction("Nonfarm Payrolls", deviation=0.07)
    assert direction == "bull", (
        f"NFP +7% (mild beat) must be 'bull'. Got '{direction}'. "
        "Previously fell through to 'Too cold = bear' branch."
    )


def test_nfp_strong_beat_is_bearish():
    """NFP > +10% deviation (too hot) must be bearish (Fed tightening risk)."""
    from surprise_detector import _classify_direction
    direction = _classify_direction("Nonfarm Payrolls", deviation=0.15)
    assert direction == "bear", (
        f"NFP +15% (too hot) must be 'bear'. Got '{direction}'"
    )


def test_nfp_cold_miss_is_bearish():
    """NFP < -10% deviation (too cold) must be bearish (recession fear)."""
    from surprise_detector import _classify_direction
    direction = _classify_direction("Nonfarm Payrolls", deviation=-0.15)
    assert direction == "bear", (
        f"NFP -15% (too cold) must be 'bear'. Got '{direction}'"
    )


def test_nfp_goldilocks_is_bullish():
    """NFP |deviation| < 5% (inline) must be bullish.

    Also check the mild-miss band -10% <= dev < -5% returns bull.
    """
    from surprise_detector import _classify_direction
    assert _classify_direction("Nonfarm Payrolls", deviation=0.02) == "bull"
    assert _classify_direction("Nonfarm Payrolls", deviation=-0.07) == "bull", (
        "NFP -7% (mild miss, Fed less hawkish) must be 'bull'"
    )


# ═════════════════════════════════════════════════════════════════════════════
# T1-11 — flow_agent ET timezone
# ═════════════════════════════════════════════════════════════════════════════

def test_flow_agent_uses_et_date_not_utc():
    """flow_agent must source the 0DTE expiration from America/New_York."""
    path = os.path.join(AGENTS, "flow_agent.py")
    with open(path, encoding="utf-8") as f:
        src = f.read()

    # The _fetch_polygon_put_call function body must reference the ET
    # timezone for building `today`. Check the specific function to
    # avoid matching a stray comment elsewhere in the file.
    func_start = src.find("def _fetch_polygon_put_call")
    assert func_start > -1, "_fetch_polygon_put_call must exist"
    func_end = src.find("\ndef ", func_start + 1)
    func_body = src[func_start:func_end]

    assert "America/New_York" in func_body, (
        "flow_agent._fetch_polygon_put_call must use America/New_York "
        "timezone when computing the expiration-date query param"
    )
    assert "ZoneInfo" in func_body, (
        "flow_agent._fetch_polygon_put_call must use ZoneInfo, not a bare "
        "date.today() (server UTC) for the 0DTE expiration date"
    )
    # The bare date.today() usage that caused T1-11 must no longer be
    # the source of `today` in this function.
    assert "date.today().isoformat()" not in func_body, (
        "flow_agent must not derive the 0DTE expiration from a bare "
        "date.today() — that is server-UTC and rolls forward after 8 PM ET"
    )


# ═════════════════════════════════════════════════════════════════════════════
# T2-1 — compute_directional_accuracy uses outcome_correct
# ═════════════════════════════════════════════════════════════════════════════

def test_directional_accuracy_uses_outcome_correct():
    """compute_directional_accuracy must query outcome_correct, not net_pnl."""
    path = os.path.join(BACKEND, "model_retraining.py")
    with open(path, encoding="utf-8") as f:
        src = f.read()

    func_start = src.find("def compute_directional_accuracy")
    assert func_start > -1
    func_end = src.find("\ndef ", func_start + 1)
    func_body = src[func_start:func_end]

    assert "outcome_correct" in func_body, (
        "compute_directional_accuracy must query the outcome_correct "
        "column on trading_prediction_outputs"
    )
    # The old win-rate proxy referenced trading_positions and net_pnl.
    # Both must disappear from this function's body.
    assert "trading_positions" not in func_body, (
        "compute_directional_accuracy must not query trading_positions "
        "any more — direction accuracy is a prediction-level metric"
    )
    assert "net_pnl" not in func_body, (
        "compute_directional_accuracy must not reference net_pnl — "
        "that was the P&L-win-rate proxy, not direction accuracy"
    )


def test_directional_accuracy_result_has_method_field():
    """Result dict must advertise the 'outcome_correct' method explicitly.

    Downstream consumers (drift detection, challenger) can now tell at
    a glance which algorithm produced the accuracy number — the old
    win-rate proxy never labeled itself.
    """
    with patch("model_retraining.get_client") as mock_client:
        mock_result = MagicMock()
        mock_result.data = []
        # Mirror the real Supabase call chain:
        #   .table(...).select(...).gte(...).eq(...).not_.is_(...).execute()
        chain = MagicMock()
        chain.execute.return_value = mock_result
        mock_client.return_value.table.return_value \
            .select.return_value \
            .gte.return_value \
            .eq.return_value \
            .not_.is_.return_value = chain

        from model_retraining import compute_directional_accuracy
        result = compute_directional_accuracy(days=7)

    assert "method" in result, "result must include a 'method' field"
    assert result["method"] == "outcome_correct", (
        f"method must be 'outcome_correct', got {result['method']}"
    )
    assert result["sufficient_data"] is False, (
        "empty rows must yield sufficient_data=False"
    )


def test_directional_accuracy_math_with_mixed_outcomes():
    """Accuracy must equal correct/total from outcome_correct values.

    Regression guard against any future regression that re-introduces
    a P&L proxy — if the math is ever computed off something other
    than outcome_correct, this assertion will break.
    """
    rows = [
        {"outcome_correct": True},
        {"outcome_correct": True},
        {"outcome_correct": True},
        {"outcome_correct": False},
        {"outcome_correct": False},
        {"outcome_correct": True},
        {"outcome_correct": True},
    ]  # 5 of 7 correct = 0.7143

    with patch("model_retraining.get_client") as mock_client:
        mock_result = MagicMock()
        mock_result.data = rows
        chain = MagicMock()
        chain.execute.return_value = mock_result
        mock_client.return_value.table.return_value \
            .select.return_value \
            .gte.return_value \
            .eq.return_value \
            .not_.is_.return_value = chain

        from model_retraining import compute_directional_accuracy
        result = compute_directional_accuracy(days=7)

    assert result["sufficient_data"] is True
    assert result["observations"] == 7
    assert result["correct"] == 5
    assert result["accuracy"] == round(5 / 7, 4), (
        f"accuracy must equal correct/total (5/7), got {result['accuracy']}"
    )
    assert result["method"] == "outcome_correct"


# ═════════════════════════════════════════════════════════════════════════════
# T2-2 — label_prediction_outcomes ET boundaries
# ═════════════════════════════════════════════════════════════════════════════

def test_label_outcomes_uses_et_boundaries():
    """label_prediction_outcomes must use ET session boundaries."""
    path = os.path.join(BACKEND, "model_retraining.py")
    with open(path, encoding="utf-8") as f:
        src = f.read()

    func_start = src.find("def label_prediction_outcomes")
    assert func_start > -1
    func_end = src.find("\ndef ", func_start + 1)
    func_body = src[func_start:func_end]

    assert "America/New_York" in func_body, (
        "label_prediction_outcomes must use America/New_York for the "
        "session-window boundaries"
    )
    # The critical negative assertion: the old UTC-midnight literal
    # must not appear anywhere in this function body.
    assert "T00:00:00+00:00" not in func_body, (
        "label_prediction_outcomes must not use a UTC-midnight "
        "day_start string. Use ET 04:00 AM / 20:00 PM datetime objects"
    )
    assert "T23:59:59+00:00" not in func_body, (
        "label_prediction_outcomes must not use a UTC day_end string"
    )


# ═════════════════════════════════════════════════════════════════════════════
# T2-4 — RTH gate in run_cycle
# ═════════════════════════════════════════════════════════════════════════════

def test_run_cycle_skips_before_market_open():
    """run_cycle must return None when market is closed."""
    from prediction_engine import PredictionEngine

    engine = PredictionEngine.__new__(PredictionEngine)
    engine.redis_client = MagicMock()
    engine.redis_client.ping.return_value = True
    engine._cycle_count = 0
    engine._write_heartbeat = MagicMock()

    # T2-4 patches market_calendar.is_market_open directly because the
    # import inside run_cycle is method-local (critical rule #2).
    with patch("market_calendar.is_market_open", return_value=False):
        result = engine.run_cycle()

    assert result is None, (
        "run_cycle must return None when market is closed — pre-market "
        "cycles pollute outcome labeling and drift detection"
    )
    # Heartbeat must still fire so the health dashboard does not flag
    # the engine as silently stale during pre-market hours.
    assert engine._write_heartbeat.call_count >= 1, (
        "run_cycle must still write a heartbeat on the market-closed "
        "skip path"
    )


def test_run_cycle_rth_gate_grep():
    """Source-grep guard: prediction_engine.run_cycle calls is_market_open."""
    path = os.path.join(BACKEND, "prediction_engine.py")
    with open(path, encoding="utf-8") as f:
        src = f.read()
    assert "is_market_open" in src, (
        "prediction_engine.run_cycle must call is_market_open() to gate "
        "the 9:00-9:25 ET pre-RTH cron fires"
    )
    assert "prediction_cycle_skipped_market_closed" in src, (
        "the RTH-skip path must log a structured event so operators "
        "can observe the gate firing in Railway"
    )
    # The import must be inside a try/except — otherwise a broken
    # calendar import silently halts trading during a real session.
    rth_block_start = src.find("prediction_cycle_skipped_market_closed")
    # look back 500 chars for the `try:`
    before = src[max(0, rth_block_start - 800): rth_block_start]
    assert "try:" in before, (
        "is_market_open() call must be wrapped in try/except that "
        "fails open — otherwise a broken calendar module stops trading"
    )


# ═════════════════════════════════════════════════════════════════════════════
# T2-5 — minor catalyst regime override
# ═════════════════════════════════════════════════════════════════════════════

def test_minor_catalyst_triggers_event_regime():
    """has_minor_catalyst must produce event regime with RCS > major's 55."""
    from prediction_engine import PredictionEngine

    engine = PredictionEngine.__new__(PredictionEngine)

    intel = {
        "has_major_catalyst": False,
        "has_major_earnings": False,
        "has_minor_catalyst": True,
        "day_classification": "catalyst_minor",
    }

    def mock_read(key, default=None):
        if key == "calendar:today:intel":
            return json.dumps(intel)
        return default

    engine._read_redis = mock_read
    engine.redis_client = MagicMock()

    result = engine._compute_regime()

    assert result["regime"] == "event", (
        f"minor catalyst day must return event regime, got: {result['regime']}"
    )
    assert result["rcs"] > 55.0, (
        f"minor catalyst RCS must be > 55 (softer than major). "
        f"Got: {result['rcs']}"
    )
    assert result["allocation_tier"] == "low", (
        f"minor catalyst must use tier='low' (not 'moderate' like major). "
        f"Got: {result['allocation_tier']}"
    )
    # Downstream strategy_selector inspects regime_agreement — the
    # minor override must mark both layers as agreeing so no D-021
    # disagreement penalty kicks in.
    assert result["regime_agreement"] is True


def test_major_catalyst_rcs_lower_than_minor():
    """Major catalyst is more restrictive → lower RCS than minor."""
    from prediction_engine import PredictionEngine

    engine = PredictionEngine.__new__(PredictionEngine)
    engine.redis_client = MagicMock()

    def make_reader(intel: dict):
        def _read(key, default=None):
            if key == "calendar:today:intel":
                return json.dumps(intel)
            return default
        return _read

    engine._read_redis = make_reader({
        "has_major_catalyst": True,
        "has_major_earnings": False,
        "has_minor_catalyst": False,
        "day_classification": "catalyst_major",
    })
    major = engine._compute_regime()

    engine._read_redis = make_reader({
        "has_major_catalyst": False,
        "has_major_earnings": False,
        "has_minor_catalyst": True,
        "day_classification": "catalyst_minor",
    })
    minor = engine._compute_regime()

    assert major["rcs"] < minor["rcs"], (
        f"major RCS ({major['rcs']}) must be lower than minor "
        f"({minor['rcs']}) — major is the more restrictive case"
    )
    # Regression guard: neither branch may quietly downgrade to a
    # non-event regime. strategy_selector relies on regime=='event'
    # to route to long_straddle / calendar_spread on these days.
    assert major["regime"] == "event"
    assert minor["regime"] == "event"
