"""
T-ACT-047 Choice C tests — postgrest persistent-error classification at the
prediction_engine persist site.

These tests verify that:
1. PostgrestAPIError raised by the supabase insert at L1495-1500 (post-edit)
   is caught at the new inner try/except block (NOT the outer except
   Exception handler at the bottom of run_cycle).
2. Persistent errors are logged at WARN with structured fields including
   pgrst_code / pgrst_details / pgrst_hint (R3).
3. write_health_status is called with status="error" and a
   "PERSISTENT[<code>]" prefix in last_error_message (R2).
4. send_alert(CRITICAL, ...) is called with the hint included in the email
   body (R3).
5. Non-postgrest exceptions (httpx.ConnectError = transient network,
   RuntimeError = generic) fall through to the outer except Exception
   handler (logged at ERROR with event "prediction_cycle_failed", per
   the current behavior preserved by Choice C scope).

R4 tightening: pytest.importorskip("postgrest.exceptions", ...) — guards
against the partial-install edge case (postgrest installed but submodule
missing). Production reality: postgrest is a transitive dep via
supabase==2.10.0 (backend/requirements.txt:1) so this guard is forward-
defensive only.

R5 splitting: Test 4 split into Test 4a (httpx.ConnectError) and Test 4b
(RuntimeError) per operator authorization. Each verifies a distinct
non-persistent exception class falls through to the outer handler.
"""
import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

postgrest_exc = pytest.importorskip(
    "postgrest.exceptions",
    reason="T-ACT-047 tests require postgrest.exceptions",
)
PostgrestAPIError = postgrest_exc.APIError


# ─── Fixtures ──────────────────────────────────────────────────────────────


def _build_pgrst_error(code="PGRST204", message="column not found",
                       details="Column 'foo' of trading_prediction_outputs",
                       hint="Run a migration to add the column"):
    """Construct a PostgrestAPIError matching the dict-based constructor
    in postgrest 0.18.0 (postgrest/exceptions.py:21).

    The constructor accepts a dict with code/message/details/hint keys;
    these are exposed as attributes on the resulting instance.
    """
    return PostgrestAPIError({
        "code": code,
        "message": message,
        "details": details,
        "hint": hint,
    })


@pytest.fixture
def engine_at_persist_site():
    """Build a PredictionEngine instance with all upstream dependencies of
    run_cycle stubbed to canned values, so the cycle reaches the supabase
    insert site at L1495-1500 (post-edit) deterministically.

    Each test then varies only what happens at the insert site (raises
    PostgrestAPIError vs. httpx.ConnectError vs. RuntimeError vs. success)
    and asserts on the resulting log/health/alert behavior.

    Returns the engine. Tests are responsible for patching get_client at
    the prediction_engine module scope using `with patch(...)`.
    """
    from prediction_engine import PredictionEngine

    engine = PredictionEngine.__new__(PredictionEngine)
    # Required attributes referenced inside run_cycle
    engine._cycle_count = 0
    engine._cv_stress_degenerate_logged = False  # T-ACT-054 flag
    # redis_client: present + responsive so the cycle proceeds past the
    # availability check at L1252-1258.
    engine.redis_client = MagicMock()
    engine.redis_client.ping.return_value = True
    return engine


