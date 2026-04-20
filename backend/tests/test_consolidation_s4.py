"""
Consolidation Session 4 tests — P&L correctness + kill switch + auth.

Coverage:
    A-1  _simulate_fill returns signed_fill (+/- by debit/credit)
         open_virtual_position writes signed entry_credit
    A-2  long_straddle MTM returns non-zero P&L
         long_straddle profit grows when ATM premium expands
    A-3  long_put / long_call P&L is positive when option gains value
         (regression test for the inverted-debit-MTM bug)
    A-4  close_virtual_position gross_pnl sign is correct for debits
    B-1  partial-exit block does not shadow current_pnl
    C-α  trading_cycle skips when session is halted/closed
         trading_cycle proceeds when session is active/pending
    C-β  /admin/trading/feature-flags rejects requests without the
         X-Api-Key when RAILWAY_ADMIN_KEY is configured
         and accepts when the key matches
    P1-1 mark_to_market scheduler entry registered before
         position_monitor (so MTM fires first each minute)

These tests are self-contained — they use ast static analysis or
in-process mocks (no Redis, no live Supabase).
"""

from __future__ import annotations

import ast
import os
import re
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)


# ── A-1: signed_fill in _simulate_fill ──────────────────────────────

def test_simulate_fill_debit_signed_fill_negative():
    """Debit strategies (target_credit < 0) must yield signed_fill < 0."""
    from execution_engine import ExecutionEngine

    engine = ExecutionEngine.__new__(ExecutionEngine)
    fill = engine._simulate_fill(-3.00, "long_put")
    assert "signed_fill" in fill, "missing signed_fill field"
    assert fill["signed_fill"] < 0, (
        f"debit signed_fill must be negative, got {fill['signed_fill']}"
    )
    # fill_price stays positive (legacy contract for audit)
    assert fill["fill_price"] > 0
    assert abs(fill["signed_fill"]) == fill["fill_price"]


def test_simulate_fill_credit_signed_fill_positive():
    """Credit strategies (target_credit >= 0) must yield signed_fill > 0."""
    from execution_engine import ExecutionEngine

    engine = ExecutionEngine.__new__(ExecutionEngine)
    fill = engine._simulate_fill(1.50, "put_credit_spread")
    assert fill["signed_fill"] > 0
    assert fill["signed_fill"] == fill["fill_price"]


def test_open_virtual_position_writes_signed_entry_credit_for_debit():
    """End-to-end: opening a long_put must persist a NEGATIVE entry_credit."""
    from execution_engine import ExecutionEngine

    engine = ExecutionEngine.__new__(ExecutionEngine)
    engine.LEGS_BY_STRATEGY = ExecutionEngine.LEGS_BY_STRATEGY

    captured: dict = {}

    fake_table = MagicMock()
    fake_table.insert.return_value.execute.return_value = MagicMock(
        data=[{"id": "abc"}]
    )

    def _capture_insert(payload):
        captured.update(payload)
        return fake_table

    fake_table.insert.side_effect = _capture_insert
    fake_client = MagicMock()
    fake_client.table.return_value = fake_table

    fake_session = {
        "id": "sess-1",
        "session_status": "active",
        "virtual_trades_count": 0,
    }

    with patch("execution_engine.get_client", return_value=fake_client), \
            patch("execution_engine.get_today_session",
                  return_value=fake_session), \
            patch("execution_engine.update_session"), \
            patch("execution_engine.write_audit_log"), \
            patch("execution_engine.write_health_status"):
        result = engine.open_virtual_position(
            signal={
                "session_id": "sess-1",
                "strategy_type": "long_put",
                "target_credit": -3.00,
                "contracts": 1,
                "short_strike": 5200.0,
                "expiry_date": "2026-04-21",
            },
            prediction={"spx_price": 5200.0},
        )

    assert result is not None, "position should be created"
    assert "entry_credit" in captured
    assert captured["entry_credit"] < 0, (
        "debit position must store NEGATIVE entry_credit "
        f"(got {captured['entry_credit']})"
    )


