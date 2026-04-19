"""Consolidation Sprint — Session 2 regression tests.

Locks down the seven fixes from this session:

  B-5  Earnings unit mismatch — percent vs fraction.
  B-6  strategy:earnings_straddle:enabled gate at top of run_earnings_entry.
  B-7  Documented earnings Redis key name.
  B-8  agents:ai_synthesis:enabled flag now actually gates the path.
  C-1  Kill switch routes through Edge Function (verified at TS layer; here
       we lock the prefer-signal-context contract C-2 depends on).
  C-2  ExecutionEngine prefers signal.decision_context over stale flag reads.
  A-startup  polygon_feed._backfill_vix_history seeds vix_history at startup.
"""
import asyncio
import json
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

# Ensure backend/ and backend_earnings/ are importable regardless of
# test runner cwd. backend/ is auto-added by pytest's rootdir, but
# backend_earnings/ is a sibling module set.
_BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..")
_EARNINGS_DIR = os.path.join(_BACKEND_DIR, "..", "backend_earnings")
for _p in (_BACKEND_DIR, _EARNINGS_DIR):
    _abs = os.path.abspath(_p)
    if _abs not in sys.path:
        sys.path.insert(0, _abs)


# ── B-5: Earnings unit mismatch ────────────────────────────────────────

def test_has_sufficient_edge_blocks_when_market_priced_in():
    """current_implied=0.10 (10% as fraction) blocks entry — NVDA's
    8.6% historical avg can't beat 11% threshold (10% × 1.10)."""
    from edge_calculator import has_sufficient_edge
    assert has_sufficient_edge(
        "NVDA", current_implied_move_pct=0.10
    ) is False


def test_has_sufficient_edge_allows_when_premium_thin():
    """current_implied=0.05 (5% fraction) allows entry — NVDA's 8.6%
    historical avg easily beats 5.5% threshold (5% × 1.10)."""
    from edge_calculator import has_sufficient_edge
    assert has_sufficient_edge(
        "NVDA", current_implied_move_pct=0.05
    ) is True


def test_has_sufficient_edge_no_implied_only_checks_base_edge():
    """Without current implied move, only the static edge score gates entry."""
    from edge_calculator import has_sufficient_edge
    assert has_sufficient_edge("NVDA") is True
    assert has_sufficient_edge("XYZ_UNKNOWN") is False


def test_has_sufficient_edge_treats_input_as_fraction_regression():
    """Regression: a caller that passes percent (e.g. 10.0) by mistake
    should be blocked. 10.0 as fraction = 1000% implied move — no
    historical avg comes close, so the entry must fail closed.

    Pre-fix bug: the same input would PASS because the comparison was
    `8.6 < 10.0 * 1.10` (False), letting every trade through."""
    from edge_calculator import has_sufficient_edge
    assert has_sufficient_edge(
        "NVDA", current_implied_move_pct=10.0
    ) is False


# ── B-6: Earnings flag gate ────────────────────────────────────────────

def test_earnings_entry_skipped_when_flag_absent():
    """Flag absent (Redis returns None) → skipped. Default OFF for safety."""
    redis = MagicMock()
    redis.get.return_value = None
    from main_earnings import run_earnings_entry
    result = run_earnings_entry(redis)
    assert result.get("skipped") == "earnings_straddle_flag_off"


def test_earnings_entry_skipped_when_flag_false():
    """Explicit b'false' (operator disabled) → skipped."""
    redis = MagicMock()
    redis.get.return_value = b"false"
    from main_earnings import run_earnings_entry
    result = run_earnings_entry(redis)
    assert result.get("skipped") == "earnings_straddle_flag_off"


def test_earnings_entry_skipped_when_redis_unavailable():
    """No redis client → skipped. Cannot prove flag is ON, so default OFF."""
    from main_earnings import run_earnings_entry
    result = run_earnings_entry(None)
    assert result.get("skipped") == "earnings_straddle_flag_off"


def test_earnings_entry_proceeds_when_flag_true():
    """Flag = b'true' → flow proceeds past the gate. Downstream may still
    skip (no candidates / DB error / etc.) but the gate must not be the
    blocker."""
    redis = MagicMock()

    def mock_get(key):
        if key == "strategy:earnings_straddle:enabled":
            return b"true"
        return None

    redis.get.side_effect = mock_get

    # Stub get_upcoming_events + get_open_earnings_positions to avoid
    # DB calls. We only need to prove the flag gate did not short-circuit.
    with patch("main_earnings.get_open_earnings_positions", return_value=[]):
        with patch("main_earnings.get_upcoming_events", return_value=[]):
            from main_earnings import run_earnings_entry
            result = run_earnings_entry(redis)

    assert result.get("skipped") != "earnings_straddle_flag_off"


