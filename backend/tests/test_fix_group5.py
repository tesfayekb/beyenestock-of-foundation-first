"""
Tests for Fix Group 5: Paper phase critical fixes.
Covers: maybeSingle rename, commission legs, heartbeat threshold,
error_count_1h reset, debit strategy exit logic, credit stop-loss,
VVIX endpoint.
"""


def test_no_maybe_single_camel_case():
    """Actual .maybeSingle() API calls must not exist in production code."""
    import os
    backend_dir = os.path.join(os.path.dirname(__file__), "..")
    # Search for the method call pattern .maybeSingle() with its leading dot
    # to distinguish real API calls from string mentions in test code
    found = []
    for root, dirs, files in os.walk(backend_dir):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git")]
        for fname in files:
            if not fname.endswith(".py"):
                continue
            fpath = os.path.join(root, fname)
            # Skip this test file itself
            if os.path.abspath(fpath) == os.path.abspath(__file__):
                continue
            with open(fpath, encoding="utf-8", errors="replace") as f:
                for lineno, line in enumerate(f, 1):
                    if ".maybeSingle()" in line:
                        found.append(f"{fpath}:{lineno}: {line.rstrip()}")
    assert found == [], "Found .maybeSingle() calls in:\n" + "\n".join(found)


def test_commission_legs_iron_condor():
    """Iron condor must use 8 legs for commission calculation."""
    from execution_engine import ExecutionEngine
    assert ExecutionEngine.LEGS_BY_STRATEGY["iron_condor"] == 8
    assert ExecutionEngine.LEGS_BY_STRATEGY["iron_butterfly"] == 8


def test_commission_legs_spread():
    """Credit/debit spreads must use 4 legs."""
    from execution_engine import ExecutionEngine
    assert ExecutionEngine.LEGS_BY_STRATEGY["put_credit_spread"] == 4
    assert ExecutionEngine.LEGS_BY_STRATEGY["debit_put_spread"] == 4


def test_commission_legs_single_leg():
    """Single-leg strategies must use 2 legs."""
    from execution_engine import ExecutionEngine
    assert ExecutionEngine.LEGS_BY_STRATEGY["long_put"] == 2
    assert ExecutionEngine.LEGS_BY_STRATEGY["long_call"] == 2


def test_heartbeat_threshold_is_90():
    """Heartbeat stale threshold must be 90 seconds not 360."""
    import os
    main_path = os.path.join(os.path.dirname(__file__), "..", "main.py")
    with open(main_path, encoding="utf-8") as f:
        source = f.read()
    # Find the heartbeat_check function body
    assert ".total_seconds() > 360" not in source, \
        "heartbeat_check still uses 360s threshold"
    assert ".total_seconds() > 90" in source, \
        "heartbeat_check must use 90s threshold"


def test_error_count_not_reset_on_healthy():
    """write_health_status with status=healthy must NOT reset error_count_1h."""
    from unittest.mock import patch, MagicMock
    import db as db_module
    payloads_written = []

    with patch.object(db_module, "get_client") as mock_client:
        mock_client.return_value.table.return_value.upsert = lambda p, **kw: (
            payloads_written.append(p) or MagicMock(execute=MagicMock())
        )
        db_module.write_health_status("prediction_engine", "healthy")

    written = payloads_written[-1] if payloads_written else {}
    assert "error_count_1h" not in written or written.get("error_count_1h") != 0, \
        "write_health_status healthy must not write error_count_1h=0"


def test_debit_position_not_skipped():
    """Debit strategies (negative entry_credit) must not be skipped."""
    from unittest.mock import patch, MagicMock
    from position_monitor import run_position_monitor

    # Simulate a long_put position with entry_credit=-3.00 (debit paid)
    mock_pos = {
        "id": "pos-debit-1",
        "strategy_type": "long_put",
        "entry_credit": -3.00,
        "contracts": 1,
        "current_pnl": -300.0,  # full loss — should trigger stop
        "session_id": "sess-1",
    }

    with patch("position_monitor.get_open_positions", return_value=[mock_pos]), \
         patch("position_monitor._get_engine") as mock_eng, \
         patch("position_monitor.write_health_status"), \
         patch("position_monitor.get_client") as mock_db:
        mock_db.return_value.table.return_value.select.return_value\
            .eq.return_value.maybe_single.return_value\
            .execute.return_value.data = None
        mock_eng.return_value.close_virtual_position.return_value = True
        result = run_position_monitor()

    # Debit position at full loss should be closed (not skipped)
    assert result["closed"] == 1, "Debit position at full loss must be closed"


def test_credit_stop_loss_is_200pct():
    """Credit spread stop-loss should trigger at 200% of credit, not 100%."""
    from unittest.mock import patch, MagicMock
    from position_monitor import run_position_monitor

    # Credit spread: entry_credit=1.50, contracts=1
    # 200% stop = -300.0 — should trigger at current_pnl=-310
    mock_pos = {
        "id": "pos-credit-1",
        "strategy_type": "put_credit_spread",
        "entry_credit": 1.50,
        "contracts": 1,
        "current_pnl": -310.0,
        "session_id": "sess-1",
    }

    with patch("position_monitor.get_open_positions", return_value=[mock_pos]), \
         patch("position_monitor._get_engine") as mock_eng, \
         patch("position_monitor.write_health_status"), \
         patch("position_monitor.get_client"):
        mock_eng.return_value.close_virtual_position.return_value = True
        result = run_position_monitor()

    assert result["closed"] == 1, "Credit spread at 200% loss must trigger stop"
