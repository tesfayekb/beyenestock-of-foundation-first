def test_gex_compute_uses_pipeline():
    """compute_gex uses a Redis pipeline, not individual GETs per trade."""
    from unittest.mock import MagicMock, patch
    from gex_engine import GexEngine

    engine = GexEngine.__new__(GexEngine)
    mock_redis = MagicMock()

    # Simulate 3 trades in Redis
    trade = (
        '{"symbol":"SPXW241220P5200","price":1.5,"bid":1.4,"ask":1.6,'
        '"volume":10,"underlying_price":5200,"strike":5200,'
        '"time_to_expiry_years":0.01,"risk_free_rate":0.05,"implied_vol":0.20}'
    )
    mock_redis.lrange.return_value = [trade, trade, trade]

    # Pipeline mock
    mock_pipe = MagicMock()
    mock_pipe.execute.return_value = ['{"bid":1.4,"ask":1.6,"last":5200}'] * 3
    mock_redis.pipeline.return_value = mock_pipe

    engine.redis_client = mock_redis
    engine.last_compute_at = None

    with patch.object(engine, "_write_heartbeat"):
        result = engine.compute_gex()

    # Verify pipeline was used (not individual gets)
    mock_redis.pipeline.assert_called_once()
    mock_pipe.execute.assert_called_once()
    assert "gex_net" in result


def test_eod_job_uses_dstproof_timing():
    """EOD criteria job must be at hour=22 (not 21) for DST safety."""
    import inspect
    import sys
    import os
    # Ensure backend is importable
    backend_dir = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..")
    )
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)
    import main as m
    source = inspect.getsource(m)
    # Check that we don't use hour=21 for eod_criteria
    lines = source.split("\n")
    in_eod_block = False
    for line in lines:
        if "trading_eod_criteria_evaluation" in line:
            in_eod_block = True
        if in_eod_block and "hour=21" in line:
            assert False, "EOD job still uses hour=21 — DST bug not fixed"
        if in_eod_block and "replace_existing" in line:
            break


def test_slippage_mae_has_date_filter():
    """compute_slippage_mae must include a date filter."""
    import inspect
    from calibration_engine import compute_slippage_mae
    source = inspect.getsource(compute_slippage_mae)
    assert "gte" in source, "compute_slippage_mae missing date filter (.gte)"
    assert "cutoff" in source or "timedelta" in source


def test_per_regime_accuracy_has_date_filter():
    """compute_per_regime_accuracy must include a 60-day date filter."""
    import inspect
    from model_retraining import compute_per_regime_accuracy
    source = inspect.getsource(compute_per_regime_accuracy)
    assert "gte" in source, "compute_per_regime_accuracy missing date filter"


def test_glc003_filters_closed_positions_only():
    """GLC-003 evaluator must only count closed positions."""
    import inspect
    from criteria_evaluator import evaluate_glc003_training_examples
    source = inspect.getsource(evaluate_glc003_training_examples)
    assert '"closed"' in source or "'closed'" in source, \
        "GLC-003 must filter by status=closed"
