from unittest.mock import patch


def test_compute_position_size_zero_contracts_when_spread_width_zero():
    """Zero spread_width must return 0 contracts — prevents division by zero."""
    from risk_engine import compute_position_size
    result = compute_position_size(
        account_value=100_000.0, spread_width=0, sizing_phase=1
    )
    assert result["contracts"] == 0


def test_compute_position_size_reduced_regime_disagreement():
    """D-021: regime_agreement=False must halve the risk_pct."""
    from risk_engine import compute_position_size
    agreed = compute_position_size(
        account_value=100_000.0, spread_width=5.0,
        sizing_phase=1, regime_agreement=True
    )
    disagreed = compute_position_size(
        account_value=100_000.0, spread_width=5.0,
        sizing_phase=1, regime_agreement=False
    )
    assert disagreed["risk_pct"] < agreed["risk_pct"]
    assert disagreed["size_reduction_reason"] is not None
    assert "d021" in disagreed["size_reduction_reason"]


def test_compute_position_size_reduced_consecutive_losses():
    """D-022: 3 consecutive losses must halve the risk_pct."""
    from risk_engine import compute_position_size
    normal = compute_position_size(
        account_value=100_000.0, spread_width=5.0,
        sizing_phase=1, consecutive_losses_today=0
    )
    reduced = compute_position_size(
        account_value=100_000.0, spread_width=5.0,
        sizing_phase=1, consecutive_losses_today=3
    )
    assert reduced["risk_pct"] < normal["risk_pct"]
    assert reduced["size_reduction_reason"] is not None
    assert "d022" in reduced["size_reduction_reason"]


def test_check_daily_drawdown_halts_at_minus_3pct():
    """D-005: -$3100 on $100k account (> -3%) must trigger halt."""
    from risk_engine import check_daily_drawdown
    with patch("risk_engine.update_session", return_value=True), \
         patch("risk_engine.write_audit_log", return_value=True), \
         patch("risk_engine.write_health_status", return_value=True):
        result = check_daily_drawdown("session-id", -3100.0, 100_000.0)
    assert result is True


def test_check_daily_drawdown_ok_under_threshold():
    """D-005: -$2000 on $100k account (-2%) must NOT trigger halt."""
    from risk_engine import check_daily_drawdown
    with patch("risk_engine.update_session", return_value=True), \
         patch("risk_engine.write_audit_log", return_value=True), \
         patch("risk_engine.write_health_status", return_value=True):
        result = check_daily_drawdown("session-id", -2000.0, 100_000.0)
    assert result is False


def test_check_trade_frequency_blocked_in_panic():
    """D-020: panic regime must block all entries (max_trades=0)."""
    from risk_engine import check_trade_frequency
    allowed, reason = check_trade_frequency(0, "panic")
    assert allowed is False
    assert reason is not None
    assert "panic" in reason


def test_check_trade_frequency_blocked_at_regime_cap():
    """D-020: must block when trade count reaches the regime cap."""
    from risk_engine import check_trade_frequency, REGIME_MAX_TRADES
    cap = REGIME_MAX_TRADES["pin_range"]  # 3
    allowed, reason = check_trade_frequency(cap, "pin_range")
    assert allowed is False
    assert reason is not None
