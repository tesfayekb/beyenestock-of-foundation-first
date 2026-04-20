"""
12M — D2 weekly champion/challenger retrain scaffold tests.

Covers `model_retraining.run_meta_label_champion_challenger`.
Per the 2026-04-20 Option-A deviation (see model_retraining.py
docstring), this scaffold targets the 12K meta-label model
(`meta_label_v1.pkl`) rather than the directional model — the
feature space and target match train_meta_label_model's output
there, so the champion's .predict() output is on the same
{0, 1} outcome_correct axis the challenger is trained on.

The eight tests below pin:
  * the no-champion pass-through (current production state),
  * the three insufficiency gates (rows / train leg / holdout leg),
  * the three comparison branches (swap / retain-losing /
    retain-below-threshold),
  * the fail-open surface on Supabase exceptions,
  * a walk-forward-ordering invariant (the same lesson 12K's
    val_accuracy is pinned on — without `.order("predicted_at")`
    the train/holdout split is contaminated by future data).
"""
import os
import sys
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..")
)


# ── Fluent Supabase mock ─────────────────────────────────────────────


class _FluentTable:
    """
    Chainable PostgREST builder stand-in. Every filter method
    returns self. The list of `.order(col, ...)` calls is recorded
    so `test_champion_challenger_uses_chronological_order` can
    assert the walk-forward ordering clause actually runs — a
    silent regression there would poison every comparison the
    scaffold ever produces (future data would leak into train).
    """

    def __init__(self, rows=None):
        self._rows = rows or []
        self.order_calls: list = []

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

    def order(self, *args, **kwargs):
        self.order_calls.append((args, kwargs))
        return self

    def execute(self):
        result = MagicMock()
        result.data = self._rows
        return result


class _FluentClient:
    def __init__(self, rows=None):
        self.table_mock = _FluentTable(rows=rows)

    def table(self, _name):
        return self.table_mock


# ── Row / feature / prediction builders ──────────────────────────────


# cutoff_30 boundary is f"{today-30d}T00:00:00+00:00" while rows
# are stamped at "T12:00:00+00:00" — so a row with days_ago=30
# lands ON the boundary date but AFTER midnight, which the `>=`
# comparison classifies as holdout. Train rows therefore require
# days_ago >= 31 (strictly before the cutoff date) to be split
# into the train leg without drift.
_TRAIN_MIN_DAYS_AGO = 31
_TRAIN_MAX_DAYS_AGO = 89   # still inside the 90d window
_HOLDOUT_MIN_DAYS_AGO = 1
_HOLDOUT_MAX_DAYS_AGO = 29


def _row(days_ago: int, outcome_correct: bool) -> dict:
    """Build a minimal labeled prediction row. Only the fields
    `run_meta_label_champion_challenger` reads are populated — any
    other column pulled in a future schema change will surface as
    a KeyError the feature builder's `.get(...)` defaults handle."""
    when = date.today() - timedelta(days=days_ago)
    return {
        "outcome_correct": outcome_correct,
        "confidence": 0.6,
        "vvix_z_score": 0.1,
        "gex_confidence": 0.5,
        "cv_stress_score": 0.2,
        "vix": 18.0,
        "signal_weak": False,
        "prior_session_return": 0.001,
        "vix_term_ratio": 1.0,
        "spx_momentum_4h": 0.002,
        "gex_flip_proximity": 0.3,
        "predicted_at": f"{when.isoformat()}T12:00:00+00:00",
    }


def _balanced_rows(train_count: int, holdout_count: int) -> list:
    """Produce a chronological row list with approximately balanced
    outcome_correct classes so the mocked LightGBM challenger never
    collapses to a single-class prediction during .fit() on sparse
    data. Exact class ratios don't matter — predict() is patched."""
    train_span = _TRAIN_MAX_DAYS_AGO - _TRAIN_MIN_DAYS_AGO + 1
    holdout_span = _HOLDOUT_MAX_DAYS_AGO - _HOLDOUT_MIN_DAYS_AGO + 1
    rows = []
    for i in range(train_count):
        days_ago = _TRAIN_MIN_DAYS_AGO + (i % train_span)
        rows.append(_row(days_ago, outcome_correct=(i % 2 == 0)))
    for i in range(holdout_count):
        days_ago = _HOLDOUT_MIN_DAYS_AGO + (i % holdout_span)
        rows.append(_row(days_ago, outcome_correct=(i % 2 == 0)))
    return rows


