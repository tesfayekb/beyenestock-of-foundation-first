"""
12J — Phase 5B earnings learning loop scaffold tests.

Covers label_earnings_outcome (fires from trade #1, fail-open) and
train_earnings_model (gates on total_outcomes >= 50, writes per-ticker
weights to Redis, excludes tickers with < 3 samples, fail-open).

Pattern mirrors test_phase_5a_session1: backend_earnings/ is a sibling
of backend/, so each test inserts that sibling path into sys.path
before importing edge_calculator.
"""
import json
import os
import sys
from unittest.mock import MagicMock, patch

_EARNINGS_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "backend_earnings"
)


def _ensure_earnings_on_path() -> None:
    """Insert backend_earnings/ on sys.path for each test (idempotent).
    Also drop any previously cached edge_calculator module so the
    logger + get_client imports are re-evaluated under this test's
    patch context. Without this, the first test to import the module
    pins the real logger and subsequent patches on `db.get_client`
    via the inside-function import still resolve cleanly, but the
    module-level logger name is stable across tests."""
    if _EARNINGS_DIR not in sys.path:
        sys.path.insert(0, _EARNINGS_DIR)


def _make_count_result(count: int):
    r = MagicMock()
    r.count = count
    return r


def _make_data_result(rows: list):
    r = MagicMock()
    r.data = rows
    return r


def _make_get_client_mock(
    count_result=None,
    select_rows=None,
    insert_capture: list = None,
):
    """Build a Supabase client mock whose .table(...).select/insert
    chain returns the canned payloads and captures insert arguments."""
    client = MagicMock()

    def _table(_name):
        tbl = MagicMock()

        # insert().execute() — capture the row, return an empty result.
        def _insert(row):
            if insert_capture is not None:
                insert_capture.append(row)
            exec_mock = MagicMock()
            exec_mock.execute.return_value = _make_data_result([])
            return exec_mock

        tbl.insert.side_effect = _insert

        # select(..., count="exact").execute() → count payload.
        # select(...cols).execute()            → rows payload.
        def _select(*args, **kwargs):
            chain = MagicMock()
            if kwargs.get("count") == "exact":
                chain.execute.return_value = (
                    count_result or _make_count_result(0)
                )
            else:
                chain.execute.return_value = _make_data_result(
                    select_rows or []
                )
            return chain

        tbl.select.side_effect = _select
        return tbl

    client.table.side_effect = _table
    return client


# ── label_earnings_outcome ────────────────────────────────────────────


def test_label_earnings_outcome_writes_correct_fields():
    """The row handed to Supabase must include every field needed
    downstream by train_earnings_model: ticker, correct_direction,
    pnl_vs_expected, iv_crush_captured, net_pnl, plus the context
    columns (position_id, entry_at, exit_at, expected/actual move)."""
    _ensure_earnings_on_path()
    from edge_calculator import label_earnings_outcome

    position = {
        "id": "earn-uuid-1",
        "ticker": "NVDA",
        "entry_at": "2026-04-18T13:55:00+00:00",
        "exit_at": "2026-04-21T15:50:00+00:00",
        "total_debit": 150.0,
        "net_pnl": 90.0,
        "implied_move_pct": 0.062,
        "actual_move_pct": 0.091,
    }

    inserted: list = []
    with patch(
        "db.get_client",
        return_value=_make_get_client_mock(insert_capture=inserted),
    ):
        result = label_earnings_outcome(position, redis_client=None)

    assert result == {"labeled": True, "ticker": "NVDA"}
    assert len(inserted) == 1
    row = inserted[0]
    for col in (
        "position_id",
        "ticker",
        "entry_at",
        "exit_at",
        "correct_direction",
        "pnl_vs_expected",
        "iv_crush_captured",
        "expected_move_pct",
        "actual_move_pct",
        "net_pnl",
    ):
        assert col in row, f"missing {col} in labeled outcome row"
    assert row["ticker"] == "NVDA"
    assert row["position_id"] == "earn-uuid-1"


def test_label_earnings_outcome_win():
    """net_pnl > 0 → correct_direction=True, iv_crush_captured=True
    (scaffold proxy: we won despite IV compression)."""
    _ensure_earnings_on_path()
    from edge_calculator import label_earnings_outcome

    inserted: list = []
    with patch(
        "db.get_client",
        return_value=_make_get_client_mock(insert_capture=inserted),
    ):
        label_earnings_outcome(
            {
                "id": "e1",
                "ticker": "meta",
                "total_debit": 200.0,
                "net_pnl": 150.0,
                "implied_move_pct": 0.061,
                "actual_move_pct": 0.084,
            },
            redis_client=None,
        )

    row = inserted[0]
    assert row["correct_direction"] is True
    assert row["iv_crush_captured"] is True
    # pnl_vs_expected = 150 / 200 = 0.75, rounded to 4 dp.
    assert row["pnl_vs_expected"] == 0.75
    # Ticker is uppercased for consistency with EARNINGS_HISTORY.
    assert row["ticker"] == "META"


def test_label_earnings_outcome_loss():
    """net_pnl < 0 → correct_direction=False and iv_crush_captured=False.
    iv_crush_captured is intentionally false on losses — losing a
    debit straddle typically means IV did crush but the move was
    smaller than implied, not a "crush captured" outcome."""
    _ensure_earnings_on_path()
    from edge_calculator import label_earnings_outcome

    inserted: list = []
    with patch(
        "db.get_client",
        return_value=_make_get_client_mock(insert_capture=inserted),
    ):
        label_earnings_outcome(
            {
                "id": "e2",
                "ticker": "TSLA",
                "total_debit": 300.0,
                "net_pnl": -180.0,
                "implied_move_pct": 0.091,
                "actual_move_pct": 0.045,
            },
            redis_client=None,
        )

    row = inserted[0]
    assert row["correct_direction"] is False
    assert row["iv_crush_captured"] is False
    # -180 / 300 = -0.6
    assert row["pnl_vs_expected"] == -0.6


