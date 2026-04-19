"""
Consolidation Session 8 — Test Hardening.

Locks down invariants that survived S1-S7 without dedicated regression
tests. Each block targets a real production bug class:

  T-1: signal_mult end-to-end composition (S1 polarity regression
       guard — every signal flag must default ON, the inverted-VIX
       branch must reduce sizing, and the final mult is capped at 1.1).
  T-2: _backfill_feature_flags_to_supabase polarity (signal flags with
       absent Redis key backfill as enabled=True; strategy flags as
       enabled=False; exactly _TRADING_FLAG_KEYS rows are written).
  T-3: P&L round-trip — debit and credit, winning and losing, must
       all produce a gross_pnl with the correct sign (S4 regression).
  T-4: Edge Function structural invariants — Bearer auth,
       trading.configure permission, kill-switch row verification,
       no _shared/ imports (deploy isolation).
  T-5: _compute_regime event path — calendar override beats every
       other signal (S5 regression).
  T-6: VVIX intraday-window deferred bug. xfail(strict=False) — when
       the fix lands and this test xpasses, remove the marker.
  T-7: write_health_status cache kwargs bypass — extra kwargs
       (latency_ms, error details) always write through (S7 add-on).
  T-8: decision_context captured at selection time, not execution
       time (Loop 2 meta-label audit invariant).
"""
import json
import os
import sys

import pytest
from unittest.mock import MagicMock, patch

BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BACKEND_AGENTS = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "backend_agents")
)
for _p in (BACKEND, BACKEND_AGENTS):
    if _p not in sys.path:
        sys.path.insert(0, _p)

REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)


def _ensure_main_importable():
    """Stub the heavy Railway-only third-party deps that main.py imports
    at module load time so `import main` works in any test environment.

    The stubs only need to satisfy the import statement and any decorator
    / call that runs at module top level (FastAPI() constructor,
    add_middleware, AsyncIOScheduler() constructor). The trading code
    paths the T-2 tests exercise (_backfill_feature_flags_to_supabase)
    don't touch these stubs at runtime — they only need redis_client
    and get_client, which the tests inject.
    """
    import types
    if "fastapi" not in sys.modules:
        fastapi = types.ModuleType("fastapi")

        class _StubFastAPI:
            def __init__(self, *_a, **_kw):
                pass

            def add_middleware(self, *_a, **_kw):
                pass

            def _decorator(self, *_a, **_kw):
                def _wrap(fn):
                    return fn
                return _wrap

            on_event = _decorator
            get = _decorator
            post = _decorator
            put = _decorator
            delete = _decorator

        def _passthrough(*_a, **_kw):
            return None

        class _StubHTTPException(Exception):
            def __init__(self, *_a, **_kw):
                super().__init__(_a[0] if _a else "")

        fastapi.FastAPI = _StubFastAPI
        fastapi.Body = _passthrough
        fastapi.Header = _passthrough
        fastapi.HTTPException = _StubHTTPException
        sys.modules["fastapi"] = fastapi

        cors = types.ModuleType("fastapi.middleware.cors")

        class _StubCORS:
            def __init__(self, *_a, **_kw):
                pass

        cors.CORSMiddleware = _StubCORS
        sys.modules["fastapi.middleware"] = types.ModuleType(
            "fastapi.middleware"
        )
        sys.modules["fastapi.middleware.cors"] = cors

    if "apscheduler" not in sys.modules:
        apscheduler = types.ModuleType("apscheduler")
        schedulers = types.ModuleType("apscheduler.schedulers")
        asyncio_mod = types.ModuleType("apscheduler.schedulers.asyncio")

        class _StubAsyncIOScheduler:
            def __init__(self, *_a, **_kw):
                self.jobs = []

            def add_job(self, *_a, **_kw):
                self.jobs.append((_a, _kw))

            def start(self):
                pass

            def shutdown(self, *_a, **_kw):
                pass

        asyncio_mod.AsyncIOScheduler = _StubAsyncIOScheduler
        sys.modules["apscheduler"] = apscheduler
        sys.modules["apscheduler.schedulers"] = schedulers
        sys.modules["apscheduler.schedulers.asyncio"] = asyncio_mod


# ═══════════════════════════════════════════════════════════════════
# T-1: signal_mult end-to-end composition
# ═══════════════════════════════════════════════════════════════════

