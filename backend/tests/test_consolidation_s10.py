"""
Consolidation Session 10 — Risk Hard Gates.

Tests for:
  T2-14 — session_manager None guards (3 locations)
  T0-1a — check_daily_drawdown fails CLOSED on exception
  T0-1b — trading_cycle halts on MTM fetch failure / None
  T0-8  — 5-consecutive-loss halt actually calls update_session(halted)
  T0-9  — run_prediction_cycle has max_instances=1 + coalesce=True
  T0-10 — drawdown alert copy is honest (does not claim positions closed)
  T2-13 — TRADIER_SANDBOX warns when unset instead of silent default

All tests must pass with 0 failures.
"""
import os
import sys

import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ─── T2-14: session_manager None guards ──────────────────────────────────────

def test_get_or_create_session_handles_none_execute_result():
    """maybe_single().execute() returning None must not raise AttributeError.

    Pre-fix this raised "AttributeError: 'NoneType' object has no attribute
    'data'", got swallowed by the outer except, logged
    "session_create_failed", and returned None — causing trading_cycle to
    skip the entire 5-minute cycle with reason "no_session".
    """
    import session_manager

    with patch("session_manager.get_client") as mock_client:
        mock_execute = MagicMock()
        mock_execute.execute.return_value = None
        mock_client.return_value.table.return_value \
            .select.return_value \
            .eq.return_value \
            .maybe_single.return_value = mock_execute

        try:
            session_manager.get_or_create_session()
        except AttributeError as e:
            raise AssertionError(
                "session_manager raised AttributeError on None "
                f"result.execute(): {e}"
            )


def test_get_or_create_session_handles_none_data():
    """execute() returning a response object whose .data is None must not
    raise. We expect the function to fall through to the upsert path.
    """
    import session_manager

    with patch("session_manager.get_client") as mock_client:
        mock_resp = MagicMock()
        mock_resp.data = None
        mock_execute = MagicMock()
        mock_execute.execute.return_value = mock_resp
        mock_client.return_value.table.return_value \
            .select.return_value \
            .eq.return_value \
            .maybe_single.return_value = mock_execute

        try:
            session_manager.get_or_create_session()
        except AttributeError as e:
            raise AssertionError(
                f"AttributeError on data=None: {e}"
            )


def test_get_today_session_handles_none_execute_result():
    """Third T2-14 location: get_today_session must not crash on None."""
    import session_manager

    with patch("session_manager.get_client") as mock_client:
        mock_execute = MagicMock()
        mock_execute.execute.return_value = None
        mock_client.return_value.table.return_value \
            .select.return_value \
            .eq.return_value \
            .maybe_single.return_value = mock_execute

        result = session_manager.get_today_session()
        assert result is None, (
            "get_today_session must return None on None response, "
            f"got: {result!r}"
        )


# ─── T0-1a: Drawdown fails CLOSED ────────────────────────────────────────────

def test_check_daily_drawdown_returns_true_on_exception():
    """Outer exception must return True (halted) — was returning False
    (allow trading) which silently disabled the -3% safety net during
    any DB blip. This test guards the fail-CLOSED contract.
    """
    from risk_engine import check_daily_drawdown

    with patch("risk_engine.update_session"), \
         patch("risk_engine.write_audit_log"), \
         patch("risk_engine.write_health_status"), \
         patch("risk_engine._get_redis", return_value=None):
        # Force the inner numeric block to raise by passing a string for
        # current_daily_pnl. This propagates to the outer except which
        # is the one we care about.
        result = check_daily_drawdown(
            session_id="sess-001",
            current_daily_pnl="not_a_number",  # type: ignore[arg-type]
            account_value=100_000.0,
        )

    assert result is True, (
        "check_daily_drawdown must fail CLOSED (return True) on "
        f"exception. Got {result} — trading would continue on DB failure."
    )


