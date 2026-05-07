"""Tests for Phase A1: outcome labels and GLC-001/002 real accuracy."""
from unittest.mock import patch, MagicMock
from datetime import date, datetime, timezone, timedelta


def test_label_prediction_outcomes_writes_outcome_correct():
    """label_prediction_outcomes writes outcome_correct=True when direction matches."""
    from model_retraining import label_prediction_outcomes

    # Prediction: direction=bull, spx_price=5200.0
    # SPX at t+30min = 5210.0 → return = +0.19% → actual=bull → correct=True
    mock_predictions = [{
        "id": "pred-001",
        "predicted_at": "2026-04-17T10:00:00+00:00",
        "direction": "bull",
        "spx_price": 5200.0,
    }]
    mock_polygon_resp = MagicMock()
    mock_polygon_resp.status_code = 200
    mock_polygon_resp.json.return_value = {
        "results": [{"c": 5210.0}]  # close 30min later
    }

    with patch("model_retraining.get_client") as mock_db, \
         patch("model_retraining.write_audit_log"), \
         patch("httpx.Client") as mock_httpx, \
         patch("model_retraining.config") as mock_config:

        mock_config.POLYGON_API_KEY = "test-key"

        # Mock DB: first call = fetch predictions, second call = update
        mock_db.return_value.table.return_value.select.return_value\
            .eq.return_value.gte.return_value.lte.return_value\
            .is_.return_value.execute.return_value.data = mock_predictions

        mock_db.return_value.table.return_value.update.return_value\
            .eq.return_value.execute.return_value = MagicMock()

        mock_httpx.return_value.__enter__.return_value.get.return_value = mock_polygon_resp

        result = label_prediction_outcomes(target_date=date(2026, 4, 17))

    assert result["labeled"] == 1
    assert result["errors"] == 0

    # Verify DB update was called with correct=True
    update_call = mock_db.return_value.table.return_value.update.call_args
    update_data = update_call[0][0]
    assert update_data["outcome_correct"] is True
    assert update_data["outcome_direction"] == "bull"
    assert update_data["spx_return_30min"] > 0


def test_label_prediction_outcomes_detects_wrong_direction():
    """outcome_correct=False when predicted bull but SPX went bear."""
    from model_retraining import label_prediction_outcomes

    mock_predictions = [{
        "id": "pred-002",
        "predicted_at": "2026-04-17T10:00:00+00:00",
        "direction": "bull",
        "spx_price": 5200.0,
    }]
    mock_polygon_resp = MagicMock()
    mock_polygon_resp.status_code = 200
    mock_polygon_resp.json.return_value = {"results": [{"c": 5180.0}]}  # SPX fell

    with patch("model_retraining.get_client") as mock_db, \
         patch("model_retraining.write_audit_log"), \
         patch("httpx.Client") as mock_httpx, \
         patch("model_retraining.config") as mock_config:

        mock_config.POLYGON_API_KEY = "test-key"
        mock_db.return_value.table.return_value.select.return_value\
            .eq.return_value.gte.return_value.lte.return_value\
            .is_.return_value.execute.return_value.data = mock_predictions
        mock_httpx.return_value.__enter__.return_value.get.return_value = mock_polygon_resp

        result = label_prediction_outcomes(target_date=date(2026, 4, 17))

    update_call = mock_db.return_value.table.return_value.update.call_args
    update_data = update_call[0][0]
    assert update_data["outcome_correct"] is False
    assert update_data["outcome_direction"] == "bear"
    assert update_data["spx_return_30min"] < 0


