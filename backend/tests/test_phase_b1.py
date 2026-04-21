"""Tests for Phase B Session 1: dynamic spread width.

Width table recalibrated 2026-04-20 for SPX at ~7000 levels. Previous
values (2.5/5/7.5/10) were designed for SPY and were too narrow at
SPX 7000 — a 5-point wing is 0.07% of spot and got blown through on
normal intraday moves. New values (10/15/20/30) keep the "hot zone"
between short and long wide enough to survive a ~0.25-sigma move
while letting a $100k paper account still produce contracts >= 1 at
Phase 1 core allocation. See commit history for the paired
risk_engine.py change that doubled Phase 1 risk_pct.
"""


def test_get_dynamic_spread_width_low_vix():
    """VIX < 15 returns $10 width (quiet regime)."""
    from strike_selector import get_dynamic_spread_width
    assert get_dynamic_spread_width(12.0) == 10.00
    assert get_dynamic_spread_width(14.9) == 10.00


def test_get_dynamic_spread_width_normal_vix():
    """VIX 15-20 returns $15 width (today's band)."""
    from strike_selector import get_dynamic_spread_width
    assert get_dynamic_spread_width(15.0) == 15.00
    assert get_dynamic_spread_width(18.0) == 15.00
    assert get_dynamic_spread_width(19.9) == 15.00


def test_get_dynamic_spread_width_elevated_vix():
    """VIX 20-30 returns $20 width."""
    from strike_selector import get_dynamic_spread_width
    assert get_dynamic_spread_width(20.0) == 20.00
    assert get_dynamic_spread_width(25.0) == 20.00
    assert get_dynamic_spread_width(29.9) == 20.00


def test_get_dynamic_spread_width_high_stress():
    """VIX >= 30 returns $30 width (crisis regime)."""
    from strike_selector import get_dynamic_spread_width
    assert get_dynamic_spread_width(30.0) == 30.00
    assert get_dynamic_spread_width(45.0) == 30.00
    assert get_dynamic_spread_width(80.0) == 30.00


def test_get_dynamic_spread_width_invalid():
    """Invalid VIX (0 or negative) returns DEFAULT_SPREAD_WIDTH."""
    from strike_selector import get_dynamic_spread_width, DEFAULT_SPREAD_WIDTH
    assert get_dynamic_spread_width(0.0) == DEFAULT_SPREAD_WIDTH
    assert get_dynamic_spread_width(-1.0) == DEFAULT_SPREAD_WIDTH


def test_default_spread_width_sized_for_spx():
    """DEFAULT_SPREAD_WIDTH must be >= 10pt to prevent drift back
    to the pre-2026-04-20 SPY-era values (which got blown through
    on any normal SPX intraday move at ~7000 price levels)."""
    from strike_selector import DEFAULT_SPREAD_WIDTH
    assert DEFAULT_SPREAD_WIDTH >= 10.0, (
        f"DEFAULT_SPREAD_WIDTH={DEFAULT_SPREAD_WIDTH} is too narrow "
        f"for SPX at ~7000 price levels. Must stay >= 10pt per the "
        f"2026-04-20 recalibration. See TASK_REGISTER.md Item 12."
    )


def test_width_table_floor_for_spx_price_levels():
    """Every width in VIX_SPREAD_WIDTH_TABLE must be >= 10pt.
    Regression guard for the 2026-04-20 recalibration — prevents a
    future refactor from accidentally restoring SPY-era values."""
    from strike_selector import VIX_SPREAD_WIDTH_TABLE
    for threshold, width in VIX_SPREAD_WIDTH_TABLE:
        assert width >= 10.0, (
            f"width={width} at VIX<{threshold} is narrower than the "
            f"10pt floor for SPX at ~7000 price levels. A 5-point "
            f"wing is 0.07% of spot and gets blown through on any "
            f"normal intraday move."
        )


def test_width_table_monotonically_widens_with_vix():
    """Width must not decrease as VIX rises — higher vol always
    warrants at least as wide a wing."""
    from strike_selector import VIX_SPREAD_WIDTH_TABLE
    widths = [w for _, w in VIX_SPREAD_WIDTH_TABLE]
    for i in range(1, len(widths)):
        assert widths[i] >= widths[i - 1], (
            f"width table not monotonic: row {i - 1} = {widths[i-1]}, "
            f"row {i} = {widths[i]}. Wider wings belong in higher-vol "
            f"regimes, not narrower."
        )


def test_get_strikes_uses_vix_from_redis():
    """get_strikes returns width based on VIX from Redis."""
    from unittest.mock import MagicMock, patch
    from strike_selector import get_strikes

    mock_redis = MagicMock()
    mock_redis.get.side_effect = lambda key: (
        b"25.0" if key == "polygon:vix:current" else
        b"5200.0" if key == "tradier:quotes:SPX" else None
    )

    with patch("strike_selector._get_option_chain_tradier", return_value=[]):
        result = get_strikes("put_credit_spread", mock_redis)

    assert result["spread_width"] == 20.00, \
        f"Expected $20.00 for VIX=25, got ${result['spread_width']}"


def test_get_strikes_fallback_width_when_no_vix():
    """get_strikes uses DEFAULT_SPREAD_WIDTH (15) when VIX not in Redis."""
    from unittest.mock import MagicMock, patch
    from strike_selector import get_strikes, DEFAULT_SPREAD_WIDTH

    mock_redis = MagicMock()
    mock_redis.get.return_value = None

    with patch("strike_selector._get_option_chain_tradier", return_value=[]):
        result = get_strikes("put_credit_spread", mock_redis)

    assert result["spread_width"] == DEFAULT_SPREAD_WIDTH, \
        f"Expected DEFAULT_SPREAD_WIDTH when no VIX data, got ${result['spread_width']}"


def test_fallback_strikes_uses_dynamic_width():
    """_fallback_strikes uses the passed spread_width, not a hardcoded default."""
    from strike_selector import _fallback_strikes

    result_narrow = _fallback_strikes(5200.0, "put_credit_spread", spread_width=10.00)
    result_wide = _fallback_strikes(5200.0, "put_credit_spread", spread_width=30.00)

    assert result_narrow["spread_width"] == 10.00
    assert result_wide["spread_width"] == 30.00

    narrow_diff = result_narrow["short_strike"] - result_narrow["long_strike"]
    wide_diff = result_wide["short_strike"] - result_wide["long_strike"]
    assert narrow_diff == 10.00, f"Narrow spread long-short diff should be 10.00, got {narrow_diff}"
    assert wide_diff == 30.00, f"Wide spread long-short diff should be 30.00, got {wide_diff}"


def test_get_strikes_tradier_chain_uses_dynamic_width():
    """Tradier happy-path: long_strike reflects dynamic_width, not hardcoded.
    Covers the consistency fix (option B) where the chain branch previously
    used DEFAULT_SPREAD_WIDTH regardless of VIX regime."""
    from unittest.mock import MagicMock, patch
    from strike_selector import get_strikes

    mock_redis = MagicMock()
    mock_redis.get.side_effect = lambda key: (
        b"25.0" if key == "polygon:vix:current" else None
    )

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

    assert result["spread_width"] == 20.00, \
        f"Expected $20.00 for VIX=25, got ${result['spread_width']}"
    assert result["short_strike"] == 5150.0, \
        f"Expected short_strike=5150.0, got {result['short_strike']}"
    assert result["long_strike"] == 5150.0 - 20.00, \
        (f"Expected long_strike=5130.0 (short - dynamic_width 20.00), "
         f"got {result['long_strike']}")