def test_check_daily_drawdown_normal_loss_returns_false():
    """Baseline: small loss below the -3% threshold must still allow
    trading (return False). Confirms the fail-closed change did not
    over-correct into a permanent halt.
    """
    from risk_engine import check_daily_drawdown

    with patch("risk_engine.update_session"), \
         patch("risk_engine.write_audit_log"), \
         patch("risk_engine.write_health_status"), \
         patch("risk_engine._get_redis", return_value=None):
        # -$100 on $100k = -0.1% — well below the -3% halt
        result = check_daily_drawdown(
            session_id="sess-001",
            current_daily_pnl=-100.0,
            account_value=100_000.0,
        )

    assert result is False, (
        f"-0.1% drawdown must NOT trigger halt. Got {result}."
    )


# ─── T0-1b: MTM failure halts cycle ──────────────────────────────────────────

def _reset_trading_cycle_globals():
    """Clear lazy-init engines so each test starts clean."""
    import trading_cycle
    trading_cycle._prediction_engine = MagicMock()
    trading_cycle._strategy_selector = MagicMock()
    trading_cycle._execution_engine = MagicMock()


def test_trading_cycle_skips_when_mtm_fetch_fails():
    """trading_cycle must skip (not trade on 0 unrealized) when MTM
    raises. Substituting 0 silently could mask a -3%+ loss already in
    the open book.
    """
    _reset_trading_cycle_globals()
    from trading_cycle import run_trading_cycle

    with patch("trading_cycle.get_or_create_session") as mock_session, \
         patch("trading_cycle.get_client") as mock_client, \
         patch("trading_cycle.check_daily_drawdown", return_value=False):

        mock_session.return_value = {
            "id": "sess-001",
            "session_status": "active",
            "virtual_pnl": -200.0,
        }
        # MTM fetch raises
        mock_client.return_value.table.return_value \
            .select.return_value \
            .eq.return_value \
            .eq.return_value \
            .execute.side_effect = Exception("DB timeout")

        result = run_trading_cycle()

    assert result.get("skipped_reason") == "mtm_fetch_failed", (
        "Expected mtm_fetch_failed skip, got: "
        f"{result.get('skipped_reason')!r}"
    )


def test_trading_cycle_skips_when_mtm_returns_none():
    """trading_cycle must skip when MTM execute() returns None
    (transient Supabase blip, same family as T2-14).
    """
    _reset_trading_cycle_globals()
    from trading_cycle import run_trading_cycle

    with patch("trading_cycle.get_or_create_session") as mock_session, \
         patch("trading_cycle.get_client") as mock_client, \
         patch("trading_cycle.check_daily_drawdown", return_value=False):

        mock_session.return_value = {
            "id": "sess-001",
            "session_status": "active",
            "virtual_pnl": -200.0,
        }
        mock_client.return_value.table.return_value \
            .select.return_value \
            .eq.return_value \
            .eq.return_value \
            .execute.return_value = None

        result = run_trading_cycle()

    assert result.get("skipped_reason") == "mtm_fetch_failed", (
        "Expected mtm_fetch_failed on None response, got: "
        f"{result.get('skipped_reason')!r}"
    )


# ─── T0-8: 5-consecutive-loss halt actually executes ─────────────────────────

