"""D4 (12E) — tests for the counterfactual engine.

Three test groups:

1. `_simulate_pnl` — pure math. Verifies the short-gamma / long-gamma
   branches and the generic fallback produce positive P&L on the
   favourable move and negative on the unfavourable one.

2. `label_counterfactual_outcomes` — EOD labeler. Verifies skip-paths
   (entry_spx<=0, exit_spx unavailable) and the write payload shape
   when a row IS labeled.

3. `generate_weekly_summary` + `run_counterfactual_job` — top-level
   entry points. Verifies the 30-session warmup gate and fail-open
   behaviour on Supabase outage.

The engine's Polygon fetch and Supabase client are both imported
lazily inside the functions, so we patch them at the source module
(`counterfactual_engine._fetch_spx_price_after_signal`, `db.get_client`).
"""
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── 1. _simulate_pnl: pure math ──────────────────────────────────────

def test_simulate_pnl_condor_win():
    """SPX moved only 1pt: inside spread_width/2 = 2.5pt → iron_condor
    collects ~40% of credit. Must be strictly positive."""
    from counterfactual_engine import _simulate_pnl

    pnl = _simulate_pnl(
        entry_spx=5000.0,
        exit_spx=5001.0,
        strategy_type="iron_condor",
        confidence=0.6,
    )
    assert pnl > 0, f"small move on iron_condor must be positive; got {pnl}"


def test_simulate_pnl_condor_loss():
    """SPX moved 10pt: well outside the 5pt spread width → iron_condor
    takes the ~150% stop-loss. Must be strictly negative."""
    from counterfactual_engine import _simulate_pnl

    pnl = _simulate_pnl(
        entry_spx=5000.0,
        exit_spx=5010.0,
        strategy_type="iron_condor",
        confidence=0.6,
    )
    assert pnl < 0, f"big move on iron_condor must be negative; got {pnl}"


def test_simulate_pnl_straddle_win():
    """Inverted branch: long_straddle needs the big move to pay.
    10pt move is >= spread width → straddle wins."""
    from counterfactual_engine import _simulate_pnl

    pnl = _simulate_pnl(
        entry_spx=5000.0,
        exit_spx=5010.0,
        strategy_type="long_straddle",
        confidence=0.6,
    )
    assert pnl > 0, f"big move on long_straddle must be positive; got {pnl}"


# ── 2. label_counterfactual_outcomes ─────────────────────────────────

class _StubResult:
    def __init__(self, data=None, count=None):
        self.data = data
        self.count = count


class _ChainStub:
    """Minimal method-chain stub that mimics supabase-py's builder.

    Captures the select/eq/... chain, the row id targeted by update()
    and the payload written by execute(). Each .table() call returns
    a fresh stub so upsert/update interactions don't bleed across
    test invocations.
    """

    def __init__(self, select_data=None, count=None):
        self._data = select_data
        self._count = count
        self.updates = []  # list of (row_id, payload) tuples
        self._pending_update = None

    # Read-path methods — return self so the chain can continue.
    def table(self, *_a, **_kw):
        return self

    def select(self, *_a, **_kw):
        return self

    def eq(self, col, val):
        # Capture the id filter on update() to assert downstream.
        if self._pending_update is not None:
            self._pending_update["row_id"] = val
        return self

    def gte(self, *_a, **_kw):
        return self

    def is_(self, *_a, **_kw):
        return self

    @property
    def not_(self):
        return self

    # Write-path methods.
    def update(self, payload):
        self._pending_update = {"payload": payload, "row_id": None}
        return self

    def execute(self):
        if self._pending_update is not None:
            self.updates.append(
                (
                    self._pending_update["row_id"],
                    self._pending_update["payload"],
                )
            )
            self._pending_update = None
            return _StubResult(data=[], count=None)
        return _StubResult(data=self._data, count=self._count)


