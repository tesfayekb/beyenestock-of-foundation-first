"""Tests for GEX/ZG backtest signal logic."""


def test_classify_regime_pin_range():
    """SPX above ZG, low vol -> pin_range."""
    from scripts.backtest_gex_zg import classify_regime
    assert classify_regime(0.005, 0.5) == "pin_range"


def test_classify_regime_quiet_bullish():
    """SPX slightly above ZG, very calm -> quiet_bullish."""
    from scripts.backtest_gex_zg import classify_regime
    assert classify_regime(0.002, 0.3) == "quiet_bullish"


def test_classify_regime_volatile_bearish():
    """SPX below ZG, high vol -> volatile_bearish."""
    from scripts.backtest_gex_zg import classify_regime
    assert classify_regime(-0.005, 2.0) == "volatile_bearish"


def test_classify_regime_crisis():
    """Extreme vol -> crisis regardless of ZG position."""
    from scripts.backtest_gex_zg import classify_regime
    assert classify_regime(0.01, 3.0) == "crisis"
    assert classify_regime(-0.01, 3.0) == "crisis"


def test_regime_to_strategy_sit_out_regimes():
    """Directional and crisis regimes sit out."""
    from scripts.backtest_gex_zg import regime_to_strategy
    assert regime_to_strategy("volatile_bearish") == "sit_out"
    assert regime_to_strategy("trend") == "sit_out"
    assert regime_to_strategy("crisis") == "sit_out"


def test_regime_to_strategy_trade_regimes():
    """Range regimes produce tradeable strategies."""
    from scripts.backtest_gex_zg import regime_to_strategy
    assert regime_to_strategy("pin_range") == "iron_condor"
    assert regime_to_strategy("quiet_bullish") == "put_credit_spread"
    assert regime_to_strategy("range") == "iron_condor"


def test_simulate_trade_win():
    """Trade wins when SPX stays within short strikes."""
    from scripts.backtest_gex_zg import simulate_trade
    # Put credit spread: short strike ~5120 (1 sigma below 5200)
    # SPX closes at 5180 (above short strike) -> win
    result = simulate_trade(
        date="2022-06-01",
        spx_open=5200.0,
        spx_close=5180.0,
        iv_atm=0.20,
        zero_gamma=5150.0,
        strategy="put_credit_spread",
        spread_width=5.0,
    )
    assert result["result"] == "win"
    assert result["net_pnl"] > 0


def test_simulate_trade_loss():
    """Trade loses when SPX breaches short strike significantly."""
    from scripts.backtest_gex_zg import simulate_trade
    # Put credit spread: short strike ~5120
    # SPX crashes to 5050 (well below short strike) -> loss
    result = simulate_trade(
        date="2022-06-02",
        spx_open=5200.0,
        spx_close=4950.0,
        iv_atm=0.20,
        zero_gamma=5150.0,
        strategy="put_credit_spread",
        spread_width=5.0,
    )
    assert result["result"] == "loss"
    assert result["net_pnl"] < 0


def test_estimate_credit_positive():
    """Credit estimate is positive for valid inputs."""
    from scripts.backtest_gex_zg import estimate_credit
    credit = estimate_credit(0.20, 5.0, "put_credit_spread")
    assert credit > 0
    iron_condor_credit = estimate_credit(0.20, 5.0, "iron_condor")
    assert iron_condor_credit > credit  # iron condor collects more