def test_five_consecutive_losses_calls_update_session_halted():
    """5th consecutive loss must call update_session(session_status='halted').

    Pre-fix: only an audit log was written claiming "session_halt" while
    the session_status was never updated, so the kill switch promised by
    capital preservation D-022 was never actually engaged. trading_cycle
    and open_virtual_position both rely on session_status, so the next
    5-min cycle would happily open new positions.
    """
    from execution_engine import ExecutionEngine

    engine = ExecutionEngine.__new__(ExecutionEngine)

    # Position lookup: chain is .select(*).eq(id).eq(status).maybe_single()
    mock_pos = MagicMock()
    mock_pos.data = {
        "id": "pos-001",
        "strategy_type": "iron_condor",
        "entry_credit": 1.50,
        "contracts": 1,
        "session_id": "sess-001",
        "entry_slippage": 0.15,
        "entry_regime": "range",
        "entry_cv_stress": 0.0,
        "current_pnl": -50.0,
        "current_state": "open",
    }

    # Session lookup: chain is .select(*).eq(id).maybe_single()
    # (one .eq fewer than the position lookup)
    mock_session = MagicMock()
    mock_session.data = {
        "virtual_pnl": -800.0,
        "virtual_wins": 2,
        "virtual_losses": 4,
        # 4 prior losses — this losing close pushes us to 5 → halt
        "consecutive_losses_today": 4,
    }

    halt_calls: list = []

    def fake_update_session(sid, **kw):
        halt_calls.append(kw)
        return True

    with patch("execution_engine.get_client") as mock_get_client, \
         patch("execution_engine.write_audit_log"), \
         patch("execution_engine.write_health_status"), \
         patch("execution_engine.check_execution_quality"), \
         patch("execution_engine.update_session",
               side_effect=fake_update_session), \
         patch(
             "execution_engine.STATIC_SLIPPAGE_BY_STRATEGY",
             {"iron_condor": 0.15},
         ):

        client = MagicMock()
        # Position lookup: depth = .select.eq.eq.maybe_single.execute
        client.table.return_value.select.return_value \
            .eq.return_value.eq.return_value \
            .maybe_single.return_value.execute.return_value = mock_pos
        # Session lookup: depth = .select.eq.maybe_single.execute
        # (note: M_select.eq.return_value is the SAME M_eq1; from M_eq1
        # the .maybe_single path is distinct from the .eq.maybe_single
        # path used by the position lookup, so both can coexist)
        client.table.return_value.select.return_value \
            .eq.return_value.maybe_single.return_value \
            .execute.return_value = mock_session
        mock_get_client.return_value = client

        engine.close_virtual_position(
            position_id="pos-001",
            exit_credit=2.55,  # losing trade (entry=1.50 credit)
            exit_reason="stop_loss",
        )

    halt_kwargs = [
        kw for kw in halt_calls
        if kw.get("session_status") == "halted"
    ]
    assert len(halt_kwargs) >= 1, (
        "5th consecutive loss must call update_session("
        "session_status='halted'). All update_session calls: "
        f"{halt_calls}"
    )
    assert (
        halt_kwargs[0].get("halt_reason") == "D022_five_consecutive_losses"
    ), (
        "halt_reason must be D022_five_consecutive_losses for audit "
        f"clarity. Got: {halt_kwargs[0].get('halt_reason')!r}"
    )


def test_three_consecutive_losses_does_not_halt():
    """Source guard: 3 consecutive losses still trigger size reduction,
    not a session halt. Only 5 losses halt.
    """
    path = os.path.join(
        os.path.dirname(__file__), "..", "execution_engine.py"
    )
    with open(path) as f:
        src = f.read()
    # Size 50% at 3 losses
    assert "size_50pct" in src, (
        "execution_engine must still reduce sizing at 3 consecutive losses"
    )
    # Halt audit text only at 5
    assert "session_halt" in src
    # The actual halt call must be gated on consecutive == 5, not 3
    assert "if consecutive == 5:" in src, (
        "Halt must be gated on consecutive == 5 only — never on 3"
    )


# ─── T0-9: Prediction cycle concurrency ──────────────────────────────────────

def test_prediction_cycle_has_max_instances():
    """trading_prediction_cycle_local must have max_instances=1 and
    coalesce=True. Without these, a slow cycle can overlap the next
    5-minute fire and produce duplicate position entries.
    """
    path = os.path.join(os.path.dirname(__file__), "..", "main.py")
    with open(path) as f:
        src = f.read()

    cycle_block_start = src.find("trading_prediction_cycle_local")
    assert cycle_block_start > -1, (
        "trading_prediction_cycle_local job ID not found in main.py"
    )

    # Search a generous window around the id= line for both kwargs
    nearby = src[
        max(0, cycle_block_start - 400): cycle_block_start + 400
    ]
    assert "max_instances=1" in nearby, (
        "trading_prediction_cycle_local must have max_instances=1 "
        "to prevent duplicate concurrent cycles."
    )
    assert "coalesce=True" in nearby, (
        "trading_prediction_cycle_local must have coalesce=True."
    )