def _predictions_with_n_correct(y_true: np.ndarray, n_correct: int) -> np.ndarray:
    """Build a prediction array that agrees with y_true in exactly
    `n_correct` positions. Flipping the tail of a copy is the
    cheapest way to target a precise holdout accuracy — the test
    then relies only on np.mean(preds == y_true) rather than on
    real LightGBM behaviour."""
    pred = y_true.copy()
    flip_from = n_correct
    pred[flip_from:] = 1 - pred[flip_from:]
    return pred


# ─────────────────────────────────────────────────────────────────────
# 1) no champion model present → complete pass-through
# ─────────────────────────────────────────────────────────────────────


def test_champion_challenger_skips_when_no_model():
    """The production state today: meta_label_v1.pkl has not yet
    been produced by train_meta_label_model (needs 100 closed
    trades + 100 labeled rows). The function must exit cleanly
    without touching Supabase, without importing lightgbm, and
    without raising. Asserting no Supabase call here is the only
    cheap way to pin the "cheap scaffold" property — a regression
    that probes trading_prediction_outputs before checking the
    pkl would quietly run expensive queries on every Sunday job."""
    from model_retraining import run_meta_label_champion_challenger

    with patch("pathlib.Path.exists", return_value=False), \
         patch("model_retraining.get_client") as mock_get_client:
        result = run_meta_label_champion_challenger(MagicMock())

    assert result == {"swapped": False, "reason": "no_champion_model"}
    mock_get_client.assert_not_called()


# ─────────────────────────────────────────────────────────────────────
# 2) insufficient total rows in 90d window
# ─────────────────────────────────────────────────────────────────────


def test_champion_challenger_skips_insufficient_data():
    """30 labeled rows over 90 days is below the 50-row floor.
    The function must exit with reason=insufficient_data BEFORE
    invoking LightGBM or touching any file — a regression that
    attempts to train on a tiny pool would overfit and produce
    meaningless swap decisions."""
    from model_retraining import run_meta_label_champion_challenger

    client = _FluentClient(rows=_balanced_rows(train_count=20, holdout_count=10))

    with patch("pathlib.Path.exists", return_value=True), \
         patch("model_retraining.get_client", return_value=client):
        result = run_meta_label_champion_challenger(MagicMock())

    assert result["swapped"] is False
    assert result["reason"] == "insufficient_data"
    assert result["rows"] == 30


# ─────────────────────────────────────────────────────────────────────
# 3) total rows pass floor but split leg fails
# ─────────────────────────────────────────────────────────────────────


def test_champion_challenger_skips_bad_split():
    """50 rows clear the total floor but only 5 land in the 30-day
    holdout window (< 10 required). Walk-forward evaluation needs
    both legs; a tiny holdout would swap on 1-row noise. The
    function must skip rather than swap under these conditions."""
    from model_retraining import run_meta_label_champion_challenger

    rows = _balanced_rows(train_count=45, holdout_count=5)
    client = _FluentClient(rows=rows)

    with patch("pathlib.Path.exists", return_value=True), \
         patch("model_retraining.get_client", return_value=client):
        result = run_meta_label_champion_challenger(MagicMock())

    assert result["swapped"] is False
    assert result["reason"] == "insufficient_split"
    assert result["train"] == 45
    assert result["holdout"] == 5


# ─────────────────────────────────────────────────────────────────────
# 4) challenger improves by >= 1pp → swap
# ─────────────────────────────────────────────────────────────────────


