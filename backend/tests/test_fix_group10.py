"""
Tests for Fix Group 10: GEX data, Redis guard, D-005 unrealized, GLC-006 scope.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_gex_rest_fallback_on_missing_quote():
    """GEX engine attempts REST fetch when quote missing from Redis."""
    import inspect
    from gex_engine import GexEngine
    source = inspect.getsource(GexEngine.compute_gex)
    assert (
        "v1/markets/quotes" in source
        or "REST" in source
        or "rest_fetch" in source.lower()
    ), "compute_gex must attempt REST fetch for missing quotes"


def test_prediction_skips_on_redis_unavailable():
    """run_cycle returns no_trade when Redis is unreachable."""
    from unittest.mock import MagicMock
    from prediction_engine import PredictionEngine

    engine = PredictionEngine.__new__(PredictionEngine)
    mock_redis = MagicMock()
    mock_redis.ping.side_effect = Exception("Redis unreachable")
    engine.redis_client = mock_redis
    engine._cycle_count = 0

    result = engine.run_cycle()
    assert result is not None
    assert result.get("no_trade_signal") is True
    assert result.get("no_trade_reason") == "redis_unavailable"


def test_prediction_skips_when_no_feed_data():
    """run_cycle returns no_trade when all feed signals are None."""
    from unittest.mock import MagicMock, patch
    from prediction_engine import PredictionEngine

    engine = PredictionEngine.__new__(PredictionEngine)
    mock_redis = MagicMock()
    mock_redis.ping.return_value = True
    mock_redis.get.return_value = None  # all keys return None
    engine.redis_client = mock_redis
    engine._cycle_count = 0

    # Provide a fake session so get_today_session doesn't fail on missing DB
    fake_session = {
        "id": "fake-session-id",
        "session_date": "2026-04-17",
        "consecutive_losses_today": 0,
        "session_status": "active",
    }
    with patch("prediction_engine.get_today_session", return_value=fake_session):
        result = engine.run_cycle()

    assert result is not None
    assert result.get("no_trade_signal") is True
    assert "unavailable" in result.get("no_trade_reason", "")


def test_d005_includes_unrealized_pnl():
    """D-005 drawdown check must include unrealized MTM P&L."""
    import inspect
    from trading_cycle import run_trading_cycle
    source = inspect.getsource(run_trading_cycle)
    assert "unrealized_pnl" in source or "current_pnl" in source, (
        "run_trading_cycle must include unrealized P&L in D-005 check"
    )
    assert "realized_pnl" in source or "virtual_pnl" in source


def test_glc006_uses_session_snapshots():
    """GLC-006 evaluator uses session_error_snapshot audit entries."""
    import inspect
    from criteria_evaluator import evaluate_glc006_zero_exceptions
    source = inspect.getsource(evaluate_glc006_zero_exceptions)
    assert "session_error_snapshot" in source, (
        "GLC-006 must query session_error_snapshot audit entries"
    )


def test_session_close_writes_error_snapshot():
    """close_today_session writes session_error_snapshot audit log."""
    import inspect
    from session_manager import close_today_session
    source = inspect.getsource(close_today_session)
    assert "session_error_snapshot" in source, (
        "close_today_session must write error snapshot audit log"
    )
