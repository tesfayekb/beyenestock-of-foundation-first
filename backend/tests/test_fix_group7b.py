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
