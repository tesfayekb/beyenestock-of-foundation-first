import math


def test_regime_above_zero_gamma_low_vol():
    """SPX above ZG, low VVIX → pin_range (dealers long gamma)."""
    from unittest.mock import patch
    from prediction_engine import PredictionEngine

    engine = PredictionEngine.__new__(PredictionEngine)

    def mock_redis(key, default=None):
        return {
            "polygon:vvix:z_score": "0.3",
            "gex:confidence": "0.8",
            "gex:flip_zone": "5200.0",
            "tradier:quotes:SPX": '{"last": 5220.0}',
        }.get(key, default)

    engine.redis_client = None
    with patch.object(engine, "_read_redis", side_effect=mock_redis), \
         patch.object(engine, "_get_spx_price", return_value=5220.0), \
         patch("prediction_engine.write_audit_log"), \
         patch("prediction_engine.logger"):
        result = engine._compute_regime()

    assert result["regime_lgbm"] == "pin_range"
    assert result["regime_agreement"] is True  # both say range


def test_regime_below_zero_gamma_high_vol():
    """SPX below ZG, rising VVIX → volatile_bearish."""
    from unittest.mock import patch
    from prediction_engine import PredictionEngine

    engine = PredictionEngine.__new__(PredictionEngine)

    def mock_redis(key, default=None):
        return {
            "polygon:vvix:z_score": "1.8",
            "gex:confidence": "0.75",
            "gex:flip_zone": "5250.0",
            "tradier:quotes:SPX": '{"last": 5220.0}',
        }.get(key, default)

    engine.redis_client = None
    with patch.object(engine, "_read_redis", side_effect=mock_redis), \
         patch.object(engine, "_get_spx_price", return_value=5220.0), \
         patch("prediction_engine.write_audit_log"), \
         patch("prediction_engine.logger"):
        result = engine._compute_regime()

    assert result["regime_lgbm"] == "volatile_bearish"


def test_d021_fires_on_genuine_disagreement():
    """D-021 penalty applies when VVIX and GEX disagree."""
    from unittest.mock import patch, MagicMock
    from prediction_engine import PredictionEngine

    engine = PredictionEngine.__new__(PredictionEngine)
    audit_calls = []

    # VVIX says quiet_bullish (z=1.8), GEX says volatile_bearish (SPX below ZG)
    def mock_redis(key, default=None):
        return {
            "polygon:vvix:z_score": "1.8",
            "gex:confidence": "0.8",
            "gex:flip_zone": "5250.0",
        }.get(key, default)

    engine.redis_client = None
    with patch.object(engine, "_read_redis", side_effect=mock_redis), \
         patch.object(engine, "_get_spx_price", return_value=5220.0), \
         patch("prediction_engine.write_audit_log",
               side_effect=lambda **kw: audit_calls.append(kw)), \
         patch("prediction_engine.logger"):
        result = engine._compute_regime()

    assert result["regime_agreement"] is False
    assert any(
        c.get("action") == "trading.regime_disagreement"
        for c in audit_calls
    ), "D-021 audit log must fire on disagreement"


def test_direction_above_zero_gamma_tilts_bull():
    """SPX above ZG → p_bull > p_bear (positive tilt)."""
    from prediction_engine import PredictionEngine
    engine = PredictionEngine.__new__(PredictionEngine)
    result = engine._compute_direction(
        "pin_range", 30.0,
        spx_price=5220.0, flip_zone=5200.0, gex_conf=0.8
    )
    assert result["p_bull"] > result["p_bear"]
    assert result["expected_move_pts"] > 0


def test_direction_below_zero_gamma_tilts_bear():
    """SPX below ZG → p_bear > p_bull (negative tilt)."""
    from prediction_engine import PredictionEngine
    engine = PredictionEngine.__new__(PredictionEngine)
    result = engine._compute_direction(
        "volatile_bearish", 40.0,
        spx_price=5180.0, flip_zone=5200.0, gex_conf=0.8
    )
    assert result["p_bear"] > result["p_bull"]


def test_direction_signal_weak_when_near_zero_gamma():
    """SPX very close to ZG → signal_weak=True."""
    from prediction_engine import PredictionEngine
    engine = PredictionEngine.__new__(PredictionEngine)
    result = engine._compute_direction(
        "pin_range", 20.0,
        spx_price=5201.0, flip_zone=5200.0, gex_conf=0.8
    )
    assert result["signal_weak"] is True


def test_direction_no_gex_uses_regime_fallback():
    """No GEX data → uses regime-based fallback (not zero)."""
    from prediction_engine import PredictionEngine
    engine = PredictionEngine.__new__(PredictionEngine)
    result = engine._compute_direction(
        "quiet_bullish", 30.0,
        spx_price=5200.0, flip_zone=None, gex_conf=0.0
    )
    assert result["p_bull"] > 0
    assert result["p_bear"] > 0
    assert abs(result["p_bull"] + result["p_bear"] + result["p_neutral"] - 1.0) < 0.001


def test_low_gex_confidence_both_use_hmm():
    """Low GEX confidence → regime_lgbm falls back to regime_hmm."""
    from unittest.mock import patch
    from prediction_engine import PredictionEngine

    engine = PredictionEngine.__new__(PredictionEngine)

    def mock_redis(key, default=None):
        return {
            "polygon:vvix:z_score": "0.5",
            "gex:confidence": "0.1",  # below 0.3 threshold
            "gex:flip_zone": "5200.0",
        }.get(key, default)

    engine.redis_client = None
    with patch.object(engine, "_read_redis", side_effect=mock_redis), \
         patch.object(engine, "_get_spx_price", return_value=5180.0), \
         patch("prediction_engine.write_audit_log"), \
         patch("prediction_engine.logger"):
        result = engine._compute_regime()

    assert result["regime_hmm"] == result["regime_lgbm"]
    assert result["regime_agreement"] is True