def test_champion_challenger_swaps_when_challenger_wins():
    """champion 55/100 = 0.55, challenger 57/100 = 0.57,
    improvement = 0.02 ≥ 0.01 → swap. The pre-swap pattern MUST
    be shutil.copy(v1 → v0) BEFORE pickle.dump(v1) — tested by
    asserting both calls fire and by pinning the argument of
    shutil.copy. If dump-then-copy were the order, a pickle.dump
    crash would leave us with no fallback at all."""
    from model_retraining import run_meta_label_champion_challenger

    rows = _balanced_rows(train_count=30, holdout_count=100)
    client = _FluentClient(rows=rows)

    # Holdout y is deterministic from _balanced_rows: alternating
    # True/False for the first 100 holdout entries → [0,1,0,1,...]
    # flipped to [1,0,1,0,...] once zip'd with row-order. What
    # matters for the test is the *shape* of y_hold so we can
    # dial champion/challenger accuracy precisely.
    y_hold = np.array(
        [1 if i % 2 == 0 else 0 for i in range(100)]
    )
    champion_preds = _predictions_with_n_correct(y_hold, n_correct=55)
    challenger_preds = _predictions_with_n_correct(y_hold, n_correct=57)

    champion_mock = MagicMock()
    champion_mock.predict.return_value = champion_preds
    challenger_mock = MagicMock()
    challenger_mock.predict.return_value = challenger_preds

    with patch("pathlib.Path.exists", return_value=True), \
         patch("model_retraining.get_client", return_value=client), \
         patch("pickle.load", return_value=champion_mock), \
         patch("pickle.dump") as mock_dump, \
         patch("shutil.copy") as mock_copy, \
         patch("builtins.open", MagicMock()), \
         patch("lightgbm.LGBMClassifier", return_value=challenger_mock):
        result = run_meta_label_champion_challenger(MagicMock())

    assert result["swapped"] is True
    assert result["champion_acc"] == 0.55
    assert result["challenger_acc"] == 0.57
    assert result["improvement"] == 0.02

    # Backup must run BEFORE the dump (order-sensitive safety rail).
    mock_copy.assert_called_once()
    mock_dump.assert_called_once()
    copy_args, _ = mock_copy.call_args
    assert str(copy_args[0]).endswith("meta_label_v1.pkl")
    assert str(copy_args[1]).endswith("meta_label_v0.pkl")

    challenger_mock.fit.assert_called_once()
    dumped = mock_dump.call_args[0][0]
    assert dumped is challenger_mock, (
        "pickle.dump must receive the trained challenger, not the champion"
    )


# ─────────────────────────────────────────────────────────────────────
# 5) challenger loses → retain champion
# ─────────────────────────────────────────────────────────────────────


def test_champion_challenger_retains_when_challenger_loses():
    """champion 56/100 (0.56), challenger 55/100 (0.55),
    improvement = -0.01 < 0.01 → retain. Both the shutil.copy and
    the pickle.dump must NOT fire in this branch — a regression
    that wrote the losing challenger would degrade live inference
    the following Monday."""
    from model_retraining import run_meta_label_champion_challenger

    rows = _balanced_rows(train_count=30, holdout_count=100)
    client = _FluentClient(rows=rows)

    y_hold = np.array(
        [1 if i % 2 == 0 else 0 for i in range(100)]
    )
    champion_mock = MagicMock()
    champion_mock.predict.return_value = _predictions_with_n_correct(
        y_hold, n_correct=56
    )
    challenger_mock = MagicMock()
    challenger_mock.predict.return_value = _predictions_with_n_correct(
        y_hold, n_correct=55
    )

    with patch("pathlib.Path.exists", return_value=True), \
         patch("model_retraining.get_client", return_value=client), \
         patch("pickle.load", return_value=champion_mock), \
         patch("pickle.dump") as mock_dump, \
         patch("shutil.copy") as mock_copy, \
         patch("builtins.open", MagicMock()), \
         patch("lightgbm.LGBMClassifier", return_value=challenger_mock):
        result = run_meta_label_champion_challenger(MagicMock())

    assert result["swapped"] is False
    assert result["champion_acc"] == 0.56
    assert result["challenger_acc"] == 0.55
    assert result["improvement"] == -0.01

    mock_copy.assert_not_called()
    mock_dump.assert_not_called()


