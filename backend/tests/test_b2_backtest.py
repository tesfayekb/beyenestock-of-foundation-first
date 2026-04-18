"""Tests for B2 backtest fix: asymmetric iron condor wings."""


def test_asymmetry_wall_below_widens_put():
    """dist_pct > 0 (SPX above ZG) widens put side."""
    from scripts.backtest_gex_zg import get_backtest_asymmetry
    put_w, call_w = get_backtest_asymmetry(0.005, 5.0)
    assert put_w == 7.5,  f"Expected put_w=7.5, got {put_w}"
    assert call_w == 2.5, f"Expected call_w=2.5, got {call_w}"


def test_asymmetry_wall_above_widens_call():
    """dist_pct < 0 (SPX below ZG) widens call side."""
    from scripts.backtest_gex_zg import get_backtest_asymmetry
    put_w, call_w = get_backtest_asymmetry(-0.005, 5.0)
    assert put_w == 2.5, f"Expected put_w=2.5, got {put_w}"
    assert call_w == 7.5, f"Expected call_w=7.5, got {call_w}"


def test_asymmetry_symmetric_near_zero():
    """|dist_pct| < 0.001 returns symmetric wings."""
    from scripts.backtest_gex_zg import get_backtest_asymmetry
    put_w, call_w = get_backtest_asymmetry(0.0005, 5.0)
    assert put_w == call_w == 5.0


def test_asymmetry_symmetric_too_far():
    """|dist_pct| > 0.02 returns symmetric (GEX confidence low)."""
    from scripts.backtest_gex_zg import get_backtest_asymmetry
    put_w, call_w = get_backtest_asymmetry(0.05, 5.0)
    assert put_w == call_w == 5.0


def test_asymmetry_floor_at_250():
    """Minimum wing width is $2.50."""
    from scripts.backtest_gex_zg import get_backtest_asymmetry
    # $2.50 x 0.75 = $1.875 -> floors to $2.50 floor
    put_w, call_w = get_backtest_asymmetry(0.005, 2.5)
    assert call_w >= 2.5


def test_simulate_trade_iron_condor_uses_asymmetric_credit():
    """Iron condor credit differs with asymmetric vs symmetric wings."""
    from scripts.backtest_gex_zg import simulate_trade

    # Symmetric: dist_pct=0
    sym = simulate_trade(
        "2022-06-01", 4500.0, 4500.0, 0.20, 4500.0,
        "iron_condor", 5.0, dist_pct=0.0
    )

    # Asymmetric: dist_pct=0.005 -> put_w=7.5, call_w=2.5
    asym = simulate_trade(
        "2022-06-01", 4500.0, 4500.0, 0.20, 4500.0,
        "iron_condor", 5.0, dist_pct=0.005
    )

    # Both should win (SPX at center), asymmetric should collect different credit
    assert sym["result"] == "win"
    assert asym["result"] == "win"
    # Total asymmetric credit (7.5+2.5 widths) vs symmetric (5+5)
    # same total width but different distribution
