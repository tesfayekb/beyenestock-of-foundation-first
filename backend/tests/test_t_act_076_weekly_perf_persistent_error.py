"""
T-ACT-076 Scope B / F-068-A tests — postgrest persistent-error
classification at the weekly model-performance persist site
(model_retraining.run_weekly_model_performance, the second
A.7-family persist site after prediction_engine.run_cycle).

These tests verify that:
1. PostgrestAPIError raised by the supabase insert at
   model_retraining.py ~L677 is caught at the NEW inner
   try/except block (NOT the outer except Exception handler at
   the bottom of run_weekly_model_performance).
2. Persistent errors are logged at WARN with event
   `weekly_model_performance_persistent_error` and structured
   fields including pgrst_code / pgrst_details / pgrst_hint /
   drift_status_attempted.
3. write_health_status is called with status="error" and a
   "PERSISTENT[<code>]" prefix in last_error_message.
4. send_alert(CRITICAL, ...) is called with the hint and the
   drift_status_attempted included in the email body.
5. The function returns
   {"error": "persistent_postgrest:<code>"} (NOT collapsed to
   the generic outer-except message).

Pattern is byte-for-byte aligned with the T-ACT-047 Choice C
test file (test_t_act_047_persistent_error_classification.py)
to keep the two A.7-family persist-site tests in lock-step.

R-discipline: pytest.importorskip("postgrest.exceptions", ...) —
guards against the partial-install edge case. Production reality:
postgrest is a transitive dep via supabase==2.10.0 so this guard
is forward-defensive only.
"""
from unittest.mock import MagicMock, patch

import pytest

postgrest_exc = pytest.importorskip(
    "postgrest.exceptions",
    reason="T-ACT-076 tests require postgrest.exceptions",
)
PostgrestAPIError = postgrest_exc.APIError


def _build_pgrst_error(
    code="23514",
    message="new row for relation \"trading_model_performance\" "
            "violates check constraint",
    details=(
        "Failing row contains (..., ok, ...). check_violation."
    ),
    hint=(
        "Widen drift_status CHECK constraint to include 'ok' "
        "and 'unknown' (T-ACT-076 / F-068-A)."
    ),
):
    """Construct a PostgrestAPIError that mimics the actual
    23514 check_violation Supabase produces on the F-068-A
    insert path. Same constructor shape as
    test_t_act_047_persistent_error_classification.py:_build_pgrst_error."""
    return PostgrestAPIError({
        "code": code,
        "message": message,
        "details": details,
        "hint": hint,
    })


def _make_inserter_raising(err):
    """Build a mock get_client() chain whose .insert(...).execute()
    raises `err`. All other call paths used by
    run_weekly_model_performance return harmless MagicMocks."""
    mock_client = MagicMock()
    table_chain = mock_client.table.return_value
    table_chain.insert.return_value.execute.side_effect = err
    return mock_client


def _stub_compute_paths():
    """Common patch dict for the upstream compute helpers so the
    cycle reaches the persist site deterministically. Returns
    drift_status='ok' (the F-068-A trigger value) so the test
    asserts the drift_status_attempted field is captured."""
    return {
        "compute_directional_accuracy": {"accuracy": 0.55, "observations": 50},
        "compute_per_regime_accuracy": {},
        "detect_drift": {"drift_status": "ok", "drift_z_score": 0.1},
        "compute_sharpe_ratio": 1.2,
        "compute_profit_factor": 1.4,
        "count_preservation_triggers_this_week": 0,
    }


