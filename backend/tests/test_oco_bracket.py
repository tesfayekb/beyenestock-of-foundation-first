"""
12I (C1) — OCO bracket order tests.

The OCO submission path has two independent guards:
  (1) TRADIER_SANDBOX=False    — real-capital environment
  (2) OCO_BRACKET_ENABLED=True — operator acknowledgement that the
                                  MUST-FIX items in
                                  _submit_oco_bracket's docstring have
                                  been addressed and the order shape
                                  validated in Tradier sandbox.

Both must be True for any Tradier POST to occur. These tests pin the
dual-guard semantics and the fail-open behaviour (OCO failure must
never fail a position open) so a regression in either dimension fires
loudly during CI rather than silently the first day someone flips
OCO_BRACKET_ENABLED=true.
"""
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def signal():
    return {
        "instrument": "SPX",
        "contracts": 2,
        "strategy_type": "iron_butterfly",
    }


@pytest.fixture
def fill():
    # iron_butterfly: signed_fill positive (credit strategy) so that
    # the scaffold's credit-oriented TP/SL math is at least correct
    # for this particular case — the tests don't need to validate the
    # math (see MUST-FIX #2 in _submit_oco_bracket's docstring).
    return {
        "signed_fill": 1.50,
        "fill_price": 1.50,
        "is_debit": False,
        "actual_slippage": 0.05,
    }


def _make_resp(status_code: int, order_id: str = ""):
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = '{"order": {"id": "fake"}}'
    resp.json.return_value = (
        {"order": {"id": order_id}} if order_id else {}
    )
    return resp


# ── guard tests: sandbox mode ─────────────────────────────────────────


def test_oco_helper_routes_to_sandbox_host_when_sandbox_flag_set(signal, fill):
    """MUST-FIX #4 (sandbox verification) prerequisite: when the
    helper IS invoked with TRADIER_SANDBOX=True — the intended
    staged-rollout posture — the POST goes to sandbox.tradier.com,
    never api.tradier.com. This is the property the sandbox round-trip
    test in MUST-FIX #4 will rely on."""
    from execution_engine import _submit_oco_bracket

    with patch("requests.post") as mock_post, \
         patch("config.TRADIER_SANDBOX", True), \
         patch("config.TRADIER_API_KEY", "sandbox-key"), \
         patch("config.TRADIER_ACCOUNT_ID", "VA00000000"), \
         patch("config.OCO_BRACKET_ENABLED", True):
        mock_post.return_value = _make_resp(200, "sbx-oid-1")
        result = _submit_oco_bracket(signal, fill, "pos-sbx-00001")

    assert result == "sbx-oid-1"
    args, _ = mock_post.call_args
    assert "sandbox.tradier.com" in args[0]
    assert "api.tradier.com" not in args[0]


# ── guard tests: real mode ────────────────────────────────────────────


def test_oco_submitted_in_real_mode(signal, fill):
    """Guard (1) + (2): TRADIER_SANDBOX=False AND
    OCO_BRACKET_ENABLED=True → helper returns the Tradier order ID
    from the POST response. Also pins the payload shape so a silent
    change to the MUST-FIX-listed fields fires loudly."""
    from execution_engine import _submit_oco_bracket

    with patch("requests.post") as mock_post, \
         patch("config.TRADIER_SANDBOX", False), \
         patch("config.TRADIER_API_KEY", "test-key"), \
         patch("config.TRADIER_ACCOUNT_ID", "VA00000000"), \
         patch("config.OCO_BRACKET_ENABLED", True):
        mock_post.return_value = _make_resp(200, "oid-42")
        result = _submit_oco_bracket(signal, fill, "pos-abc-12345678")

    assert result == "oid-42"
    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    # URL points to production host (not sandbox) because
    # TRADIER_SANDBOX=False inside this test — matches gex_engine /
    # position_monitor's base-URL pattern.
    assert "api.tradier.com" in args[0]
    assert "/v1/accounts/VA00000000/orders" in args[0]
    assert kwargs["headers"]["Authorization"] == "Bearer test-key"
    assert kwargs["data"]["class"] == "bracket"
    assert kwargs["data"]["tag"].startswith("mm_")


# ── fail-open paths ───────────────────────────────────────────────────


def test_oco_fail_open_on_api_error(signal, fill):
    """Tradier returns non-200 (e.g. 400 validation error) → helper
    returns None and does not raise. Position open must continue
    unaffected — OCO is observability, not a trading invariant."""
    from execution_engine import _submit_oco_bracket

    with patch("requests.post") as mock_post, \
         patch("config.TRADIER_SANDBOX", False), \
         patch("config.TRADIER_API_KEY", "test-key"), \
         patch("config.TRADIER_ACCOUNT_ID", "VA00000000"), \
         patch("config.OCO_BRACKET_ENABLED", True):
        err = _make_resp(400)
        err.text = '{"errors": {"error": ["invalid class"]}}'
        mock_post.return_value = err
        result = _submit_oco_bracket(signal, fill, "pos-abc-12345678")

    assert result is None


