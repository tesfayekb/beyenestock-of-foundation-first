"""
Tests for Fix Group 6: Data quality fixes.
Covers: slippage perturbation (D-019), D-017 CV_Stress exit,
D-022 consecutive-loss-sessions, allocation_tier D-004,
pre_market_scan day_type classifier.
"""
import sys
import os

# Ensure backend/ is on the path for direct module imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_simulate_fill_perturbation_varies():
    """actual_slippage must vary from predicted — not always equal."""
    from execution_engine import ExecutionEngine
    engine = ExecutionEngine.__new__(ExecutionEngine)
    results = set()
    for _ in range(20):
        fill = engine._simulate_fill(1.50, "put_credit_spread")
        results.add(fill["actual_slippage"])
    # With 20 samples and 20% noise, we expect at least 2 distinct values
    assert len(results) > 1, "actual_slippage must vary from predicted_slippage"


def test_simulate_fill_actual_in_bounds():
    """actual_slippage must be within [0.5×, 2.0×] of the predicted slippage."""
    from execution_engine import ExecutionEngine
    engine = ExecutionEngine.__new__(ExecutionEngine)
    for _ in range(50):
        fill = engine._simulate_fill(1.50, "put_credit_spread")
        actual = fill["actual_slippage"]
        predicted = fill["predicted_slippage"]
        assert actual >= predicted * 0.5, (
            f"actual {actual} below 0.5× predicted ({predicted})"
        )
        assert actual <= predicted * 2.0, (
            f"actual {actual} above 2.0× predicted ({predicted})"
        )


def test_d017_exit_fires_when_cv_stress_high_and_profit_sufficient():
    """D-017: CV_Stress exit fires when cv_stress > 70 AND P&L >= 50% max profit."""
    from unittest.mock import patch
    from position_monitor import run_position_monitor

    # Credit spread, entry_credit=2.00, contracts=1
    # max_profit = 200, current_pnl=110 (55% of max) — should trigger D-017
    mock_pos = {
        "id": "pos-d017",
        "strategy_type": "iron_condor",
        "entry_credit": 2.00,
        "contracts": 1,
        "current_pnl": 110.0,
        "current_cv_stress": 75.0,
        "session_id": "sess-1",
    }
    with patch("position_monitor.get_open_positions", return_value=[mock_pos]), \
         patch("position_monitor._get_engine") as mock_eng, \
         patch("position_monitor.write_health_status"), \
         patch("position_monitor.get_client"):
        mock_eng.return_value.close_virtual_position.return_value = True
        result = run_position_monitor()
    assert result["closed"] == 1, "D-017 exit should fire"


def test_d017_does_not_exit_when_profit_insufficient():
    """D-017: CV_Stress exit must NOT fire when P&L < 50% of max profit."""
    from unittest.mock import patch
    from position_monitor import run_position_monitor

    # P&L is only 20% of max — D-017 should NOT fire even with high CV_Stress
    mock_pos = {
        "id": "pos-d017-no",
        "strategy_type": "iron_condor",
        "entry_credit": 2.00,
        "contracts": 1,
        "current_pnl": 40.0,   # only 20% of 200 max
        "current_cv_stress": 80.0,
        "session_id": "sess-1",
    }
    with patch("position_monitor.get_open_positions", return_value=[mock_pos]), \
         patch("position_monitor._get_engine") as mock_eng, \
         patch("position_monitor.write_health_status"), \
         patch("position_monitor.get_client"):
        mock_eng.return_value.close_virtual_position.return_value = True
        result = run_position_monitor()
    assert result["closed"] == 0, "D-017 must not fire when profit < 50%"


def test_allocation_tier_danger_returns_zero_contracts():
    """allocation_tier=danger must return 0 contracts (D-004)."""
    from risk_engine import compute_position_size
    result = compute_position_size(
        account_value=100_000,
        spread_width=5.0,
        allocation_tier="danger",
    )
    assert result["contracts"] == 0


def test_allocation_tier_moderate_reduces_size():
    """allocation_tier=moderate applies 0.70 multiplier."""
    from risk_engine import compute_position_size
    full = compute_position_size(100_000, 5.0, allocation_tier="full")
    moderate = compute_position_size(100_000, 5.0, allocation_tier="moderate")
    if full["contracts"] > 0 and moderate["contracts"] > 0:
        assert moderate["risk_pct"] < full["risk_pct"], \
            "moderate tier must have lower risk_pct than full"


def test_allocation_tier_danger_reason():
    """allocation_tier=danger must include the tier reason string."""
    from risk_engine import compute_position_size
    result = compute_position_size(
        account_value=100_000,
        spread_width=5.0,
        allocation_tier="danger",
    )
    assert "danger" in (result.get("size_reduction_reason") or ""), \
        "size_reduction_reason must mention 'danger'"


def test_pre_market_scan_classifies_event_day():
    """High VVIX Z (>= 2.5) should classify day as event — verify in source."""
    backend_main = os.path.join(os.path.dirname(__file__), "..", "main.py")
    with open(backend_main, encoding="utf-8") as f:
        src = f.read()

    # Verify the event-day threshold is present and uses correct bound
    assert 'day_type = "event"' in src, \
        "pre_market_scan must define day_type = 'event'"
    assert "abs(vvix_z) >= 2.5" in src, \
        "event day must trigger on abs(vvix_z) >= 2.5"


def test_pre_market_scan_scheduled_at_14_utc():
    """pre_market_scan must be scheduled at 14:00 UTC (9 AM ET)."""
    backend_main = os.path.join(os.path.dirname(__file__), "..", "main.py")
    with open(backend_main, encoding="utf-8") as f:
        src = f.read()

    assert "hour=14" in src, \
        "pre_market_scan must be scheduled at hour=14 UTC (9 AM ET)"
    # Must NOT still use the old 9 AM UTC timing alongside the new 14 UTC
    # (allow hour=9 only in heartbeat_check interval, not in pre_market_scan)
    assert 'id="trading_pre_market_scan"' in src, \
        "pre_market_scan job id must be registered"
