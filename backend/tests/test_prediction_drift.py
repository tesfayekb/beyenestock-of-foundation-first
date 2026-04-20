"""
12L (D1) — daily outcome loop drift alert tests.

Covers the pure-observability drift check that runs after
label_prediction_outcomes in run_eod_criteria_evaluation:
  * fires a Redis `model_drift_alert` key when 10d accuracy drops
    >5pp below 30d baseline,
  * clears the same key on recovery,
  * gracefully skips when either window has <10 labeled rows,
  * fails open (returns an error payload) on any Supabase exception,
  * holds no import of any trade-decision module (ROI rule 1).
"""
import ast
import inspect
import os
import sys
import textwrap
from unittest.mock import MagicMock, patch

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..")
)


# ── Supabase fluent mock ─────────────────────────────────────────────


class _FluentChain:
    """
    Chainable query-builder stand-in. Each call to .execute() pops
    the next row list off the queue so a single test can drive the
    two .table('trading_prediction_outputs') queries that
    check_prediction_drift performs (10d window, then 30d window).
    """

    def __init__(self, row_queue: list):
        self._queue = row_queue

    def select(self, *args, **kwargs):
        return self

    def eq(self, *args):
        return self

    @property
    def not_(self):
        return self

    def is_(self, *args):
        return self

    def gte(self, *args):
        return self

    def execute(self):
        rows = self._queue.pop(0) if self._queue else []
        result = MagicMock()
        result.data = rows
        return result


class _FluentClient:
    def __init__(self, row_queue: list):
        self._queue = row_queue

    def table(self, _name):
        return _FluentChain(self._queue)


def _rows(total: int, correct: int) -> list:
    """Build a list of `total` outcome rows, `correct` of them with
    outcome_correct=True. Content beyond outcome_correct is ignored
    by the drift check — keeping them minimal keeps the tests
    resilient to schema additions."""
    return [
        {"outcome_correct": i < correct}
        for i in range(total)
    ]


# ── happy paths ──────────────────────────────────────────────────────


def test_drift_alert_fires_when_accuracy_drops():
    """10d=48% (100 rows) vs 30d=55% (300 rows) → drop=0.07 > 0.05.
    The alert must be written to Redis with the 86400s TTL and the
    literal value "1" so dashboards polling the key see a truthy
    payload regardless of Redis's decode_responses setting. The
    returned dict must expose enough context for main.py to build
    the operator-facing email detail string."""
    from model_retraining import check_prediction_drift

    client = _FluentClient(row_queue=[
        _rows(total=100, correct=48),   # 10d → 0.48
        _rows(total=300, correct=165),  # 30d → 0.55
    ])
    redis_mock = MagicMock()

    with patch("model_retraining.get_client", return_value=client):
        result = check_prediction_drift(redis_mock)

    assert result["alert"] is True
    assert result["acc_10d"] == 0.48
    assert result["acc_30d"] == 0.55
    assert result["drop"] == 0.07

    redis_mock.setex.assert_called_once_with(
        "model_drift_alert", 86400, "1"
    )
    redis_mock.delete.assert_not_called()


def test_drift_alert_clears_when_accuracy_healthy():
    """10d=58% vs 30d=60% → drop=0.02 < 0.05 threshold. The
    function must call redis.delete to clear any stale alert from
    a prior degraded period — without this, a one-off bad day
    would leave the dashboard red forever."""
    from model_retraining import check_prediction_drift

    client = _FluentClient(row_queue=[
        _rows(total=100, correct=58),   # 10d → 0.58
        _rows(total=300, correct=180),  # 30d → 0.60
    ])
    redis_mock = MagicMock()

    with patch("model_retraining.get_client", return_value=client):
        result = check_prediction_drift(redis_mock)

    assert result["alert"] is False
    assert result["acc_10d"] == 0.58
    assert result["acc_30d"] == 0.60
    assert result["drop"] == 0.02

    redis_mock.setex.assert_not_called()
    redis_mock.delete.assert_called_once_with("model_drift_alert")


# ── gate paths ───────────────────────────────────────────────────────


