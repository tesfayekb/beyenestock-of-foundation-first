def test_panic_regime_has_no_candidates():
    """Panic regime must have an empty strategy list — no trades allowed."""
    from strategy_selector import REGIME_STRATEGY_MAP
    assert REGIME_STRATEGY_MAP["panic"] == []


def test_all_strategies_in_slippage_map_with_positive_value():
    """All 8 strategy types must be in STATIC_SLIPPAGE_BY_STRATEGY with value > 0."""
    from strategy_selector import STATIC_SLIPPAGE_BY_STRATEGY
    expected_strategies = {
        "put_credit_spread", "call_credit_spread", "iron_condor",
        "iron_butterfly", "debit_put_spread", "debit_call_spread",
        "long_put", "long_call",
    }
    for strategy in expected_strategies:
        assert strategy in STATIC_SLIPPAGE_BY_STRATEGY, (
            f"{strategy} missing from STATIC_SLIPPAGE_BY_STRATEGY"
        )
        assert STATIC_SLIPPAGE_BY_STRATEGY[strategy] > 0, (
            f"{strategy} slippage must be > 0"
        )


def test_short_and_long_gamma_strategies_have_no_overlap():
    """SHORT_GAMMA_STRATEGIES and LONG_GAMMA_STRATEGIES must be mutually exclusive."""
    from strategy_selector import SHORT_GAMMA_STRATEGIES, LONG_GAMMA_STRATEGIES
    overlap = SHORT_GAMMA_STRATEGIES & LONG_GAMMA_STRATEGIES
    assert overlap == set(), f"Unexpected overlap: {overlap}"
