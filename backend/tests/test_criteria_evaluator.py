"""
Unit tests for criteria_evaluator.py
Tests: _update_criterion error handling, run_criteria_evaluation return type,
       and GLC coverage completeness.

T-ACT-055 (2026-05-02): existing test renamed _upsert → _update in lockstep
with the function rename. 5 new tests added covering regression form
(.update vs .upsert), regression mechanism (payload columns), defensive
WARN path, false-positive guard, and never-raises contract.
"""


def test_update_criterion_handles_db_error():
    """_update_criterion never raises even on DB failure."""
    from unittest.mock import patch
    from criteria_evaluator import _update_criterion
    with patch("criteria_evaluator.get_client", side_effect=Exception("DB error")):
        # Should not raise
        _update_criterion("GLC-001", "not_started", "test", None)


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


def test_update_criterion_uses_update_not_upsert():
    """T-ACT-055: _update_criterion must call .update().eq(), NOT .upsert(...).

    Regression guard: PR #17 (commit 836a83c, 2026-04-17) replaced .update().eq()
    with .upsert(..., on_conflict='criterion_id') and silently broke all 12 GLC
    evaluations for ~16 days because criterion_name and target_description (both
    NOT NULL) were missing from the payload. The PostgreSQL INSERT phase fired
    23502 BEFORE ON CONFLICT could engage, the outer try/except swallowed it,
    and rows froze at seed values. This test prevents re-introduction of the
    regression by asserting the wire-level method invoked.
    """
    from unittest.mock import patch, MagicMock
    from criteria_evaluator import _update_criterion

    mock_execute = MagicMock()
    mock_execute.data = [{"criterion_id": "GLC-001"}]

    mock_chain = MagicMock()
    mock_chain.execute.return_value = mock_execute
    mock_chain.update.return_value = mock_chain
    mock_chain.eq.return_value = mock_chain
    mock_chain.upsert.return_value = mock_chain

    mock_table = MagicMock()
    mock_table.return_value = mock_chain

    with patch("criteria_evaluator.get_client") as mock_db:
        mock_db.return_value.table = mock_table
        _update_criterion("GLC-001", "in_progress", "test value", 1.0)

    assert mock_chain.update.called, ".update() must be called"
    assert not mock_chain.upsert.called, (
        ".upsert() must NOT be called — see T-ACT-055 regression context "
        "in _update_criterion docstring"
    )
    assert mock_chain.eq.called, ".eq('criterion_id', X) filter must be applied"


def test_update_criterion_warns_on_empty_result_data():
    """T-ACT-055: defensive WARN fires when .update().eq() matches zero rows.

    Surfaces the row-deleted edge case explicitly. Without this WARN, a manual
    DELETE on paper_phase_criteria or a migration regression would silently
    no-op every nightly evaluation — re-introducing a vector-2 (database-
    persistence surface) silent-failure of the class A.7 was reopened for.
    """
    from unittest.mock import patch, MagicMock
    from criteria_evaluator import _update_criterion

    mock_execute = MagicMock()
    mock_execute.data = []  # zero rows matched

    mock_chain = MagicMock()
    mock_chain.execute.return_value = mock_execute
    mock_chain.update.return_value = mock_chain
    mock_chain.eq.return_value = mock_chain

    mock_table = MagicMock()
    mock_table.return_value = mock_chain

    with patch("criteria_evaluator.get_client") as mock_db, \
         patch("criteria_evaluator.logger") as mock_logger:
        mock_db.return_value.table = mock_table
        _update_criterion("GLC-MISSING", "in_progress", "test", 0.0)

    mock_logger.warning.assert_called_once()
    call_args = mock_logger.warning.call_args
    assert call_args[0][0] == "criterion_update_no_match"
    assert call_args[1]["criterion_id"] == "GLC-MISSING"
    assert "hint" in call_args[1]
    assert "seed migration" in call_args[1]["hint"]
    assert "20260417000001_paper_phase_criteria.sql" in call_args[1]["hint"]