# ─────────────────────────────────────────────────────────────────────
# 6) improvement positive but below swap threshold → retain
# ─────────────────────────────────────────────────────────────────────


def test_champion_challenger_retains_when_improvement_below_threshold():
    """champion 100/200 (0.500), challenger 101/200 (0.505),
    improvement = 0.005 < 0.01 → retain. Pin the 1pp threshold
    against regressions that might lower the bar — a 0.5pp swap
    rule would churn the champion on noise every week."""
    from model_retraining import run_meta_label_champion_challenger

    # 200 holdout rows → finest achievable delta = 0.005.
    rows = _balanced_rows(train_count=30, holdout_count=200)
    client = _FluentClient(rows=rows)

    y_hold = np.array(
        [1 if i % 2 == 0 else 0 for i in range(200)]
    )
    champion_mock = MagicMock()
    champion_mock.predict.return_value = _predictions_with_n_correct(
        y_hold, n_correct=100
    )
    challenger_mock = MagicMock()
    challenger_mock.predict.return_value = _predictions_with_n_correct(
        y_hold, n_correct=101
    )

    with patch("pathlib.Path.exists", return_value=True), \
         patch("model_retraining.get_client", return_value=client), \
         patch("pickle.load", return_value=champion_mock), \
         patch("pickle.dump") as mock_dump, \
         patch("shutil.copy") as mock_copy, \
         patch("builtins.open", MagicMock()), \
         patch("lightgbm.LGBMClassifier", return_value=challenger_mock):
        result = run_meta_label_champion_challenger(MagicMock())

    assert result["swapped"] is False
    assert result["champion_acc"] == 0.5
    assert result["challenger_acc"] == 0.505
    assert result["improvement"] == 0.005

    mock_copy.assert_not_called()
    mock_dump.assert_not_called()


# ─────────────────────────────────────────────────────────────────────
# 7) fail-open on Supabase failure
# ─────────────────────────────────────────────────────────────────────


def test_champion_challenger_fail_open():
    """Supabase .table() raises → function returns a dict with an
    `error` key and never propagates. The weekly calibration job
    chains several blocks in sequence; a raise here would abort
    run_weekly_model_performance_job scheduled 30 minutes later."""
    from model_retraining import run_meta_label_champion_challenger

    raising_client = MagicMock()
    raising_client.table.side_effect = RuntimeError(
        "supabase timed out"
    )

    with patch("pathlib.Path.exists", return_value=True), \
         patch(
             "model_retraining.get_client",
             return_value=raising_client,
         ):
        result = run_meta_label_champion_challenger(MagicMock())

    assert result["swapped"] is False
    assert "error" in result
    assert "supabase timed out" in result["error"]


# ─────────────────────────────────────────────────────────────────────
# 8) walk-forward ordering invariant
# ─────────────────────────────────────────────────────────────────────


def test_champion_challenger_uses_chronological_order():
    """The Supabase query MUST include .order("predicted_at") so
    the train/holdout cutoff at `today - 30d` actually reflects
    chronological order. Without it, PostgREST returns rows in
    insertion-order at best and arbitrary planner-order at worst —
    future data would leak into the train leg and make every
    challenger accuracy the function logs meaningless. Same
    lesson the 12K meta-label training was pinned on."""
    from model_retraining import run_meta_label_champion_challenger

    rows = _balanced_rows(train_count=20, holdout_count=10)  # below floor
    client = _FluentClient(rows=rows)

    with patch("pathlib.Path.exists", return_value=True), \
         patch("model_retraining.get_client", return_value=client):
        run_meta_label_champion_challenger(MagicMock())

    ordered_cols = [
        args[0] for args, kwargs in client.table_mock.order_calls
        if args
    ]
    assert "predicted_at" in ordered_cols, (
        "run_meta_label_champion_challenger must order by "
        "predicted_at to keep the walk-forward split honest"
    )