def _stub_engine_internals(engine, fresh_spx=True):
    """Patch engine internals to canned values that drive run_cycle past
    every guard up to (but not over) the supabase insert.

    Returns a tuple of (patches, expected_output_dict). The caller enters
    each patch via a context manager; the expected_output_dict is the
    payload that would be passed to .insert(...) in a clean run.
    """
    fetched_at = datetime.now(timezone.utc).isoformat()
    spx_meta = json.dumps({
        "price": 5200.0,
        "fetched_at": fetched_at,
        "fetched_at_source": "polygon",
    })

    def _read_redis_stub(key, default=None):
        if key == "polygon:vvix:z_score":
            return "0.5"
        if key == "gex:confidence":
            return "0.7"
        if key == "polygon:spx:current":
            return spx_meta
        if key == "polygon:vvix:current":
            return "20.0"
        if key == "polygon:vix:current":
            return "18.0"
        if key in ("gex:net", "gex:nearest_wall", "gex:flip_zone"):
            return "0.0"
        return default

    regime_data = {
        "regime": "balanced",
        "rcs": 50.0,
        "gex_flip_zone_used": None,
        "gex_conf_at_regime": 0.7,
    }
    cv_data = {
        "cv_stress_score": 30.0,
        "charm_velocity": 0.0,
        "vanna_velocity": 0.0,
    }
    direction_data = {
        "direction": "long",
        "confidence": 0.6,
        "signal_weak": False,
    }
    phase_a_features = {
        "earnings_proximity_score": 0.0,
    }

    return {
        "_read_redis": _read_redis_stub,
        "_get_spx_price": lambda: 5200.0,
        "_compute_regime": lambda: regime_data,
        "_compute_cv_stress": lambda: cv_data,
        "_compute_direction": lambda *a, **k: direction_data,
        "_evaluate_no_trade": lambda *a, **k: (False, ""),
        "_compute_phase_a_features": lambda **k: phase_a_features,
        "_write_heartbeat": lambda: None,
    }


def _run_cycle_with_insert_behavior(engine, insert_side_effect):
    """Drive engine.run_cycle() with the supabase insert raising the given
    exception (or returning a clean result if side_effect is None).

    `insert_side_effect`: an Exception instance to raise at .execute() time,
    or None for a clean insert that returns a Mock result with
    `.data == [{"id": "test"}]`.

    Returns a dict of MagicMock handles for assertion:
      - mock_write_health: write_health_status mock
      - mock_send_alert:   alerting.send_alert mock
      - mock_get_client:   get_client mock (the chain root)
      - mock_logger:       prediction_engine.logger mock
      - run_result:        return value of run_cycle()
    """
    stubs = _stub_engine_internals(engine)

    # Build the supabase insert chain. Each .table().insert().execute() is
    # a method-chain attribute lookup; we make .execute() either raise or
    # return a canned dict.
    mock_execute = MagicMock()
    if insert_side_effect is not None:
        mock_execute.execute.side_effect = insert_side_effect
    else:
        mock_execute.execute.return_value = MagicMock(data=[{"id": "test"}])
    mock_insert = MagicMock()
    mock_insert.insert.return_value = mock_execute
    mock_table = MagicMock()
    mock_table.table.return_value = mock_insert

    # Patch all internals + module-level functions in one stack.
    with patch.object(engine, "_read_redis",
                      side_effect=stubs["_read_redis"]), \
         patch.object(engine, "_get_spx_price",
                      side_effect=stubs["_get_spx_price"]), \
         patch.object(engine, "_compute_regime",
                      side_effect=stubs["_compute_regime"]), \
         patch.object(engine, "_compute_cv_stress",
                      side_effect=stubs["_compute_cv_stress"]), \
         patch.object(engine, "_compute_direction",
                      side_effect=stubs["_compute_direction"]), \
         patch.object(engine, "_evaluate_no_trade",
                      side_effect=stubs["_evaluate_no_trade"]), \
         patch.object(engine, "_compute_phase_a_features",
                      side_effect=stubs["_compute_phase_a_features"]), \
         patch.object(engine, "_write_heartbeat",
                      side_effect=stubs["_write_heartbeat"]), \
         patch("prediction_engine.get_client",
               return_value=mock_table) as mock_get_client, \
         patch("prediction_engine.write_health_status") as mock_write_health, \
         patch("prediction_engine.write_audit_log"), \
         patch("prediction_engine.get_today_session",
               return_value={"id": "test_session",
                             "consecutive_losses_today": 0}), \
         patch("market_calendar.is_market_open", return_value=True), \
         patch("alerting.send_alert") as mock_send_alert, \
         patch("prediction_engine.logger") as mock_logger:
        run_result = engine.run_cycle()

    return {
        "mock_write_health": mock_write_health,
        "mock_send_alert": mock_send_alert,
        "mock_get_client": mock_get_client,
        "mock_logger": mock_logger,
        "run_result": run_result,
    }


# ─── Tests ─────────────────────────────────────────────────────────────────


