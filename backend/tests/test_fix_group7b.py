"""
Tests for Fix Group 7B: Strike selection + mark-to-market.
Covers: strike fallback logic, iron condor four-strike output,
Black-Scholes pricing, mark-to-market no-position case,
0DTE expiry weekday constraint.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_strike_selector_fallback_returns_valid_strikes():
    """Fallback strike selection returns valid put_credit_spread strikes."""
    from unittest.mock import MagicMock, patch
    from strike_selector import get_strikes

    mock_redis = MagicMock()
    mock_redis.get.return_value = None  # no SPX quote

    with patch("strike_selector._get_option_chain_tradier", return_value=[]):
        result = get_strikes("put_credit_spread", mock_redis)

    assert result["short_strike"] is not None
    assert result["long_strike"] is not None
    assert result["short_strike"] > result["long_strike"]
    assert result["expiry_date"] is not None


def test_strike_selector_iron_condor_has_four_strikes():
    """Iron condor fallback returns all 4 strikes."""
    from unittest.mock import MagicMock, patch
    from strike_selector import get_strikes

    mock_redis = MagicMock()
    mock_redis.get.return_value = None

    with patch("strike_selector._get_option_chain_tradier", return_value=[]):
        result = get_strikes("iron_condor", mock_redis)

    assert result["short_strike"] is not None
    assert result["long_strike"] is not None
    assert result["short_strike_2"] is not None
    assert result["long_strike_2"] is not None


def test_bs_option_price_put_otm():
    """Black-Scholes put OTM should return positive price."""
    from mark_to_market import _bs_option_price
    # SPX at 5200, put at 5100 (100 OTM), 0.002y, 15% IV
    price = _bs_option_price(S=5200, K=5100, T=0.002, sigma=0.15, option_type="P")
    assert price >= 0.0
    assert price < 50.0  # sanity: OTM 0DTE put should be cheap


def test_bs_option_price_call_atm():
    """Black-Scholes ATM call should return positive price (skipped if scipy absent)."""
    import pytest
    scipy = pytest.importorskip("scipy", reason="scipy not installed in dev env")
    from mark_to_market import _bs_option_price
    price = _bs_option_price(S=5200, K=5200, T=0.01, sigma=0.15, option_type="C")
    assert price > 0.0


def test_mark_to_market_handles_no_positions():
    """run_mark_to_market returns zeros when no open positions."""
    from unittest.mock import patch, MagicMock
    from mark_to_market import run_mark_to_market

    mock_redis = MagicMock()
    with patch("mark_to_market.get_client") as mock_db, \
         patch("mark_to_market.write_health_status"):
        mock_db.return_value.table.return_value.select.return_value\
            .eq.return_value.eq.return_value.execute.return_value.data = []
        result = run_mark_to_market(mock_redis)

    assert result["updated"] == 0


def test_0dte_expiry_is_weekday():
    """_get_0dte_expiry always returns a weekday date."""
    from strike_selector import _get_0dte_expiry
    from datetime import date
    expiry = _get_0dte_expiry()
    d = date.fromisoformat(expiry)
    assert d.weekday() < 5, f"{expiry} is not a weekday"


# ── Commit 1 (2026-04-25): IC/IB target_credit chain extraction ────────────
#
# The iron_condor / iron_butterfly block in get_strikes() correctly
# selected strikes from the Tradier chain but never extracted
# target_credit. Result: strategy_selector fell through to the
# stale PLACEHOLDER_CREDIT_BY_STRATEGY (calibrated for SPX ~5200),
# booking entry_credit ≈ $2.30 against a real-market value of $5+.
# mark_to_market then read live chain prices and produced an instant
# phantom loss on every IC/IB entry.
#
# These three tests pin the fix:
#   1. With a complete chain, target_credit equals the 4-leg mid-price sum.
#   2. With an incomplete chain, target_credit stays None — strikes are
#      still populated; PLACEHOLDER fallback engages upstream as today.
#   3. Iron butterfly uses the same 4-leg formula as iron condor.
#
# Tests follow the existing fixture pattern in this file: MagicMock
# Redis, patch _get_option_chain_tradier for chain content, and patch
# _find_strike_by_delta for deterministic strike selection (greeks
# math is exercised in the existing fallback tests above).


def test_iron_condor_target_credit_extracted_from_chain():
    """IC target_credit = (short_put - long_put) + (short_call - long_call)
    from Tradier chain mid-prices."""
    from unittest.mock import MagicMock, patch
    from strike_selector import get_strikes

    mock_redis = MagicMock()
    mock_redis.get.return_value = None  # symmetric GEX, default VIX=18 → width 15

    # 4 legs at SPX ~7100 with 15-pt symmetric wings.
    # put_short=7080 (mid 4.50), put_long=7065 (mid 1.20)
    # call_short=7120 (mid 4.10), call_long=7135 (mid 1.10)
    # Expected target_credit = (4.50 - 1.20) + (4.10 - 1.10) = 6.30
    chain = [
        {"strike": 7080, "option_type": "put",  "bid": 4.45, "ask": 4.55, "greeks": {"delta": -0.16}},
        {"strike": 7065, "option_type": "put",  "bid": 1.15, "ask": 1.25, "greeks": {"delta": -0.10}},
        {"strike": 7120, "option_type": "call", "bid": 4.05, "ask": 4.15, "greeks": {"delta":  0.16}},
        {"strike": 7135, "option_type": "call", "bid": 1.05, "ask": 1.15, "greeks": {"delta":  0.10}},
    ]

    with patch(
        "strike_selector._get_option_chain_tradier", return_value=chain
    ), patch(
        "strike_selector._find_strike_by_delta",
        side_effect=lambda c, d, t, abv: 7080.0 if t == "put" else 7120.0,
    ):
        result = get_strikes("iron_condor", mock_redis)

    assert result["short_strike"] == 7080.0
    assert result["long_strike"] == 7080.0 - 15.0
    assert result["short_strike_2"] == 7120.0
    assert result["long_strike_2"] == 7120.0 + 15.0
    assert result["target_credit"] == 6.30


def test_iron_condor_target_credit_none_when_chain_incomplete():
    """Missing leg (or any bid/ask=0) → target_credit None; strikes
    still populated. Upstream PLACEHOLDER fallback engages as today —
    that's the existing graceful-degradation path."""
    from unittest.mock import MagicMock, patch
    from strike_selector import get_strikes

    mock_redis = MagicMock()
    mock_redis.get.return_value = None

    # Chain MISSING the call_long leg (7135 not present). The other 3
    # legs have valid bid/ask.
    chain = [
        {"strike": 7080, "option_type": "put",  "bid": 4.45, "ask": 4.55, "greeks": {"delta": -0.16}},
        {"strike": 7065, "option_type": "put",  "bid": 1.15, "ask": 1.25, "greeks": {"delta": -0.10}},
        {"strike": 7120, "option_type": "call", "bid": 4.05, "ask": 4.15, "greeks": {"delta":  0.16}},
        # 7135 call_long deliberately missing
    ]

    with patch(
        "strike_selector._get_option_chain_tradier", return_value=chain
    ), patch(
        "strike_selector._find_strike_by_delta",
        side_effect=lambda c, d, t, abv: 7080.0 if t == "put" else 7120.0,
    ):
        result = get_strikes("iron_condor", mock_redis)

    # Strikes must still be populated — geometry succeeded.
    assert result["short_strike"] == 7080.0
    assert result["long_strike"] == 7080.0 - 15.0
    assert result["short_strike_2"] == 7120.0
    assert result["long_strike_2"] == 7120.0 + 15.0
    # Credit lookup failed cleanly — no partial value, no placeholder
    # injection here. Strategy_selector handles the fallback.
    assert result["target_credit"] is None


