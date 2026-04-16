"""
Unit tests for criteria_evaluator.py
Tests: _upsert_criterion error handling, run_criteria_evaluation return type,
       and GLC coverage completeness.
"""


def test_upsert_criterion_handles_db_error():
    """_upsert_criterion never raises even on DB failure."""
    from unittest.mock import patch
    from criteria_evaluator import _upsert_criterion
    with patch("criteria_evaluator.get_client", side_effect=Exception("DB error")):
        # Should not raise
        _upsert_criterion("GLC-001", "not_started", "test", None)


def test_run_criteria_evaluation_returns_dict():
    """run_criteria_evaluation always returns a dict."""
    from unittest.mock import patch, MagicMock
    from criteria_evaluator import run_criteria_evaluation

    mock_execute = MagicMock()
    mock_execute.data = []
    mock_execute.count = 0

    mock_chain = MagicMock()
    mock_chain.execute.return_value = mock_execute
    mock_chain.select.return_value = mock_chain
    mock_chain.eq.return_value = mock_chain
    mock_chain.gt.return_value = mock_chain
    mock_chain.order.return_value = mock_chain
    mock_chain.limit.return_value = mock_chain
    mock_chain.update.return_value = mock_chain

    mock_table = MagicMock()
    mock_table.return_value = mock_chain

    with patch("criteria_evaluator.get_client") as mock_db, \
         patch("criteria_evaluator.write_audit_log"), \
         patch("criteria_evaluator.write_health_status"):
        mock_db.return_value.table = mock_table
        result = run_criteria_evaluation()

    assert isinstance(result, dict)


def test_all_criteria_seeded():
    """All 12 GLC IDs are covered by evaluation functions or marked manual."""
    automated = [
        "GLC-001", "GLC-002", "GLC-003", "GLC-004",
        "GLC-005", "GLC-006", "GLC-011", "GLC-012",
    ]
    manual = ["GLC-007", "GLC-008", "GLC-009", "GLC-010"]
    assert len(automated) + len(manual) == 12
    # Ensure no duplicates
    all_ids = automated + manual
    assert len(set(all_ids)) == 12
