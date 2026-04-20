"""
12G — Butterfly threshold auto-tuning.

Exercises two halves:
  1. calibration_engine.calibrate_butterfly_thresholds + _find_best_threshold
     — gating, scoring, Redis writes, fail-open.
  2. strategy_selector — reads calibrated thresholds from Redis with
     hardcoded fallbacks via _read_butterfly_thresholds.

All Supabase / Redis interactions mocked. No network required.
"""
import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Supabase stub (mirrors the exact chain used by calibrate_butterfly_thresholds)
# ---------------------------------------------------------------------------

def _make_supabase_stub(butterfly_count, trade_rows):
    """
    Stub supports:
      .table("trading_positions").select("id", count="exact")
        .eq(...).eq(...).eq(...).execute() -> SimpleNamespace(count=N)
      .table("trading_positions").select("net_pnl, decision_context")
        .eq(...).eq(...).eq(...).gte(...).execute()
          -> SimpleNamespace(data=[...])
    """
    count_q = MagicMock()
    count_q.select.return_value = count_q
    count_q.eq.return_value = count_q
    count_q.execute.return_value = SimpleNamespace(
        count=butterfly_count, data=None,
    )

    rows_q = MagicMock()
    rows_q.select.return_value = rows_q
    rows_q.eq.return_value = rows_q
    rows_q.gte.return_value = rows_q
    rows_q.execute.return_value = SimpleNamespace(data=trade_rows)

    client = MagicMock()
    state = {"calls": 0}

    def _table(name):
        # First call is the count query (select id, count=exact),
        # second is the detail query (select net_pnl, decision_context).
        # The function invokes them in that order per cycle.
        state["calls"] += 1
        if state["calls"] == 1:
            return count_q
        return rows_q

    client.table.side_effect = _table
    return client


def _trade(gex_conf, dist_pct, conc, net_pnl):
    """Shorthand for a parsed-friendly trade row."""
    ctx = {}
    if gex_conf is not None:
        ctx["gex_conf"] = gex_conf
    if dist_pct is not None:
        ctx["dist_pct"] = dist_pct
    if conc is not None:
        ctx["wall_concentration"] = conc
    return {"net_pnl": net_pnl, "decision_context": ctx}


# ---------------------------------------------------------------------------
# Gating
# ---------------------------------------------------------------------------

def test_calibration_skips_below_20_trades():
    """< 20 closed butterfly trades → no Redis writes, calibrated=False."""
    from calibration_engine import calibrate_butterfly_thresholds

    redis = MagicMock()
    stub = _make_supabase_stub(butterfly_count=15, trade_rows=[])

    with patch("calibration_engine.get_client", return_value=stub):
        result = calibrate_butterfly_thresholds(redis)

    assert result["calibrated"] is False
    assert result["butterfly_trades"] == 15
    redis.setex.assert_not_called()


def test_calibration_skips_insufficient_context():
    """
    25 trades but decision_context has no gate metrics → calibrated=False
    with reason=insufficient_decision_context, Redis untouched.
    """
    from calibration_engine import calibrate_butterfly_thresholds

    rows = [
        {"net_pnl": 100.0, "decision_context": {"signal_mult": 1.0}}
        for _ in range(25)
    ]
    redis = MagicMock()
    stub = _make_supabase_stub(butterfly_count=25, trade_rows=rows)

    with patch("calibration_engine.get_client", return_value=stub):
        result = calibrate_butterfly_thresholds(redis)

    assert result["calibrated"] is False
    assert result["reason"] == "insufficient_decision_context"
    redis.setex.assert_not_called()


# ---------------------------------------------------------------------------
# _find_best_threshold — scoring
# ---------------------------------------------------------------------------