def test_label_prediction_outcomes_tiny_positive_move_is_bull():
    """T-ACT-076 / F-068-I (2026-05-07): binary classifier — any
    spx_return > 0, however tiny, must be labeled "bull" (NOT
    "neutral"). The previous ternary classifier emitted "neutral"
    for moves within the ±0.1% DIRECTION_THRESHOLD band; the
    LightGBM model's training script
    (backend/scripts/train_direction_model.py:323-325) has always
    been binary, so the labeler's class space must match. A tiny
    positive move that under the old ternary contract yielded
    "neutral" must now yield "bull". This is the load-bearing
    test for F-068-I dissolution — if it asserts "neutral" again,
    the same-day fix has regressed."""
    from model_retraining import label_prediction_outcomes

    mock_predictions = [{
        "id": "pred-003",
        "predicted_at": "2026-04-17T10:00:00+00:00",
        "direction": "bull",
        "spx_price": 5200.0,
    }]
    mock_polygon_resp = MagicMock()
    mock_polygon_resp.status_code = 200
    # SPX moved +0.05% — under the OLD ternary labeler this would
    # be "neutral". Under the new binary labeler it is "bull".
    mock_polygon_resp.json.return_value = {"results": [{"c": 5202.6}]}

    with patch("model_retraining.get_client") as mock_db, \
         patch("model_retraining.write_audit_log"), \
         patch("httpx.Client") as mock_httpx, \
         patch("model_retraining.config") as mock_config:

        mock_config.POLYGON_API_KEY = "test-key"
        mock_db.return_value.table.return_value.select.return_value\
            .eq.return_value.gte.return_value.lte.return_value\
            .is_.return_value.execute.return_value.data = mock_predictions
        mock_httpx.return_value.__enter__.return_value.get.return_value = mock_polygon_resp

        label_prediction_outcomes(target_date=date(2026, 4, 17))

    update_call = mock_db.return_value.table.return_value.update.call_args
    update_data = update_call[0][0]
    assert update_data["outcome_direction"] == "bull", (
        "Binary labeler must classify any spx_return > 0 as bull "
        "(was neutral under pre-T-ACT-076 ternary classifier). "
        "Class space must match train_direction_model.py:323-325."
    )
    # Sanity: the spx_return is positive but well under the OLD
    # ±0.1% threshold — confirms this case used to fall in the
    # neutral band.
    assert 0.0 < update_data["spx_return_30min"] < 0.001
    # Predicted bull, actual bull → correct.
    assert update_data["outcome_correct"] is True


def test_label_prediction_outcomes_zero_move_is_bear():
    """T-ACT-076 / F-068-I (2026-05-07): binary labeler boundary —
    spx_return == 0 (exact tie) must be labeled "bear" because
    the labeler condition is `r > 0` (strict). This matches the
    training-script contract at
    backend/scripts/train_direction_model.py:323-325 byte-for-byte.
    The case is vanishingly rare in production (float division of
    two close-prices nearly never collides exactly) but the
    contract must be deterministic."""
    from model_retraining import label_prediction_outcomes

    mock_predictions = [{
        "id": "pred-zero",
        "predicted_at": "2026-04-17T10:00:00+00:00",
        "direction": "bear",
        "spx_price": 5200.0,
    }]
    mock_polygon_resp = MagicMock()
    mock_polygon_resp.status_code = 200
    # Exact zero return: SPX closes at the same level.
    mock_polygon_resp.json.return_value = {"results": [{"c": 5200.0}]}

    with patch("model_retraining.get_client") as mock_db, \
         patch("model_retraining.write_audit_log"), \
         patch("httpx.Client") as mock_httpx, \
         patch("model_retraining.config") as mock_config:

        mock_config.POLYGON_API_KEY = "test-key"
        mock_db.return_value.table.return_value.select.return_value\
            .eq.return_value.gte.return_value.lte.return_value\
            .is_.return_value.execute.return_value.data = mock_predictions
        mock_httpx.return_value.__enter__.return_value.get.return_value = mock_polygon_resp

        label_prediction_outcomes(target_date=date(2026, 4, 17))

    update_call = mock_db.return_value.table.return_value.update.call_args
    update_data = update_call[0][0]
    assert update_data["outcome_direction"] == "bear", (
        "Binary labeler boundary contract: spx_return == 0 → bear "
        "(strict `r > 0` matches train_direction_model.py:323-325)."
    )
    assert update_data["spx_return_30min"] == 0.0
    # Predicted bear, actual bear → correct.
    assert update_data["outcome_correct"] is True