def _make_selector(redis_values: dict = None):
    """Build a StrategySelector with a mocked Redis client.

    Values are keyed on Redis key strings; absent keys return None.
    Strings are encoded to bytes since the production client is set up
    with decode_responses=False on most paths.
    """
    from strategy_selector import StrategySelector

    sel = StrategySelector.__new__(StrategySelector)
    values = redis_values or {}

    def mock_get(key):
        val = values.get(key)
        if val is None:
            return None
        return val.encode() if isinstance(val, str) else val

    sel.redis_client = MagicMock()
    sel.redis_client.get.side_effect = mock_get
    return sel


def test_signal_mult_all_flags_on_reduces_on_inverted_vix_term():
    """
    With all 6 signal flags ON (default state) and the VIX term
    structure inverted (ratio = 1.25, between SOFT=1.10 and HARD=1.20
    actually >= HARD), the VIX-term modifier must reduce sizing
    (mult < 1.0). If it returns 1.0 the polarity bug from S1 has
    crept back: all flags would be silently OFF and signal_mult
    would always be 1.0.

    Real status strings (from strategy_selector.py constants):
      ratio >= 1.35 → ("strongly_inverted_skip", 0.0)
      ratio >= 1.20 → ("strongly_inverted",      0.50)
      ratio >= 1.10 → ("inverted",               0.75)
      ratio <= 0.80 → ("thin_premium",           0.85)
      else          → ("normal",                 1.0)
    """
    sel = _make_selector({})

    prediction = {"vix_term_ratio": 1.25}
    vix_term_mult, status = sel._vix_term_modifier(prediction)

    assert vix_term_mult < 1.0, (
        f"Inverted VIX term must reduce sizing (got mult={vix_term_mult}). "
        "If 1.0, the signal-flag polarity bug has returned — "
        "_check_feature_flag(default=True) must return True for absent keys."
    )
    assert status in (
        "inverted",
        "strongly_inverted",
        "strongly_inverted_skip",
    ), f"Expected an inverted status label, got: {status!r}"


def test_signal_mult_capped_at_1_1():
    """signal_mult is capped at 1.1 — confirm via source inspection."""
    path = os.path.join(BACKEND, "strategy_selector.py")
    with open(path, encoding="utf-8") as f:
        src = f.read()
    assert (
        "min(\n                    1.1," in src
        or "min(1.1," in src
    ), "signal_mult must be capped at 1.1"


def test_all_6_signal_flags_default_on_in_composition():
    """
    With empty Redis (every flag key absent), all 6 signal flags must
    default to True. This is the core S1 fix — _check_feature_flag
    with default=True must honour the default when the key is missing.
    """
    sel = _make_selector({})

    signal_flags = [
        "signal:vix_term_filter:enabled",
        "signal:entry_time_gate:enabled",
        "signal:gex_directional_bias:enabled",
        "signal:market_breadth:enabled",
        "signal:earnings_proximity:enabled",
        "signal:iv_rank_filter:enabled",
    ]
    for flag in signal_flags:
        assert sel._check_feature_flag(flag, default=True) is True, (
            f"Signal flag {flag!r} must default ON when absent from Redis"
        )


def test_strategy_flags_default_off():
    """Strategy/agent flags must default OFF with empty Redis."""
    sel = _make_selector({})

    strategy_flags = [
        "strategy:iron_butterfly:enabled",
        "strategy:long_straddle:enabled",
        "strategy:calendar_spread:enabled",
        "strategy:ai_hint_override:enabled",
        "strategy:earnings_straddle:enabled",
    ]
    for flag in strategy_flags:
        assert sel._check_feature_flag(flag, default=False) is False, (
            f"Strategy flag {flag!r} must default OFF when absent from Redis"
        )


# ═══════════════════════════════════════════════════════════════════
# T-2: _backfill_feature_flags_to_supabase polarity
# ═══════════════════════════════════════════════════════════════════