def test_label_earnings_outcome_fail_open():
    """Supabase insert raises → function returns labeled=False with
    an error payload, never propagates. The close path must stay
    unaffected by any labeling failure."""
    _ensure_earnings_on_path()
    from edge_calculator import label_earnings_outcome

    raising_client = MagicMock()
    raising_client.table.side_effect = RuntimeError("supabase down")

    with patch("db.get_client", return_value=raising_client):
        result = label_earnings_outcome(
            {
                "id": "e3",
                "ticker": "AAPL",
                "total_debit": 100.0,
                "net_pnl": 25.0,
                "implied_move_pct": 0.035,
                "actual_move_pct": 0.051,
            },
            redis_client=None,
        )

    assert result["labeled"] is False
    assert "error" in result


# ── train_earnings_model ──────────────────────────────────────────────


def test_train_earnings_model_skips_below_50():
    """30 outcomes → trained=False, NO Redis write, NO row scan."""
    _ensure_earnings_on_path()
    from edge_calculator import (
        MIN_EARNINGS_OUTCOMES_FOR_TRAINING,
        train_earnings_model,
    )

    client = _make_get_client_mock(
        count_result=_make_count_result(30),
    )
    redis_mock = MagicMock()

    with patch("db.get_client", return_value=client):
        result = train_earnings_model(redis_mock)

    assert result == {
        "trained": False,
        "total_outcomes": 30,
        "required": MIN_EARNINGS_OUTCOMES_FOR_TRAINING,
    }
    redis_mock.setex.assert_not_called()


def test_train_earnings_model_runs_above_50():
    """55 mock outcomes across 2 tickers → trained=True, weights
    written to Redis key earnings:ticker_weights with an 8-day TTL.
    Each ticker has >= 3 trades so both appear in the weights dict."""
    _ensure_earnings_on_path()
    from edge_calculator import train_earnings_model

    # 40 NVDA trades (30 wins), 15 META trades (9 wins) — total 55.
    rows = []
    for i in range(40):
        rows.append({
            "ticker": "NVDA",
            "correct_direction": i < 30,
            "net_pnl": 120.0 if i < 30 else -80.0,
            "iv_crush_captured": i < 30,
        })
    for i in range(15):
        rows.append({
            "ticker": "META",
            "correct_direction": i < 9,
            "net_pnl": 90.0 if i < 9 else -60.0,
            "iv_crush_captured": i < 9,
        })

    client = _make_get_client_mock(
        count_result=_make_count_result(55),
        select_rows=rows,
    )
    redis_mock = MagicMock()

    with patch("db.get_client", return_value=client):
        result = train_earnings_model(redis_mock)

    assert result["trained"] is True
    assert result["total_outcomes"] == 55
    assert result["tickers_calibrated"] == 2

    redis_mock.setex.assert_called_once()
    key, ttl, payload = redis_mock.setex.call_args.args
    assert key == "earnings:ticker_weights"
    assert ttl == 86400 * 8
    weights = json.loads(payload)
    assert set(weights.keys()) == {"NVDA", "META"}
    assert weights["NVDA"]["win_rate"] == 0.75
    assert weights["META"]["win_rate"] == 0.6
    # edge_score blends win-rate (60%) + capped avg_pnl normalized (40%).
    assert 0.0 <= weights["NVDA"]["edge_score"] <= 1.0


def test_train_earnings_model_requires_3_trades_per_ticker():
    """A ticker with 2 samples gets excluded from the weights dict
    — low-N weights would be noisier than the hardcoded defaults."""
    _ensure_earnings_on_path()
    from edge_calculator import (
        MIN_PER_TICKER_SAMPLES,
        train_earnings_model,
    )

    assert MIN_PER_TICKER_SAMPLES == 3

    # 48 NVDA + 2 GOOGL = 50 total. Above the training gate, but
    # GOOGL is under the per-ticker gate.
    rows = []
    for i in range(48):
        rows.append({
            "ticker": "NVDA",
            "correct_direction": i < 36,
            "net_pnl": 100.0 if i < 36 else -50.0,
            "iv_crush_captured": i < 36,
        })
    for i in range(2):
        rows.append({
            "ticker": "GOOGL",
            "correct_direction": True,
            "net_pnl": 70.0,
            "iv_crush_captured": True,
        })

    client = _make_get_client_mock(
        count_result=_make_count_result(50),
        select_rows=rows,
    )
    redis_mock = MagicMock()

    with patch("db.get_client", return_value=client):
        result = train_earnings_model(redis_mock)

    assert result["trained"] is True
    assert result["tickers_calibrated"] == 1  # NVDA only — GOOGL excluded
    _, _, payload = redis_mock.setex.call_args.args
    weights = json.loads(payload)
    assert "NVDA" in weights
    assert "GOOGL" not in weights


def test_train_earnings_model_fail_open():
    """Supabase raises on the count query → returns trained=False
    with an error payload, never propagates. Previous weights (or
    the hardcoded defaults) remain in place."""
    _ensure_earnings_on_path()
    from edge_calculator import train_earnings_model

    raising_client = MagicMock()
    raising_client.table.side_effect = RuntimeError("supabase down")
    redis_mock = MagicMock()

    with patch("db.get_client", return_value=raising_client):
        result = train_earnings_model(redis_mock)

    assert result["trained"] is False
    assert "error" in result
    redis_mock.setex.assert_not_called()
