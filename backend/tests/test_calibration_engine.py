"""Unit tests for calibration_engine.py."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_run_weekly_calibration_returns_dict():
    from unittest.mock import patch, MagicMock
    from calibration_engine import run_weekly_calibration
    with patch("calibration_engine.get_client") as mock_db, \
         patch("calibration_engine.write_audit_log"), \
         patch("calibration_engine.write_health_status"):
        mock_db.return_value.table.return_value.select.return_value\
            .not_.return_value.is_.return_value.execute.return_value.data = []
        mock_db.return_value.table.return_value.insert\
            .return_value.execute.return_value = MagicMock()
        result = run_weekly_calibration()
    assert isinstance(result, dict)


def test_slippage_mae_returns_none_when_insufficient_data():
    from unittest.mock import patch
    from calibration_engine import compute_slippage_mae
    with patch("calibration_engine.get_client") as mock_db:
        mock_db.return_value.table.return_value.select.return_value\
            .not_.return_value.is_.return_value.execute.return_value.data = []
        result = compute_slippage_mae()
    assert result["mae"] is None
    assert result["model_ready"] is False


def test_cv_stress_cwer_returns_none_when_insufficient_data():
    from unittest.mock import patch
    from calibration_engine import compute_cv_stress_cwer
    with patch("calibration_engine.get_client") as mock_db:
        mock_db.return_value.table.return_value.select.return_value\
            .not_.return_value.is_.return_value.execute.return_value.data = []
        result = compute_cv_stress_cwer()
    assert result["fn_rate"] is None
    assert result["calibrated"] is False