def test_drift_check_skips_when_insufficient_10d_data():
    """Fewer than 10 labeled rows in the 10-day window → checked=False
    with reason=insufficient_data. The function must NOT touch Redis
    in this branch — a warmup window should neither fire an alert
    nor clear a pre-existing one, since we have no signal either way."""
    from model_retraining import check_prediction_drift

    client = _FluentClient(row_queue=[
        _rows(total=5, correct=3),      # 10d → below gate
        _rows(total=100, correct=55),   # 30d plenty
    ])
    redis_mock = MagicMock()

    with patch("model_retraining.get_client", return_value=client):
        result = check_prediction_drift(redis_mock)

    assert result["checked"] is False
    assert result["reason"] == "insufficient_data"
    assert result["count_10d"] == 5
    assert result["count_30d"] == 100

    redis_mock.setex.assert_not_called()
    redis_mock.delete.assert_not_called()


def test_drift_check_skips_when_insufficient_30d_data():
    """Conceptually the 30d window is a superset of the 10d window
    so in production count_30d >= count_10d — but the gate is still
    expressed as an independent `acc_30d is None` check in the
    function, so a defensive test pins it. Mock returns fewer 30d
    rows than 10d rows to confirm the gate fires on either leg."""
    from model_retraining import check_prediction_drift

    client = _FluentClient(row_queue=[
        _rows(total=15, correct=8),    # 10d passes gate
        _rows(total=8, correct=4),     # 30d below gate
    ])
    redis_mock = MagicMock()

    with patch("model_retraining.get_client", return_value=client):
        result = check_prediction_drift(redis_mock)

    assert result["checked"] is False
    assert result["reason"] == "insufficient_data"
    assert result["count_30d"] == 8

    redis_mock.setex.assert_not_called()
    redis_mock.delete.assert_not_called()


# ── fail-open ────────────────────────────────────────────────────────


def test_drift_check_fail_open():
    """Supabase raises on .table() → outer try/except swallows and
    returns an error payload. Never propagates — the EOD criteria
    evaluation step must run regardless, and the weekly model
    performance job depends on criteria evaluation firing daily."""
    from model_retraining import check_prediction_drift

    raising_client = MagicMock()
    raising_client.table.side_effect = RuntimeError("supabase down")
    redis_mock = MagicMock()

    with patch(
        "model_retraining.get_client", return_value=raising_client
    ):
        result = check_prediction_drift(redis_mock)

    assert result["checked"] is False
    assert "error" in result
    assert "supabase down" in result["error"]

    redis_mock.setex.assert_not_called()
    redis_mock.delete.assert_not_called()


# ── ROI invariant ────────────────────────────────────────────────────


def test_drift_check_does_not_affect_trades():
    """Rule 1 guard: check_prediction_drift must be pure observability.
    An AST-level scan of the function body must contain ZERO Import /
    ImportFrom / Attribute / Name nodes referencing any trade-decision
    module — a regression that imports one of these in a future edit
    (e.g. 'also gate contracts on recent drift') would silently
    violate the ROI invariant in a way only a structural test catches.
    Docstring mentions of the module names are excluded by walking the
    AST rather than grep'ing the source text."""
    from model_retraining import check_prediction_drift

    forbidden = {
        "execution_engine",
        "strategy_selector",
        "risk_engine",
        "trading_cycle",
    }
    src = textwrap.dedent(inspect.getsource(check_prediction_drift))
    tree = ast.parse(src)

    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in forbidden:
                    violations.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.split(".")[0] in forbidden:
                violations.append(node.module)
        elif isinstance(node, ast.Name):
            if node.id in forbidden:
                violations.append(node.id)
        elif isinstance(node, ast.Attribute):
            if (
                isinstance(node.value, ast.Name)
                and node.value.id in forbidden
            ):
                violations.append(f"{node.value.id}.{node.attr}")

    assert not violations, (
        "check_prediction_drift must not reference any trade-decision "
        "module (ROI invariant — drift is pure observability). "
        f"Found references: {violations}"
    )