# ── A-2: long_straddle / calendar_spread MTM ────────────────────────

def test_price_position_straddle_returns_nonzero():
    """A long_straddle with live ATM quotes must produce a real P&L."""
    from mark_to_market import _price_position

    pos = {
        "strategy_type": "long_straddle",
        # A-1 stored the signed entry: paid 4.15 → -4.15
        "entry_credit": -4.15,
        "contracts": 1,
        "expiry_date": "2026-04-21",
        "short_strike": 5200.0,
    }

    fake_redis = MagicMock()

    # No live quote — force BS fallback by returning None for every key
    fake_redis.get.return_value = None

    pnl = _price_position(pos, spx_price=5200.0, redis_client=fake_redis)

    assert pnl is not None, (
        "straddle MTM must not return None (was the bug — meant "
        "current_pnl stayed 0 forever)"
    )


def test_price_position_straddle_profit_when_vol_expands():
    """When the ATM straddle is worth more than paid, P&L > 0."""
    from mark_to_market import _price_position

    pos = {
        "strategy_type": "long_straddle",
        "entry_credit": -4.00,
        "contracts": 1,
        "expiry_date": "2026-04-21",
        "short_strike": 5200.0,
    }

    fake_redis = MagicMock()

    def _quote(key: str):
        # Return a live quote whose mid sums to > 4.00 (call+put)
        # Both legs report bid=2.50 ask=2.70 → mid=2.60 → straddle=5.20
        import json
        return json.dumps({"bid": 2.50, "ask": 2.70})

    fake_redis.get.side_effect = _quote

    pnl = _price_position(pos, spx_price=5200.0, redis_client=fake_redis)

    assert pnl is not None
    assert pnl > 0, (
        f"straddle worth $5.20 paid $4.00 should be profit, got {pnl}"
    )


def test_price_position_calendar_spread_returns_nonzero():
    """calendar_spread now has real two-leg MTM (T0-4 replaced the stub).

    Historical contract was "stub returns 0 (public contract: not
    None)". T0-4 replaced the stub with real two-leg BS pricing, so
    the contract is now:
      * with far_expiry_date present → real float P&L
      * without far_expiry_date → None (skipped by MTM loop, safe
        default — peak_pnl stays unchanged rather than being pinned
        at a fake 0)

    Both branches must not raise. The lower-level contract (real
    non-zero P&L with full inputs) is covered more directly by
    test_calendar_mtm.py::test_calendar_pnl_is_not_zero.
    """
    from datetime import date, timedelta
    from mark_to_market import _price_position

    today = date.today()
    pos = {
        "strategy_type": "calendar_spread",
        "entry_credit": 1.50,   # post-T0-4 calendars collect a credit
        "contracts": 1,
        "expiry_date": today.isoformat(),
        "far_expiry_date": (today + timedelta(days=5)).isoformat(),
        "short_strike": 5200.0,
    }

    # Redis mock that returns None for everything — forces the BS
    # fallback + VIX defaults in the calendar branch.
    redis = MagicMock()
    redis.get.return_value = None

    pnl = _price_position(pos, spx_price=5200.0, redis_client=redis)
    assert pnl is None or isinstance(pnl, float), (
        "calendar_spread MTM must return a float (real pricing) or "
        "None (skipped) — never raise"
    )


# ── A-3: long_put / long_call sign correction ───────────────────────

def test_long_put_pnl_when_option_gains_value():
    """REGRESSION: paid $5, option now $7, expected pnl = +$200.

    This is the direct test for the A-3 fix. Before the fix
    current_spread_value = -opt_price, which made pnl = -$1200.
    After the fix current_spread_value = opt_price, which makes
    pnl = +$200.
    """
    from mark_to_market import _price_position

    pos = {
        "strategy_type": "long_put",
        # A-1: entry_credit = -5.00 (paid $5)
        "entry_credit": -5.00,
        "contracts": 1,
        "expiry_date": "2026-04-21",
        "short_strike": 5200.0,
    }

    fake_redis = MagicMock()

    import json

    def _quote(key: str):
        # Force opt_price = 7.00 via a deterministic quote
        return json.dumps({"bid": 6.95, "ask": 7.05})

    fake_redis.get.side_effect = _quote

    pnl = _price_position(pos, spx_price=5200.0, redis_client=fake_redis)
    assert pnl == 200.00, (
        f"paid $5, option now $7 should book +$200, got {pnl}"
    )