def test_oco_fail_open_on_exception(signal, fill):
    """requests.post raises ConnectionError → helper swallows and
    returns None. The outer caller's try/except makes the failure
    invisible to the trade lifecycle."""
    from execution_engine import _submit_oco_bracket

    with patch("requests.post", side_effect=ConnectionError("tradier down")), \
         patch("config.TRADIER_SANDBOX", False), \
         patch("config.TRADIER_API_KEY", "test-key"), \
         patch("config.TRADIER_ACCOUNT_ID", "VA00000000"), \
         patch("config.OCO_BRACKET_ENABLED", True):
        result = _submit_oco_bracket(signal, fill, "pos-abc-12345678")

    assert result is None


def test_oco_skipped_when_missing_credentials(signal, fill):
    """TRADIER_ACCOUNT_ID absent → helper short-circuits before any
    network call. Prevents an accidental live deploy with broken env
    vars from spamming Tradier with malformed requests."""
    from execution_engine import _submit_oco_bracket

    with patch("requests.post") as mock_post, \
         patch("config.TRADIER_SANDBOX", False), \
         patch("config.TRADIER_API_KEY", "test-key"), \
         patch("config.TRADIER_ACCOUNT_ID", None), \
         patch("config.OCO_BRACKET_ENABLED", True):
        result = _submit_oco_bracket(signal, fill, "pos-abc-12345678")

    assert result is None
    mock_post.assert_not_called()


def test_oco_returns_none_when_order_id_absent(signal, fill):
    """Tradier returns 200 but an empty body (no order.id) → helper
    returns None rather than writing an empty-string oco_order_id to
    Supabase."""
    from execution_engine import _submit_oco_bracket

    with patch("requests.post") as mock_post, \
         patch("config.TRADIER_SANDBOX", False), \
         patch("config.TRADIER_API_KEY", "test-key"), \
         patch("config.TRADIER_ACCOUNT_ID", "VA00000000"), \
         patch("config.OCO_BRACKET_ENABLED", True):
        mock_post.return_value = _make_resp(200, "")
        result = _submit_oco_bracket(signal, fill, "pos-abc-12345678")

    assert result is None


# ── end-to-end: open_virtual_position dual-guard ──────────────────────


class _FakeTable:
    """
    Supabase table mock mirroring the minimal surface exercised by
    open_virtual_position: insert(row).execute() → row with id, and
    update(payload).eq("id", pid).execute() captured in self._events.

    All pre-insert fluent chains (.select().eq().in_().execute())
    are intentionally absent — open_virtual_position wraps each in a
    try/except that fails OPEN, so AttributeErrors here exercise the
    same resilient path that a transient Supabase blip would.
    """

    def __init__(self, events: list):
        self._events = events
        self._pending_update = None

    def insert(self, row):
        self._pending_insert = row
        return self

    def update(self, payload):
        self._pending_update = payload
        return self

    def eq(self, col, val):
        if self._pending_update is not None:
            self._events.append(
                ("update", dict(self._pending_update), col, val)
            )
            self._pending_update = None
        return self

    def execute(self):
        if getattr(self, "_pending_insert", None):
            row = self._pending_insert
            row.setdefault("id", "pos-uuid-0001")
            self._pending_insert = None
            self._events.append(("insert", row))
            return MagicMock(data=[row])
        return MagicMock(data=[])


class _FakeClient:
    def __init__(self, events: list):
        self._events = events

    def table(self, _name):
        return _FakeTable(self._events)


def _minimal_signal():
    return {
        "session_id": "sess-1",
        "instrument": "SPX",
        "contracts": 1,
        "strategy_type": "iron_butterfly",
        "target_credit": 1.50,
        "regime_at_signal": "pin_range",
        "rcs_at_signal": 80.0,
        "cv_stress_at_signal": 20.0,
        "expiry_date": "2026-04-21",
        "short_strike": 5200,
        "long_strike": 5210,
        "position_type": "core",
        "decision_context": {},
    }


def _minimal_prediction():
    return {"id": "pred-1", "spx_price": 5200.0, "cv_stress_score": 20.0}


def _engine():
    """Build an ExecutionEngine without touching Redis — mirrors the
    pattern used by test_consolidation_s2.py so we stay consistent
    with existing engine-level tests."""
    from execution_engine import ExecutionEngine

    engine = ExecutionEngine.__new__(ExecutionEngine)
    engine.redis_client = None
    return engine


