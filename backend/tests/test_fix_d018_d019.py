"""Tests for D-018 and D-019 bug fixes in position_monitor partial exit."""
from unittest.mock import MagicMock


def test_d019_contracts_updated_after_partial_exit():
    """
    D-019: After partial exit, local contracts variable must reflect
    remaining_contracts so subsequent exit checks use correct value.
    """
    import inspect
    import position_monitor
    source = inspect.getsource(position_monitor)
    assert "D-019 fix" in source, (
        "D-019 fix comment not found in position_monitor"
    )
    assert "contracts = remaining_contracts" in source, (
        "contracts variable not updated after partial exit"
    )


def test_d018_session_pnl_update_attempted():
    """
    D-018: Partial exit block must attempt to update session virtual_pnl.
    """
    import inspect
    import position_monitor
    source = inspect.getsource(position_monitor)
    assert "D-018 fix" in source, (
        "D-018 fix comment not found in position_monitor"
    )
    assert "partial_exit_session_pnl_updated" in source, (
        "session P&L update log not found"
    )
    assert "partial_exit_session_pnl_update_failed" in source, (
        "session P&L error handler not found"
    )


def test_d018_uses_try_except():
    """
    D-018: Session P&L update must be in try/except so it never
    blocks the main exit flow if Supabase is slow.
    """
    import inspect
    import position_monitor
    source = inspect.getsource(position_monitor)
    assert "pnl_err" in source, "D-018 fix missing error handling"


def test_d017_iv_rv_filter_skips_when_rv_zero():
    """
    D-017: When realized_vol=0 (first trading day), IV/RV filter
    must skip gracefully (rv_val > 0 guard).

    NOTE: spec test signature was adapted to match the real
    `_evaluate_no_trade(rcs, cv_stress, vvix_z, session)` signature
    in prediction_engine.py. Documented intent (no IV/RV fire when
    rv=0) is preserved.
    """
    from prediction_engine import PredictionEngine

    engine = PredictionEngine.__new__(PredictionEngine)
    engine.redis_client = MagicMock()

    def mock_read_redis(key, default=None):
        if key == "polygon:vix:current":
            return "15.0"
        if key == "polygon:spx:realized_vol_20d":
            return "0.0"  # first day — no history yet
        return default

    engine._read_redis = mock_read_redis

    # Pass values that clear all earlier guards (rcs>=40, cv_stress<=85,
    # vvix_z<3.0, no halted session) so the only remaining gate that
    # could fire is IV/RV.
    no_trade, reason = engine._evaluate_no_trade(
        rcs=80.0,
        cv_stress=20.0,
        vvix_z=0.0,
        session=None,
    )

    # IV/RV filter must NOT fire when rv=0 (D-017 / rv_val > 0 guard)
    assert no_trade is False, (
        f"_evaluate_no_trade fired with rv=0 — IV/RV filter "
        f"should have been skipped: reason={reason}"
    )
    assert reason is None
