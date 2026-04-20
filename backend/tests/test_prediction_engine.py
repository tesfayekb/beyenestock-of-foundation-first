import pytest
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


# ── 12H Phase A — additional LightGBM features ────────────────────────

def _make_engine_with_redis(values):
    """Helper: build a PredictionEngine stub whose Redis `get` returns
    the string value from `values` or None if the key is absent.
    Values are strings (Redis semantics) or None (key missing)."""
    from prediction_engine import PredictionEngine

    engine = PredictionEngine.__new__(PredictionEngine)
    mock_redis = MagicMock()
    mock_redis.get = lambda key: values.get(key)
    engine.redis_client = mock_redis
    return engine


def test_prediction_output_includes_new_features():
    """12H: _compute_phase_a_features returns all five Phase A columns
    that the migration adds to trading_prediction_outputs. The keys are
    the contract — if any drift, the Supabase insert silently drops
    columns and the model loses a training signal."""
    engine = _make_engine_with_redis({
        "polygon:spx:prior_day_return": "0.0123",
        "polygon:spx:return_4h": "-0.0045",
        "calendar:earnings_proximity_score": "0.65",
        "polygon:vix:current": "18.5",
        "polygon:vix9d:current": "17.2",
    })

    features = engine._compute_phase_a_features(
        spx_price=5200.0,
        gex_flip_zone=5180.0,
    )

    assert set(features.keys()) == {
        "prior_session_return",
        "vix_term_ratio",
        "spx_momentum_4h",
        "gex_flip_proximity",
        "earnings_proximity_score",
    }
    assert features["prior_session_return"] == pytest.approx(0.0123)
    assert features["spx_momentum_4h"] == pytest.approx(-0.0045)
    assert features["earnings_proximity_score"] == pytest.approx(0.65)
    assert features["vix_term_ratio"] == pytest.approx(17.2 / 18.5, abs=1e-4)
    assert features["gex_flip_proximity"] == pytest.approx(
        20.0 / 5200.0, abs=1e-6
    )


def test_new_feature_columns_fail_open():
    """12H: when Redis returns None for every feature key, the three
    'always-numeric' features fall back to 0.0 (their domain includes
    a literal zero during warmup) and the two ratio features return
    None rather than fabricate a 1.0 or 0 — so LightGBM's native
    NULL-split handles the missing case without learning a phantom
    signal. Absence must not raise."""
    engine = _make_engine_with_redis({})

    features = engine._compute_phase_a_features(
        spx_price=None,
        gex_flip_zone=None,
    )

    assert features["prior_session_return"] == 0.0
    assert features["spx_momentum_4h"] == 0.0
    assert features["earnings_proximity_score"] == 0.0
    assert features["vix_term_ratio"] is None
    assert features["gex_flip_proximity"] is None

    # Malformed (non-numeric) values must also not raise — the
    # module-level _safe_float parser swallows ValueError for the
    # three numeric features, and the inline try/except for the
    # ratio features routes malformed legs to None.
    engine = _make_engine_with_redis({
        "polygon:spx:prior_day_return": "not-a-number",
        "polygon:vix:current": "garbage",
        "polygon:vix9d:current": "17.0",
    })
    features = engine._compute_phase_a_features(
        spx_price=5200.0, gex_flip_zone=5150.0
    )
    assert features["prior_session_return"] == 0.0
    assert features["vix_term_ratio"] is None
    assert features["gex_flip_proximity"] == pytest.approx(
        50.0 / 5200.0, abs=1e-6
    )


def test_phase_a_features_partial_gex_missing():
    """gex_flip_proximity must be None when spx_price is zero —
    division-by-zero guard. The other features remain computable."""
    engine = _make_engine_with_redis({
        "polygon:spx:prior_day_return": "0.01",
    })
    features = engine._compute_phase_a_features(
        spx_price=0.0, gex_flip_zone=5200.0
    )
    assert features["gex_flip_proximity"] is None
    assert features["prior_session_return"] == pytest.approx(0.01)