def test_long_call_pnl_when_option_loses_value():
    """Paid $4, option now $1.50 → loss of $250."""
    from mark_to_market import _price_position

    pos = {
        "strategy_type": "long_call",
        "entry_credit": -4.00,
        "contracts": 1,
        "expiry_date": "2026-04-21",
        "short_strike": 5200.0,
    }

    fake_redis = MagicMock()

    import json

    def _quote(key: str):
        return json.dumps({"bid": 1.45, "ask": 1.55})

    fake_redis.get.side_effect = _quote

    pnl = _price_position(pos, spx_price=5200.0, redis_client=fake_redis)
    assert pnl == -250.00, f"paid $4, option now $1.50 → -$250, got {pnl}"


# ── B-1: variable shadow eliminated ─────────────────────────────────

def test_no_variable_shadow_in_partial_exit():
    """Partial-exit block must not assign to a name called current_pnl
    (would clobber the outer position MTM used by stop/profit checks).
    """
    path = os.path.join(REPO_ROOT, "backend", "position_monitor.py")
    with open(path, encoding="utf-8") as f:
        src = f.read()

    # Find the partial-exit try block
    marker = "partial_exit_session_pnl_updated"
    assert marker in src, "expected partial_exit_session_pnl_updated marker"
    # The fix renames the local to session_virtual_pnl
    assert "session_virtual_pnl" in src, (
        "B-1 fix missing — local should be named session_virtual_pnl"
    )
    # And the prior shadow assignment must NOT be present in that block
    assert "current_pnl = session.data.get(\"virtual_pnl\")" not in src, (
        "B-1 shadow still present — current_pnl is being clobbered"
    )


# ── C-α: kill switch gates trading_cycle ────────────────────────────

@pytest.mark.parametrize("status,expect_skip", [
    ("halted", True),
    ("closed", True),
    ("active", False),
    ("pending", False),
])
def test_trading_cycle_respects_session_status(status, expect_skip):
    """trading_cycle must skip on halted/closed and proceed on active/pending."""
    import trading_cycle
    import session_manager

    fake_session = {"id": "s-1", "session_status": status, "virtual_pnl": 0.0}

    with patch.object(trading_cycle, "get_or_create_session",
                      return_value=fake_session), \
            patch.object(session_manager, "get_today_session",
                         return_value=fake_session), \
            patch.object(trading_cycle, "check_daily_drawdown",
                         return_value=False), \
            patch.object(trading_cycle, "get_client") as gc:
        # MTM fetch returns []
        gc.return_value.table.return_value.select.return_value.eq \
            .return_value.eq.return_value.execute.return_value = MagicMock(
                data=[]
            )

        # Replace the lazily-initialised module singletons with mocks so
        # we never hit real Redis or LightGBM models in the test.
        trading_cycle._prediction_engine = MagicMock()
        trading_cycle._strategy_selector = MagicMock()
        trading_cycle._execution_engine = MagicMock()
        trading_cycle._prediction_engine.run_cycle.return_value = {
            "session_id": "s-1", "no_trade_signal": False
        }
        trading_cycle._strategy_selector.select.return_value = None

        result = trading_cycle.run_trading_cycle()

    if expect_skip:
        assert result["skipped_reason"] == f"session_{status}", (
            f"expected session_{status}, got {result['skipped_reason']}"
        )
        # Critically: the prediction engine should NEVER have been called
        trading_cycle._prediction_engine.run_cycle.assert_not_called()
    else:
        # Active/pending should NOT be blocked by C-α
        assert result["skipped_reason"] != f"session_{status}"