def test_iron_butterfly_target_credit_extracted_from_chain():
    """Iron butterfly uses the same 4-leg credit formula as iron condor.
    Geometry differs (ATM short / OTM long) but the credit math is
    structurally identical."""
    from unittest.mock import MagicMock, patch
    from strike_selector import get_strikes

    mock_redis = MagicMock()
    mock_redis.get.return_value = None

    # iron_butterfly target_delta = 0.50 (ATM). _find_strike_by_delta
    # returns the ATM strike for BOTH put and call legs.
    # ATM = 7100. Wings ±15.
    # short_put=7100 (mid 35.00), long_put=7085 (mid 25.00)
    # short_call=7100 (mid 32.00), long_call=7115 (mid 22.00)
    # target_credit = (35.00 - 25.00) + (32.00 - 22.00) = 20.00
    chain = [
        {"strike": 7100, "option_type": "put",  "bid": 34.95, "ask": 35.05, "greeks": {"delta": -0.50}},
        {"strike": 7085, "option_type": "put",  "bid": 24.95, "ask": 25.05, "greeks": {"delta": -0.40}},
        {"strike": 7100, "option_type": "call", "bid": 31.95, "ask": 32.05, "greeks": {"delta":  0.50}},
        {"strike": 7115, "option_type": "call", "bid": 21.95, "ask": 22.05, "greeks": {"delta":  0.40}},
    ]

    with patch(
        "strike_selector._get_option_chain_tradier", return_value=chain
    ), patch(
        "strike_selector._find_strike_by_delta",
        side_effect=lambda c, d, t, abv: 7100.0,
    ):
        result = get_strikes("iron_butterfly", mock_redis)

    assert result["short_strike"] == 7100.0
    assert result["long_strike"] == 7100.0 - 15.0
    assert result["short_strike_2"] == 7100.0
    assert result["long_strike_2"] == 7100.0 + 15.0
    assert result["target_credit"] == 20.00


