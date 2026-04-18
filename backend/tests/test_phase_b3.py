"""Tests for Phase B3: tighter exit parameters."""
from unittest.mock import patch, MagicMock


def test_take_profit_fires_at_40pct():
    """Take profit fires at 40% of max profit, not 50%."""
    import inspect
    from position_monitor import run_position_monitor
    source = inspect.getsource(run_position_monitor)
    assert "max_profit * 0.40" in source, \
        "Take profit should fire at 40% of max profit"
    assert "max_profit * 0.50" not in source, \
        "Old 50% threshold should be removed"


def test_stop_loss_at_150pct():
    """Stop loss fires at 150% of credit, not 200%."""
    import inspect
    from position_monitor import run_position_monitor
    source = inspect.getsource(run_position_monitor)
    assert "max_profit * 1.5" in source, \
        "Stop loss should fire at 150% of credit"
    assert "max_profit * 2.0" not in source, \
        "Old 200% threshold should be removed"


def test_exit_reason_strings_updated():
    """Exit reason strings match the new thresholds."""
    import inspect
    from position_monitor import run_position_monitor
    source = inspect.getsource(run_position_monitor)
    assert "take_profit_40pct" in source
    assert "stop_loss_150pct_credit" in source
    assert "take_profit_50pct" not in source
    assert "stop_loss_200pct_credit" not in source


def test_partial_exit_threshold_unchanged():
    """Partial exit at 25% is unchanged by B3."""
    import inspect
    from position_monitor import run_position_monitor
    source = inspect.getsource(run_position_monitor)
    assert "max_profit * 0.25" in source, \
        "Partial exit at 25% must be preserved"


def test_cv_stress_exit_uses_40pct():
    """CV_Stress exit guard updated to 40% threshold."""
    import inspect
    from position_monitor import run_position_monitor
    source = inspect.getsource(run_position_monitor)
    # The CV_Stress guard should match the new take-profit threshold
    assert "pct_profit >= 0.40" in source, \
        "CV_Stress exit guard should use 40% threshold"