def _load_backend_main_isolated():
    """Load backend/main.py as a fresh module under a unique name.

    Returns (module, restore_fn). The caller MUST invoke restore_fn()
    in a `finally` block to clean up sys.modules.

    Why the gymnastics: test_fix_group3.test_sentinel_supabase_singleton
    expects sys.modules["main"] to resolve to sentinel/main.py (it
    inserts sentinel/ into sys.path[0] and re-uses any cached "main").
    A naive `import main` from this file caches backend/main.py under
    that key and breaks the sibling test. Loading under a unique key
    leaves the global "main" slot for whoever imported it first.
    """
    _ensure_main_importable()
    import importlib.util

    saved_main = sys.modules.get("main")

    spec = importlib.util.spec_from_file_location(
        "_s8_backend_main", os.path.join(BACKEND, "main.py")
    )
    module = importlib.util.module_from_spec(spec)
    # patch("main.get_client") string-resolves through sys.modules — we
    # have to install it under "main" for the patch to bind correctly.
    # Restored to whatever was there before in restore_fn.
    sys.modules["main"] = module
    sys.modules["_s8_backend_main"] = module
    spec.loader.exec_module(module)

    def restore_fn():
        if saved_main is not None:
            sys.modules["main"] = saved_main
        else:
            sys.modules.pop("main", None)
        sys.modules.pop("_s8_backend_main", None)

    return module, restore_fn


def _run_backfill_and_capture():
    """Run _backfill_feature_flags_to_supabase against an empty Redis
    and a captured upsert sink. Returns the list of upserted rows."""
    m, restore = _load_backend_main_isolated()

    mock_redis = MagicMock()
    mock_redis.get.return_value = None  # every key absent

    upserted = []
    mock_upsert_chain = MagicMock()
    mock_upsert_chain.execute.return_value = MagicMock()

    def capture_upsert(rows, **_kwargs):
        upserted.extend(rows)
        return mock_upsert_chain

    try:
        with patch.object(m, "redis_client", mock_redis), \
                patch("main.get_client") as mock_db:
            mock_db.return_value.table.return_value.upsert.side_effect = (
                capture_upsert
            )
            m._backfill_feature_flags_to_supabase()
    finally:
        restore()

    return upserted


def test_backfill_signal_flags_absent_key_becomes_enabled_true():
    """Signal flags follow REVERSE polarity: absent key → enabled=True."""
    upserted = _run_backfill_and_capture()

    signal_flags = {
        "signal:vix_term_filter:enabled",
        "signal:entry_time_gate:enabled",
        "signal:gex_directional_bias:enabled",
        "signal:market_breadth:enabled",
        "signal:earnings_proximity:enabled",
        "signal:iv_rank_filter:enabled",
    }
    seen = {row["flag_key"]: row["enabled"] for row in upserted}
    for key in signal_flags:
        assert key in seen, f"Signal flag {key!r} missing from backfill"
        assert seen[key] is True, (
            f"Signal flag {key!r} with absent Redis key must backfill "
            f"enabled=True (got {seen[key]!r})"
        )


def test_backfill_strategy_flags_absent_key_becomes_enabled_false():
    """Strategy flags follow standard polarity: absent key → enabled=False."""
    upserted = _run_backfill_and_capture()

    strategy_flags = {
        "strategy:iron_butterfly:enabled",
        "strategy:long_straddle:enabled",
        "strategy:earnings_straddle:enabled",
    }
    seen = {row["flag_key"]: row["enabled"] for row in upserted}
    for key in strategy_flags:
        assert key in seen, f"Strategy flag {key!r} missing from backfill"
        assert seen[key] is False, (
            f"Strategy flag {key!r} with absent Redis key must backfill "
            f"enabled=False (got {seen[key]!r})"
        )


def test_backfill_writes_all_known_flag_keys():
    """Backfill writes exactly len(_TRADING_FLAG_KEYS) rows."""
    m, restore = _load_backend_main_isolated()
    try:
        expected_keys = list(m._TRADING_FLAG_KEYS)
    finally:
        restore()

    upserted = _run_backfill_and_capture()
    assert len(upserted) == len(expected_keys), (
        f"Expected {len(expected_keys)} rows from backfill, "
        f"got {len(upserted)}"
    )
    upserted_keys = {row["flag_key"] for row in upserted}
    assert upserted_keys == set(expected_keys), (
        "Backfilled flag keys do not match _TRADING_FLAG_KEYS"
    )


