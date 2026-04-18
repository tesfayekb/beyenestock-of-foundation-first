"""Tests for Phase 3C: Calendar spread strategy."""
from datetime import date


def test_calendar_spread_in_strategy_maps():
    """Calendar spread present in all required data structures."""
    from strategy_selector import (
        STATIC_SLIPPAGE_BY_STRATEGY,
        PLACEHOLDER_CREDIT_BY_STRATEGY,
        _NEUTRAL_PREFERRED,
        REGIME_STRATEGY_MAP,
    )
    assert "calendar_spread" in STATIC_SLIPPAGE_BY_STRATEGY
    assert "calendar_spread" in PLACEHOLDER_CREDIT_BY_STRATEGY
    assert "calendar_spread" in _NEUTRAL_PREFERRED
    assert "calendar_spread" in REGIME_STRATEGY_MAP.get("event", [])


def test_calendar_spread_risk_pct():
    """Calendar spread uses 0.3% risk budget."""
    from risk_engine import _DEBIT_RISK_PCT
    assert _DEBIT_RISK_PCT.get("calendar_spread") == 0.003


def test_calendar_sizing_nonzero():
    """Calendar spread sizing returns at least 1 contract."""
    from risk_engine import compute_position_size
    result = compute_position_size(
        account_value=100_000.0,
        spread_width=0,
        strategy_type="calendar_spread",
    )
    assert result["contracts"] >= 1
    assert result["risk_pct"] == 0.003


def test_next_friday_expiry_is_friday():
    """_get_next_friday_expiry always returns a Friday."""
    from strike_selector import _get_next_friday_expiry
    expiry = _get_next_friday_expiry()
    d = date.fromisoformat(expiry)
    assert d.weekday() == 4, (
        f"Expected Friday (weekday=4), got {d.strftime('%A')} ({d.weekday()})"
    )


def test_next_friday_is_after_today():
    """Far expiry is always strictly in the future (next Friday, not today)."""
    from strike_selector import _get_next_friday_expiry
    expiry = date.fromisoformat(_get_next_friday_expiry())
    assert expiry > date.today()


def test_calendar_strikes_include_both_expiries():
    """Calendar spread strikes include near_expiry and far_expiry plus all
    four legs at the ATM strike."""
    from unittest.mock import MagicMock
    from strike_selector import get_strikes
    mock_redis = MagicMock()
    mock_redis.get.return_value = b'{"last": 5200.0}'
    result = get_strikes("calendar_spread", mock_redis)
    # Both expiries should be present
    assert "near_expiry" in result
    assert "far_expiry" in result
    # All four legs at the same ATM strike
    assert result.get("short_strike") is not None
    assert result.get("long_strike") == result.get("short_strike")
    assert result.get("short_strike_2") == result.get("short_strike")
    assert result.get("long_strike_2") == result.get("short_strike")
    # ATM strike should be near 5200 (rounded to $5)
    assert abs(result["short_strike"] - 5200.0) <= 5.0
    # spread_width must be 0 so risk_engine takes the cost-based branch
    assert result.get("spread_width") == 0
    # Net target_credit positive (post-catalyst credit)
    assert result.get("target_credit") == 1.50


def test_calendar_spread_flag_off_by_default():
    """Calendar spread feature flag defaults to OFF."""
    from unittest.mock import MagicMock
    from strategy_selector import StrategySelector
    s = StrategySelector.__new__(StrategySelector)
    mock_redis = MagicMock()
    mock_redis.get.return_value = None
    s.redis_client = mock_redis
    assert s._check_feature_flag("strategy:calendar_spread:enabled") is False
