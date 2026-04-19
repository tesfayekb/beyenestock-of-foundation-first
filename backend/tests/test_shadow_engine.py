"""Tests for Phase 3B shadow engine (Portfolio A rule-based baseline)."""

from unittest.mock import MagicMock, patch


def _make_redis(values: dict) -> MagicMock:
    """Create a mock Redis client with preset string values."""
    mock = MagicMock()
    mock.get.side_effect = lambda k: values.get(k)
    return mock


def test_shadow_cycle_records_prediction():
    """Shadow cycle writes one row to shadow_predictions and returns dict."""
    redis = _make_redis({
        "polygon:vix:current":   "18.0",
        "polygon:vvix:z_score":  "0.5",
        "gex:net":               "1000000000",
        "gex:confidence":        "0.75",
        "gex:flip_zone":         "4800.0",
        "gex:nearest_wall":      "5300.0",
        "tradier:quotes:SPX":    "5200.0",
    })

    with patch("shadow_engine.get_client") as mock_client:
        from shadow_engine import run_shadow_cycle
        result = run_shadow_cycle(redis, "session-123")

    assert result is not None
    assert result["regime"] in (
        "quiet_bullish", "pin_range", "range",
        "volatile_bearish", "volatile_bullish",
    )
    assert "direction" in result
    assert "no_trade_signal" in result
    mock_client.return_value.table.assert_called_with("shadow_predictions")


def test_shadow_cycle_never_reads_synthesis():
    """Shadow engine must NOT read any key containing 'synthesis' or 'agent'."""
    accessed_keys = []

    redis = MagicMock()

    def tracking_get(key):
        k = key if isinstance(key, str) else key.decode()
        accessed_keys.append(k)
        defaults = {
            "polygon:vix:current":   "18.0",
            "polygon:vvix:z_score":  "0.5",
            "gex:net":               "0",
            "gex:confidence":        "0.5",
            "gex:flip_zone":         "0",
            "gex:nearest_wall":      "0",
            "tradier:quotes:SPX":    "5200.0",
        }
        return defaults.get(k)

    redis.get = tracking_get

    with patch("shadow_engine.get_client"):
        from shadow_engine import run_shadow_cycle
        run_shadow_cycle(redis, "session-123")

    assert accessed_keys, "Shadow engine should read at least one Redis key"
    for key in accessed_keys:
        assert "synthesis" not in key, (
            f"Shadow engine read synthesis key: {key}"
        )
        assert "agent" not in key, (
            f"Shadow engine read agent key: {key}"
        )


def test_shadow_crisis_regime_no_trade():
    """VIX > 30 + extreme VVIX z-score (>=3.0) triggers no_trade."""
    redis = _make_redis({
        "polygon:vix:current":   "35.0",
        "polygon:vvix:z_score":  "3.5",
        "gex:net":               "-2000000000",
        "gex:confidence":        "0.3",
        "gex:flip_zone":         "0",
        "gex:nearest_wall":      "0",
        "tradier:quotes:SPX":    "5000.0",
    })

    from shadow_engine import _compute_rule_based_prediction
    result = _compute_rule_based_prediction(redis)

    assert result is not None
    assert result["no_trade_signal"] is True


def test_shadow_quiet_market_trades():
    """Low VIX, low |VVIX z|, strong positive GEX → produces a prediction."""
    redis = _make_redis({
        "polygon:vix:current":   "14.0",
        "polygon:vvix:z_score":  "0.2",
        "gex:net":               "2000000000",
        "gex:confidence":        "0.85",
        "gex:flip_zone":         "4500.0",
        "gex:nearest_wall":      "5400.0",
        "tradier:quotes:SPX":    "5200.0",
    })

    from shadow_engine import _compute_rule_based_prediction
    result = _compute_rule_based_prediction(redis)

    assert result is not None
    assert result["rcs"] > 30
    assert result["regime"] != "crisis"


def test_shadow_redis_failure_returns_none():
    """Hard internal failure → _compute returns None gracefully (never raises).

    Redis errors alone are absorbed by _read() (returns defaults), which
    is by design. To prove the never-raises contract on a deeper failure,
    we force float() to raise and confirm the function returns None
    instead of propagating the exception.
    """
    mock_redis = MagicMock()
    mock_redis.get.side_effect = Exception("Redis connection refused")

    from shadow_engine import _compute_rule_based_prediction

    # Soft failure path: defaults absorb the redis error → still a dict.
    soft_result = _compute_rule_based_prediction(mock_redis)
    assert isinstance(soft_result, dict)

    # Hard failure path: deeper exception → graceful None, no raise.
    with patch("shadow_engine.float", side_effect=Exception("boom")):
        hard_result = _compute_rule_based_prediction(mock_redis)
    assert hard_result is None


def test_shadow_cycle_failure_returns_none():
    """DB write failure → run_shadow_cycle returns None, never raises."""
    redis = _make_redis({
        "polygon:vix:current":   "18.0",
        "polygon:vvix:z_score":  "0.5",
        "gex:net":               "0",
        "gex:confidence":        "0.5",
        "gex:flip_zone":         "0",
        "gex:nearest_wall":      "0",
        "tradier:quotes:SPX":    "5200.0",
    })

    with patch("shadow_engine.get_client") as mock_client:
        (
            mock_client.return_value.table.return_value
            .insert.return_value.execute.side_effect
        ) = Exception("DB error")
        from shadow_engine import run_shadow_cycle
        result = run_shadow_cycle(redis, "session-123")

    assert result is None
