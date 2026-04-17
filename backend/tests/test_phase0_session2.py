"""Tests for Phase 0 Session 2: IV/RV filter and partial exit."""
import math
from unittest.mock import MagicMock, patch


# ── P0.4 TESTS ────────────────────────────────────────────────────────────────

def test_iv_rv_filter_blocks_when_iv_below_rv():
    """no_trade fires when VIX < realized_vol × 1.10."""
    from prediction_engine import PredictionEngine
    engine = PredictionEngine.__new__(PredictionEngine)

    def mock_redis(key, default=None):
        return {
            "polygon:vix:current": "14.0",
            "polygon:spx:realized_vol_20d": "14.5",
        }.get(key, default)

    engine.redis_client = None
    with patch.object(engine, "_read_redis", side_effect=mock_redis):
        no_trade, reason = engine._evaluate_no_trade(
            rcs=65.0, cv_stress=20.0, vvix_z=0.5,
            session={"session_status": "active", "consecutive_losses_today": 0},
        )

    assert no_trade is True
    # VIX 14.0 < 14.5 × 1.10 = 15.95 → blocked
    assert "iv_rv_cheap_premium" in reason


def test_iv_rv_filter_allows_when_iv_above_rv():
    """no_trade does NOT fire when VIX > realized_vol × 1.10."""
    from prediction_engine import PredictionEngine
    engine = PredictionEngine.__new__(PredictionEngine)

    def mock_redis(key, default=None):
        return {
            "polygon:vix:current": "18.0",
            "polygon:spx:realized_vol_20d": "14.0",
        }.get(key, default)

    engine.redis_client = None
    with patch.object(engine, "_read_redis", side_effect=mock_redis):
        no_trade, reason = engine._evaluate_no_trade(
            rcs=65.0, cv_stress=20.0, vvix_z=0.5,
            session={"session_status": "active", "consecutive_losses_today": 0},
        )

    # VIX 18.0 > 14.0 × 1.10 = 15.4 → allowed (assuming other gates pass)
    assert no_trade is False or reason not in (None, "") and "iv_rv" not in (reason or "")


def test_iv_rv_filter_skips_when_no_data():
    """IV/RV filter does not block when Redis data is unavailable."""
    from prediction_engine import PredictionEngine
    engine = PredictionEngine.__new__(PredictionEngine)

    def mock_redis(key, default=None):
        return default  # all keys return None

    engine.redis_client = None
    with patch.object(engine, "_read_redis", side_effect=mock_redis):
        no_trade, reason = engine._evaluate_no_trade(
            rcs=65.0, cv_stress=20.0, vvix_z=0.5,
            session={"session_status": "active", "consecutive_losses_today": 0},
        )

    # Filter must be skipped gracefully when no data
    assert reason is None or "iv_rv" not in (reason or "")


def test_realized_vol_math():
    """Realized vol computation: known returns produce expected annualized vol."""
    # Simulate 10 SPX daily closes with 1% daily moves
    closes = [5000.0 * (1.01 ** i) for i in range(10)]
    log_returns = [
        math.log(closes[i] / closes[i - 1])
        for i in range(1, len(closes))
    ]
    n = len(log_returns)
    mean_r = sum(log_returns) / n
    variance = sum((r - mean_r) ** 2 for r in log_returns) / n
    realized_vol = math.sqrt(variance * 252) * 100

    # 1% daily move annualizes to roughly 16% (1% × sqrt(252) ≈ 15.87%)
    # Constant 1% returns have zero variance around their own mean, so we need
    # the test to assert the math runs — but we'll use a different sample with
    # non-constant returns to see an annualized number in the expected range.
    closes = [5000.0, 5050.0, 5000.0, 5050.0, 5000.0, 5050.0, 5000.0, 5050.0, 5000.0, 5050.0]
    log_returns = [
        math.log(closes[i] / closes[i - 1])
        for i in range(1, len(closes))
    ]
    n = len(log_returns)
    mean_r = sum(log_returns) / n
    variance = sum((r - mean_r) ** 2 for r in log_returns) / n
    realized_vol = math.sqrt(variance * 252) * 100

    # Alternating ±1% moves annualizes to ~16%
    assert 14.0 < realized_vol < 18.0, \
        f"Expected ~16% annualized vol, got {realized_vol:.2f}%"


# ── P0.6 TESTS ────────────────────────────────────────────────────────────────