def test_postgrest_error_logged_with_structured_fields():
    """T-ACT-076 acceptance #1 + #2: PostgrestAPIError on the
    weekly insert is logged at WARN with the new structured
    event name and rich pgrst_* fields. Must NOT fall through to
    the outer except Exception (which would log at ERROR with
    `weekly_model_performance_failed`)."""
    from model_retraining import run_weekly_model_performance

    err = _build_pgrst_error()
    mock_client = _make_inserter_raising(err)
    stubs = _stub_compute_paths()

    with patch("model_retraining.get_client", return_value=mock_client), \
         patch("model_retraining.compute_directional_accuracy",
               return_value=stubs["compute_directional_accuracy"]), \
         patch("model_retraining.compute_per_regime_accuracy",
               return_value=stubs["compute_per_regime_accuracy"]), \
         patch("model_retraining.detect_drift",
               return_value=stubs["detect_drift"]), \
         patch("model_retraining.compute_sharpe_ratio",
               return_value=stubs["compute_sharpe_ratio"]), \
         patch("model_retraining.compute_profit_factor",
               return_value=stubs["compute_profit_factor"]), \
         patch("model_retraining.count_preservation_triggers_this_week",
               return_value=stubs["count_preservation_triggers_this_week"]), \
         patch("model_retraining.write_health_status"), \
         patch("model_retraining.write_audit_log"), \
         patch("model_retraining.logger") as mock_logger, \
         patch("alerting.send_alert"):

        result = run_weekly_model_performance()

    assert mock_logger.warning.called, (
        "T-ACT-076: PostgrestAPIError must be classified at WARN "
        "via the inner try/except, not at ERROR via the outer "
        "except Exception."
    )
    warn_calls = [
        c for c in mock_logger.warning.call_args_list
        if c.args and c.args[0] == "weekly_model_performance_persistent_error"
    ]
    assert warn_calls, (
        "Missing structured event "
        "`weekly_model_performance_persistent_error` — the "
        "inner classifier did not fire."
    )
    kwargs = warn_calls[0].kwargs
    assert kwargs.get("error_class") == "postgrest_api_error"
    assert kwargs.get("pgrst_code") == "23514"
    assert "check_violation" in (kwargs.get("pgrst_details") or "")
    assert "Widen drift_status" in (kwargs.get("pgrst_hint") or "")
    assert kwargs.get("drift_status_attempted") == "ok", (
        "T-ACT-076 differentiator vs. T-ACT-047: this site must "
        "record drift_status_attempted so the F-068-A vs "
        "non-F-068-A cases are distinguishable from logs."
    )
    assert result == {"error": "persistent_postgrest:23514"}, (
        "Function must return the structured persistent-class "
        "key, not the generic outer-except str(e)."
    )


def test_postgrest_error_writes_health_error_with_persistent_prefix():
    """T-ACT-076 acceptance #3: write_health_status is called
    with status='error' and a 'PERSISTENT[<code>]' prefix on
    last_error_message — same convention as T-ACT-047."""
    from model_retraining import run_weekly_model_performance

    err = _build_pgrst_error(code="PGRST204")
    mock_client = _make_inserter_raising(err)
    stubs = _stub_compute_paths()

    with patch("model_retraining.get_client", return_value=mock_client), \
         patch("model_retraining.compute_directional_accuracy",
               return_value=stubs["compute_directional_accuracy"]), \
         patch("model_retraining.compute_per_regime_accuracy",
               return_value=stubs["compute_per_regime_accuracy"]), \
         patch("model_retraining.detect_drift",
               return_value=stubs["detect_drift"]), \
         patch("model_retraining.compute_sharpe_ratio",
               return_value=stubs["compute_sharpe_ratio"]), \
         patch("model_retraining.compute_profit_factor",
               return_value=stubs["compute_profit_factor"]), \
         patch("model_retraining.count_preservation_triggers_this_week",
               return_value=stubs["count_preservation_triggers_this_week"]), \
         patch("model_retraining.write_health_status") as mock_health, \
         patch("model_retraining.write_audit_log"), \
         patch("alerting.send_alert"):

        run_weekly_model_performance()

    assert mock_health.called
    args, kwargs = mock_health.call_args
    assert args[0] == "prediction_engine"
    assert args[1] == "error"
    last_err = kwargs.get("last_error_message", "")
    assert last_err.startswith("PERSISTENT[PGRST204]"), (
        f"Expected PERSISTENT[PGRST204] prefix, got: {last_err!r}"
    )


def test_postgrest_error_fires_critical_alert_with_hint():
    """T-ACT-076 acceptance #4: send_alert(CRITICAL, ...) fires
    with the hint and drift_status_attempted included so the
    operator can act without a log dive."""
    from model_retraining import run_weekly_model_performance

    err = _build_pgrst_error(
        code="23514",
        hint="Widen drift_status CHECK constraint to include 'ok'.",
    )
    mock_client = _make_inserter_raising(err)
    stubs = _stub_compute_paths()

    with patch("model_retraining.get_client", return_value=mock_client), \
         patch("model_retraining.compute_directional_accuracy",
               return_value=stubs["compute_directional_accuracy"]), \
         patch("model_retraining.compute_per_regime_accuracy",
               return_value=stubs["compute_per_regime_accuracy"]), \
         patch("model_retraining.detect_drift",
               return_value=stubs["detect_drift"]), \
         patch("model_retraining.compute_sharpe_ratio",
               return_value=stubs["compute_sharpe_ratio"]), \
         patch("model_retraining.compute_profit_factor",
               return_value=stubs["compute_profit_factor"]), \
         patch("model_retraining.count_preservation_triggers_this_week",
               return_value=stubs["count_preservation_triggers_this_week"]), \
         patch("model_retraining.write_health_status"), \
         patch("model_retraining.write_audit_log"), \
         patch("alerting.send_alert") as mock_alert, \
         patch("alerting.CRITICAL", "CRITICAL"):

        run_weekly_model_performance()

    assert mock_alert.called, (
        "T-ACT-076 acceptance #4: CRITICAL alert must fire on "
        "persistent-class persist failure."
    )
    args, _ = mock_alert.call_args
    severity, subject, body = args[0], args[1], args[2]
    assert severity == "CRITICAL"
    assert subject == "weekly_model_performance_persistent_error"
    assert "code=23514" in body
    assert "Widen drift_status" in body
    assert "drift_status_attempted=ok" in body, (
        "Body must include drift_status_attempted for F-068-A "
        "diagnostic clarity."
    )