def test_open_virtual_position_sandbox_no_oco_submit():
    """End-to-end guard: TRADIER_SANDBOX=True → open_virtual_position
    completes normally, never calls _submit_oco_bracket, never updates
    oco_order_id on the row. This is the production state today and
    MUST remain a no-op for the virtual-only flow."""
    engine = _engine()
    events = []

    with patch("execution_engine.get_today_session", return_value={
            "id": "sess-1", "virtual_trades_count": 0,
         }), \
         patch("execution_engine.get_client",
               return_value=_FakeClient(events)), \
         patch("execution_engine.update_session"), \
         patch("execution_engine.write_audit_log"), \
         patch("execution_engine.write_health_status"), \
         patch("execution_engine._submit_oco_bracket") as mock_oco, \
         patch("config.TRADIER_SANDBOX", True), \
         patch("config.OCO_BRACKET_ENABLED", True):
        result = engine.open_virtual_position(
            _minimal_signal(), _minimal_prediction()
        )

    assert result is not None
    mock_oco.assert_not_called()
    # No update on trading_positions should carry oco_order_id.
    update_payloads = [e[1] for e in events if e[0] == "update"]
    assert not any("oco_order_id" in p for p in update_payloads)


def test_open_virtual_position_real_but_flag_off_no_oco_submit():
    """Critical guard: TRADIER_SANDBOX=False BUT OCO_BRACKET_ENABLED
    still defaults to False → NO submission. Documents that flipping
    only TRADIER_SANDBOX is not sufficient — the MUST-FIX items in
    _submit_oco_bracket's docstring must be addressed AND
    OCO_BRACKET_ENABLED explicitly set before any Tradier POST."""
    engine = _engine()
    events = []

    with patch("execution_engine.get_today_session", return_value={
            "id": "sess-1", "virtual_trades_count": 0,
         }), \
         patch("execution_engine.get_client",
               return_value=_FakeClient(events)), \
         patch("execution_engine.update_session"), \
         patch("execution_engine.write_audit_log"), \
         patch("execution_engine.write_health_status"), \
         patch("execution_engine._submit_oco_bracket") as mock_oco, \
         patch("config.TRADIER_SANDBOX", False), \
         patch("config.OCO_BRACKET_ENABLED", False):
        engine.open_virtual_position(
            _minimal_signal(), _minimal_prediction()
        )

    mock_oco.assert_not_called()


def test_oco_order_id_written_to_position():
    """Happy path: TRADIER_SANDBOX=False AND OCO_BRACKET_ENABLED=True
    → _submit_oco_bracket returns "live-oid-77" → open_virtual_position
    issues a Supabase UPDATE({oco_order_id: ...}).eq("id", inserted_id).
    Pins the exact column name so a rename regression fires loudly."""
    engine = _engine()
    events = []

    with patch("execution_engine.get_today_session", return_value={
            "id": "sess-1", "virtual_trades_count": 0,
         }), \
         patch("execution_engine.get_client",
               return_value=_FakeClient(events)), \
         patch("execution_engine.update_session"), \
         patch("execution_engine.write_audit_log"), \
         patch("execution_engine.write_health_status"), \
         patch(
             "execution_engine._submit_oco_bracket",
             return_value="live-oid-77",
         ) as mock_oco, \
         patch("config.TRADIER_SANDBOX", False), \
         patch("config.OCO_BRACKET_ENABLED", True):
        engine.open_virtual_position(
            _minimal_signal(), _minimal_prediction()
        )

    mock_oco.assert_called_once()
    updates = [
        e for e in events
        if e[0] == "update" and "oco_order_id" in e[1]
    ]
    assert len(updates) == 1
    _, payload, col, val = updates[0]
    assert payload == {"oco_order_id": "live-oid-77"}
    assert col == "id"
    assert val == "pos-uuid-0001"


def test_oco_failure_does_not_fail_position_open():
    """When _submit_oco_bracket raises (simulating a torn outer
    try/except), open_virtual_position must still return the created
    position row. ROI invariant: OCO is observability, never a gate."""
    engine = _engine()
    events = []

    def _boom(*_a, **_kw):
        raise RuntimeError("unexpected OCO crash")

    with patch("execution_engine.get_today_session", return_value={
            "id": "sess-1", "virtual_trades_count": 0,
         }), \
         patch("execution_engine.get_client",
               return_value=_FakeClient(events)), \
         patch("execution_engine.update_session"), \
         patch("execution_engine.write_audit_log"), \
         patch("execution_engine.write_health_status"), \
         patch(
             "execution_engine._submit_oco_bracket",
             side_effect=_boom,
         ), \
         patch("config.TRADIER_SANDBOX", False), \
         patch("config.OCO_BRACKET_ENABLED", True):
        result = engine.open_virtual_position(
            _minimal_signal(), _minimal_prediction()
        )

    assert result is not None
    assert result.get("id") == "pos-uuid-0001"
