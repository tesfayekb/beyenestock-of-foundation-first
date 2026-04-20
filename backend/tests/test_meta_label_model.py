"""
12K — Loop 2 meta-label model scaffold tests.

Two surfaces:
  * model_retraining.train_meta_label_model — training side.
      Gates on closed_trades >= 100 AND labeled_rows >= 100, walks
      forward-only via .order("predicted_at"), never raises.
  * execution_engine.open_virtual_position — inference side.
      pkl-gated: absence of the model file is pure pass-through.
      Score < 0.55 skips, >= 0.75 boosts contracts up to a hard 2×
      cap, all else is a no-op. Fail-open on any inference error.

Tests mirror the mock patterns from test_earnings_learning.py and
test_oco_bracket.py so the fluent Supabase chain and the
ExecutionEngine.__new__ bypass stay consistent with the rest of the
backend test suite.
"""
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..")
)


# ── Fluent Supabase mocks ─────────────────────────────────────────────


class _FluentTable:
    """
    Chainable stand-in for a PostgREST query builder. Any filter
    method (eq, in_, not_, is_, order) returns self so the real
    .select(...).eq(...).eq(...).execute() chain used in
    train_meta_label_model resolves cleanly. execute() returns a
    payload shaped by the mode set during select() — count mode
    exposes .count, row mode exposes .data.
    """

    def __init__(self, count: int = 0, rows=None):
        self._count = count
        self._rows = rows or []
        self._mode = "rows"

    def select(self, *args, **kwargs):
        self._mode = "count" if kwargs.get("count") == "exact" else "rows"
        return self

    def eq(self, *args):
        return self

    def in_(self, *args):
        return self

    @property
    def not_(self):
        return self

    def is_(self, *args):
        return self

    def order(self, *args, **kwargs):
        return self

    def execute(self):
        result = MagicMock()
        if self._mode == "count":
            result.count = self._count
            result.data = None
        else:
            result.data = self._rows
            result.count = None
        return result


class _FluentClient:
    def __init__(
        self,
        count_by_table: dict = None,
        rows_by_table: dict = None,
        raise_on_tables: set = None,
    ):
        self._count_by_table = count_by_table or {}
        self._rows_by_table = rows_by_table or {}
        self._raise_on_tables = raise_on_tables or set()

    def table(self, name):
        if name in self._raise_on_tables:
            raise RuntimeError(f"forced supabase error on {name}")
        return _FluentTable(
            count=self._count_by_table.get(name, 0),
            rows=self._rows_by_table.get(name, []),
        )


def _labeled_rows(n: int) -> list:
    """Synthesize n valid labeled prediction rows for training-mode
    tests. Feature values are chosen inside plausible ranges so
    lightgbm can actually fit on them (half positive labels)."""
    rows = []
    for i in range(n):
        rows.append({
            "predicted_at": f"2026-04-0{(i % 9) + 1}T14:30:00+00:00",
            "outcome_correct": bool(i % 2),
            "confidence": 0.55 + (i % 10) * 0.01,
            "vvix_z_score": (i % 7) * 0.3 - 1.0,
            "gex_confidence": 0.40 + (i % 5) * 0.05,
            "cv_stress_score": 20.0 + (i % 8) * 3.0,
            "vix": 17.5 + (i % 6) * 0.4,
            "signal_weak": bool(i % 3 == 0),
            "prior_session_return": (i % 11) * 0.0005 - 0.002,
            "vix_term_ratio": 0.95 + (i % 4) * 0.02,
            "spx_momentum_4h": (i % 9) * 0.0008 - 0.0025,
            "gex_flip_proximity": (i % 6) * 0.0015,
        })
    return rows


# ── train_meta_label_model — gate & fail-open tests ──────────────────