def test_label_counterfactual_skips_when_no_spx_price():
    """entry_spx=0 (or missing) → row is skipped; no update written.
    Prevents propagating noise from a prediction where SPX snapshot
    failed."""
    from counterfactual_engine import label_counterfactual_outcomes

    fixture = [
        {
            "id": "row-1",
            "predicted_at": "2026-04-20T18:00:00+00:00",
            "spx_price": 0,          # ← disqualifying
            "no_trade_reason": "vix_spike",
            "regime": "volatile_bullish",
            "confidence": 0.4,
        }
    ]
    stub = _ChainStub(select_data=fixture)

    with patch("db.get_client", return_value=stub):
        result = label_counterfactual_outcomes()

    assert result == {"labeled": 0, "skipped": 1}
    assert stub.updates == []


def test_label_counterfactual_skips_when_exit_price_unavailable():
    """Polygon returning None → row is skipped. The next day's run
    will pick it up if Polygon is back; if not, it stays skipped —
    fail-open by design, no partial or fabricated P&L written."""
    from counterfactual_engine import label_counterfactual_outcomes

    fixture = [
        {
            "id": "row-2",
            "predicted_at": "2026-04-20T18:00:00+00:00",
            "spx_price": 5000.0,
            "no_trade_reason": "low_confidence",
            "regime": "pin_range",
            "confidence": 0.5,
        }
    ]
    stub = _ChainStub(select_data=fixture)

    with patch("db.get_client", return_value=stub), patch(
        "counterfactual_engine._fetch_spx_price_after_signal",
        return_value=None,
    ):
        result = label_counterfactual_outcomes()

    assert result == {"labeled": 0, "skipped": 1}
    assert stub.updates == []


def test_label_counterfactual_writes_correct_columns():
    """Happy path: entry + exit prices available → update() is called
    with counterfactual_pnl (numeric), counterfactual_strategy
    ('iron_condor' per the documented fallback), and a valid
    counterfactual_simulated_at ISO timestamp."""
    from counterfactual_engine import label_counterfactual_outcomes

    fixture = [
        {
            "id": "row-3",
            "predicted_at": "2026-04-20T18:00:00+00:00",
            "spx_price": 5000.0,
            "no_trade_reason": "gex_thin",
            "regime": "volatile_bearish",
            "confidence": 0.55,
        }
    ]
    stub = _ChainStub(select_data=fixture)

    # Exit 1pt above entry → win on iron_condor (default strategy).
    with patch("db.get_client", return_value=stub), patch(
        "counterfactual_engine._fetch_spx_price_after_signal",
        return_value=5001.0,
    ):
        result = label_counterfactual_outcomes()

    assert result == {"labeled": 1, "skipped": 0}
    assert len(stub.updates) == 1
    row_id, payload = stub.updates[0]
    assert row_id == "row-3"
    # All three new columns present and well-typed.
    assert "counterfactual_pnl" in payload
    assert isinstance(payload["counterfactual_pnl"], float)
    assert payload["counterfactual_strategy"] == "iron_condor"
    assert "counterfactual_simulated_at" in payload
    # ISO-8601 with UTC offset (either +00:00 or 'Z'-equivalent).
    assert payload["counterfactual_simulated_at"].endswith("+00:00")
    # Win condition confirmed: P&L strictly positive.
    assert payload["counterfactual_pnl"] > 0


# ── 3. generate_weekly_summary + run_counterfactual_job ──────────────

def test_weekly_summary_skips_when_insufficient_sessions(caplog):
    """< 30 closed sessions → function returns None and logs a
    structured skip event. No Supabase row fetch should happen."""
    import logging
    from counterfactual_engine import generate_weekly_summary

    stub = _ChainStub(count=15)

    caplog.set_level(logging.INFO)
    with patch("db.get_client", return_value=stub):
        result = generate_weekly_summary()

    assert result is None