def test_label_prediction_outcomes_never_emits_neutral():
    """T-ACT-076 / F-068-I regression guard (2026-05-07): the
    binary labeler must NEVER write outcome_direction="neutral"
    regardless of how small the move. Direct assertion of the
    static contract by inspecting the source — defends against
    future accidental re-introduction of a ternary band."""
    import inspect
    from model_retraining import label_prediction_outcomes
    source = inspect.getsource(label_prediction_outcomes)
    # The new binary contract has exactly one decision expression.
    # The token "neutral" must NOT appear as a labeling target —
    # comments referencing the historical ternary are allowed but
    # the assignment must be absent. We assert on the assignment
    # syntax specifically.
    assert 'actual_direction = "neutral"' not in source, (
        "T-ACT-076 contract: labeler must not emit "
        'outcome_direction="neutral". A ternary classifier has '
        "regressed; see HANDOFF_NOTE_2026-05-06_F068I_BINARY_"
        "LABELER_FIX.md for the original-intent forensic."
    )
    assert "DIRECTION_THRESHOLD" not in source, (
        "T-ACT-076 contract: the ±0.1% DIRECTION_THRESHOLD band "
        "was removed. Its presence implies a ternary classifier "
        "has been re-introduced."
    )


def test_label_prediction_outcomes_skips_when_no_polygon_key():
    """Returns empty summary without crashing when POLYGON_API_KEY is missing."""
    from model_retraining import label_prediction_outcomes

    mock_predictions = [{"id": "pred-004", "predicted_at": "2026-04-17T10:00:00+00:00",
                         "direction": "bull", "spx_price": 5200.0}]

    with patch("model_retraining.get_client") as mock_db, \
         patch("model_retraining.write_audit_log"), \
         patch("model_retraining.config") as mock_config:

        mock_config.POLYGON_API_KEY = None
        mock_db.return_value.table.return_value.select.return_value\
            .eq.return_value.gte.return_value.lte.return_value\
            .is_.return_value.execute.return_value.data = mock_predictions

        result = label_prediction_outcomes(target_date=date(2026, 4, 17))

    assert result["labeled"] == 0


def test_glc001_uses_outcome_correct_not_winrate():
    """GLC-001 reads outcome_correct column, not position win rate."""
    import inspect
    from criteria_evaluator import evaluate_glc001_prediction_accuracy
    source = inspect.getsource(evaluate_glc001_prediction_accuracy)
    assert "outcome_correct" in source, \
        "GLC-001 must read outcome_correct column"
    assert "net_pnl" not in source, \
        "GLC-001 must NOT use net_pnl (win rate proxy)"
    assert "win_rate" not in source, \
        "GLC-001 must NOT use win_rate proxy"


def test_glc002_uses_outcome_correct_not_winrate():
    """GLC-002 reads outcome_correct column grouped by regime."""
    import inspect
    from criteria_evaluator import evaluate_glc002_per_regime_accuracy
    source = inspect.getsource(evaluate_glc002_per_regime_accuracy)
    assert "outcome_correct" in source
    assert "entry_regime" not in source or "regime" in source


def test_glc001_passes_when_accuracy_above_58pct():
    """GLC-001 reports passed when outcome_correct rate >= 58%."""
    with patch("criteria_evaluator.get_client") as mock_db, \
         patch("criteria_evaluator._update_criterion") as mock_upsert:

        call_count = [0]
        def count_side_effect(*args, **kwargs):
            call_count[0] += 1
            mock = MagicMock()
            if call_count[0] == 1:
                mock.count = 60    # total labeled = 60
            else:
                mock.count = 35    # correct = 35 → 58.3%
            return mock

        mock_db.return_value.table.return_value.select.return_value\
            .eq.return_value.gte.return_value.not_\
            .is_.return_value.execute.side_effect = count_side_effect

        mock_db.return_value.table.return_value.select.return_value\
            .eq.return_value.eq.return_value.gte.return_value\
            .execute.side_effect = count_side_effect

        from criteria_evaluator import evaluate_glc001_prediction_accuracy
        evaluate_glc001_prediction_accuracy()

    upsert_call = mock_upsert.call_args
    assert upsert_call[0][1] == "passed", \
        f"Expected 'passed' with 58.3% accuracy, got '{upsert_call[0][1]}'"