def test_meta_label_skips_below_100_trades():
    """50 closed trades < 100 → trained=False. The second query
    (labeled rows) must NOT be issued, since the count gate short-
    circuits before it. Verified implicitly: no sklearn / lightgbm
    import would fire either."""
    from model_retraining import (
        MIN_CLOSED_TRADES_FOR_META_LABEL,
        train_meta_label_model,
    )

    client = _FluentClient(count_by_table={"trading_positions": 50})

    with patch("model_retraining.get_client", return_value=client):
        result = train_meta_label_model(redis_client=None)

    assert result == {
        "trained": False,
        "closed_trades": 50,
        "required": MIN_CLOSED_TRADES_FOR_META_LABEL,
    }


def test_meta_label_skips_insufficient_labeled_rows():
    """100 closed trades passes gate 1, but only 60 labeled
    prediction rows returned → gate 2 fires with
    reason=insufficient_labeled_rows. Separate reason strings let
    ops dashboards distinguish 'not enough trades' (grow the book)
    from 'not enough labels' (check Polygon SPX coverage)."""
    from model_retraining import (
        MIN_LABELED_ROWS_FOR_META_LABEL,
        train_meta_label_model,
    )

    client = _FluentClient(
        count_by_table={"trading_positions": 100},
        rows_by_table={"trading_prediction_outputs": _labeled_rows(60)},
    )

    with patch("model_retraining.get_client", return_value=client):
        result = train_meta_label_model(redis_client=None)

    assert result["trained"] is False
    assert result["labeled_rows"] == 60
    assert result["required"] == MIN_LABELED_ROWS_FOR_META_LABEL
    assert result["reason"] == "insufficient_labeled_rows"


def test_meta_label_skips_when_lightgbm_missing():
    """Both gates pass, but `import lightgbm` fails. The function
    must catch ImportError and return trained=False with a
    distinct reason so ops know to pip-install rather than
    chase a data-volume issue. sys.modules injection mirrors
    the pattern used elsewhere in this suite to simulate
    missing optional dependencies without uninstalling them."""
    from model_retraining import train_meta_label_model

    client = _FluentClient(
        count_by_table={"trading_positions": 150},
        rows_by_table={
            "trading_prediction_outputs": _labeled_rows(120),
        },
    )

    with patch.dict(sys.modules, {"lightgbm": None}), \
         patch("model_retraining.get_client", return_value=client):
        result = train_meta_label_model(redis_client=None)

    assert result == {
        "trained": False,
        "reason": "lightgbm_not_installed",
    }


def test_meta_label_fail_open_on_supabase_error():
    """Supabase raises on the very first .table() call → the
    outer try/except swallows and returns trained=False with an
    error payload. Never propagates — the weekly calibration
    chain must survive a transient Supabase blip."""
    from model_retraining import train_meta_label_model

    raising_client = MagicMock()
    raising_client.table.side_effect = RuntimeError("supabase down")

    with patch(
        "model_retraining.get_client", return_value=raising_client
    ):
        result = train_meta_label_model(redis_client=None)

    assert result["trained"] is False
    assert "error" in result
    assert "supabase down" in result["error"]


# ── open_virtual_position — inference-side meta-label tests ──────────


class _FakeExecTable:
    """
    Minimal Supabase stand-in for open_virtual_position. All pre-
    insert fluent chains fail-open inside the engine, so missing
    methods here simply exercise the same resilient path. insert()
    captures the row and materializes an id so the caller's
    downstream update path works unchanged.
    """

    def __init__(self, events: list):
        self._events = events
        self._pending_insert = None
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
        if self._pending_insert is not None:
            row = self._pending_insert
            row.setdefault("id", "pos-uuid-meta")
            self._events.append(("insert", dict(row)))
            self._pending_insert = None
            return MagicMock(data=[row])
        return MagicMock(data=[])


class _FakeExecClient:
    def __init__(self, events: list):
        self._events = events

    def table(self, _name):
        return _FakeExecTable(self._events)


def _exec_signal(contracts: int = 2) -> dict:
    return {
        "session_id": "sess-meta",
        "instrument": "SPX",
        "contracts": contracts,
        "strategy_type": "iron_butterfly",
        "target_credit": 1.50,
        "regime_at_signal": "pin_range",
        "rcs_at_signal": 72.0,
        "cv_stress_at_signal": 25.0,
        "expiry_date": "2026-04-21",
        "short_strike": 5200,
        "long_strike": 5210,
        "position_type": "core",
        "decision_context": {},
    }


