"""Tests for Phase B Session 1: dynamic spread width."""


def test_get_dynamic_spread_width_low_vix():
    """VIX < 15 returns $2.50 width."""
    from strike_selector import get_dynamic_spread_width
    assert get_dynamic_spread_width(12.0) == 2.50
    assert get_dynamic_spread_width(14.9) == 2.50


def test_get_dynamic_spread_width_normal_vix():
    """VIX 15-20 returns $5.00 width."""
    from strike_selector import get_dynamic_spread_width
    assert get_dynamic_spread_width(15.0) == 5.00
    assert get_dynamic_spread_width(18.0) == 5.00
    assert get_dynamic_spread_width(19.9) == 5.00


def test_get_dynamic_spread_width_elevated_vix():
    """VIX 20-30 returns $7.50 width."""
    from strike_selector import get_dynamic_spread_width
    assert get_dynamic_spread_width(20.0) == 7.50
    assert get_dynamic_spread_width(25.0) == 7.50
    assert get_dynamic_spread_width(29.9) == 7.50


def test_get_dynamic_spread_width_high_stress():
    """VIX >= 30 returns $10.00 width."""
    from strike_selector import get_dynamic_spread_width
    assert get_dynamic_spread_width(30.0) == 10.00
    assert get_dynamic_spread_width(45.0) == 10.00
    assert get_dynamic_spread_width(80.0) == 10.00


def test_get_dynamic_spread_width_invalid():
    """Invalid VIX (0 or negative) returns default $5.00."""
    from strike_selector import get_dynamic_spread_width, DEFAULT_SPREAD_WIDTH
    assert get_dynamic_spread_width(0.0) == DEFAULT_SPREAD_WIDTH
    assert get_dynamic_spread_width(-1.0) == DEFAULT_SPREAD_WIDTH


def test_get_strikes_uses_vix_from_redis():
    """get_strikes returns width based on VIX from Redis."""
    from unittest.mock import MagicMock, patch
    from strike_selector import get_strikes

    mock_redis = MagicMock()
    # VIX = 25 -> should return $7.50 width
    mock_redis.get.side_effect = lambda key: (
        b"25.0" if key == "polygon:vix:current" else
        b"5200.0" if key == "tradier:quotes:SPX" else None
    )

    with patch("strike_selector._get_option_chain_tradier", return_value=[]):
        result = get_strikes("put_credit_spread", mock_redis)

    assert result["spread_width"] == 7.50, \
        f"Expected $7.50 for VIX=25, got ${result['spread_width']}"


def test_get_strikes_fallback_width_when_no_vix():
    """get_strikes uses $5.00 default when VIX not in Redis."""
    from unittest.mock import MagicMock, patch
    from strike_selector import get_strikes

    mock_redis = MagicMock()
    mock_redis.get.return_value = None  # no VIX data

    with patch("strike_selector._get_option_chain_tradier", return_value=[]):
        result = get_strikes("put_credit_spread", mock_redis)

    assert result["spread_width"] == 5.00, \
        f"Expected $5.00 default when no VIX data, got ${result['spread_width']}"


def test_fallback_strikes_uses_dynamic_width():
    """_fallback_strikes uses the passed spread_width, not hardcoded $5."""
    from strike_selector import _fallback_strikes

    result_narrow = _fallback_strikes(5200.0, "put_credit_spread", spread_width=2.50)
    result_wide   = _fallback_strikes(5200.0, "put_credit_spread", spread_width=10.00)

    assert result_narrow["spread_width"] == 2.50
    assert result_wide["spread_width"] == 10.00

    # Long strike should differ by the spread width
    narrow_diff = result_narrow["short_strike"] - result_narrow["long_strike"]
    wide_diff   = result_wide["short_strike"] - result_wide["long_strike"]
    assert narrow_diff == 2.50, f"Narrow spread long-short diff should be 2.50, got {narrow_diff}"
    assert wide_diff == 10.00, f"Wide spread long-short diff should be 10.00, got {wide_diff}"


def test_get_strikes_tradier_chain_uses_dynamic_width():
    """Tradier happy-path: long_strike reflects dynamic_width, not hardcoded $5.
    Covers the consistency fix (option B) where the chain branch previously
    used DEFAULT_SPREAD_WIDTH regardless of VIX regime."""
    from unittest.mock import MagicMock, patch
    from strike_selector import get_strikes

    mock_redis = MagicMock()
    # VIX = 25 -> dynamic_width should be $7.50
    mock_redis.get.side_effect = lambda key: (
        b"25.0" if key == "polygon:vix:current" else None
    )

    # Minimal chain: one put at strike 5150 with delta -0.16 (target match)
    mock_chain = [
        {
            "option_type": "put",
            "strike": 5150.0,
            "greeks": {"delta": -0.16},
            "bid": 1.40,
            "ask": 1.50,
        }
    ]

    with patch("strike_selector._get_option_chain_tradier", return_value=mock_chain):
        result = get_strikes("put_credit_spread", mock_redis)

    assert result["spread_width"] == 7.50, \
        f"Expected $7.50 for VIX=25, got ${result['spread_width']}"
    assert result["short_strike"] == 5150.0, \
        f"Expected short_strike=5150.0, got {result['short_strike']}"
    assert result["long_strike"] == 5150.0 - 7.50, \
        (f"Expected long_strike=5142.5 (short - dynamic_width 7.50), "
         f"got {result['long_strike']}")