def test_find_best_threshold_above():
    """
    Low-gex_conf trades lose, high-gex_conf trades win. The tuner's
    optimal threshold must be strictly between 0.3 and 0.6 so all the
    low-conf losers get blocked without blocking the high-conf winners.
    """
    from calibration_engine import (
        _find_best_threshold,
        _BUTTERFLY_GEX_CONF_CANDIDATES,
    )

    trades = []
    for _ in range(5):
        trades.append({"gex_conf": 0.3, "won": False, "net_pnl": -200.0})
    for _ in range(5):
        trades.append({"gex_conf": 0.6, "won": True, "net_pnl": 150.0})

    best = _find_best_threshold(
        trades, "gex_conf",
        _BUTTERFLY_GEX_CONF_CANDIDATES, direction="above",
    )

    assert best is not None
    assert 0.30 < best <= 0.60, (
        f"optimal threshold should split the classes, got {best}"
    )


def test_find_best_threshold_below():
    """
    Small distance → winners, large distance → losers.
    direction='below' blocks when value > threshold, so the best
    threshold must be tight enough to block the far-from-wall losers.
    """
    from calibration_engine import (
        _find_best_threshold,
        _BUTTERFLY_WALL_DIST_CANDIDATES,
    )

    trades = []
    for _ in range(5):
        trades.append({"dist_pct": 0.001, "won": True, "net_pnl": 150.0})
    for _ in range(5):
        trades.append({"dist_pct": 0.005, "won": False, "net_pnl": -200.0})

    best = _find_best_threshold(
        trades, "dist_pct",
        _BUTTERFLY_WALL_DIST_CANDIDATES, direction="below",
    )

    assert best is not None
    # Threshold must be >= 0.001 (keep winners) and < 0.005 (block losers).
    assert 0.001 <= best < 0.005


# ---------------------------------------------------------------------------
# Happy path — Redis writes
# ---------------------------------------------------------------------------

def test_calibration_writes_redis_keys():
    """25 trades with full context → all three keys written, 8-day TTL."""
    from calibration_engine import calibrate_butterfly_thresholds

    rows = []
    for _ in range(13):
        rows.append(_trade(
            gex_conf=0.3, dist_pct=0.005, conc=0.15, net_pnl=-200.0,
        ))
    for _ in range(12):
        rows.append(_trade(
            gex_conf=0.6, dist_pct=0.001, conc=0.50, net_pnl=150.0,
        ))

    redis = MagicMock()
    stub = _make_supabase_stub(butterfly_count=25, trade_rows=rows)

    with patch("calibration_engine.get_client", return_value=stub):
        result = calibrate_butterfly_thresholds(redis)

    assert result["calibrated"] is True
    assert result["butterfly_trades"] == 25
    assert result["parsed_trades"] == 25

    # 3 Redis writes, all 8-day TTL, correct keys.
    assert redis.setex.call_count == 3
    written_keys = {c.args[0] for c in redis.setex.call_args_list}
    assert written_keys == {
        "butterfly:threshold:gex_conf",
        "butterfly:threshold:wall_distance",
        "butterfly:threshold:concentration",
    }
    for c in redis.setex.call_args_list:
        assert c.args[1] == 86400 * 8


# ---------------------------------------------------------------------------
# Fail-open — Supabase raises
# ---------------------------------------------------------------------------

def test_calibration_fails_open():
    """Supabase raises → returns calibrated=False, never propagates."""
    from calibration_engine import calibrate_butterfly_thresholds

    redis = MagicMock()
    with patch(
        "calibration_engine.get_client",
        side_effect=RuntimeError("supabase down"),
    ):
        result = calibrate_butterfly_thresholds(redis)

    assert result["calibrated"] is False
    assert "error" in result
    redis.setex.assert_not_called()


# ---------------------------------------------------------------------------
# strategy_selector reader path
# ---------------------------------------------------------------------------

def _make_selector(redis_client):
    from strategy_selector import StrategySelector
    selector = StrategySelector.__new__(StrategySelector)
    selector.redis_client = redis_client
    return selector