def _exec_prediction() -> dict:
    """Populated so the meta-label feature builder sees real
    floats for every input. Values chosen so _safe defaults in
    the inference block are NOT the deciding factor — the test's
    mocked predict_proba is."""
    return {
        "id": "pred-meta",
        "spx_price": 5200.0,
        "cv_stress_score": 25.0,
        "confidence": 0.70,
        "vvix_z_score": -0.4,
        "gex_confidence": 0.55,
        "vix": 17.8,
        "signal_weak": False,
        "prior_session_return": 0.0012,
        "vix_term_ratio": 0.98,
        "spx_momentum_4h": 0.0018,
        "gex_flip_proximity": 0.0035,
    }


def _engine():
    """Bypass __init__ so we don't touch Redis. Same pattern as
    test_oco_bracket.py's _engine() helper."""
    from execution_engine import ExecutionEngine

    engine = ExecutionEngine.__new__(ExecutionEngine)
    engine.redis_client = None
    return engine


def _fake_model(score: float) -> MagicMock:
    """Build a pickle-loadable stand-in. The inference block reads
    [0][1] off the predict_proba 2D array, so shape must match."""
    import numpy as np
    m = MagicMock()
    m.predict_proba.return_value = np.array([[1.0 - score, score]])
    return m


def test_meta_label_model_absent_pass_through():
    """No pkl on disk → entire scoring block is skipped. Trade
    proceeds with its original contracts count and no meta-label
    log event is emitted. This is the steady-state production
    behaviour today (pkl does not exist until weekly calibration
    produces it), so a regression here would silently gate trades
    on an empty code path."""
    engine = _engine()
    events = []
    signal = _exec_signal(contracts=2)

    with patch("pathlib.Path.exists", return_value=False), \
         patch("execution_engine.get_today_session", return_value={
             "id": "sess-meta", "virtual_trades_count": 0,
         }), \
         patch(
             "execution_engine.get_client",
             return_value=_FakeExecClient(events),
         ), \
         patch("execution_engine.update_session"), \
         patch("execution_engine.write_audit_log"), \
         patch("execution_engine.write_health_status"), \
         patch("config.TRADIER_SANDBOX", True), \
         patch("config.OCO_BRACKET_ENABLED", False):
        result = engine.open_virtual_position(signal, _exec_prediction())

    assert result is not None
    inserts = [e for e in events if e[0] == "insert"]
    assert len(inserts) == 1
    assert inserts[0][1]["contracts"] == 2


def test_meta_label_low_score_skips_trade():
    """pkl exists, model returns score=0.45 (< 0.55 cutoff) →
    open_virtual_position returns None BEFORE any Supabase insert.
    Documents that the meta-label gate is a hard filter, not a
    size downgrade — the trade is skipped entirely."""
    engine = _engine()
    events = []

    with patch("pathlib.Path.exists", return_value=True), \
         patch("pickle.load", return_value=_fake_model(0.45)), \
         patch("builtins.open", MagicMock()), \
         patch("execution_engine.get_today_session", return_value={
             "id": "sess-meta", "virtual_trades_count": 0,
         }), \
         patch(
             "execution_engine.get_client",
             return_value=_FakeExecClient(events),
         ), \
         patch("execution_engine.update_session"), \
         patch("execution_engine.write_audit_log"), \
         patch("execution_engine.write_health_status"), \
         patch("config.TRADIER_SANDBOX", True), \
         patch("config.OCO_BRACKET_ENABLED", False):
        result = engine.open_virtual_position(
            _exec_signal(contracts=2), _exec_prediction()
        )

    assert result is None
    assert not [e for e in events if e[0] == "insert"]


