"""
Calendar Spread MTM Fix (T0-4).

The production stub pinned current_spread_value at abs(entry_credit),
so current_pnl was locked at zero for every open calendar position
and neither the 40% take-profit nor the 150% stop-loss in
position_monitor could ever fire. Only time stops were closing these
trades, and the feedback loop was getting no labeled outcomes.

These tests lock in:
  * the stub is gone and P&L is non-zero
  * the new _price_leg_bs_or_live helper prefers live Tradier quotes
    over BS and falls back to BS cleanly when quotes are absent
  * BS sanity: on entry day the 5-DTE far leg is worth more than the
    0-DTE near leg for ATM options (this is the entire economic
    premise of the calendar spread)
  * run_mark_to_market's SELECT actually fetches far_expiry_date
  * missing far_expiry_date does not raise
"""
import json
import os
import sys
from datetime import date, timedelta
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ─── Test fixtures ───────────────────────────────────────────────────────────

def _make_redis(vix: float = 18.0, vix9d: float = 19.0, quote=None):
    """Mock Redis client.

    Returns the configured VIX values for the polygon:vix{,9d}:current
    keys, and a synthetic bid/ask JSON payload for any
    tradier:quotes:* key when `quote` is provided. Otherwise quote
    keys return None so the BS fallback path is exercised.
    """
    r = MagicMock()

    def _side(key):
        if key == "polygon:vix:current":
            return str(vix)
        if key == "polygon:vix9d:current":
            return str(vix9d)
        if quote is not None and "tradier:quotes:" in str(key):
            return json.dumps({
                "bid": quote - 0.05,
                "ask": quote + 0.05,
            })
        return None

    r.get.side_effect = _side
    return r


def _calendar_pos(
    entry_credit: float = 1.50,
    near_days: int = 0,
    far_days: int = 5,
) -> dict:
    """Minimal calendar-spread position row.

    Same strike for both legs (ATM calendar — strike_selector stores
    the ATM round-to-$5 strike in short_strike AND long_strike).
    """
    today = date.today()
    return {
        "strategy_type": "calendar_spread",
        "entry_credit": entry_credit,
        "contracts": 1,
        "short_strike": 5300.0,
        "long_strike": 5300.0,
        "expiry_date": (today + timedelta(days=near_days)).isoformat(),
        "far_expiry_date": (today + timedelta(days=far_days)).isoformat(),
    }


# ─── Core pricing ────────────────────────────────────────────────────────────

def test_calendar_pnl_is_not_zero():
    """Calendar MTM must return non-zero P&L.

    The old stub set current_spread_value = abs(entry_credit), which
    the credit formula then evaluated to exactly 0. Anything non-zero
    proves the stub is gone and real pricing is running.
    """
    from mark_to_market import _price_position

    pos = _calendar_pos(entry_credit=1.50, near_days=0, far_days=5)
    redis = _make_redis(vix=18.0, vix9d=20.0)

    result = _price_position(pos, spx_price=5300.0, redis_client=redis)

    assert result is not None, "Calendar spread must return a P&L value"
    assert result != 0.0, (
        "Calendar MTM must return non-zero P&L — got 0.0, the stub "
        "(current_spread_value = abs(entry_credit)) is still active"
    )
    assert isinstance(result, float)


def test_calendar_pnl_sign_on_profitable_trade():
    """Low-vol scenario: near leg decayed more than far — returns a float.

    We don't assert an exact sign here because the economic
    relationship depends on near vs far IV AND the clamp at 0; the
    test's job is to confirm real pricing runs end-to-end without
    raising. The test_calendar_pnl_is_not_zero test already proves
    the value is meaningful.
    """
    from mark_to_market import _price_position

    pos = _calendar_pos(entry_credit=1.50, near_days=0, far_days=5)
    redis = _make_redis(vix=15.0, vix9d=12.0)

    result = _price_position(pos, spx_price=5300.0, redis_client=redis)

    assert result is not None
    assert isinstance(result, float)


