def test_commission_is_035_per_leg():
    """Commission must be $0.35/contract/leg not $0.65."""
    import inspect
    from execution_engine import ExecutionEngine
    source = inspect.getsource(ExecutionEngine.close_virtual_position)
    assert "0.35 * contracts * legs" in source, \
        "Commission must be 0.35 not 0.65"
    assert "0.65 * contracts * legs" not in source, \
        "Old 0.65 commission still present"


def test_entry_gate_is_935am_not_1000am():
    """Entry gate must be 9:35 AM not 10:00 AM."""
    import inspect
    from strategy_selector import StrategySelector
    source = inspect.getsource(StrategySelector._stage0_time_gate)
    assert "9 * 60 + 35" in source, \
        "Entry gate must be 9:35 AM (9*60+35=575)"
    assert "before_935am" in source, \
        "Reason string must be before_935am"
    assert "10 * 60" not in source or "10 * 60 + 30" in source, \
        "Old 10:00 AM gate still present (10*60=600)"


def test_signal_weak_threshold_is_005():
    """signal_weak threshold must be 0.05 not 0.10."""
    from prediction_engine import PredictionEngine
    engine = PredictionEngine.__new__(PredictionEngine)

    # At 0.5% above ZG: |diff| ≈ 0.066 — should NOT be weak at 0.05
    result_clear = engine._compute_direction(
        "pin_range", 20.0,
        spx_price=5226.0, flip_zone=5200.0, gex_conf=0.8
    )
    assert not result_clear["signal_weak"], \
        "0.5% from ZG should NOT be signal_weak at threshold 0.05"

    # At 0.1% above ZG: |diff| ≈ 0.018 — should be weak
    result_weak = engine._compute_direction(
        "pin_range", 20.0,
        spx_price=5205.0, flip_zone=5200.0, gex_conf=0.8
    )
    assert result_weak["signal_weak"], \
        "0.1% from ZG SHOULD be signal_weak"


def test_signal_weak_was_wrong_at_010():
    """Confirm the old 0.10 threshold would have blocked 0.5% ZG distance."""
    from prediction_engine import PredictionEngine
    import math
    # Reproduce the math: at dist_pct=0.005, tilt=0.15*tanh(0.005*50)
    dist_pct = 5226.0 / 5200.0 - 1.0  # ~0.005
    tilt = 0.15 * math.tanh(dist_pct * 50.0)
    p_bull_raw = 0.50 + tilt
    p_bear_raw = 0.50 - tilt
    p_neutral_raw = 0.12
    total = p_bull_raw + p_bear_raw + p_neutral_raw
    p_bull = p_bull_raw / total
    p_bear = p_bear_raw / total
    diff = abs(p_bull - p_bear)
    # Old threshold 0.10 would have blocked this
    assert diff < 0.10, f"Confirming old threshold 0.10 blocks 0.5% ZG trades (diff={diff:.3f})"
    # New threshold 0.05 allows it
    assert diff > 0.05, f"Confirming new threshold 0.05 allows 0.5% ZG trades (diff={diff:.3f})"


def test_event_day_size_cut_to_40pct():
    """Event-day session must reduce contracts to 40% of normal."""
    from unittest.mock import patch, MagicMock
    from strategy_selector import StrategySelector

    selector = StrategySelector.__new__(StrategySelector)
    selector.redis_client = MagicMock()
    selector.redis_client.get.return_value = None

    # Mock out all the internal dependencies
    with patch("strategy_selector.compute_position_size") as mock_sizing, \
         patch("strategy_selector.check_trade_frequency", return_value=(True, None)), \
         patch("strategy_selector.get_strikes", return_value={
             "short_strike": 5200.0, "long_strike": 5195.0,
             "expiry_date": "2026-04-17", "spread_width": 5.0,
             "short_strike_2": None, "long_strike_2": None, "target_credit": 1.50
         }), \
         patch.object(selector, "_stage0_time_gate", return_value=(True, None)), \
         patch.object(selector, "_stage1_regime_gate", return_value=["put_credit_spread"]), \
         patch.object(selector, "_stage2_direction_filter", return_value=["put_credit_spread"]):

        mock_session = MagicMock()
        mock_session.return_value = {
            "id": "test-123",
            "day_type": "event",  # ← Event day
            "virtual_trades_count": 0,
            "consecutive_losses_today": 0,
            "session_status": "active",
        }
        mock_sizing.return_value = {
            "contracts": 10,
            "risk_pct": 0.005,
            "reason": "normal",
        }

        prediction = {
            "regime": "pin_range",
            "direction": "bear",
            "p_bull": 0.35,
            "p_bear": 0.45,
            "p_neutral": 0.20,
            "rcs": 65.0,
            "allocation_tier": "moderate",
            "regime_agreement": True,
            "cv_stress_score": 20.0,
            "no_trade_signal": False,
            "no_trade_reason": None,
        }

        result = selector.select(
            prediction,
            mock_session.return_value,
            account_value=100000.0,
        )

        assert result is not None, "Signal should be generated"
        assert result["contracts"] <= 4, \
            f"Event day must cut contracts to 40% of 10 = 4, got {result['contracts']}"


def test_non_event_day_no_size_cut():
    """Non-event day must NOT apply size cut."""
    from unittest.mock import patch, MagicMock
    from strategy_selector import StrategySelector

    selector = StrategySelector.__new__(StrategySelector)
    selector.redis_client = MagicMock()
    selector.redis_client.get.return_value = None

    with patch("strategy_selector.compute_position_size") as mock_sizing, \
         patch("strategy_selector.check_trade_frequency", return_value=(True, None)), \
         patch("strategy_selector.get_strikes", return_value={
             "short_strike": 5200.0, "long_strike": 5195.0,
             "expiry_date": "2026-04-17", "spread_width": 5.0,
             "short_strike_2": None, "long_strike_2": None, "target_credit": 1.50
         }), \
         patch.object(selector, "_stage0_time_gate", return_value=(True, None)), \
         patch.object(selector, "_stage1_regime_gate", return_value=["put_credit_spread"]), \
         patch.object(selector, "_stage2_direction_filter", return_value=["put_credit_spread"]):

        mock_session = MagicMock()
        mock_session.return_value = {
            "id": "test-456",
            "day_type": "trend",  # ← Non-event day
            "virtual_trades_count": 0,
            "consecutive_losses_today": 0,
            "session_status": "active",
        }
        mock_sizing.return_value = {
            "contracts": 10,
            "risk_pct": 0.005,
            "reason": "normal",
        }

        prediction = {
            "regime": "pin_range",
            "direction": "bear",
            "p_bull": 0.35,
            "p_bear": 0.45,
            "p_neutral": 0.20,
            "rcs": 65.0,
            "allocation_tier": "moderate",
            "regime_agreement": True,
            "cv_stress_score": 20.0,
            "no_trade_signal": False,
            "no_trade_reason": None,
        }

        result = selector.select(
            prediction,
            mock_session.return_value,
            account_value=100000.0,
        )

        assert result is not None, "Signal should be generated"
        assert result["contracts"] == 10, \
            f"Non-event day must NOT cut contracts, got {result['contracts']}"
