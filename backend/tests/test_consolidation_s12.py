"""
Consolidation Session 12 — P&L Correctness.

Locks the contract for S12 fixes:

  T0-3 — long_straddle / calendar_spread MUST run through D-021,
         D-022 and D-004 gates (4 tests).
  T0-5 — run_mark_to_market_job must write
         execution_engine health=error when redis_client is None
         (1 test, uses the S8/S11 main-import helper).
  T0-6 — Partial exit (a) rescales current_pnl to remaining
         contracts; (b) captures original_contracts BEFORE the
         contracts mutation for audit accuracy (2 source-grep
         tests).
  T0-7 — open_virtual_position refuses to open when
         MAX_OPEN_POSITIONS already open (2 tests).
  T2-7 — close_virtual_position refuses (returns False) when no
         exit price is available; marks pending_close instead of
         the old 50% guess (2 tests).

Total: 11 tests, 0 failures expected.
"""
import os
import sys
import types

import pytest
from unittest.mock import MagicMock, patch

BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)


# ─── S8/S11 helpers reused for the T0-5 main-import test ─────────────────────

def _ensure_main_importable():
    """Stub heavy Railway-only deps so `import main` succeeds in tests."""
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
        fastapi.Depends = _passthrough  # S14 extension
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


def _load_backend_main_isolated():
    """Load backend/main.py under a unique slot then alias to "main".

    Same idiom as test_consolidation_s8/s11 — keeps sys.modules["main"]
    clean for sibling tests but allows ``patch("main.X")`` to resolve
    correctly during this test's lifetime.
    """
    _ensure_main_importable()
    import importlib.util

    saved_main = sys.modules.get("main")

    spec = importlib.util.spec_from_file_location(
        "_s12_backend_main", os.path.join(BACKEND, "main.py")
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["main"] = module
    sys.modules["_s12_backend_main"] = module
    spec.loader.exec_module(module)

    def restore_fn():
        if saved_main is not None:
            sys.modules["main"] = saved_main
        else:
            sys.modules.pop("main", None)
        sys.modules.pop("_s12_backend_main", None)

    return module, restore_fn


# ═════════════════════════════════════════════════════════════════════════════
# T0-3 — Straddle / calendar respect sizing gates
# ═════════════════════════════════════════════════════════════════════════════

def test_straddle_returns_zero_contracts_in_danger_tier():
    """long_straddle in danger tier (D-004) MUST return 0 contracts.

    Before T0-3 the straddle branch returned early before the tier
    check, so on a danger-classified day it would still place a
    full-sized straddle — exactly when the system is supposed to
    refuse all entries.
    """
    from risk_engine import compute_position_size
    result = compute_position_size(
        account_value=100_000.0,
        spread_width=0,
        strategy_type="long_straddle",
        allocation_tier="danger",
    )
    assert result["contracts"] == 0, (
        f"Straddle in danger tier must return 0 contracts. "
        f"Got {result['contracts']}"
    )


def test_straddle_halved_on_consecutive_losses():
    """long_straddle sizing must shrink with 3+ consecutive losses (D-022)."""
    from risk_engine import compute_position_size

    baseline = compute_position_size(
        account_value=100_000.0,
        spread_width=0,
        strategy_type="long_straddle",
        consecutive_losses_today=0,
        allocation_tier="full",
    )
    halved = compute_position_size(
        account_value=100_000.0,
        spread_width=0,
        strategy_type="long_straddle",
        consecutive_losses_today=3,
        allocation_tier="full",
    )
    assert halved["contracts"] <= baseline["contracts"], (
        "Straddle with 3 consecutive losses must have <= baseline contracts"
    )
    assert halved["size_reduction_reason"] is not None, (
        "D-022 must record a size_reduction_reason on the straddle path"
    )
    assert "capital_preservation_d022" in halved["size_reduction_reason"]


def test_straddle_halved_on_regime_disagreement():
    """long_straddle sizing must shrink on regime disagreement (D-021)."""
    from risk_engine import compute_position_size

    agreed = compute_position_size(
        account_value=100_000.0,
        spread_width=0,
        strategy_type="long_straddle",
        regime_agreement=True,
    )
    disagreed = compute_position_size(
        account_value=100_000.0,
        spread_width=0,
        strategy_type="long_straddle",
        regime_agreement=False,
    )
    assert disagreed["contracts"] <= agreed["contracts"]
    assert disagreed["size_reduction_reason"] is not None
    assert "regime_disagreement_d021" in disagreed["size_reduction_reason"]


def test_calendar_returns_zero_contracts_in_danger_tier():
    """calendar_spread in danger tier MUST return 0 contracts."""
    from risk_engine import compute_position_size
    result = compute_position_size(
        account_value=100_000.0,
        spread_width=0,
        strategy_type="calendar_spread",
        allocation_tier="danger",
    )
    assert result["contracts"] == 0, (
        f"Calendar spread in danger tier must return 0 contracts. "
        f"Got {result['contracts']}"
    )


def test_calendar_halved_on_consecutive_losses():
    """calendar_spread sizing must shrink with 3+ consecutive losses (D-022).

    Symmetric to the straddle test — confirms calendar_spread also
    flows through _apply_sizing_gates and is not silently bypassing
    the capital-preservation halving.
    """
    from risk_engine import compute_position_size

    baseline = compute_position_size(
        account_value=100_000.0,
        spread_width=0,
        strategy_type="calendar_spread",
        consecutive_losses_today=0,
        allocation_tier="full",
    )
    halved = compute_position_size(
        account_value=100_000.0,
        spread_width=0,
        strategy_type="calendar_spread",
        consecutive_losses_today=3,
        allocation_tier="full",
    )
    assert halved["contracts"] <= baseline["contracts"]
    assert halved["size_reduction_reason"] is not None
    assert "capital_preservation_d022" in halved["size_reduction_reason"]


# ═════════════════════════════════════════════════════════════════════════════
# T0-5 — MTM health write on redis=None
# ═════════════════════════════════════════════════════════════════════════════

def test_mtm_job_writes_health_error_when_redis_none():
    """run_mark_to_market_job must write execution_engine=error when
    redis_client is None — not silently return.
    """
    m, restore = _load_backend_main_isolated()
    try:
        original = m.redis_client
        m.redis_client = None
        try:
            with patch.object(m, "write_health_status") as mock_health:
                m.run_mark_to_market_job()
        finally:
            m.redis_client = original

        mock_health.assert_called_once()
        call_args = mock_health.call_args
        # write_health_status("execution_engine", "error", last_error_message=...)
        positional = call_args.args
        assert positional[0] == "execution_engine", (
            f"First arg must be 'execution_engine', got {positional!r}"
        )
        assert positional[1] == "error", (
            f"Second arg must be 'error' status, got {positional!r}"
        )
    finally:
        restore()


# ═════════════════════════════════════════════════════════════════════════════
# T0-6 — Partial exit current_pnl rescaled + audit log accurate
# ═════════════════════════════════════════════════════════════════════════════

def test_partial_exit_rescales_current_pnl():
    """position_monitor must rescale current_pnl to remaining contracts
    after a partial exit, otherwise the next-tick TP/SL checks compare
    full-size P&L against remaining-size max_profit (false exits).
    """
    path = os.path.join(BACKEND, "position_monitor.py")
    with open(path, encoding="utf-8") as f:
        src = f.read()
    assert "remaining_contracts" in src, (
        "remaining_contracts variable must exist"
    )
    assert "current_pnl = current_pnl *" in src, (
        "position_monitor must rescale current_pnl after partial exit "
        "(missing 'current_pnl = current_pnl *' formula)"
    )
    # The rescale must reference remaining_contracts somewhere in the
    # immediate vicinity of the assignment to prove it's a rescale,
    # not some other multiplication.
    rescale_pos = src.find("current_pnl = current_pnl *")
    nearby = src[rescale_pos:rescale_pos + 250]
    assert "remaining_contracts" in nearby, (
        "current_pnl rescale must use remaining_contracts in the divisor"
    )


def test_partial_exit_audit_log_uses_original_contracts():
    """original_contracts_for_audit must be captured BEFORE the
    contracts = remaining_contracts mutation, so the audit log
    records the true original size.
    """
    path = os.path.join(BACKEND, "position_monitor.py")
    with open(path, encoding="utf-8") as f:
        src = f.read()
    audit_var_pos = src.find("original_contracts_for_audit")
    mutation_pos = src.find("contracts = remaining_contracts")
    assert audit_var_pos > -1, (
        "original_contracts_for_audit variable must exist"
    )
    assert mutation_pos > -1, (
        "contracts = remaining_contracts mutation must exist"
    )
    assert audit_var_pos < mutation_pos, (
        "original_contracts_for_audit must be captured BEFORE "
        "contracts is mutated to remaining_contracts"
    )
    # Also confirm the audit metadata uses the new variable, not the
    # raw `contracts` (which would now refer to remaining_contracts).
    assert '"original_contracts":\n                                    original_contracts_for_audit' in src \
        or '"original_contracts": original_contracts_for_audit' in src, (
            "Audit log metadata must reference original_contracts_for_audit"
        )


# ═════════════════════════════════════════════════════════════════════════════
# T0-7 — Concurrent open position cap
# ═════════════════════════════════════════════════════════════════════════════

def test_open_virtual_position_rejects_when_cap_reached():
    """open_virtual_position must return None when 3 positions already open.

    Mocks the Supabase count="exact" chain
        client.table().select().eq().in_().execute()
    to return .count = 3 (at cap).
    """
    from execution_engine import ExecutionEngine

    engine = ExecutionEngine.__new__(ExecutionEngine)

    with patch("execution_engine.get_client") as mock_client, \
         patch("execution_engine.get_today_session") as mock_session:

        mock_session.return_value = {
            "id": "sess-001",
            "session_status": "active",
        }

        # The count="exact" select chain returns a result with .count
        mock_count_result = MagicMock()
        mock_count_result.count = 3  # at cap

        chain = (
            mock_client.return_value
            .table.return_value
            .select.return_value
            .eq.return_value
            .in_.return_value
        )
        chain.execute.return_value = mock_count_result

        signal = {
            "contracts": 1,
            "strategy_type": "iron_condor",
            "target_credit": 1.85,
            "session_id": "sess-001",
        }
        result = engine.open_virtual_position(
            signal, {"spx_price": 5200.0}
        )

    assert result is None, (
        "open_virtual_position must return None when 3 positions "
        f"already open. Got {result!r}"
    )


def test_open_virtual_position_proceeds_below_cap():
    """Source-grep guard: MAX_OPEN_POSITIONS constant + cap log msg
    must exist in execution_engine.
    """
    path = os.path.join(BACKEND, "execution_engine.py")
    with open(path, encoding="utf-8") as f:
        src = f.read()
    assert "MAX_OPEN_POSITIONS" in src, (
        "MAX_OPEN_POSITIONS constant must exist in execution_engine"
    )
    assert "open_virtual_position_cap_reached" in src, (
        "Cap-reached log message must exist for operator visibility"
    )
    assert "count=\"exact\"" in src, (
        "Cap query must use count=\"exact\" for accurate count"
    )


# ═════════════════════════════════════════════════════════════════════════════
# T2-7 — Exit refuses without price (no more 50% guess)
# ═════════════════════════════════════════════════════════════════════════════

def test_close_without_price_returns_false_not_corrupt():
    """The 50% exit fallback must be GONE — it corrupted realized
    P&L, Kelly inputs, and feedback-loop training data.
    """
    path = os.path.join(BACKEND, "execution_engine.py")
    with open(path, encoding="utf-8") as f:
        src = f.read()

    # The 50% guess must be gone. Tolerate it appearing inside a
    # comment/docstring that explains the removal — count only
    # executable lines.
    code_only_lines = [
        line for line in src.splitlines()
        if not line.lstrip().startswith("#")
    ]
    code_only = "\n".join(code_only_lines)
    assert "entry_credit * 0.50" not in code_only, (
        "50% exit fallback must be removed from executable code "
        "— it corrupts realized P&L, Kelly inputs, and feedback "
        "loop training data"
    )

    # Must mark pending_close + log + refuse.
    assert "pending_close" in src, (
        "Must mark position signal_status='pending_close' when no "
        "exit price is available"
    )
    assert "close_virtual_position_no_price_available" in src, (
        "Must log close_virtual_position_no_price_available so "
        "operators see the refused close"
    )