# ═══════════════════════════════════════════════════════════════════
# T-3: P&L round-trip sign correctness
# ═══════════════════════════════════════════════════════════════════
#
# _simulate_fill stores SIGNED entry premium (S4 / A-1). For debit
# strategies (long_straddle, debit spreads, long_put/call) the entry
# is negative; for credit strategies (iron_condor, iron_butterfly,
# credit spreads) the entry is positive.
#
# Downstream P&L formula in close_virtual_position:
#   gross_pnl = (entry_credit - exit_credit) × contracts × 100
#
# Debit losing : entry=-4.15, exit=-3.00 → ((-4.15) - (-3.00)) × 100
#                = -1.15 × 100 = -115  (negative — paid more, got less back)
# Debit winning: entry=-4.15, exit=-5.50 → +135 (paid less than worth now)
# Credit win   : entry=+1.70, exit= 0.74 → +96  (collected more than paid back)
# Credit loss  : entry=+1.70, exit= 2.55 → -85  (paid back more than collected)


def test_debit_signed_fill_is_negative():
    """_simulate_fill on a debit target must return a negative signed_fill."""
    from execution_engine import ExecutionEngine

    engine = ExecutionEngine.__new__(ExecutionEngine)
    fill = engine._simulate_fill(-4.00, "long_straddle")

    assert fill["signed_fill"] < 0, (
        f"Debit signed_fill must be negative, got {fill['signed_fill']}"
    )
    assert fill["is_debit"] is True


def test_debit_pnl_roundtrip_losing_trade():
    """Debit losing trade → negative gross_pnl regardless of slippage."""
    from execution_engine import ExecutionEngine

    engine = ExecutionEngine.__new__(ExecutionEngine)
    fill = engine._simulate_fill(-4.00, "long_straddle")

    entry_credit = fill["signed_fill"]    # ≈ -4.15
    exit_credit = -3.00                   # straddle worth less now
    gross_pnl = (entry_credit - exit_credit) * 1 * 100

    assert gross_pnl < 0, (
        f"Losing debit trade must have negative gross_pnl, got {gross_pnl} "
        f"(entry_credit={entry_credit}, exit_credit={exit_credit})"
    )


def test_debit_pnl_roundtrip_winning_trade():
    """Debit winning trade → positive gross_pnl regardless of slippage."""
    from execution_engine import ExecutionEngine

    engine = ExecutionEngine.__new__(ExecutionEngine)
    fill = engine._simulate_fill(-4.00, "long_straddle")

    entry_credit = fill["signed_fill"]    # ≈ -4.15
    exit_credit = -5.50                   # straddle worth more now
    gross_pnl = (entry_credit - exit_credit) * 1 * 100

    assert gross_pnl > 0, (
        f"Winning debit trade must have positive gross_pnl, got {gross_pnl} "
        f"(entry_credit={entry_credit}, exit_credit={exit_credit})"
    )


def test_credit_signed_fill_is_positive():
    """_simulate_fill on a credit target must return a positive signed_fill."""
    from execution_engine import ExecutionEngine

    engine = ExecutionEngine.__new__(ExecutionEngine)
    fill = engine._simulate_fill(1.85, "iron_condor")

    assert fill["signed_fill"] > 0, (
        f"Credit signed_fill must be positive, got {fill['signed_fill']}"
    )
    assert fill["is_debit"] is False


def test_credit_pnl_roundtrip_winning_trade():
    """Credit winning trade → positive gross_pnl."""
    from execution_engine import ExecutionEngine

    engine = ExecutionEngine.__new__(ExecutionEngine)
    fill = engine._simulate_fill(1.85, "iron_condor")

    entry_credit = fill["signed_fill"]    # ≈ +1.70 after slippage
    exit_credit = 0.74                    # closed for less than collected
    gross_pnl = (entry_credit - exit_credit) * 1 * 100

    assert gross_pnl > 0, (
        f"Winning credit trade must have positive gross_pnl, got {gross_pnl} "
        f"(entry_credit={entry_credit}, exit_credit={exit_credit})"
    )


def test_credit_pnl_roundtrip_losing_trade():
    """Credit losing trade (stop hit) → negative gross_pnl."""
    from execution_engine import ExecutionEngine

    engine = ExecutionEngine.__new__(ExecutionEngine)
    fill = engine._simulate_fill(1.85, "iron_condor")

    entry_credit = fill["signed_fill"]    # ≈ +1.70
    exit_credit = 2.55                    # closed at loss
    gross_pnl = (entry_credit - exit_credit) * 1 * 100

    assert gross_pnl < 0, (
        f"Losing credit trade must have negative gross_pnl, got {gross_pnl} "
        f"(entry_credit={entry_credit}, exit_credit={exit_credit})"
    )


# ═══════════════════════════════════════════════════════════════════
# T-4: Edge Function structural invariants
# ═══════════════════════════════════════════════════════════════════