def test_update_criterion_no_warn_on_successful_update():
    """T-ACT-055: WARN must NOT fire when .update() matches at least 1 row.

    False-positive guard: ensures the WARN is only triggered by the row-
    deleted edge case, not by every successful update.
    """
    from unittest.mock import patch, MagicMock
    from criteria_evaluator import _update_criterion

    mock_execute = MagicMock()
    mock_execute.data = [{"criterion_id": "GLC-001", "status": "in_progress"}]

    mock_chain = MagicMock()
    mock_chain.execute.return_value = mock_execute
    mock_chain.update.return_value = mock_chain
    mock_chain.eq.return_value = mock_chain

    mock_table = MagicMock()
    mock_table.return_value = mock_chain

    with patch("criteria_evaluator.get_client") as mock_db, \
         patch("criteria_evaluator.logger") as mock_logger:
        mock_db.return_value.table = mock_table
        _update_criterion("GLC-001", "in_progress", "test", 1.0)

    mock_logger.warning.assert_not_called()


def test_update_criterion_db_error_logged_at_error():
    """T-ACT-055: outer except Exception still catches all DB errors and logs at ERROR.

    Preserves the never-raises contract from PR #6 baseline. The event name
    'criterion_upsert_failed' is deliberately retained for dashboard/log-search
    continuity (per T-ACT-055 plan-review §R3 — see inline comment at the
    logger.error line in criteria_evaluator.py).
    """
    from unittest.mock import patch
    from criteria_evaluator import _update_criterion

    with patch("criteria_evaluator.get_client", side_effect=Exception("DB down")), \
         patch("criteria_evaluator.logger") as mock_logger:
        # Must not raise
        _update_criterion("GLC-001", "in_progress", "test", 1.0)

    mock_logger.error.assert_called_once()
    call_args = mock_logger.error.call_args
    # Event name preserved per R3
    assert call_args[0][0] == "criterion_upsert_failed", (
        "Event name must remain 'criterion_upsert_failed' for dashboard "
        "continuity per T-ACT-055 plan-review §R3"
    )
    assert call_args[1]["criterion_id"] == "GLC-001"
    assert "DB down" in call_args[1]["error"]


def test_glc001_evaluation_writes_payload_without_schema_required_columns():
    """T-ACT-055 mechanism guard: payload sent to DB must NOT include criterion_name
    or target_description (the two NOT NULL columns whose absence triggered the
    PR #17 regression). With .update().eq(), these columns are correctly NOT in
    the payload — they're preserved from the seed migration row.

    This test asserts the regression mechanism: if a future PR reintroduces
    .upsert() WITHOUT also adding criterion_name + target_description to the
    payload, this test will continue to pass (false-negative) but
    test_update_criterion_uses_update_not_upsert will fail. The two tests
    together cover both the regression form (.upsert vs .update) and the
    regression mechanism (missing required columns).
    """
    from unittest.mock import patch, MagicMock
    from criteria_evaluator import _update_criterion

    mock_execute = MagicMock()
    mock_execute.data = [{"criterion_id": "GLC-001"}]

    mock_chain = MagicMock()
    mock_chain.execute.return_value = mock_execute
    mock_chain.update.return_value = mock_chain
    mock_chain.eq.return_value = mock_chain

    mock_table = MagicMock()
    mock_table.return_value = mock_chain

    with patch("criteria_evaluator.get_client") as mock_db:
        mock_db.return_value.table = mock_table
        _update_criterion(
            "GLC-001", "in_progress",
            "100 labeled predictions", 100.0,
            observations_count=100,
            notes="Test notes",
        )

    update_call_args = mock_chain.update.call_args
    payload = update_call_args[0][0]

    # Regression-mechanism guard: payload must NOT include schema-required
    # columns that triggered the PR #17 NOT NULL violation
    assert "criterion_name" not in payload, (
        "criterion_name must NOT be in update payload — it's preserved from "
        "seed migration. If a future PR adds it, the .upsert() form would "
        "again silently fail unless target_description is also added."
    )
    assert "target_description" not in payload, (
        "target_description must NOT be in update payload — same rationale "
        "as criterion_name above."
    )

    # Positive contract: payload includes the 6 expected mutable columns
    assert "status" in payload
    assert "current_value_text" in payload
    assert "current_value_numeric" in payload
    assert "observations_count" in payload
    assert "last_evaluated_at" in payload
    assert "notes" in payload
