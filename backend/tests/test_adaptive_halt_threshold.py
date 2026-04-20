"""
12F — Phase C adaptive halt threshold.

Exercises both halves of the system:
  1. calibration_engine.calibrate_halt_threshold — gating, floor/ceiling,
     Redis writes.
  2. risk_engine.check_daily_drawdown — adaptive read, fallback, halt
     firing at the adaptive threshold instead of the hardcoded -3%.

All Supabase and Redis interactions are mocked. No network required.
"""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_supabase_stub(closed_trades_count, sessions_rows):
    """
    Build a minimal Supabase client stub that satisfies the exact call
    chain used by calibrate_halt_threshold. Supports:
      .table("trading_positions").select("id", count="exact")
        .eq(...).eq(...).execute() -> SimpleNamespace(count=N)
      .table("trading_sessions").select("session_date, virtual_pnl")
        .gte(...).not_.is_(...).order(...).limit(...).execute()
          -> SimpleNamespace(data=[{...}, ...])
    """
    positions_query = MagicMock()
    positions_query.select.return_value = positions_query
    positions_query.eq.return_value = positions_query
    positions_query.execute.return_value = SimpleNamespace(
        count=closed_trades_count,
        data=None,
    )

    sessions_query = MagicMock()
    sessions_query.select.return_value = sessions_query
    sessions_query.gte.return_value = sessions_query
    sessions_query.not_ = MagicMock()
    sessions_query.not_.is_.return_value = sessions_query
    sessions_query.order.return_value = sessions_query
    sessions_query.limit.return_value = sessions_query
    sessions_query.execute.return_value = SimpleNamespace(
        data=sessions_rows,
    )

    client = MagicMock()

    def _table(name):
        if name == "trading_positions":
            return positions_query
        if name == "trading_sessions":
            return sessions_query
        return MagicMock()

    client.table.side_effect = _table
    return client


def _sessions_with_stddev(count, stddev_fraction, equity=100_000.0):
    """
    Build `count` synthetic sessions whose virtual_pnl has the requested
    population stddev as a fraction of equity. Uses a symmetric two-valued
    distribution so stddev == |value|, and places an even split around 0.
    """
    assert count % 2 == 0, "use even count for symmetric stddev"
    value = stddev_fraction * equity
    rows = []
    for i in range(count):
        pnl = value if i % 2 == 0 else -value
        rows.append({
            "session_date": f"2026-01-{(i % 28) + 1:02d}",
            "virtual_pnl": pnl,
        })
    return rows


# ---------------------------------------------------------------------------
# Calibration — gating
# ---------------------------------------------------------------------------

def test_calibration_skips_below_100_trades():
    """< 100 closed trades → no Redis write, fallback result returned."""
    from calibration_engine import calibrate_halt_threshold

    redis = MagicMock()
    stub = _make_supabase_stub(
        closed_trades_count=50,
        sessions_rows=[],
    )

    with patch("calibration_engine.get_client", return_value=stub):
        result = calibrate_halt_threshold(redis)

    assert result["calibrated"] is False
    assert result["closed_trades"] == 50
    assert result["fallback"] == -0.03
    redis.setex.assert_not_called()


def test_calibration_skips_below_20_sessions():
    """100+ trades but <20 sessions → no Redis write."""
    from calibration_engine import calibrate_halt_threshold

    redis = MagicMock()
    stub = _make_supabase_stub(
        closed_trades_count=150,
        sessions_rows=_sessions_with_stddev(10, 0.01),
    )

    with patch("calibration_engine.get_client", return_value=stub):
        result = calibrate_halt_threshold(redis)

    assert result["calibrated"] is False
    assert result["session_count"] == 10
    redis.setex.assert_not_called()


# ---------------------------------------------------------------------------
# Calibration — happy path + floor/ceiling
# ---------------------------------------------------------------------------

def test_calibration_writes_threshold_above_100_trades():
    """
    100 trades + 30 sessions with stddev=0.01 of equity →
    raw = -2.5 * 0.01 = -0.025, within [-0.05, -0.02] window → no clamp.
    """
    from calibration_engine import calibrate_halt_threshold

    redis = MagicMock()
    redis.get.return_value = b"100000"  # capital:live_equity
    stub = _make_supabase_stub(
        closed_trades_count=120,
        sessions_rows=_sessions_with_stddev(30, 0.01),
    )

    with patch("calibration_engine.get_client", return_value=stub):
        result = calibrate_halt_threshold(redis)

    assert result["calibrated"] is True
    assert result["sessions_used"] == 30
    assert abs(result["stddev"] - 0.01) < 1e-6
    assert abs(result["threshold"] - (-0.025)) < 1e-6
    assert result["floor_applied"] is False
    assert result["ceiling_applied"] is False

    redis.setex.assert_called_once()
    args, _ = redis.setex.call_args
    assert args[0] == "risk:halt_threshold_pct"
    assert args[1] == 86400 * 8
    assert abs(float(args[2]) - (-0.025)) < 1e-6


