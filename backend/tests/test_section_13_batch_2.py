"""
Section 13 Batch 2 — cleanup + observability regression tests.

Four guards, one per shipped change:

  1. test_sharpe_returns_none_on_negative_mean
     — _annualised_sharpe must return None (not 0.0) when the cohort
       mean P&L is non-positive. Distinguishes "negative mean, gate
       impossible" from a legitimately-computed Sharpe of 0.0.

  2. test_sizing_phase_not_advanced_on_none_sharpe
     — end-to-end: 50 sessions of all-negative P&L → E1 gate must
       NOT advance, reason must flag negative mean explicitly.

  3. test_safe_float_rename_no_shadow
     — static check: prediction_engine.py must expose
       _read_float_key and must NOT define _safe_float twice in the
       same module scope (the module-level def at top + an inline
       def inside run_cycle would both carry the literal name).

  4. test_drawdown_block_in_reasons_list
     — regression guard for the butterfly_gate_daily_stats reasons
       list in main.py. "drawdown_block" must remain present so the
       writer (when it ships) surfaces in EOD stats without a
       schema change.
"""
import ast
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..")
)


# ─────────────────────────────────────────────────────────────────────
# 1) _annualised_sharpe returns None on non-positive mean
# ─────────────────────────────────────────────────────────────────────


def test_sharpe_returns_none_on_negative_mean():
    """All-negative P&L stream (n=50) → mean < 0 → helper must return
    None. Pre-Batch-2 it returned 0.0, which was ambiguous with a
    legitimate 0-Sharpe cohort and masked the reason a phase did not
    advance in the structured-log payload."""
    from calibration_engine import _annualised_sharpe

    pnls = [-500.0] * 50
    result = _annualised_sharpe(pnls)

    assert result is None, (
        f"expected None for negative-mean cohort, got {result!r}"
    )


def test_sharpe_returns_none_on_zero_mean():
    """Boundary: mean exactly 0.0 is also non-positive — the gate can
    never pass from a flat-performance cohort, and None is the
    correct observability signal."""
    from calibration_engine import _annualised_sharpe

    pnls = [100.0, -100.0] * 25  # mean = 0 exactly
    result = _annualised_sharpe(pnls)

    assert result is None


def test_sharpe_positive_mean_still_returns_float():
    """Regression guard — Batch 2 changes must NOT break the happy
    path. A positive-mean, moderately-volatile cohort must still
    return a float Sharpe (not None) so E1/E2 can advance."""
    from calibration_engine import _annualised_sharpe

    pnls = [1100.0 if i % 2 == 0 else -900.0 for i in range(50)]
    result = _annualised_sharpe(pnls)

    assert isinstance(result, float)
    assert result > 1.0


# ─────────────────────────────────────────────────────────────────────
# 2) evaluate_sizing_phase with None Sharpe → no advance
# ─────────────────────────────────────────────────────────────────────