# Commit 3 (PCS/CCS target_credit net-spread fix) — chain-extraction tests.
#
# These tests verify that PCS/CCS target_credit is computed as the NET spread
# (short_mid - long_mid) via the module-level _chain_leg_mid helper, not the
# pre-Commit-3 single-leg-mid bug (which used only the short leg's mid). The
# IC/IB tests above (lines 111 and 183) serve as the regression-equivalence
# proof for the helper refactor — they pin target_credit == 6.30 / 20.00 and
# MUST pass without modification post-refactor.
#
# Pre-fix bug shape (eliminated by Commit 3):
#   target_credit = round((short_bid + short_ask) / 2, 2)  # single leg
# Post-fix correct shape:
#   target_credit = round(short_mid - long_mid, 2)  # net spread


def test_put_credit_spread_target_credit_extracted_from_chain():
    """PCS target_credit = short_mid - long_mid from Tradier chain mid-prices.

    Pre-Commit-3 bug returned short_mid only (4.50). Post-fix returns the
    net spread (3.30) which is the actual credit collected per contract.
    """
    from unittest.mock import MagicMock, patch
    from strike_selector import get_strikes

    mock_redis = MagicMock()
    mock_redis.get.return_value = None  # default VIX=18 -> width 15

    # SPX ~7100 with 15-pt width.
    # short_put=7080 (mid 4.50), long_put=7065 (mid 1.20)
    # Expected target_credit = 4.50 - 1.20 = 3.30
    chain = [
        {"strike": 7080, "option_type": "put", "bid": 4.40, "ask": 4.60, "greeks": {"delta": -0.16}},
        {"strike": 7065, "option_type": "put", "bid": 1.10, "ask": 1.30, "greeks": {"delta": -0.10}},
    ]

    with patch(
        "strike_selector._get_option_chain_tradier", return_value=chain
    ), patch(
        "strike_selector._find_strike_by_delta",
        side_effect=lambda c, d, t, abv: 7080.0,
    ):
        result = get_strikes("put_credit_spread", mock_redis)

    assert result["short_strike"] == 7080.0
    assert result["long_strike"] == 7080.0 - 15.0
    assert result["target_credit"] == 3.30


