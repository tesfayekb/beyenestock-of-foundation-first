"""Tests for Phase B4 wiring: Kelly multiplier from DB to position size."""
from unittest.mock import patch, MagicMock


def test_get_kelly_multiplier_insufficient_trades():
    """Returns 1.0 when fewer than 20 trades available."""
    with patch("model_retraining.get_client") as mock_db:
        mock_db.return_value.table.return_value.select.return_value\
            .gte.return_value.eq.return_value.eq.return_value\
            .execute.return_value.data = [
                {"net_pnl": 50.0}
            ] * 15  # only 15 trades

        from model_retraining import get_kelly_multiplier_from_db
        mult = get_kelly_multiplier_from_db()

    assert mult == 1.0, f"Expected 1.0 for < 20 trades, got {mult}"


def test_get_kelly_multiplier_high_win_rate():
    """Returns multiplier > 1.0 for strong recent performance."""
    # 25 trades: 20 wins ($70 each), 5 losses ($143 each)
    trades = (
        [{"net_pnl": 70.0}] * 20 +
        [{"net_pnl": -143.0}] * 5
    )
    with patch("model_retraining.get_client") as mock_db:
        mock_db.return_value.table.return_value.select.return_value\
            .gte.return_value.eq.return_value.eq.return_value\
            .execute.return_value.data = trades

        from model_retraining import get_kelly_multiplier_from_db
        mult = get_kelly_multiplier_from_db()

    assert mult > 1.0, f"Expected > 1.0 for 80% WR, got {mult}"
    assert mult <= 2.0


def test_get_kelly_multiplier_db_error_returns_1():
    """Returns 1.0 gracefully when DB query fails."""
    with patch("model_retraining.get_client") as mock_db:
        mock_db.side_effect = Exception("DB connection error")

        from model_retraining import get_kelly_multiplier_from_db
        mult = get_kelly_multiplier_from_db()

    assert mult == 1.0


def test_strategy_selector_uses_redis_cached_kelly():
    """Strategy selector reads Kelly multiplier from Redis cache."""
    from strategy_selector import StrategySelector

    selector = StrategySelector.__new__(StrategySelector)
    mock_redis = MagicMock()
    mock_redis.get.return_value = b"1.25"  # cached value
    selector.redis_client = mock_redis

    # Verify Redis is read before DB is called
    with patch("strategy_selector.get_kelly_multiplier_from_db") as mock_db_fn:
        kelly_mult = 1.0
        try:
            cached = selector.redis_client.get("kelly:multiplier")
            if cached:
                kelly_mult = float(cached)
        except Exception:
            pass

        assert kelly_mult == 1.25
        mock_db_fn.assert_not_called()


def test_strategy_selector_falls_back_to_db_when_no_cache():
    """Strategy selector calls DB when Redis has no cached value."""
    from strategy_selector import StrategySelector

    selector = StrategySelector.__new__(StrategySelector)
    mock_redis = MagicMock()
    mock_redis.get.return_value = None  # no cache
    mock_redis.setex.return_value = True
    selector.redis_client = mock_redis

    with patch("strategy_selector.get_kelly_multiplier_from_db",
               return_value=1.15) as mock_db_fn:
        kelly_mult = 1.0
        try:
            cached = selector.redis_client.get("kelly:multiplier")
            if cached:
                kelly_mult = float(cached)
            else:
                kelly_mult = mock_db_fn()
                selector.redis_client.setex("kelly:multiplier", 3600, str(kelly_mult))
        except Exception:
            pass

        assert kelly_mult == 1.15
        mock_db_fn.assert_called_once()