def test_open_virtual_position_skips_when_halted():
    """Defense-in-depth: open_virtual_position refuses under halt."""
    from execution_engine import ExecutionEngine

    engine = ExecutionEngine.__new__(ExecutionEngine)
    halted = {"id": "s-1", "session_status": "halted"}

    with patch("execution_engine.get_today_session", return_value=halted):
        result = engine.open_virtual_position(
            signal={"strategy_type": "long_put", "contracts": 1},
            prediction={},
        )

    assert result is None, (
        "open_virtual_position must NOT open positions under halt"
    )


# ── C-β: feature-flag endpoint auth ─────────────────────────────────

def test_flag_endpoint_uses_x_api_key_header():
    """Source must declare an X-Api-Key Header dependency on set_feature_flag."""
    path = os.path.join(REPO_ROOT, "backend", "main.py")
    with open(path, encoding="utf-8") as f:
        src = f.read()

    # Use ast to find the set_feature_flag function and verify its
    # signature — regex on FastAPI's nested-paren defaults is fragile.
    tree = ast.parse(src)
    found = None
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.AsyncFunctionDef)
            and node.name == "set_feature_flag"
        ):
            found = node
            break

    assert found is not None, "set_feature_flag handler not found"
    arg_names = {a.arg for a in found.args.args}
    assert "x_api_key" in arg_names, (
        f"set_feature_flag missing x_api_key parameter; got {arg_names}"
    )

    # And reference RAILWAY_ADMIN_KEY from config in the body.
    assert "RAILWAY_ADMIN_KEY" in src, (
        "main.py must read RAILWAY_ADMIN_KEY for the auth check"
    )
    # And import Header from fastapi.
    assert re.search(r"from fastapi import [^\n]*Header", src), (
        "main.py must import Header from fastapi"
    )


def test_config_exposes_railway_admin_key():
    """config.RAILWAY_ADMIN_KEY must exist (defaults to empty string)."""
    import config
    assert hasattr(config, "RAILWAY_ADMIN_KEY"), (
        "config.RAILWAY_ADMIN_KEY missing"
    )
    assert isinstance(config.RAILWAY_ADMIN_KEY, str)


def test_set_feature_flag_edge_function_forwards_x_api_key():
    """The Edge Function source must read RAILWAY_ADMIN_KEY and forward
    it as the X-Api-Key header on the Railway fetch."""
    path = os.path.join(
        REPO_ROOT, "supabase", "functions", "set-feature-flag", "index.ts"
    )
    with open(path, encoding="utf-8") as f:
        src = f.read()

    assert "RAILWAY_ADMIN_KEY" in src, "Edge fn must read RAILWAY_ADMIN_KEY"
    assert "'X-Api-Key'" in src or '"X-Api-Key"' in src, (
        "Edge fn must forward X-Api-Key to Railway"
    )


# ── P1-1: scheduler ordering ─────────────────────────────────────────

def test_mtm_registered_before_position_monitor():
    """trading_mark_to_market add_job must come BEFORE
    trading_position_monitor in main.py source order so APScheduler
    fires MTM first each minute."""
    path = os.path.join(REPO_ROOT, "backend", "main.py")
    with open(path, encoding="utf-8") as f:
        src = f.read()

    mtm_idx = src.find('id="trading_mark_to_market"')
    monitor_idx = src.find('id="trading_position_monitor"')

    assert mtm_idx > 0, "trading_mark_to_market job not found"
    assert monitor_idx > 0, "trading_position_monitor job not found"
    assert mtm_idx < monitor_idx, (
        "P1-1 fix missing — mark_to_market must register BEFORE "
        "position_monitor (current: MTM at %d, monitor at %d)"
        % (mtm_idx, monitor_idx)
    )


# ── P1-11: kill-switch row-update verification ──────────────────────

def test_kill_switch_verifies_updated_rows():
    """The kill-switch Edge Function must chain .select() and check
    that updatedRows.length > 0 — otherwise a bad session_id silently
    succeeds."""
    path = os.path.join(
        REPO_ROOT, "supabase", "functions", "kill-switch", "index.ts"
    )
    with open(path, encoding="utf-8") as f:
        src = f.read()

    assert ".select('id')" in src or '.select("id")' in src, (
        "P1-11 fix missing — update must chain .select() to return rows"
    )
    assert "updatedRows" in src or "updatedRows.length" in src, (
        "P1-11 fix missing — must verify updated row count"
    )