# ─── T0-10: Alert copy honesty ───────────────────────────────────────────────

def test_drawdown_alert_copy_does_not_claim_positions_closed():
    """The CRITICAL drawdown alert must not claim 'All positions closed'
    — the halt only blocks NEW entries; position_monitor continues to
    manage open positions until their stops/TPs fire.
    """
    path = os.path.join(os.path.dirname(__file__), "..", "risk_engine.py")
    with open(path) as f:
        src = f.read()
    assert "All positions closed" not in src, (
        "Alert copy says 'All positions closed' but drawdown halt does "
        "NOT close existing positions. Operator gets a false picture of "
        "the book state."
    )


def test_drawdown_alert_copy_uses_corrected_phrasing():
    """Positive guard: corrected copy must explicitly tell the operator
    that NEW entries are halted while existing positions continue to
    be managed.
    """
    path = os.path.join(os.path.dirname(__file__), "..", "risk_engine.py")
    with open(path) as f:
        src = f.read()
    assert "New entries halted for today" in src, (
        "Corrected alert copy 'New entries halted for today' missing"
    )
    assert "Existing positions continue to be managed" in src, (
        "Corrected alert copy must clarify existing positions keep "
        "being managed (stops + TP active)"
    )


# ─── T2-13: TRADIER_SANDBOX guard ────────────────────────────────────────────

def test_tradier_sandbox_warns_when_unset():
    """When TRADIER_SANDBOX is not set, config must emit a warning
    (instead of silently defaulting). Defaults to True for safety
    only after the warning is raised.
    """
    import importlib
    import warnings
    import config as cfg

    env_backup = os.environ.pop("TRADIER_SANDBOX", None)
    try:
        # Patch load_dotenv so the .env file does not silently re-set
        # TRADIER_SANDBOX during the reload.
        with patch("config.load_dotenv"):
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                importlib.reload(cfg)
                sandbox_warnings = [
                    w for w in caught
                    if "TRADIER_SANDBOX" in str(w.message)
                ]
                assert len(sandbox_warnings) >= 1, (
                    "config must emit a warning when TRADIER_SANDBOX "
                    f"is unset. Caught warnings: {[str(w.message) for w in caught]}"
                )
                assert cfg.TRADIER_SANDBOX is True, (
                    "Default value when unset must still be True "
                    f"(safe sandbox), got: {cfg.TRADIER_SANDBOX!r}"
                )
    finally:
        if env_backup is not None:
            os.environ["TRADIER_SANDBOX"] = env_backup
        # Restore real config state for the rest of the suite
        with patch("config.load_dotenv"):
            importlib.reload(cfg)


def test_tradier_sandbox_explicit_false():
    """TRADIER_SANDBOX=false must yield TRADIER_SANDBOX = False with
    no warning emitted (operator made an explicit choice).
    """
    import importlib
    import warnings
    import config as cfg

    env_backup = os.environ.get("TRADIER_SANDBOX")
    os.environ["TRADIER_SANDBOX"] = "false"
    try:
        with patch("config.load_dotenv"):
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                importlib.reload(cfg)
                assert cfg.TRADIER_SANDBOX is False, (
                    "TRADIER_SANDBOX=false must set the constant to "
                    f"False, got: {cfg.TRADIER_SANDBOX!r}"
                )
                sandbox_warnings = [
                    w for w in caught
                    if "TRADIER_SANDBOX" in str(w.message)
                ]
                assert len(sandbox_warnings) == 0, (
                    "No warning expected when TRADIER_SANDBOX is "
                    "explicitly set. Got: "
                    f"{[str(w.message) for w in sandbox_warnings]}"
                )
    finally:
        if env_backup is not None:
            os.environ["TRADIER_SANDBOX"] = env_backup
        else:
            os.environ.pop("TRADIER_SANDBOX", None)
        with patch("config.load_dotenv"):
            importlib.reload(cfg)