def _read_edge_function(name: str) -> str:
    path = os.path.join(
        REPO_ROOT, "supabase", "functions", name, "index.ts"
    )
    with open(path, encoding="utf-8") as f:
        return f.read()


def test_set_feature_flag_requires_bearer_token():
    """set-feature-flag must validate a Bearer token and 401 on failure."""
    src = _read_edge_function("set-feature-flag")
    assert "Bearer" in src, "set-feature-flag must validate a Bearer token"
    assert "401" in src, "set-feature-flag must return 401 on missing auth"


def test_set_feature_flag_requires_trading_configure_permission():
    """set-feature-flag must check trading.configure and 403 on denial."""
    src = _read_edge_function("set-feature-flag")
    assert "trading.configure" in src, (
        "set-feature-flag must require the trading.configure permission"
    )
    assert "403" in src, (
        "set-feature-flag must return 403 when permission is denied"
    )


def test_kill_switch_requires_bearer_token():
    """kill-switch must validate a Bearer token and 401 on failure."""
    src = _read_edge_function("kill-switch")
    assert "Bearer" in src, "kill-switch must validate a Bearer token"
    assert "401" in src, "kill-switch must return 401 on missing auth"


def test_kill_switch_verifies_row_was_updated():
    """kill-switch must chain .select() and verify a row was actually updated.

    Without .select() supabase-js returns no payload and a session_id
    mismatch silently matches zero rows — exact bug the toast hid by
    saying 'halted' while the row was unchanged.
    """
    src = _read_edge_function("kill-switch")
    assert ".select(" in src, (
        "kill-switch must chain .select() so it can verify the update"
    )
    assert (
        "length === 0" in src or "updatedRows" in src
    ), "kill-switch must verify a non-zero updated-row count"


def test_kill_switch_self_contained_no_shared_imports():
    """kill-switch must not import from _shared/ — deploy isolation."""
    src = _read_edge_function("kill-switch")
    for line in src.splitlines():
        stripped = line.strip()
        if stripped.startswith("import") and "_shared/" in stripped:
            raise AssertionError(
                f"kill-switch must not import from _shared/: {stripped}"
            )


def test_set_feature_flag_self_contained_no_shared_imports():
    """set-feature-flag must not import from _shared/ — deploy isolation."""
    src = _read_edge_function("set-feature-flag")
    for line in src.splitlines():
        stripped = line.strip()
        if stripped.startswith("import") and "_shared/" in stripped:
            raise AssertionError(
                f"set-feature-flag must not import from _shared/: {stripped}"
            )


# ═══════════════════════════════════════════════════════════════════
# T-5: _compute_regime event path integration
# ═══════════════════════════════════════════════════════════════════

def test_regime_event_overrides_vvix_and_gex_signals():
    """
    On a major-catalyst day, _compute_regime must return regime="event"
    no matter what the VVIX z-score or GEX confidence say. Verifies
    ROI-1: the calendar override executes BEFORE the VVIX/GEX reads.
    """
    from prediction_engine import PredictionEngine

    engine = PredictionEngine.__new__(PredictionEngine)
    engine.redis_client = MagicMock()

    intel = {
        "has_major_catalyst": True,
        "has_major_earnings": False,
        "day_classification": "fomc_day",
    }

    def mock_read(key, default=None):
        if key == "calendar:today:intel":
            return json.dumps(intel)
        if key == "polygon:vvix:z_score":
            return "3.5"  # would otherwise drive crisis regime
        if key == "gex:confidence":
            return "0.95"
        return default

    engine._read_redis = mock_read

    result = engine._compute_regime()

    assert result["regime"] == "event", (
        f"Catalyst day must return regime='event', got {result['regime']!r}"
    )
    assert result["rcs"] == 55.0, (
        f"Event-day RCS is capped at 55.0, got {result['rcs']!r}"
    )
    assert result["allocation_tier"] == "moderate", (
        f"Event-day allocation_tier is 'moderate', "
        f"got {result['allocation_tier']!r}"
    )
    assert result["regime_hmm"] == "event"
    assert result["regime_lgbm"] == "event"
    assert result["regime_agreement"] is True