def test_persistent_error_logged_at_warn_with_structured_fields(
    engine_at_persist_site,
):
    """Test 1: PostgrestAPIError → logger.warning(prediction_cycle_persistent_error)
    with code/details/hint extracted via getattr."""
    err = _build_pgrst_error(
        code="PGRST204", message="column not found",
        details="Column 'nonexistent' of trading_prediction_outputs",
        hint="Run migration to add the column",
    )
    handles = _run_cycle_with_insert_behavior(engine_at_persist_site, err)

    # Assert: WARN log fired with the persistent-error event name
    warn_calls = handles["mock_logger"].warning.call_args_list
    persistent_calls = [
        c for c in warn_calls
        if c.args and c.args[0] == "prediction_cycle_persistent_error"
    ]
    assert len(persistent_calls) == 1, (
        f"Expected exactly 1 prediction_cycle_persistent_error WARN log, "
        f"got {len(persistent_calls)}. All WARN calls: {warn_calls}"
    )
    log_kwargs = persistent_calls[0].kwargs
    assert log_kwargs.get("error_class") == "postgrest_api_error"
    assert log_kwargs.get("pgrst_code") == "PGRST204"
    assert "nonexistent" in (log_kwargs.get("pgrst_details") or "")
    assert "migration" in (log_kwargs.get("pgrst_hint") or "")
    assert log_kwargs.get("exc_info") is True

    # Assert: outer ERROR-level prediction_cycle_failed log NOT fired
    error_calls = handles["mock_logger"].error.call_args_list
    cycle_failed_calls = [
        c for c in error_calls
        if c.args and c.args[0] == "prediction_cycle_failed"
    ]
    assert len(cycle_failed_calls) == 0, (
        "Persistent error must be caught at the inner block; outer "
        "prediction_cycle_failed ERROR log must NOT fire."
    )

    # run_cycle returns None on the persistent path
    assert handles["run_result"] is None


def test_persistent_error_writes_health_error_with_persistent_prefix(
    engine_at_persist_site,
):
    """Test 2: PostgrestAPIError → write_health_status(prediction_engine,
    error, last_error_message=PERSISTENT[code]: ...). Verifies acceptance
    criterion #4 (R2): the error_count_1h auto-increment dependency at
    db.py:233-249 fires on this code path."""
    err = _build_pgrst_error(code="PGRST204")
    handles = _run_cycle_with_insert_behavior(engine_at_persist_site, err)

    write_calls = handles["mock_write_health"].call_args_list
    assert len(write_calls) >= 1, (
        f"write_health_status was not called. Calls: {write_calls}"
    )
    # Find the persistent-error write specifically (last_error_message
    # contains the PERSISTENT[ marker).
    persistent_writes = [
        c for c in write_calls
        if "PERSISTENT[" in str(c.kwargs.get("last_error_message", ""))
    ]
    assert len(persistent_writes) == 1, (
        f"Expected exactly 1 PERSISTENT[ health write, "
        f"got {len(persistent_writes)}. Calls: {write_calls}"
    )
    pwrite = persistent_writes[0]
    assert pwrite.args[:2] == ("prediction_engine", "error")
    assert "PERSISTENT[PGRST204]" in pwrite.kwargs["last_error_message"]


def test_persistent_error_fires_critical_alert_with_hint_in_body(
    engine_at_persist_site,
):
    """Test 3: PostgrestAPIError → alerting.send_alert(CRITICAL,
    prediction_engine_persistent_error, body) with code/detail/hint in body.
    Verifies R3 (hint included in alert body)."""
    err = _build_pgrst_error(
        code="PGRST204",
        details="Column 'foo' missing",
        hint="Add column via migration XYZ",
    )
    handles = _run_cycle_with_insert_behavior(engine_at_persist_site, err)

    alert_calls = handles["mock_send_alert"].call_args_list
    persistent_alerts = [
        c for c in alert_calls
        if len(c.args) >= 2
        and c.args[1] == "prediction_engine_persistent_error"
    ]
    assert len(persistent_alerts) == 1, (
        f"Expected exactly 1 prediction_engine_persistent_error alert, "
        f"got {len(persistent_alerts)}. Calls: {alert_calls}"
    )
    a = persistent_alerts[0]
    # Severity = CRITICAL (the CRITICAL constant value is "critical")
    assert a.args[0] == "critical"
    body = a.args[2] if len(a.args) >= 3 else ""
    assert "code=PGRST204" in body
    assert "Column 'foo' missing" in body
    assert "Add column via migration XYZ" in body, (
        f"R3 violation: hint must appear in alert body. Body: {body}"
    )


