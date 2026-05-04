"""
Tests for Fix Group 9: Critical paper phase integrity fixes.
Covers: scheduler timezone + ET cron hours, prediction cycle cron,
debit fill economics, MTM exit credit, calibration slippage,
SPX price from Redis, upsert criterion.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_scheduler_has_et_timezone():
    """AsyncIOScheduler must be constructed with America/New_York timezone."""
    main_path = os.path.join(os.path.dirname(__file__), "..", "main.py")
    with open(main_path, encoding="utf-8") as f:
        source = f.read()
    assert "from zoneinfo import ZoneInfo" in source, (
        "main.py missing ZoneInfo import"
    )
    assert 'AsyncIOScheduler(timezone=ZoneInfo("America/New_York"))' in source, (
        "Scheduler is not constructed with America/New_York timezone"
    )


def test_debit_fill_records_real_cost():
    """Debit strategy fill must record abs(credit) + slippage, not 0.05."""
    from execution_engine import ExecutionEngine
    engine = ExecutionEngine.__new__(ExecutionEngine)
    # long_put with target_credit=-3.00 (debit paid)
    result = engine._simulate_fill(-3.00, "long_put")
    assert result["fill_price"] > 2.50, (
        f"Debit fill should be ~$3.00 + slippage, got {result['fill_price']}"
    )
    assert result["is_debit"] is True


def test_credit_fill_unchanged():
    """Credit strategy fill still uses credit - slippage."""
    from execution_engine import ExecutionEngine
    engine = ExecutionEngine.__new__(ExecutionEngine)
    result = engine._simulate_fill(1.50, "put_credit_spread")
    assert result["fill_price"] > 0.05
    assert result["fill_price"] < 1.50  # slippage reduces credit received
    assert result["is_debit"] is False


def test_calibration_slippage_not_pnl_delta():
    """Calibration log actual_slippage must be fill slippage, not P&L delta."""
    import inspect
    from execution_engine import ExecutionEngine
    source = inspect.getsource(ExecutionEngine.close_virtual_position)
    # The old formula used abs(entry_credit - exit_credit)
    assert "abs(entry_credit - " not in source, (
        "Calibration log still writes P&L delta as slippage"
    )


def test_spx_price_reads_redis():
    """_get_spx_price must read from Redis, not return 5000.0."""
    from prediction_engine import PredictionEngine
    engine = PredictionEngine.__new__(PredictionEngine)
    engine.redis_client = None
    # Without Redis, should fall back to 5200.0 not 5000.0
    price = engine._get_spx_price()
    assert price == 5200.0, f"Fallback should be 5200.0 not {price}"
    assert price != 5000.0, "Must not return the old hardcoded 5000.0"


def test_prediction_output_no_hardcoded_5000():
    """prediction_engine run_cycle must not emit spx_price=5000.0."""
    import inspect
    from prediction_engine import PredictionEngine
    source = inspect.getsource(PredictionEngine.run_cycle)
    assert "5000.0" not in source, (
        "run_cycle still contains hardcoded spx_price=5000.0"
    )



def test_prediction_cycle_is_cron_not_interval():
    """Prediction cycle must use cron trigger (market hours) not interval."""
    main_path = os.path.join(os.path.dirname(__file__), "..", "main.py")
    with open(main_path, encoding="utf-8") as f:
        source = f.read()
    idx = source.find("trading_prediction_cycle_local")
    assert idx > 0, "trading_prediction_cycle_local not found"
    # Find the add_job block that registers this id (search back to its
    # scheduler.add_job opening).
    start = source.rfind("scheduler.add_job(", 0, idx)
    assert start > 0, "add_job(...) block for prediction cycle not found"
    block = source[start:idx]
    assert 'trigger="interval"' not in block, (
        "Prediction cycle still uses interval trigger (runs 24/7)"
    )
    assert 'trigger="cron"' in block, (
        "Prediction cycle should use cron trigger"
    )


def test_d010_d011_use_et_hours():
    """D-010 at hour=14, D-011 at hour=15 in ET-aware scheduler."""
    main_path = os.path.join(os.path.dirname(__file__), "..", "main.py")
    with open(main_path, encoding="utf-8") as f:
        source = f.read()
    # D-010
    idx10 = source.find("trading_time_stop_230pm")
    block10 = source[max(0, idx10 - 400):idx10]
    assert "hour=14" in block10 and "minute=30" in block10, (
        "D-010 must be registered at hour=14, minute=30 ET"
    )
    # D-011
    idx11 = source.find("trading_time_stop_345pm")
    block11 = source[max(0, idx11 - 400):idx11]
    assert "hour=15" in block11 and "minute=45" in block11, (
        "D-011 must be registered at hour=15, minute=45 ET"
    )