class _FluentTable:
    def __init__(self, rows=None):
        self._rows = rows or []

    def select(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    @property
    def not_(self):
        return self

    def is_(self, *a, **k):
        return self

    def order(self, *a, **k):
        return self

    def update(self, *a, **k):
        return self

    def gte(self, *a, **k):
        return self

    def execute(self):
        result = MagicMock()
        result.data = self._rows
        return result


class _FluentClient:
    def __init__(self, rows=None):
        self._rows = rows or []

    def table(self, _name):
        return _FluentTable(rows=self._rows)


def test_sizing_phase_not_advanced_on_none_sharpe():
    """50 sessions of all-negative P&L satisfies the 45-day floor
    but produces None Sharpe. The function must:
      * NOT call redis.setex (no phase write)
      * return advanced=False
      * tag the payload with the new E1_negative_mean_pnl reason
        so an operator grepping structured logs can distinguish
        "we computed a bad Sharpe" from "mean is negative, gate
        can't pass". Before Batch 2 both collapsed to
        E1_sharpe_below_gate with sharpe=0.0."""
    from calibration_engine import evaluate_sizing_phase

    redis_mock = MagicMock()
    redis_mock.get.return_value = None  # phase 1
    rows = [
        {"session_date": f"2026-01-{(i % 28) + 1:02d}", "virtual_pnl": -500.0}
        for i in range(50)
    ]
    client = _FluentClient(rows=rows)

    with patch(
        "calibration_engine.get_client", return_value=client
    ):
        result = evaluate_sizing_phase(redis_mock)

    assert result["phase"] == 1
    assert result["advanced"] is False
    assert result["sharpe"] is None
    assert result["reason"] == "E1_negative_mean_pnl"
    # Primary phase key must NOT be written — preserves the conservative
    # contract across pathological cohorts.
    for call in redis_mock.setex.call_args_list:
        args = call.args
        assert args[0] != "capital:sizing_phase", (
            f"unexpected phase write: {call}"
        )


def test_sizing_phase_sync_writes_audit_key_and_supabase():
    """E1 gate passes → _sync_sizing_phase runs. Must:
      * write capital:sizing_phase_advanced_at to Redis with the new
        phase and a timestamp (fail-open durable audit record)
      * call .update({"sizing_phase": 2}) on trading_operator_config
        via the service-role client (single-tenant — bulk update is
        the user_id-agnostic path).
    Both writes are fail-open so a failure on either does NOT prevent
    the primary capital:sizing_phase write."""
    from calibration_engine import (
        evaluate_sizing_phase,
        SIZING_PHASE_AUDIT_REDIS_KEY,
    )

    redis_mock = MagicMock()
    redis_mock.get.return_value = None
    rows = [
        {"session_date": f"2026-01-{(i % 28) + 1:02d}",
         "virtual_pnl": (1100.0 if i % 2 == 0 else -900.0)}
        for i in range(50)
    ]

    # Track .update() calls so we can verify the Supabase side of
    # the sync. The mock has to remain chainable — return self so
    # the subsequent .gte(...).execute() still works.
    update_calls: list = []

    class _RecordingTable(_FluentTable):
        def update(self, payload, *a, **k):
            update_calls.append(payload)
            return self

    class _RecordingClient(_FluentClient):
        def table(self, _name):
            return _RecordingTable(rows=self._rows)

    client = _RecordingClient(rows=rows)

    with patch(
        "calibration_engine.get_client", return_value=client
    ):
        result = evaluate_sizing_phase(redis_mock)

    assert result["advanced"] is True
    assert result["phase"] == 2

    # Audit key written with "<phase>|<iso_timestamp>" payload.
    audit_writes = [
        c for c in redis_mock.setex.call_args_list
        if c.args[0] == SIZING_PHASE_AUDIT_REDIS_KEY
    ]
    assert len(audit_writes) == 1, audit_writes
    audit_payload = audit_writes[0].args[2]
    assert audit_payload.startswith("2|"), audit_payload
    # ISO-8601 suffix sanity check — must be parseable back.
    from datetime import datetime as _dt
    _dt.fromisoformat(audit_payload.split("|", 1)[1])

    # Supabase side: at least one .update() carrying sizing_phase=2.
    assert any(
        p.get("sizing_phase") == 2 for p in update_calls
    ), update_calls


# ─────────────────────────────────────────────────────────────────────
# 3) static check: _safe_float no longer shadowed
# ─────────────────────────────────────────────────────────────────────


def test_safe_float_rename_no_shadow():
    """Parse prediction_engine.py with ast. The file must now
    contain:
      * exactly ONE function named `_safe_float` (the module-level
        helper at the top of the file)
      * at least ONE function named `_read_float_key` (the inline
        helper inside run_cycle that used to be a second `_safe_float`
        and shadowed the module-level one).
    Before Batch 2 the file carried two separate `def _safe_float`
    statements with different signatures — a fragile arrangement
    that would silently break any future refactor that moved the
    inline callers out of scope."""
    here = os.path.dirname(__file__)
    target = os.path.abspath(
        os.path.join(here, "..", "prediction_engine.py")
    )
    with open(target, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())

    safe_float_defs = 0
    read_float_key_defs = 0
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == "_safe_float":
                safe_float_defs += 1
            elif node.name == "_read_float_key":
                read_float_key_defs += 1

    assert safe_float_defs == 1, (
        f"expected exactly one def _safe_float, found {safe_float_defs}"
    )
    assert read_float_key_defs >= 1, (
        "expected at least one def _read_float_key after rename, "
        f"found {read_float_key_defs}"
    )


# ─────────────────────────────────────────────────────────────────────
# 4) drawdown_block stays in butterfly_gate_daily_stats reasons list
# ─────────────────────────────────────────────────────────────────────


def test_drawdown_block_in_reasons_list():
    """Parse main.py with ast. The reasons list passed to the
    butterfly_gate_daily_stats block MUST still contain
    "drawdown_block" — Batch 2 added a TODO comment but MUST NOT
    remove the entry itself. Removing it would silently drop the
    column from EOD stats once the writer in execution_engine
    ships, forcing a schema-compatible log re-migration."""
    here = os.path.dirname(__file__)
    target = os.path.abspath(
        os.path.join(here, "..", "main.py")
    )
    with open(target, encoding="utf-8") as fh:
        source = fh.read()

    tree = ast.parse(source)

    found_block = False
    for node in ast.walk(tree):
        if not isinstance(node, ast.List):
            continue
        elts = [
            e.value for e in node.elts
            if isinstance(e, ast.Constant) and isinstance(e.value, str)
        ]
        # The reasons list we care about co-locates several known
        # gate names. Match on that cluster to avoid false positives
        # from unrelated string lists.
        if {"failed_today", "time_gate", "low_concentration"}.issubset(set(elts)):
            found_block = True
            assert "drawdown_block" in elts, (
                f"drawdown_block removed from reasons list: {elts}"
            )
            assert "wall_unstable" in elts, (
                f"wall_unstable also regressed, reasons={elts}"
            )

    assert found_block, (
        "could not locate butterfly_gate_daily_stats reasons list in main.py"
    )