def test_4a_httpx_connect_error_falls_through_to_outer_except(
    engine_at_persist_site,
):
    """Test 4a: httpx.ConnectError (transient network class) is NOT caught
    by the new inner block — it falls through to the outer except Exception
    handler at the bottom of run_cycle, which logs at ERROR with event
    "prediction_cycle_failed" and writes health status="error" without
    the PERSISTENT[ prefix."""
    httpx = pytest.importorskip(
        "httpx", reason="Test 4a requires httpx",
    )
    err = httpx.ConnectError("connection refused")
    handles = _run_cycle_with_insert_behavior(engine_at_persist_site, err)

    # Outer ERROR log fired
    error_calls = handles["mock_logger"].error.call_args_list
    cycle_failed_calls = [
        c for c in error_calls
        if c.args and c.args[0] == "prediction_cycle_failed"
    ]
    assert len(cycle_failed_calls) == 1, (
        "httpx.ConnectError must fall through to the outer "
        "except Exception handler (logger.error prediction_cycle_failed)."
    )

    # Inner WARN log NOT fired
    warn_calls = handles["mock_logger"].warning.call_args_list
    persistent_warns = [
        c for c in warn_calls
        if c.args and c.args[0] == "prediction_cycle_persistent_error"
    ]
    assert len(persistent_warns) == 0, (
        "httpx.ConnectError must NOT trigger the persistent-error path."
    )

    # No persistent alert fired
    alert_calls = handles["mock_send_alert"].call_args_list
    persistent_alerts = [
        c for c in alert_calls
        if len(c.args) >= 2
        and c.args[1] == "prediction_engine_persistent_error"
    ]
    assert len(persistent_alerts) == 0, (
        "httpx.ConnectError must NOT trigger the CRITICAL alert path."
    )

    # Health write happened, but WITHOUT the PERSISTENT[ prefix
    write_calls = handles["mock_write_health"].call_args_list
    assert len(write_calls) >= 1
    persistent_writes = [
        c for c in write_calls
        if "PERSISTENT[" in str(c.kwargs.get("last_error_message", ""))
    ]
    assert len(persistent_writes) == 0, (
        "Outer-handler health write must NOT carry the PERSISTENT[ prefix."
    )

    assert handles["run_result"] is None


def test_4b_runtime_error_falls_through_to_outer_except(
    engine_at_persist_site,
):
    """Test 4b: RuntimeError (generic non-postgrest, non-httpx exception)
    falls through to the outer except Exception handler. Verifies the
    inner block's catch is NARROWLY scoped to PostgrestAPIError and does
    not accidentally swallow generic exceptions."""
    err = RuntimeError("simulated generic failure")
    handles = _run_cycle_with_insert_behavior(engine_at_persist_site, err)

    # Outer ERROR log fired
    error_calls = handles["mock_logger"].error.call_args_list
    cycle_failed_calls = [
        c for c in error_calls
        if c.args and c.args[0] == "prediction_cycle_failed"
    ]
    assert len(cycle_failed_calls) == 1, (
        "RuntimeError must fall through to the outer except Exception "
        "handler (logger.error prediction_cycle_failed)."
    )

    # Inner WARN log NOT fired
    warn_calls = handles["mock_logger"].warning.call_args_list
    persistent_warns = [
        c for c in warn_calls
        if c.args and c.args[0] == "prediction_cycle_persistent_error"
    ]
    assert len(persistent_warns) == 0, (
        "RuntimeError must NOT trigger the persistent-error path."
    )

    # No persistent alert fired
    alert_calls = handles["mock_send_alert"].call_args_list
    persistent_alerts = [
        c for c in alert_calls
        if len(c.args) >= 2
        and c.args[1] == "prediction_engine_persistent_error"
    ]
    assert len(persistent_alerts) == 0, (
        "RuntimeError must NOT trigger the CRITICAL alert path."
    )

    assert handles["run_result"] is None