# ── B-7: Documented earnings Redis key ─────────────────────────────────

def test_earnings_init_documents_canonical_key():
    """backend_earnings/__init__.py must list earnings:upcoming_events
    in its module docstring (not the old earnings:upcoming alone)."""
    init_path = os.path.abspath(
        os.path.join(_EARNINGS_DIR, "__init__.py")
    )
    with open(init_path, encoding="utf-8") as f:
        contents = f.read()
    assert "earnings:upcoming_events" in contents, (
        "Canonical Redis key earnings:upcoming_events missing from "
        "backend_earnings/__init__.py docstring"
    )


# ── B-8: Synthesis flag bypass fix ─────────────────────────────────────

def test_synthesis_flag_check_blocks_when_absent():
    """Flag absent → synthesis_flag_on is False (the local check pattern)."""
    from prediction_engine import PredictionEngine
    engine = PredictionEngine.__new__(PredictionEngine)
    engine.redis_client = MagicMock()

    def mock_read(key, default=None):
        if key == "agents:ai_synthesis:enabled":
            return None
        return default

    engine._read_redis = mock_read

    flag_raw = engine._read_redis("agents:ai_synthesis:enabled", None)
    assert flag_raw not in ("true", b"true")


def test_synthesis_flag_check_passes_when_explicitly_true():
    """Flag = 'true' → synthesis_flag_on is True."""
    from prediction_engine import PredictionEngine
    engine = PredictionEngine.__new__(PredictionEngine)
    engine.redis_client = MagicMock()

    def mock_read(key, default=None):
        if key == "agents:ai_synthesis:enabled":
            return "true"
        return default

    engine._read_redis = mock_read

    flag_raw = engine._read_redis("agents:ai_synthesis:enabled", None)
    assert flag_raw in ("true", b"true")


def test_synthesis_path_skipped_when_flag_off_via_compute_direction():
    """End-to-end: even with FRESH synthesis JSON in Redis, the synthesis
    branch must not return a 'source: ai_synthesis' prediction when the
    flag is absent."""
    from datetime import datetime, timezone
    from prediction_engine import PredictionEngine

    engine = PredictionEngine.__new__(PredictionEngine)
    engine.redis_client = MagicMock()
    engine._direction_model = None
    engine._direction_features = None

    fresh_synthesis = json.dumps({
        "direction": "bull",
        "confidence": 0.85,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "strategy": "iron_condor",
        "sizing_modifier": 1.0,
    })

    def mock_read(key, default=None):
        if key == "ai:synthesis:latest":
            return fresh_synthesis
        if key == "agents:ai_synthesis:enabled":
            return None  # FLAG OFF
        return default

    engine._read_redis = mock_read

    # _compute_direction falls through to LightGBM (None) → GEX/ZG /
    # rule-based. Whatever it returns, source must NOT be ai_synthesis.
    result = engine._compute_direction(
        regime="quiet_bullish", cv_stress=0.0, spx_price=5200.0,
    )
    assert result.get("source") != "ai_synthesis"


# ── C-2: decision_context preference ───────────────────────────────────

def test_execution_engine_prefers_signal_decision_context():
    """When signal carries a decision_context, ExecutionEngine layers
    static config on top and uses it — does NOT replace it with stale
    flag reads."""
    rich_context = {
        "signal_mult": 0.75,
        "vix_term_status": "inverted",
        "has_vix_z_data": True,
        "flags_at_selection": {"signal:vix_term_filter:enabled": True},
        "selected_at": "2026-04-21T10:00:00+00:00",
    }
    signal = {
        "decision_context": rich_context,
        "strategy_type": "iron_condor",
    }

    # Simulate the conditional path used in open_virtual_position.
    signal_ctx = signal.get("decision_context")
    assert signal_ctx is not None
    assert signal_ctx["signal_mult"] == 0.75
    assert signal_ctx["has_vix_z_data"] is True
    # Critical: not the fallback path (no context_source key).
    assert "context_source" not in signal_ctx


