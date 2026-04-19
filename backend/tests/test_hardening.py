"""
Tests for HARD-A circuit breakers.
All tests mock DB and execution engine to avoid live calls.
"""
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta


# ─── Emergency Backstop ──────────────────────────────────────────────────────

def test_emergency_backstop_no_positions():
    """No positions open → backstop returns triggered=False, does nothing."""
    with patch("position_monitor.get_open_positions", return_value=[]):
        from position_monitor import run_emergency_backstop
        result = run_emergency_backstop()
    assert result["closed"] == 0
    assert result["triggered"] is False


def test_emergency_backstop_closes_stuck_positions():
    """Positions still open at 3:55 PM → all closed with emergency_backstop reason."""
    fake_positions = [
        {
            "id": "pos-001",
            "strategy_type": "iron_condor",
            "entry_at": "2026-04-21T10:00:00Z",
        },
        {
            "id": "pos-002",
            "strategy_type": "iron_condor",
            "entry_at": "2026-04-21T13:00:00Z",
        },
    ]
    mock_engine = MagicMock()
    mock_engine.close_virtual_position.return_value = True

    with patch("position_monitor.get_open_positions", return_value=fake_positions):
        with patch("position_monitor._get_engine", return_value=mock_engine):
            with patch("position_monitor.write_audit_log"):
                from position_monitor import run_emergency_backstop
                result = run_emergency_backstop()

    assert result["closed"] == 2
    assert result["triggered"] is True
    calls = mock_engine.close_virtual_position.call_args_list
    for call in calls:
        assert call.kwargs.get("exit_reason") == "emergency_backstop"


# ─── Prediction Watchdog ─────────────────────────────────────────────────────

def test_prediction_watchdog_healthy_recent_prediction():
    """Recent prediction (2 min ago) → watchdog returns healthy."""
    recent_time = (
        datetime.now(timezone.utc) - timedelta(minutes=2)
    ).isoformat()
    mock_result = MagicMock()
    mock_result.data = [{"predicted_at": recent_time}]

    with patch("position_monitor.get_client") as mock_client:
        mock_client.return_value.table.return_value \
            .select.return_value.order.return_value.limit.return_value \
            .execute.return_value = mock_result
        from position_monitor import run_prediction_watchdog
        result = run_prediction_watchdog()

    assert result["status"] == "healthy"
    assert result["age_minutes"] < 3


def test_prediction_watchdog_triggers_on_stale():
    """Prediction 15 min ago → watchdog triggers and closes open positions."""
    stale_time = (
        datetime.now(timezone.utc) - timedelta(minutes=15)
    ).isoformat()
    mock_result = MagicMock()
    mock_result.data = [{"predicted_at": stale_time}]

    fake_positions = [{"id": "pos-001", "strategy_type": "iron_condor"}]
    mock_engine = MagicMock()
    mock_engine.close_virtual_position.return_value = True

    with patch("position_monitor.get_client") as mock_client:
        mock_client.return_value.table.return_value \
            .select.return_value.order.return_value.limit.return_value \
            .execute.return_value = mock_result
        with patch(
            "position_monitor.get_open_positions", return_value=fake_positions
        ):
            with patch(
                "position_monitor._get_engine", return_value=mock_engine
            ):
                with patch("position_monitor.write_audit_log"):
                    from position_monitor import run_prediction_watchdog
                    result = run_prediction_watchdog()

    assert result["status"] == "triggered"
    assert result["positions_closed"] == 1
    # Verify exit_reason makes the cause obvious in the audit log
    call = mock_engine.close_virtual_position.call_args
    assert call.kwargs.get("exit_reason") == "watchdog_engine_silent"


def test_prediction_watchdog_no_predictions_yet():
    """No predictions in DB → watchdog returns no_predictions, no action."""
    mock_result = MagicMock()
    mock_result.data = []

    with patch("position_monitor.get_client") as mock_client:
        mock_client.return_value.table.return_value \
            .select.return_value.order.return_value.limit.return_value \
            .execute.return_value = mock_result
        from position_monitor import run_prediction_watchdog
        result = run_prediction_watchdog()

    assert result["status"] == "no_predictions"
    assert result["action"] == "none"


# ─── EOD Reconciliation ──────────────────────────────────────────────────────

def test_eod_reconciliation_clean():
    """No open positions at EOD → returns clean."""
    with patch("position_monitor.get_open_positions", return_value=[]):
        from position_monitor import run_eod_position_reconciliation
        result = run_eod_position_reconciliation()

    assert result["mismatches"] == 0
    assert result["force_closed"] == 0


def test_eod_reconciliation_force_closes_stale():
    """Open positions found at 4:15 PM → force-closed."""
    stale = [{
        "id": "pos-stale",
        "strategy_type": "iron_condor",
        "entry_at": "2026-04-21T10:00:00Z",
        "session_id": "sess-1",
    }]
    mock_engine = MagicMock()
    mock_engine.close_virtual_position.return_value = True

    with patch("position_monitor.get_open_positions", return_value=stale):
        with patch("position_monitor._get_engine", return_value=mock_engine):
            with patch("position_monitor.write_audit_log"):
                from position_monitor import run_eod_position_reconciliation
                result = run_eod_position_reconciliation()

    assert result["mismatches"] == 1
    assert result["force_closed"] == 1
    call = mock_engine.close_virtual_position.call_args
    assert "eod_reconciliation" in call.kwargs.get("exit_reason", "")


# ─── Feedback Brief Validation ───────────────────────────────────────────────

def test_validate_brief_valid_ready():
    import sys
    import os
    sys.path.insert(
        0, os.path.join(os.path.dirname(__file__), "..", "..", "backend_agents")
    )
    from feedback_agent import _validate_brief
    brief = {
        "status": "ready",
        "generated_at": "2026-04-21T09:10:00Z",
        "trade_count": 15,
        "overall": {"win_rate": 0.65},
    }
    assert _validate_brief(brief) is True


def test_validate_brief_valid_stub():
    import sys
    import os
    sys.path.insert(
        0, os.path.join(os.path.dirname(__file__), "..", "..", "backend_agents")
    )
    from feedback_agent import _validate_brief
    brief = {
        "status": "insufficient_history",
        "generated_at": "2026-04-21T09:10:00Z",
        "trade_count": 5,
    }
    assert _validate_brief(brief) is True


def test_validate_brief_invalid_win_rate():
    import sys
    import os
    sys.path.insert(
        0, os.path.join(os.path.dirname(__file__), "..", "..", "backend_agents")
    )
    from feedback_agent import _validate_brief
    brief = {
        "status": "ready",
        "generated_at": "2026-04-21T09:10:00Z",
        "trade_count": 15,
        "overall": {"win_rate": 1.5},  # Invalid: > 1.0
    }
    assert _validate_brief(brief) is False


def test_validate_brief_missing_keys():
    import sys
    import os
    sys.path.insert(
        0, os.path.join(os.path.dirname(__file__), "..", "..", "backend_agents")
    )
    from feedback_agent import _validate_brief
    assert _validate_brief({}) is False
    assert _validate_brief({"status": "ready"}) is False


def test_validate_brief_invalid_status():
    import sys
    import os
    sys.path.insert(
        0, os.path.join(os.path.dirname(__file__), "..", "..", "backend_agents")
    )
    from feedback_agent import _validate_brief
    brief = {
        "status": "unknown_state",
        "generated_at": "2026-04-21T09:10:00Z",
        "trade_count": 5,
    }
    assert _validate_brief(brief) is False