def test_non_postgrest_exception_falls_through_to_outer_handler():
    """T-ACT-076 / Choice C scope guard: non-postgrest exceptions
    (e.g. RuntimeError raised by compute_sharpe_ratio) MUST fall
    through to the outer except Exception (logged at ERROR with
    `weekly_model_performance_failed`). The inner classifier
    must not over-catch."""
    from model_retraining import run_weekly_model_performance

    stubs = _stub_compute_paths()

    with patch("model_retraining.get_client") as mock_get_client, \
         patch("model_retraining.compute_directional_accuracy",
               return_value=stubs["compute_directional_accuracy"]), \
         patch("model_retraining.compute_per_regime_accuracy",
               return_value=stubs["compute_per_regime_accuracy"]), \
         patch("model_retraining.detect_drift",
               return_value=stubs["detect_drift"]), \
         patch("model_retraining.compute_sharpe_ratio",
               side_effect=RuntimeError("synthetic compute failure")), \
         patch("model_retraining.compute_profit_factor",
               return_value=stubs["compute_profit_factor"]), \
         patch("model_retraining.count_preservation_triggers_this_week",
               return_value=stubs["count_preservation_triggers_this_week"]), \
         patch("model_retraining.write_health_status"), \
         patch("model_retraining.write_audit_log"), \
         patch("model_retraining.logger") as mock_logger:

        result = run_weekly_model_performance()

    mock_get_client.assert_not_called()
    assert mock_logger.error.called, (
        "Non-postgrest RuntimeError must reach the outer ERROR "
        "log, not the inner WARN classifier."
    )
    error_events = [
        c.args[0] for c in mock_logger.error.call_args_list
    ]
    assert "weekly_model_performance_failed" in error_events
    assert result.get("error", "").startswith("synthetic compute failure"), (
        f"Expected outer-handler str(e) propagation, got: {result!r}"
    )


def test_successful_insert_returns_summary_no_warning():
    """Happy-path regression guard: when insert succeeds the
    function returns the summary dict and does NOT log the new
    persistent-error event."""
    from model_retraining import run_weekly_model_performance

    mock_client = MagicMock()
    mock_client.table.return_value.insert.return_value.execute.return_value = (
        MagicMock()
    )
    stubs = _stub_compute_paths()

    with patch("model_retraining.get_client", return_value=mock_client), \
         patch("model_retraining.compute_directional_accuracy",
               return_value=stubs["compute_directional_accuracy"]), \
         patch("model_retraining.compute_per_regime_accuracy",
               return_value=stubs["compute_per_regime_accuracy"]), \
         patch("model_retraining.detect_drift",
               return_value=stubs["detect_drift"]), \
         patch("model_retraining.compute_sharpe_ratio",
               return_value=stubs["compute_sharpe_ratio"]), \
         patch("model_retraining.compute_profit_factor",
               return_value=stubs["compute_profit_factor"]), \
         patch("model_retraining.count_preservation_triggers_this_week",
               return_value=stubs["count_preservation_triggers_this_week"]), \
         patch("model_retraining.write_health_status"), \
         patch("model_retraining.write_audit_log"), \
         patch("model_retraining.logger") as mock_logger:

        result = run_weekly_model_performance()

    assert "error" not in result
    assert result["accuracy_5d"] == 0.55
    assert result["drift_status"] == "ok"
    persistent_warn_events = [
        c for c in mock_logger.warning.call_args_list
        if c.args and c.args[0] == "weekly_model_performance_persistent_error"
    ]
    assert not persistent_warn_events, (
        "Happy-path must not emit the persistent-error event."
    )