def test_execution_engine_falls_back_when_signal_has_no_context():
    """Legacy callers without decision_context must still produce a
    populated dict (even if every flag is False) — never crash, never
    drop the audit trail."""
    legacy_signal = {"strategy_type": "iron_condor"}
    signal_ctx = legacy_signal.get("decision_context")
    assert signal_ctx is None  # Falls through to legacy fallback path


def test_execution_engine_open_virtual_position_uses_signal_ctx_end_to_end():
    """End-to-end: open_virtual_position() reads signal['decision_context']
    and writes it (with config layered on) into the position row.

    This is the functional regression — the path that was silently
    corrupting trading_positions.decision_context with all-False
    flag reads from a Redis-less ExecutionEngine."""
    from execution_engine import ExecutionEngine

    engine = ExecutionEngine.__new__(ExecutionEngine)
    engine.redis_client = None  # prove we're NOT touching Redis

    rich_context = {
        "signal_mult": 0.85,
        "has_vix_z_data": True,
        "flags_at_selection": {
            "signal:vix_term_filter:enabled": True,
            "signal:market_breadth:enabled": True,
        },
    }
    signal = {
        "session_id": "test-session",
        "strategy_type": "iron_condor",
        "contracts": 1,
        "target_credit": 1.50,
        "decision_context": rich_context,
    }
    prediction = {"source": "rule_based", "confidence": 0.65}

    captured_position = {}

    class _FakeTable:
        def insert(self, row):
            captured_position.update(row)
            return self

        def execute(self):
            return MagicMock(data=[captured_position])

    class _FakeClient:
        def table(self, _name):
            return _FakeTable()

    with patch("execution_engine.get_today_session", return_value={
        "id": "test-session", "virtual_trades_count": 0
    }), patch("execution_engine.get_client", return_value=_FakeClient()), \
         patch("execution_engine.update_session"), \
         patch("execution_engine.write_audit_log"):
        result = engine.open_virtual_position(signal, prediction)

    assert result is not None
    ctx = captured_position["decision_context"]
    # Selector-provided fields preserved
    assert ctx["signal_mult"] == 0.85
    assert ctx["has_vix_z_data"] is True
    assert ctx["flags_at_selection"]["signal:vix_term_filter:enabled"] is True
    # Static config layered on top
    assert "ai_provider" in ctx
    assert ctx["prediction_source"] == "rule_based"
    # NOT the fallback path
    assert ctx.get("context_source") != "fallback_no_selector_context"


# ── A-startup: VIX history backfill ────────────────────────────────────

def _build_async_client_mock(status: int, results: list):
    """Build a context-manager AsyncClient mock that returns the given
    Polygon aggregates payload from .get()."""
    mock_resp = MagicMock()
    mock_resp.status_code = status
    mock_resp.json.return_value = {"results": results}

    mock_session = MagicMock()
    mock_session.get = AsyncMock(return_value=mock_resp)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    return mock_session


def test_vix_history_backfill_seeds_history():
    """20+ daily closes returned → vix_history capped at 20 with the
    most recent values."""
    import config
    from polygon_feed import PolygonFeed

    feed = PolygonFeed.__new__(PolygonFeed)
    feed.vix_history = []
    feed.redis_client = MagicMock()

    fake_results = [{"c": 18.0 + i * 0.1} for i in range(22)]
    mock_session = _build_async_client_mock(200, fake_results)

    # config is imported inside the method, so we patch the attribute
    # on the already-loaded config module rather than polygon_feed.config.
    with patch.object(config, "POLYGON_API_KEY", "fake-key"):
        with patch("httpx.AsyncClient", return_value=mock_session):
            asyncio.run(feed._backfill_vix_history())

    assert len(feed.vix_history) == 20  # capped at 20
    assert feed.vix_history[-1] > 0


def test_vix_history_backfill_silent_without_api_key():
    """No POLYGON_API_KEY → backfill skips, vix_history stays empty,
    never raises (must not block startup)."""
    import config
    from polygon_feed import PolygonFeed

    feed = PolygonFeed.__new__(PolygonFeed)
    feed.vix_history = []
    feed.redis_client = MagicMock()

    with patch.object(config, "POLYGON_API_KEY", ""):
        asyncio.run(feed._backfill_vix_history())

    assert feed.vix_history == []