def test_floor_applied_when_stddev_very_low():
    """
    stddev=0.002 → raw=-0.005 (looser than -0.02 floor) → clamp to -0.02.
    """
    from calibration_engine import calibrate_halt_threshold

    redis = MagicMock()
    redis.get.return_value = b"100000"
    stub = _make_supabase_stub(
        closed_trades_count=200,
        sessions_rows=_sessions_with_stddev(30, 0.002),
    )

    with patch("calibration_engine.get_client", return_value=stub):
        result = calibrate_halt_threshold(redis)

    assert result["calibrated"] is True
    assert abs(result["threshold"] - (-0.02)) < 1e-6
    assert result["floor_applied"] is True


def test_ceiling_applied_when_stddev_very_high():
    """
    stddev=0.03 → raw=-0.075 (tighter than -0.05 ceiling) → clamp to -0.05.
    """
    from calibration_engine import calibrate_halt_threshold

    redis = MagicMock()
    redis.get.return_value = b"100000"
    stub = _make_supabase_stub(
        closed_trades_count=200,
        sessions_rows=_sessions_with_stddev(30, 0.03),
    )

    with patch("calibration_engine.get_client", return_value=stub):
        result = calibrate_halt_threshold(redis)

    assert result["calibrated"] is True
    assert abs(result["threshold"] - (-0.05)) < 1e-6
    assert result["ceiling_applied"] is True


# ---------------------------------------------------------------------------
# risk_engine reader path
# ---------------------------------------------------------------------------

def test_risk_engine_reads_adaptive_threshold():
    """Adaptive -0.025 in Redis → halt fires at -$2600 on $100k (−2.6%)."""
    from risk_engine import check_daily_drawdown

    redis = MagicMock()
    redis.get.return_value = "-0.025"

    with patch("risk_engine.update_session", return_value=True), \
         patch("risk_engine.write_audit_log", return_value=True), \
         patch("risk_engine.write_health_status", return_value=True):
        # -2.6% > adaptive -2.5% halt but < default -3% → only halts with adaptive
        halted = check_daily_drawdown(
            "sess-a",
            current_daily_pnl=-2600.0,
            account_value=100_000.0,
            redis_client=redis,
        )

    assert halted is True


def test_risk_engine_falls_back_to_default():
    """Redis key absent → default -3% threshold, -2% loss does not halt."""
    from risk_engine import check_daily_drawdown

    redis = MagicMock()
    redis.get.return_value = None

    with patch("risk_engine.update_session", return_value=True), \
         patch("risk_engine.write_audit_log", return_value=True), \
         patch("risk_engine.write_health_status", return_value=True):
        halted = check_daily_drawdown(
            "sess-b",
            current_daily_pnl=-2000.0,
            account_value=100_000.0,
            redis_client=redis,
        )

    assert halted is False


def test_risk_engine_fails_open_on_redis_error():
    """
    Redis.get raises → function must not propagate, must fall back to
    -0.03, and must still behave correctly (not halt at -2%).
    """
    from risk_engine import check_daily_drawdown

    redis = MagicMock()
    redis.get.side_effect = RuntimeError("redis down")

    with patch("risk_engine.update_session", return_value=True), \
         patch("risk_engine.write_audit_log", return_value=True), \
         patch("risk_engine.write_health_status", return_value=True), \
         patch("risk_engine._get_redis", return_value=None):
        halted = check_daily_drawdown(
            "sess-c",
            current_daily_pnl=-2000.0,  # -2% — below default -3%
            account_value=100_000.0,
            redis_client=redis,
        )

    assert halted is False


def test_halt_fires_at_adaptive_threshold():
    """
    threshold=-0.02, daily pnl=-2100 on $100k (−2.1%) → halt fires.
    Confirms the adaptive path actually tightens from the -3% default.
    """
    from risk_engine import check_daily_drawdown

    redis = MagicMock()
    redis.get.return_value = "-0.02"

    with patch("risk_engine.update_session", return_value=True), \
         patch("risk_engine.write_audit_log", return_value=True), \
         patch("risk_engine.write_health_status", return_value=True):
        halted = check_daily_drawdown(
            "sess-d",
            current_daily_pnl=-2100.0,
            account_value=100_000.0,
            redis_client=redis,
        )

    assert halted is True


def test_halt_does_not_fire_below_threshold():
    """
    threshold=-0.02, daily pnl=-1500 on $100k (−1.5%) → no halt.
    -1.5% is at the warning edge, not yet past the halt.
    """
    from risk_engine import check_daily_drawdown

    redis = MagicMock()
    redis.get.return_value = "-0.02"

    with patch("risk_engine.update_session", return_value=True), \
         patch("risk_engine.write_audit_log", return_value=True), \
         patch("risk_engine.write_health_status", return_value=True):
        halted = check_daily_drawdown(
            "sess-e",
            current_daily_pnl=-1500.0,
            account_value=100_000.0,
            redis_client=redis,
        )

    assert halted is False