def test_weekly_summary_runs_when_sufficient_sessions():
    """>= 30 closed sessions → function aggregates the week's rows
    into top-3 by total_missed_pnl. Verifies the ordering is
    DESC so the highest-leverage reason is at index 0."""
    from counterfactual_engine import generate_weekly_summary

    week_rows = [
        # vix_spike dominates at total +300
        {"no_trade_reason": "vix_spike", "counterfactual_pnl": 200},
        {"no_trade_reason": "vix_spike", "counterfactual_pnl": 100},
        # gex_thin: total +50
        {"no_trade_reason": "gex_thin", "counterfactual_pnl": 50},
        # low_confidence: total -80
        {"no_trade_reason": "low_confidence", "counterfactual_pnl": -80},
    ]

    class _TwoCallStub:
        """First .execute() returns the sessions count; second returns
        the week's prediction rows. Mimics supabase-py's stateful
        chaining without carrying global state across tests."""

        def __init__(self):
            self.call = 0
            self.updates = []

        def table(self, name):
            self._last_table = name
            return self

        def select(self, *_a, **kw):
            self._exact_count = kw.get("count") == "exact"
            return self

        def eq(self, *_a, **_kw):
            return self

        def gte(self, *_a, **_kw):
            return self

        def is_(self, *_a, **_kw):
            return self

        @property
        def not_(self):
            return self

        def execute(self):
            if self._last_table == "trading_sessions":
                return _StubResult(count=35)
            return _StubResult(data=week_rows)

    with patch("db.get_client", return_value=_TwoCallStub()):
        summary = generate_weekly_summary()

    assert summary is not None
    assert summary["total_no_trade_rows"] == 4
    top = summary["top_opportunities"]
    assert len(top) == 3
    # Highest total_missed_pnl sorts to index 0.
    assert top[0]["reason"] == "vix_spike"
    assert top[0]["total_missed_pnl"] == 300.0
    assert top[0]["count"] == 2
    assert top[0]["avg_missed_pnl"] == 150.0
    # Ordering: vix_spike (+300) > gex_thin (+50) > low_confidence (-80)
    assert [o["reason"] for o in top] == [
        "vix_spike", "gex_thin", "low_confidence"
    ]


def test_run_counterfactual_job_fail_open():
    """Supabase raising on the initial SELECT → job returns a dict
    with `error` populated and does NOT re-raise. The scheduler
    wrapper in main.py must stay green."""
    from counterfactual_engine import run_counterfactual_job

    class _ExplodingClient:
        def table(self, *_a, **_kw):
            raise ConnectionError("simulated Supabase outage")

    with patch("db.get_client", return_value=_ExplodingClient()):
        result = run_counterfactual_job()

    assert isinstance(result, dict)
    assert "error" in result
    assert result["labeled"] == 0
    assert result["skipped"] == 0


# ── 4. health-status writes (FIX 2 / admin Engine Health page) ────────

def test_run_counterfactual_job_writes_idle_health_on_success():
    """Happy path: the EOD job must upsert `counterfactual_engine`
    with status='idle' so the admin Engine Health panel sees it as
    a healthy batch job (not as an offline heartbeat service).
    Per-run stats must land in the `details` JSONB column — the
    table has no `labeled`/`skipped` columns, so passing them as
    top-level kwargs would silently fail the upsert."""
    from counterfactual_engine import run_counterfactual_job

    mock_health = MagicMock(return_value=True)
    stub_result = {"labeled": 7, "skipped": 2}

    with patch(
        "counterfactual_engine.label_counterfactual_outcomes",
        return_value=stub_result,
    ), patch("db.write_health_status", mock_health):
        result = run_counterfactual_job()

    assert result == stub_result
    mock_health.assert_called_once()
    args, kwargs = mock_health.call_args
    assert args[0] == "counterfactual_engine"
    assert args[1] == "idle"
    assert kwargs.get("details") == {"labeled": 7, "skipped": 2}


def test_run_counterfactual_job_writes_error_health_on_exception():
    """Failure path: if label_counterfactual_outcomes itself raises
    (not just returns an error dict), the wrapper must catch it,
    record status='error' with the message, and return a safe
    zero-valued result — never re-raise into the scheduler."""
    from counterfactual_engine import run_counterfactual_job

    mock_health = MagicMock(return_value=True)

    def _boom(*_a, **_kw):
        raise RuntimeError("unexpected labeler crash")

    with patch(
        "counterfactual_engine.label_counterfactual_outcomes", _boom
    ), patch("db.write_health_status", mock_health):
        result = run_counterfactual_job()

    assert result["labeled"] == 0
    assert result["skipped"] == 0
    assert "unexpected labeler crash" in result["error"]
    mock_health.assert_called_once()
    args, kwargs = mock_health.call_args
    assert args[0] == "counterfactual_engine"
    assert args[1] == "error"
    assert "unexpected labeler crash" in kwargs.get(
        "last_error_message", ""
    )