def test_meta_label_normal_score_proceeds():
    """score=0.62 → middle band: normal sizing, no boost, no
    skip. Documents the three-way decision and guards against a
    regression where the 0.55 / 0.75 thresholds collapse."""
    engine = _engine()
    events = []

    with patch("pathlib.Path.exists", return_value=True), \
         patch("pickle.load", return_value=_fake_model(0.62)), \
         patch("builtins.open", MagicMock()), \
         patch("execution_engine.get_today_session", return_value={
             "id": "sess-meta", "virtual_trades_count": 0,
         }), \
         patch(
             "execution_engine.get_client",
             return_value=_FakeExecClient(events),
         ), \
         patch("execution_engine.update_session"), \
         patch("execution_engine.write_audit_log"), \
         patch("execution_engine.write_health_status"), \
         patch("config.TRADIER_SANDBOX", True), \
         patch("config.OCO_BRACKET_ENABLED", False):
        result = engine.open_virtual_position(
            _exec_signal(contracts=2), _exec_prediction()
        )

    assert result is not None
    inserts = [e for e in events if e[0] == "insert"]
    assert len(inserts) == 1
    assert inserts[0][1]["contracts"] == 2


def test_meta_label_high_score_boosts_sizing():
    """score=0.80 (>= 0.75 cutoff), contracts=2 → boosted to 3.
    Also pins the 2× hard cap: int(2*1.5)=3 which is within 2×2=4,
    so 3 is the expected boosted value. A regression that raised
    the boost factor would show up in the persisted row, which we
    inspect directly."""
    engine = _engine()
    events = []

    with patch("pathlib.Path.exists", return_value=True), \
         patch("pickle.load", return_value=_fake_model(0.80)), \
         patch("builtins.open", MagicMock()), \
         patch("execution_engine.get_today_session", return_value={
             "id": "sess-meta", "virtual_trades_count": 0,
         }), \
         patch(
             "execution_engine.get_client",
             return_value=_FakeExecClient(events),
         ), \
         patch("execution_engine.update_session"), \
         patch("execution_engine.write_audit_log"), \
         patch("execution_engine.write_health_status"), \
         patch("config.TRADIER_SANDBOX", True), \
         patch("config.OCO_BRACKET_ENABLED", False):
        result = engine.open_virtual_position(
            _exec_signal(contracts=2), _exec_prediction()
        )

    assert result is not None
    inserts = [e for e in events if e[0] == "insert"]
    assert len(inserts) == 1
    # 2 → int(2*1.5)=3, min(2*2=4, max(2,3))=3. 2× cap is documented,
    # not active at this size (it guards the ceiling if the 1.5×
    # multiplier is ever raised in a future revision).
    assert inserts[0][1]["contracts"] == 3


def test_meta_label_fail_open_on_model_error():
    """predict_proba raises at inference time → the inference
    block catches, logs, and lets the trade proceed with ORIGINAL
    contracts. Pins the fail-open invariant for rule 1 (no ROI
    regression from a transient model error)."""
    engine = _engine()
    events = []

    broken_model = MagicMock()
    broken_model.predict_proba.side_effect = RuntimeError(
        "model exploded"
    )

    with patch("pathlib.Path.exists", return_value=True), \
         patch("pickle.load", return_value=broken_model), \
         patch("builtins.open", MagicMock()), \
         patch("execution_engine.get_today_session", return_value={
             "id": "sess-meta", "virtual_trades_count": 0,
         }), \
         patch(
             "execution_engine.get_client",
             return_value=_FakeExecClient(events),
         ), \
         patch("execution_engine.update_session"), \
         patch("execution_engine.write_audit_log"), \
         patch("execution_engine.write_health_status"), \
         patch("config.TRADIER_SANDBOX", True), \
         patch("config.OCO_BRACKET_ENABLED", False):
        result = engine.open_virtual_position(
            _exec_signal(contracts=2), _exec_prediction()
        )

    assert result is not None
    inserts = [e for e in events if e[0] == "insert"]
    assert len(inserts) == 1
    assert inserts[0][1]["contracts"] == 2
