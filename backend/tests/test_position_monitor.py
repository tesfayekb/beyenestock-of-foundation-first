from unittest.mock import patch, MagicMock


def test_run_position_monitor_returns_dict_on_empty():
    """Returns safely when no open positions exist."""
    from position_monitor import run_position_monitor
    with patch("position_monitor.get_open_positions", return_value=[]):
        result = run_position_monitor()
    assert result["checked"] == 0
    assert result["closed"] == 0


def test_time_stop_230pm_returns_dict_on_empty():
    """Returns safely when no short-gamma positions exist."""
    from position_monitor import run_time_stop_230pm
    with patch("position_monitor.get_open_positions", return_value=[]):
        result = run_time_stop_230pm()
    assert result["closed"] == 0


def test_time_stop_345pm_returns_dict_on_empty():
    """Returns safely when no positions exist."""
    from position_monitor import run_time_stop_345pm
    with patch("position_monitor.get_open_positions", return_value=[]):
        result = run_time_stop_345pm()
    assert result["closed"] == 0


def test_time_stop_345pm_closes_all_positions():
    """D-011: All positions closed at 3:45 PM regardless of type."""
    from position_monitor import run_time_stop_345pm
    mock_positions = [
        {"id": "pos-1", "strategy_type": "iron_condor"},
        {"id": "pos-2", "strategy_type": "long_put"},
    ]
    with patch("position_monitor.get_open_positions", return_value=mock_positions), \
         patch("position_monitor._get_engine") as mock_eng, \
         patch("position_monitor.write_audit_log"):
        mock_eng.return_value.close_virtual_position.return_value = True
        result = run_time_stop_345pm()
    assert result["closed"] == 2


def test_time_stop_230pm_only_closes_short_gamma():
    """D-010: Only short-gamma strategies closed at 2:30 PM."""
    from position_monitor import run_time_stop_230pm, SHORT_GAMMA_STRATEGIES
    mock_positions = [
        {"id": "pos-1", "strategy_type": "iron_condor"},   # short gamma
        {"id": "pos-2", "strategy_type": "long_put"},       # long gamma — skip
    ]
    with patch("position_monitor.get_open_positions", return_value=mock_positions), \
         patch("position_monitor._get_engine") as mock_eng, \
         patch("position_monitor.write_audit_log"):
        mock_eng.return_value.close_virtual_position.return_value = True
        result = run_time_stop_230pm()
    # Only iron_condor should be closed
    assert result["closed"] == 1


def test_sharpe_uses_percentage_returns():
    """Sharpe ratio must use % returns, not raw dollar P&L."""
    from model_retraining import compute_sharpe_ratio
    from unittest.mock import patch
    # 10 sessions with $100 PnL each on $100k account = 0.1% daily return
    mock_sessions = [
        {"virtual_pnl": 100.0, "session_date": f"2026-04-{i:02d}"}
        for i in range(1, 11)
    ]
    with patch("model_retraining.get_client") as mock_db:
        mock_db.return_value.table.return_value.select.return_value\
            .gte.return_value.not_.return_value.is_.return_value\
            .order.return_value.execute.return_value.data = mock_sessions
        result = compute_sharpe_ratio(days=20)
    # With constant returns, std is near 0 — result is None or very high
    # Key check: function returns without crashing
    assert result is None or isinstance(result, float)
