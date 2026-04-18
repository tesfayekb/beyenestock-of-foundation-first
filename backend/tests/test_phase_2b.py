"""Tests for Phase 2B: Strategy wiring, gamma pin, long straddle.

Covers:
  - Debit/straddle risk percentages in risk_engine
  - compute_position_size strategy_type override and backwards compatibility
  - AI strategy hint override gated by feature flag
  - Gamma pin detection short-circuit to iron_butterfly
  - Long straddle in NEUTRAL_PREFERRED set
"""
from unittest.mock import MagicMock


def test_debit_risk_pct_smaller_than_credit():
    """Debit strategies use smaller risk % than credit strategies."""
    from risk_engine import _DEBIT_RISK_PCT, _RISK_PCT
    assert _DEBIT_RISK_PCT["debit_call_spread"] < _RISK_PCT[1]["core"]
    assert (
        _DEBIT_RISK_PCT["long_straddle"]
        < _DEBIT_RISK_PCT["debit_call_spread"]
    )
    assert _DEBIT_RISK_PCT["iron_butterfly"] < _RISK_PCT[1]["core"]


def test_compute_position_size_debit_smaller():
    """Debit strategy produces smaller risk_pct than credit at same account size."""
    from risk_engine import compute_position_size
    credit = compute_position_size(
        account_value=100_000.0,
        spread_width=5.0,
        strategy_type="iron_condor",
    )
    debit = compute_position_size(
        account_value=100_000.0,
        spread_width=5.0,
        strategy_type="debit_call_spread",
    )
    straddle = compute_position_size(
        account_value=100_000.0,
        spread_width=5.0,
        strategy_type="long_straddle",
    )
    assert credit["risk_pct"] >= debit["risk_pct"]
    assert debit["risk_pct"] >= straddle["risk_pct"]


def test_compute_position_size_default_unchanged():
    """Default strategy_type (iron_condor) matches explicit iron_condor."""
    from risk_engine import compute_position_size
    result = compute_position_size(
        account_value=100_000.0, spread_width=5.0,
    )
    result_explicit = compute_position_size(
        account_value=100_000.0,
        spread_width=5.0,
        strategy_type="iron_condor",
    )
    assert result["risk_pct"] == result_explicit["risk_pct"]


def test_ai_hint_ignored_when_flag_off():
    """AI strategy hint is ignored by Stage 2 when feature flag is OFF.

    With flag OFF, Stage 2 direction filter on a neutral regime returns
    iron_condor (NEUTRAL preferred) at the top regardless of any AI hint.
    """
    from strategy_selector import StrategySelector
    selector = StrategySelector.__new__(StrategySelector)
    mock_redis = MagicMock()
    mock_redis.get.return_value = None  # flag is OFF
    selector.redis_client = mock_redis

    candidates = ["iron_condor", "iron_butterfly"]
    ordered = selector._stage2_direction_filter(
        candidates, "neutral", 0.35, 0.30
    )
    # When flag is OFF, regime-based selection wins (iron_condor on top)
    assert ordered[0] == "iron_condor"


def test_gamma_pin_returns_butterfly():
    """Iron butterfly fires when SPX is within 0.3% of GEX wall."""
    from strategy_selector import StrategySelector
    selector = StrategySelector.__new__(StrategySelector)
    mock_redis = MagicMock()
    mock_redis.get.side_effect = lambda k: {
        "strategy:iron_butterfly:enabled": b"true",
        "gex:nearest_wall": b"5200.0",
        "gex:confidence": b"0.5",
        "tradier:quotes:SPX": b'{"last": 5200.0}',
    }.get(k)
    selector.redis_client = mock_redis

    result = selector._stage1_regime_gate("pin_range", True)
    assert result == ["iron_butterfly"]


def test_gamma_pin_skipped_when_far_from_wall():
    """Iron butterfly does NOT fire when SPX is far from GEX wall."""
    from strategy_selector import StrategySelector
    selector = StrategySelector.__new__(StrategySelector)
    mock_redis = MagicMock()
    mock_redis.get.side_effect = lambda k: {
        "strategy:iron_butterfly:enabled": b"true",
        "gex:nearest_wall": b"5100.0",  # 1.9% away from 5200
        "gex:confidence": b"0.5",
        "tradier:quotes:SPX": b'{"last": 5200.0}',
    }.get(k)
    selector.redis_client = mock_redis

    result = selector._stage1_regime_gate("pin_range", True)
    # Returns regime-based candidates (multiple), not the pin short-circuit
    assert "iron_butterfly" in result
    assert len(result) > 1


def test_long_straddle_in_neutral_preferred():
    """Long straddle is in neutral preferred strategy set."""
    from strategy_selector import _NEUTRAL_PREFERRED
    assert "long_straddle" in _NEUTRAL_PREFERRED


def test_straddle_debit_risk_pct():
    """Long straddle risk pct is 0.25% (our smallest allocation)."""
    from risk_engine import _DEBIT_RISK_PCT
    assert _DEBIT_RISK_PCT["long_straddle"] == 0.0025


# --- Session 2 tests: feature flag helper -----------------------------------


def test_check_feature_flag_false_when_redis_none():
    """Feature flag returns False when Redis client is unavailable."""
    from strategy_selector import StrategySelector
    selector = StrategySelector.__new__(StrategySelector)
    selector.redis_client = None
    assert selector._check_feature_flag("any:flag") is False


def test_check_feature_flag_false_when_key_missing():
    """Feature flag returns False when key is absent from Redis."""
    from strategy_selector import StrategySelector
    selector = StrategySelector.__new__(StrategySelector)
    mock_redis = MagicMock()
    mock_redis.get.return_value = None
    selector.redis_client = mock_redis
    assert selector._check_feature_flag("missing:flag") is False


def test_check_feature_flag_true_bytes():
    """Feature flag returns True for bytes 'true' (decode_responses=False)."""
    from strategy_selector import StrategySelector
    selector = StrategySelector.__new__(StrategySelector)
    mock_redis = MagicMock()
    mock_redis.get.return_value = b"true"
    selector.redis_client = mock_redis
    assert selector._check_feature_flag("some:flag") is True


def test_check_feature_flag_true_string():
    """Feature flag returns True for string 'true' (decode_responses=True)."""
    from strategy_selector import StrategySelector
    selector = StrategySelector.__new__(StrategySelector)
    mock_redis = MagicMock()
    mock_redis.get.return_value = "true"
    selector.redis_client = mock_redis
    assert selector._check_feature_flag("some:flag") is True


# --- Session 2 additional fix: straddle sizing with spread_width=0 ---------


def test_straddle_sizing_returns_nonzero_contracts():
    """Long straddle sizing works despite spread_width=0."""
    from risk_engine import compute_position_size
    result = compute_position_size(
        account_value=100_000.0,
        spread_width=0,
        strategy_type="long_straddle",
    )
    assert result["contracts"] >= 1, (
        "Straddle must produce at least 1 contract"
    )
    assert result["risk_pct"] == 0.0025