def test_call_credit_spread_target_credit_extracted_from_chain():
    """CCS target_credit = short_mid - long_mid from Tradier chain mid-prices.

    Symmetric to PCS test above; long_strike = short + width (calls go up).
    """
    from unittest.mock import MagicMock, patch
    from strike_selector import get_strikes

    mock_redis = MagicMock()
    mock_redis.get.return_value = None

    # SPX ~7100 with 15-pt width.
    # short_call=7120 (mid 4.00), long_call=7135 (mid 1.00)
    # Expected target_credit = 4.00 - 1.00 = 3.00
    chain = [
        {"strike": 7120, "option_type": "call", "bid": 3.90, "ask": 4.10, "greeks": {"delta": 0.16}},
        {"strike": 7135, "option_type": "call", "bid": 0.90, "ask": 1.10, "greeks": {"delta": 0.10}},
    ]

    with patch(
        "strike_selector._get_option_chain_tradier", return_value=chain
    ), patch(
        "strike_selector._find_strike_by_delta",
        side_effect=lambda c, d, t, abv: 7120.0,
    ):
        result = get_strikes("call_credit_spread", mock_redis)

    assert result["short_strike"] == 7120.0
    assert result["long_strike"] == 7120.0 + 15.0
    assert result["target_credit"] == 3.00


def test_put_credit_spread_target_credit_none_when_chain_incomplete():
    """Missing long-put leg (or any bid/ask=0) -> target_credit None;
    strikes still populated. Mirrors the IC None-fallback test pattern.

    Upstream PLACEHOLDER fallback engages as today — that's the existing
    graceful-degradation path."""
    from unittest.mock import MagicMock, patch
    from strike_selector import get_strikes

    mock_redis = MagicMock()
    mock_redis.get.return_value = None

    # Chain MISSING the long_put leg (7065). Short leg has valid bid/ask.
    chain = [
        {"strike": 7080, "option_type": "put", "bid": 4.40, "ask": 4.60, "greeks": {"delta": -0.16}},
        # 7065 long_put deliberately missing
    ]

    with patch(
        "strike_selector._get_option_chain_tradier", return_value=chain
    ), patch(
        "strike_selector._find_strike_by_delta",
        side_effect=lambda c, d, t, abv: 7080.0,
    ):
        result = get_strikes("put_credit_spread", mock_redis)

    # Strikes still populated — geometry succeeded.
    assert result["short_strike"] == 7080.0
    assert result["long_strike"] == 7080.0 - 15.0
    # Credit lookup failed cleanly — no partial value, no placeholder
    # injection here. Strategy_selector handles the fallback.
    assert result.get("target_credit") is None


def test_call_credit_spread_target_credit_none_when_chain_incomplete():
    """Missing long-call leg -> target_credit None; strikes still populated.
    Symmetric to PCS None-fallback test above."""
    from unittest.mock import MagicMock, patch
    from strike_selector import get_strikes

    mock_redis = MagicMock()
    mock_redis.get.return_value = None

    # Chain MISSING the long_call leg (7135). Short leg has valid bid/ask.
    chain = [
        {"strike": 7120, "option_type": "call", "bid": 3.90, "ask": 4.10, "greeks": {"delta": 0.16}},
        # 7135 long_call deliberately missing
    ]

    with patch(
        "strike_selector._get_option_chain_tradier", return_value=chain
    ), patch(
        "strike_selector._find_strike_by_delta",
        side_effect=lambda c, d, t, abv: 7120.0,
    ):
        result = get_strikes("call_credit_spread", mock_redis)

    assert result["short_strike"] == 7120.0
    assert result["long_strike"] == 7120.0 + 15.0
    assert result.get("target_credit") is None