def test_strategy_selector_reads_calibrated_gex_conf():
    """Redis has gex_conf=0.5 → _read_butterfly_thresholds returns 0.5."""
    redis = MagicMock()
    redis.get.side_effect = lambda k: {
        "butterfly:threshold:gex_conf": b"0.5",
        "butterfly:threshold:wall_distance": None,
        "butterfly:threshold:concentration": None,
    }.get(k)

    selector = _make_selector(redis)
    gex_min, dist_max, conc_min, source = selector._read_butterfly_thresholds()

    assert gex_min == 0.5
    # Defaults hold for the other two
    assert dist_max == 0.003
    assert conc_min == 0.25
    assert source == "calibrated"


def test_strategy_selector_falls_back_to_default():
    """All Redis keys absent → all three defaults, source='default'."""
    redis = MagicMock()
    redis.get.return_value = None

    selector = _make_selector(redis)
    gex_min, dist_max, conc_min, source = selector._read_butterfly_thresholds()

    assert gex_min == 0.4
    assert dist_max == 0.003
    assert conc_min == 0.25
    assert source == "default"


def test_strategy_selector_fails_open_on_redis_error():
    """Redis.get raises → defaults returned, no exception propagates."""
    redis = MagicMock()
    redis.get.side_effect = RuntimeError("redis down")

    selector = _make_selector(redis)
    gex_min, dist_max, conc_min, source = selector._read_butterfly_thresholds()

    assert gex_min == 0.4
    assert dist_max == 0.003
    assert conc_min == 0.25
    assert source == "default"


# ---------------------------------------------------------------------------
# Defensive: out-of-band Redis values are ignored (ROI guard)
# ---------------------------------------------------------------------------

def test_strategy_selector_rejects_out_of_band_values():
    """
    A garbage value in Redis (e.g. 5.0 for gex_conf) must be discarded
    and fall back to the default — never loosen the gate beyond the
    sane clamp range. Belt-and-braces against a bad write.
    """
    redis = MagicMock()
    redis.get.side_effect = lambda k: {
        "butterfly:threshold:gex_conf": b"5.0",          # way out of range
        "butterfly:threshold:wall_distance": b"0.5",     # way out of range
        "butterfly:threshold:concentration": b"-0.1",    # nonsense
    }.get(k)

    selector = _make_selector(redis)
    gex_min, dist_max, conc_min, source = selector._read_butterfly_thresholds()

    assert gex_min == 0.4
    assert dist_max == 0.003
    assert conc_min == 0.25
    assert source == "default"


# ---------------------------------------------------------------------------
# Writer extension: decision_context captures metrics for butterfly trades
# ---------------------------------------------------------------------------

def test_capture_butterfly_metrics_populates_stash():
    """
    _capture_butterfly_metrics must read gex_conf, dist_pct, and
    wall_concentration from Redis and stash them on the selector so
    select() can spread them into decision_context. Required for 12G
    to have any data to learn from.
    """
    redis = MagicMock()
    redis.get.side_effect = lambda k: {
        "gex:confidence": b"0.55",
        "gex:nearest_wall": b"5200.0",
        "tradier:quotes:SPX": b'{"last": 5210.0}',
        "gex:by_strike": json.dumps({
            "5200": 6000.0,  # top of 10k positive → 60% concentration
            "5195": 2000.0,
            "5205": 2000.0,
        }),
    }.get(k)

    selector = _make_selector(redis)
    selector._capture_butterfly_metrics()

    m = selector._last_butterfly_metrics
    assert m["gex_conf"] == 0.55
    # dist_pct = |5210 - 5200| / 5210 ≈ 0.00192
    assert abs(m["dist_pct"] - (10.0 / 5210.0)) < 1e-9
    # concentration = 6000 / 10000 = 0.6
    assert abs(m["wall_concentration"] - 0.6) < 1e-9


def test_capture_butterfly_metrics_fails_open():
    """Redis.get raises → stash is empty dict, no exception."""
    redis = MagicMock()
    redis.get.side_effect = RuntimeError("redis down")

    selector = _make_selector(redis)
    selector._capture_butterfly_metrics()

    assert selector._last_butterfly_metrics == {}
