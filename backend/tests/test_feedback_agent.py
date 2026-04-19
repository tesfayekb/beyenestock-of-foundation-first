"""Tests for Phase A: feedback_agent."""
import os
import sys

# Make backend_agents/ importable (sibling directory to backend/).
sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "..", "backend_agents"),
)


def test_wilson_ci_zero_n():
    from feedback_agent import _wilson_ci
    lo, hi = _wilson_ci(0, 0)
    assert lo == 0.0 and hi == 1.0


def test_wilson_ci_small_sample():
    from feedback_agent import _wilson_ci
    lo, hi = _wilson_ci(4, 10)
    assert 0.15 < lo < 0.45
    assert 0.55 < hi < 0.75


def test_wilson_ci_large_sample():
    from feedback_agent import _wilson_ci
    lo, hi = _wilson_ci(65, 100)
    assert lo > 0.55 and hi < 0.75


def test_cell_insufficient_below_5():
    from feedback_agent import _cell
    result = _cell(3, 4, [10, 20, -50, -30])
    assert result["sufficient"] is False
    assert "INSUFFICIENT" in result["note"]


def test_cell_sufficient_above_5():
    from feedback_agent import _cell
    pnls = [100, 150, -80, 200, 120, -60, 90]
    result = _cell(5, 7, pnls)
    assert result["sufficient"] is True
    assert "win_rate" in result
    assert "win_rate_ci" in result
    assert "avg_winner" in result
    assert "avg_loser" in result
    assert "net_pnl" in result


def test_pnl_stats_profitable():
    from feedback_agent import _pnl_stats
    stats = _pnl_stats([100.0, 150.0, -80.0, -60.0])
    assert stats["avg_winner"] == 125.0
    assert stats["avg_loser"] == -70.0
    assert stats["net_pnl"] == 110.0
    assert stats["profitable"] is True


def test_pnl_stats_losing():
    from feedback_agent import _pnl_stats
    stats = _pnl_stats([-100.0, -200.0, 50.0])
    assert stats["profitable"] is False


def test_insufficient_history_stub():
    """Below MIN_TRADES_FOR_BRIEF, agent writes stub and returns."""
    from unittest.mock import MagicMock, patch
    mock_redis = MagicMock()

    with patch("feedback_agent._fetch_closed_trades") as mock_fetch:
        mock_fetch.return_value = [{"net_pnl": 100.0}] * 5  # below 10
        with patch("feedback_agent.is_market_day", return_value=True):
            from feedback_agent import run_feedback_agent
            result = run_feedback_agent(mock_redis)

    assert result["status"] == "insufficient_history"
    assert result["trade_count"] == 5
    assert result["minimum_required"] == 10
    mock_redis.setex.assert_called_once()


def test_brief_written_when_sufficient():
    """Above MIN_TRADES_FOR_BRIEF, brief is written with status=ready."""
    from unittest.mock import MagicMock, patch
    import datetime

    mock_redis = MagicMock()

    fake_trades = [
        {
            "net_pnl": 100.0 if i % 2 == 0 else -80.0,
            "prediction_direction": "bull",
            "prediction_confidence": 0.65,
            "prediction_regime": "range",
            "entry_regime": "range",
            "entry_at": datetime.datetime(
                2026, 4, 21, 10, i, tzinfo=datetime.timezone.utc
            ).isoformat(),
            "exit_at": datetime.datetime(
                2026, 4, 21, 15, i, tzinfo=datetime.timezone.utc
            ).isoformat(),
        }
        for i in range(15)
    ]

    with patch("feedback_agent._fetch_closed_trades", return_value=fake_trades):
        with patch("feedback_agent.is_market_day", return_value=True):
            from feedback_agent import run_feedback_agent
            result = run_feedback_agent(mock_redis)

    assert result.get("status") == "ready"
    assert result["trade_count"] == 15
    assert "overall" in result
    assert "by_direction" in result
    assert "by_confidence" in result
    assert "by_regime" in result
    mock_redis.setex.assert_called_once()
    args = mock_redis.setex.call_args[0]
    assert args[0] == "ai:feedback:brief"
    assert args[1] == 345_600  # 4-day TTL


def test_skips_on_non_market_day():
    """Job skips writing brief on weekends/holidays."""
    from unittest.mock import MagicMock, patch
    mock_redis = MagicMock()

    with patch("feedback_agent.is_market_day", return_value=False):
        from feedback_agent import run_feedback_agent
        result = run_feedback_agent(mock_redis)

    assert result == {}
    mock_redis.setex.assert_not_called()


def test_recent_streak_consecutive_losses():
    from feedback_agent import _compute_recent_streak
    rows = [
        {"net_pnl": -50, "exit_at": f"2026-04-2{i}T15:00:00Z"}
        for i in range(3)
    ]
    rows += [
        {"net_pnl": 100, "exit_at": f"2026-04-1{i}T15:00:00Z"}
        for i in range(7)
    ]
    streak = _compute_recent_streak(rows)
    assert streak["consecutive_losses"] == 3
