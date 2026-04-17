"""Unit tests for model_retraining.py."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_detect_drift_unknown_when_no_data():
    from model_retraining import detect_drift
    result = detect_drift(None, None)
    assert result["drift_status"] == "unknown"


def test_detect_drift_warning_when_accuracy_drops():
    from unittest.mock import patch
    from model_retraining import detect_drift
    with patch("model_retraining.write_audit_log"), \
         patch("model_retraining.logger"):
        result = detect_drift(0.42, 0.55)
    assert result["drift_status"] in ("warning", "critical")


def test_detect_drift_ok_when_healthy():
    from model_retraining import detect_drift
    result = detect_drift(0.60, 0.62)
    assert result["drift_status"] == "ok"


def test_run_weekly_model_performance_returns_dict():
    from unittest.mock import patch, MagicMock
    from model_retraining import run_weekly_model_performance
    with patch("model_retraining.get_client") as mock_db, \
         patch("model_retraining.write_audit_log"), \
         patch("model_retraining.write_health_status"):
        mock_db.return_value.table.return_value.select.return_value\
            .gte.return_value.eq.return_value.execute.return_value.data = []
        mock_db.return_value.table.return_value.select.return_value\
            .gte.return_value.not_.return_value.is_.return_value\
            .order.return_value.execute.return_value.data = []
        mock_db.return_value.table.return_value.select.return_value\
            .eq.return_value.execute.return_value.count = 0
        mock_db.return_value.table.return_value.insert\
            .return_value.execute.return_value = MagicMock()
        result = run_weekly_model_performance()
    assert isinstance(result, dict)