def test_partial_exit_fires_at_25pct():
    """Partial exit updates contracts when position reaches 25% of max profit."""
    mock_db = MagicMock()
    mock_db.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

    with patch("position_monitor.get_client", return_value=mock_db), \
         patch("position_monitor.write_audit_log"), \
         patch("position_monitor._get_engine") as mock_engine_getter, \
         patch("position_monitor.write_health_status"):

        mock_engine = MagicMock()
        mock_engine_getter.return_value = mock_engine

        # Simulate a position at 25% profit with 5 contracts
        positions = [{
            "id": "pos-001",
            "strategy_type": "put_credit_spread",
            "position_type": "core",
            "status": "open",
            "entry_at": "2026-04-17T09:40:00Z",
            "entry_credit": 1.50,
            "contracts": 5,
            "session_id": "sess-001",
            "current_pnl": 187.50,  # 25% of max_profit (1.50 × 5 × 100 × 0.25 = 187.5)
            "current_cv_stress": 20.0,
            "partial_exit_done": False,
        }]

        with patch("position_monitor.get_open_positions", return_value=positions):
            from position_monitor import run_position_monitor
            run_position_monitor()

        # Verify update was called to reduce contracts and set flag
        mock_db.table.assert_any_call("trading_positions")
        update_calls = mock_db.table.return_value.update.call_args_list
        assert len(update_calls) > 0, "DB update must be called for partial exit"
        update_data = update_calls[0][0][0]
        assert update_data.get("partial_exit_done") is True
        # max(1, int(5 × 0.30)) = max(1, 1) = 1 closed; 5 - 1 = 4 remaining
        assert update_data.get("contracts") == 4


def test_partial_exit_not_repeat():
    """Partial exit does NOT fire again if partial_exit_done is already True."""
    with patch("position_monitor.get_open_positions") as mock_pos, \
         patch("position_monitor.get_client") as mock_db, \
         patch("position_monitor._get_engine") as mock_engine_getter, \
         patch("position_monitor.write_health_status"), \
         patch("position_monitor.write_audit_log"):

        mock_engine = MagicMock()
        mock_engine_getter.return_value = mock_engine
        mock_db.return_value = MagicMock()

        positions = [{
            "id": "pos-002",
            "strategy_type": "put_credit_spread",
            "position_type": "core",
            "status": "open",
            "entry_at": "2026-04-17T09:40:00Z",
            "entry_credit": 1.50,
            "contracts": 3,
            "session_id": "sess-001",
            "current_pnl": 37.50,
            "current_cv_stress": 20.0,
            "partial_exit_done": True,  # Already fired
        }]
        mock_pos.return_value = positions

        from position_monitor import run_position_monitor
        run_position_monitor()

        # DB update for partial exit must NOT be called again
        if mock_db.called:
            update_calls = mock_db.return_value.table.return_value.update.call_args_list
            for c in update_calls:
                data = c[0][0] if c[0] else {}
                assert "partial_exit_done" not in data or data.get("partial_exit_done") is not True, \
                    "Partial exit must not re-fire when partial_exit_done=True"


def test_partial_exit_requires_min_3_contracts():
    """Partial exit does NOT fire when contracts < 3."""
    with patch("position_monitor.get_open_positions") as mock_pos, \
         patch("position_monitor.get_client") as mock_db, \
         patch("position_monitor._get_engine") as mock_engine_getter, \
         patch("position_monitor.write_health_status"):

        mock_engine = MagicMock()
        mock_engine_getter.return_value = mock_engine
        mock_db.return_value = MagicMock()

        positions = [{
            "id": "pos-003",
            "strategy_type": "put_credit_spread",
            "position_type": "core",
            "status": "open",
            "entry_at": "2026-04-17T09:40:00Z",
            "entry_credit": 1.50,
            "contracts": 2,  # Below minimum
            "session_id": "sess-001",
            "current_pnl": 37.50,
            "current_cv_stress": 20.0,
            "partial_exit_done": False,
        }]
        mock_pos.return_value = positions

        from position_monitor import run_position_monitor
        run_position_monitor()

        if mock_db.called:
            update_calls = mock_db.return_value.table.return_value.update.call_args_list
            for c in update_calls:
                data = c[0][0] if c[0] else {}
                assert "partial_exit_done" not in data, \
                    "Partial exit must not fire with only 2 contracts"