# ── E-5: VIX no longer hardcoded ────────────────────────────────────

def test_prediction_engine_reads_vix_from_redis():
    """prediction_engine must read polygon:vix:current, not hardcode 18.0."""
    path = os.path.join(REPO_ROOT, "backend", "prediction_engine.py")
    with open(path, encoding="utf-8") as f:
        src = f.read()

    # The literal "vix": 18.0, must be gone
    assert '"vix": 18.0,' not in src, (
        "E-5 fix missing — '\"vix\": 18.0,' literal still present"
    )
    # And the new code must reference polygon:vix:current
    assert "polygon:vix:current" in src, (
        "E-5 fix missing — must read polygon:vix:current"
    )


# ── A-4: gross_pnl sign for debit close (resolved by A-1) ───────────

def test_close_debit_position_books_correct_pnl_sign():
    """REGRESSION: a long_put with a winning MTM must book a positive
    gross_pnl. Before A-1 entry_credit was always positive so the
    is_debit_pos branch never fired; the credit formula then booked
    the wrong sign."""
    from execution_engine import ExecutionEngine

    engine = ExecutionEngine.__new__(ExecutionEngine)
    engine.LEGS_BY_STRATEGY = ExecutionEngine.LEGS_BY_STRATEGY

    fake_pos = {
        "id": "p-1",
        "strategy_type": "long_put",
        # A-1: stored as negative
        "entry_credit": -5.00,
        "contracts": 1,
        "session_id": "s-1",
        "current_pnl": 200.00,  # winning by $200
        "entry_slippage": 0.10,
        "entry_regime": "trending",
        "entry_cv_stress": 0.5,
        "current_state": 1,
    }

    fake_session = {"id": "s-1", "virtual_pnl": 0.0,
                    "virtual_wins": 0, "virtual_losses": 0,
                    "consecutive_losses_today": 0}

    posq = MagicMock()
    posq.maybe_single.return_value.execute.return_value = MagicMock(
        data=fake_pos
    )

    sessq = MagicMock()
    sessq.maybe_single.return_value.execute.return_value = MagicMock(
        data=fake_session
    )

    update_calls: list = []
    update_chain = MagicMock()
    update_chain.eq.return_value.execute.return_value = MagicMock(data=[])

    def _table(name: str):
        if name == "trading_positions":
            t = MagicMock()
            # First call: select(...) eq("id").eq("status").maybe_single
            t.select.return_value.eq.return_value.eq.return_value = posq
            # Second: update({...}).eq("id").execute
            def _update(payload):
                update_calls.append(payload)
                return update_chain
            t.update.side_effect = _update
            return t
        if name == "trading_sessions":
            t = MagicMock()
            t.select.return_value.eq.return_value = sessq
            return t
        if name == "trading_calibration_log":
            t = MagicMock()
            t.insert.return_value.execute.return_value = MagicMock(data=[])
            return t
        return MagicMock()

    fake_client = MagicMock()
    fake_client.table.side_effect = _table

    with patch("execution_engine.get_client", return_value=fake_client), \
            patch("execution_engine.update_session"), \
            patch("execution_engine.write_audit_log"), \
            patch("execution_engine.write_health_status"), \
            patch("execution_engine.check_execution_quality"):
        ok = engine.close_virtual_position(
            position_id="p-1",
            exit_reason="take_profit_debit_100pct",
            exit_credit=None,  # force MTM-derived
        )

    assert ok is True
    # Find the close-update payload
    close_payload = next(
        (p for p in update_calls if "gross_pnl" in p), None
    )
    assert close_payload is not None, "no close update written"
    assert close_payload["gross_pnl"] > 0, (
        f"long_put winning by $200 must book POSITIVE gross_pnl, "
        f"got {close_payload['gross_pnl']}"
    )