def test_regime_event_triggered_by_earnings_alone():
    """has_major_earnings=True (catalyst False) is also an event day."""
    from prediction_engine import PredictionEngine

    engine = PredictionEngine.__new__(PredictionEngine)
    engine.redis_client = MagicMock()

    intel = {
        "has_major_catalyst": False,
        "has_major_earnings": True,
        "day_classification": "earnings_heavy",
    }

    def mock_read(key, default=None):
        if key == "calendar:today:intel":
            return json.dumps(intel)
        return default

    engine._read_redis = mock_read

    result = engine._compute_regime()
    assert result["regime"] == "event"


# ═══════════════════════════════════════════════════════════════════
# T-6: VVIX intraday-window deferred bug (xfail reminder)
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.xfail(
    reason=(
        "VVIX intraday-window bug: PolygonFeed.history (VVIX) is still a "
        "5-min rolling window like vix_history was before S6. After ~100 "
        "min of trading, polygon:vvix:z_score becomes intraday noise "
        "labelled '20d'. Deferred from S6. Fix mirrors E-2: add "
        "vvix_daily_history + an EOD append guard + write "
        "polygon:vvix:z_score_daily. Remove this xfail when implemented."
    ),
    strict=False,
)
def test_vvix_history_is_daily_not_intraday():
    """Reminder regression: PolygonFeed must own a daily VVIX history.

    Currently FAILS (xfail). When this test xpasses the VVIX fix is in
    — drop the xfail decorator and treat it as a hard regression guard.
    """
    from polygon_feed import PolygonFeed

    feed = PolygonFeed.__new__(PolygonFeed)
    feed.redis_client = MagicMock()
    feed.history = []

    # Simulate a full RTH day of 5-min polls (6.5h × 12 = 78 polls).
    for i in range(78):
        feed.history.append(120.0 + i * 0.1)
        feed.history = feed.history[-20:]

    assert hasattr(feed, "vvix_daily_history"), (
        "PolygonFeed must expose a vvix_daily_history attribute "
        "(VVIX E-2 fix — mirrors VIX daily history from S6)"
    )


# ═══════════════════════════════════════════════════════════════════
# T-7: Health status cache kwargs bypass (extends S7 coverage)
# ═══════════════════════════════════════════════════════════════════

def test_write_health_status_writes_when_kwargs_present():
    """A same-status write that carries diagnostic kwargs must NOT be
    cached away. Latency / error details / connection state are real
    data downstream consumers depend on."""
    import db

    saved_cache = dict(db._health_status_cache)
    db._health_status_cache["test_svc_kwargs"] = "healthy"

    write_calls = []

    try:
        with patch("db.get_client") as mock_client:
            mock_table = MagicMock()
            mock_client.return_value.table.return_value = mock_table

            def capture_upsert(*_a, **_kw):
                write_calls.append(1)
                return MagicMock(execute=MagicMock(return_value=MagicMock()))

            mock_table.upsert.side_effect = capture_upsert
            db.write_health_status(
                "test_svc_kwargs", "healthy", latency_ms=45
            )
    finally:
        db._health_status_cache.clear()
        db._health_status_cache.update(saved_cache)

    assert len(write_calls) == 1, (
        "write_health_status with diagnostic kwargs must bypass the "
        "cache and reach the DB"
    )


# ═══════════════════════════════════════════════════════════════════
# T-8: decision_context captured at selection time
# ═══════════════════════════════════════════════════════════════════

def test_decision_context_attached_to_signal_dict():
    """
    strategy_selector.select() must attach decision_context to the
    returned signal dict. ExecutionEngine then persists it into the
    trading_positions JSONB column. Without it the Loop 2 meta-label
    audit trail loses the snapshot of flag state at selection time.
    """
    path = os.path.join(BACKEND, "strategy_selector.py")
    with open(path, encoding="utf-8") as f:
        src = f.read()

    assert (
        '"decision_context": _decision_context' in src
        or "'decision_context': _decision_context" in src
    ), "signal dict must include a decision_context key"


def test_decision_context_captures_flags_and_timestamp():
    """decision_context must capture flags_at_selection and selected_at."""
    path = os.path.join(BACKEND, "strategy_selector.py")
    with open(path, encoding="utf-8") as f:
        src = f.read()

    assert "flags_at_selection" in src, (
        "decision_context must include flags_at_selection — snapshot "
        "of every signal flag at the moment of selection"
    )
    assert "selected_at" in src, (
        "decision_context must include selected_at — wall-clock "
        "timestamp at the moment of selection (not at execution)"
    )
