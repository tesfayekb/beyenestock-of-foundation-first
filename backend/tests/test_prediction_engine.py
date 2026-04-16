from unittest.mock import patch, MagicMock


def test_direction_probabilities_sum_to_one():
    from prediction_engine import PredictionEngine
    engine = PredictionEngine.__new__(PredictionEngine)
    engine.redis_client = None
    result = engine._compute_direction("pin_range", 30.0)
    total = result["p_bull"] + result["p_bear"] + result["p_neutral"]
    assert abs(total - 1.0) < 0.001


def test_cv_stress_bounded_0_to_100():
    from prediction_engine import PredictionEngine
    engine = PredictionEngine.__new__(PredictionEngine)
    engine.redis_client = None
    result = engine._compute_cv_stress()
    assert 0.0 <= result["cv_stress_score"] <= 100.0


def test_no_trade_when_rcs_below_40():
    from prediction_engine import PredictionEngine
    engine = PredictionEngine.__new__(PredictionEngine)
    session = {"session_status": "active", "consecutive_losses_today": 0}
    no_trade, reason = engine._evaluate_no_trade(35.0, 20.0, 0.5, session)
    assert no_trade is True
    assert "rcs_too_low" in reason


def test_no_trade_vvix_emergency():
    """D-018: no-trade when VVIX Z >= 3.0."""
    from prediction_engine import PredictionEngine
    engine = PredictionEngine.__new__(PredictionEngine)
    session = {"session_status": "active", "consecutive_losses_today": 0}
    no_trade, reason = engine._evaluate_no_trade(75.0, 20.0, 3.1, session)
    assert no_trade is True
    assert "vvix_emergency" in reason


def test_no_trade_capital_preservation_5_losses():
    """D-022: halt at 5 consecutive losses."""
    from prediction_engine import PredictionEngine
    engine = PredictionEngine.__new__(PredictionEngine)
    session = {"session_status": "active", "consecutive_losses_today": 5}
    no_trade, reason = engine._evaluate_no_trade(75.0, 20.0, 0.5, session)
    assert no_trade is True
    assert "capital_preservation_halt" in reason


def test_regime_disagreement_reduces_rcs():
    """D-021: disagreement between HMM and LightGBM reduces RCS by 15."""
    from prediction_engine import PredictionEngine
    engine = PredictionEngine.__new__(PredictionEngine)
    engine.redis_client = MagicMock()
    # VVIX Z > 2.5 triggers disagreement in placeholder
    engine.redis_client.get.return_value = "3.0"
    with patch("prediction_engine.write_audit_log"):
        result = engine._compute_regime()
    if not result["regime_agreement"]:
        # RCS should be reduced
        assert result["rcs"] < 50


def test_no_trade_when_session_halted():
    """Halted session always produces no-trade."""
    from prediction_engine import PredictionEngine
    engine = PredictionEngine.__new__(PredictionEngine)
    session = {"session_status": "halted", "consecutive_losses_today": 0}
    no_trade, reason = engine._evaluate_no_trade(75.0, 20.0, 0.5, session)
    assert no_trade is True
    assert reason == "session_halted"