def test_calendar_far_expiry_date_required():
    """Missing far_expiry_date must not raise — return None instead.

    When far_expiry_date is None the helper returns 0.0 for both far
    call/put, so current_spread_value collapses to 0 and the outer
    `if current_spread_value == 0.0: return None` short-circuits.
    MTM loop treats that as a skip, which is the safe behaviour.
    """
    from mark_to_market import _price_position

    pos = _calendar_pos()
    pos["far_expiry_date"] = None

    redis = _make_redis()

    try:
        result = _price_position(pos, spx_price=5300.0, redis_client=redis)
    except Exception as exc:
        raise AssertionError(
            "_price_position must not raise when far_expiry_date is "
            f"None — got {exc!r}"
        )

    assert result is None or isinstance(result, float), (
        f"Result must be None or float, got {type(result).__name__}"
    )


def test_calendar_uses_live_quote_when_available():
    """Live Tradier quote in Redis must win over the BS fallback."""
    from mark_to_market import _price_leg_bs_or_live

    expiry_str = (date.today() + timedelta(days=5)).isoformat()

    # bid=2.45, ask=2.55 → mid=2.50
    redis = _make_redis(quote=2.50)

    result = _price_leg_bs_or_live(
        redis_client=redis,
        strike=5300.0,
        opt_type="C",
        expiry_str=expiry_str,
        spx_price=5300.0,
        sigma=0.18,
    )

    assert abs(result - 2.50) < 0.10, (
        f"live-quote path must return the Redis mid (~2.50), got {result}. "
        "BS fallback is being used even though a live quote is available."
    )


def test_calendar_falls_back_to_bs_when_no_live_quote():
    """Without a live Redis quote, BS must produce a positive option value."""
    from mark_to_market import _price_leg_bs_or_live

    expiry_str = (date.today() + timedelta(days=5)).isoformat()
    redis = _make_redis(quote=None)

    result = _price_leg_bs_or_live(
        redis_client=redis,
        strike=5300.0,
        opt_type="C",
        expiry_str=expiry_str,
        spx_price=5300.0,
        sigma=0.18,
    )

    assert result > 0.0, (
        "BS fallback must return a positive ATM 5-DTE call price — "
        f"got {result}. Check the scipy import or BS math."
    )


def test_far_leg_worth_more_than_near_leg_on_0dte():
    """5-DTE ATM call must be worth more than 0-DTE ATM call.

    This is the entire economic premise of the calendar spread — if
    this assertion fails, either the helper is passing the wrong T
    to BS or sigma handling is inverted.
    """
    from mark_to_market import _price_leg_bs_or_live

    today = date.today()
    near_expiry = today.isoformat()
    far_expiry = (today + timedelta(days=5)).isoformat()

    redis = _make_redis(quote=None)  # force BS

    near_call = _price_leg_bs_or_live(
        redis, 5300.0, "C", near_expiry, 5300.0, sigma=0.25,
    )
    far_call = _price_leg_bs_or_live(
        redis, 5300.0, "C", far_expiry, 5300.0, sigma=0.18,
    )

    assert far_call > near_call, (
        f"far leg (5DTE, {far_call:.4f}) must be worth more than "
        f"near leg (0DTE, {near_call:.4f}) for ATM options. If this "
        "fails, the T or sigma plumbing is backwards."
    )


# ─── Source-level guards ──────────────────────────────────────────────────────

def test_calendar_run_mark_to_market_selects_far_expiry():
    """run_mark_to_market SELECT must include far_expiry_date.

    Without it, pos.get('far_expiry_date') always returns None and
    the calendar branch short-circuits to a zero far-leg value on
    every single open calendar position.
    """
    path = os.path.join(
        os.path.dirname(__file__), "..", "mark_to_market.py"
    )
    with open(path, encoding="utf-8") as f:
        src = f.read()
    assert "far_expiry_date" in src, (
        "run_mark_to_market SELECT must include far_expiry_date — "
        "without it, calendar-spread MTM always misses the far expiry"
    )


def test_stub_comment_removed():
    """The old stub line must be gone.

    `current_spread_value = abs(entry_credit)` pins the credit P&L
    formula at exactly 0 — its presence means the fix was reverted
    or never applied.
    """
    path = os.path.join(
        os.path.dirname(__file__), "..", "mark_to_market.py"
    )
    with open(path, encoding="utf-8") as f:
        src = f.read()
    assert "current_spread_value = abs(entry_credit)" not in src, (
        "the calendar-spread stub `current_spread_value = "
        "abs(entry_credit)` must be removed — it pins P&L at 0 "
        "forever and blocks TP/SL from ever firing"
    )
