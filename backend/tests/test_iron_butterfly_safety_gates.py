"""Tests for the iron butterfly safety sprint (Opus 4.7 review 2026-04-20).

Covers the 6 safety gates added after live losses where 3 iron butterflies
stopped out as the GEX wall drifted 80pts intraday:

  1. Butterfly short-circuit gated on regime == "pin_range"
  2. IV/RV threshold raised 1.05 → 1.10 + data-warmth guard (rv >= 5.0)
  3. strategy_failed_today flag blocks same-strategy re-entry same day
  4. GEX wall concentration >= 25% required for butterfly
  5. Time-of-day gate: butterfly only 12:00-15:15 ET
  6. Same-strategy drawdown check in execution_engine.open_virtual_position

When any butterfly safety gate fails (3/4/5), Option B semantics apply:
iron_butterfly is stripped from REGIME_STRATEGY_MAP fallthrough candidates,
but iron_condor and put_credit_spread remain available — we don't block
the whole cycle, just butterfly.
"""
import json
from unittest.mock import MagicMock, patch


# ── shared helpers ────────────────────────────────────────────────────

def _pin_day_redis(**overrides):
    """MagicMock redis client with sane defaults for a clean pin-day
    scenario. Callers override per-test. High concentration (top strike
    holds 50% of positive gamma mass) is the default so the concentration
    gate passes and butterfly can fire."""
    defaults = {
        "strategy:iron_butterfly:enabled": b"true",
        "gex:nearest_wall": b"5200.0",
        "gex:confidence": b"0.5",
        "tradier:quotes:SPX": b'{"last": 5200.0}',
        "gex:by_strike": json.dumps({
            "5200": 5000.0,    # 50% of 10k total positive gamma
            "5195": 2500.0,
            "5205": 2500.0,
        }),
    }
    defaults.update(overrides)
    mock = MagicMock()
    mock.get.side_effect = lambda k: defaults.get(k)
    return mock


def _patch_et_time(monkeypatch, hour: int, minute: int = 0):
    """Freeze datetime.now(ZoneInfo(...)) to a chosen HH:MM ET.

    Because strategy_selector imports datetime inside the function, we
    patch the datetime.datetime class attribute globally for the test.
    Uses a fixed Tuesday (2026-04-21 = weekday) date so the trading
    code's weekday checks don't surprise us."""
    from datetime import datetime as real_dt

    class _FrozenDT(real_dt):
        @classmethod
        def now(cls, tz=None):
            return real_dt(2026, 4, 21, hour, minute, 0, tzinfo=tz)

    import datetime as dt_module
    monkeypatch.setattr(dt_module, "datetime", _FrozenDT)


def _make_selector(redis_client):
    from strategy_selector import StrategySelector
    selector = StrategySelector.__new__(StrategySelector)
    selector.redis_client = redis_client
    return selector


# ── CHANGE 1: regime gate ─────────────────────────────────────────────

def test_butterfly_blocked_when_regime_not_pin_range(monkeypatch):
    """Short-circuit must NOT fire when regime != pin_range, even when
    wall-distance and gex_conf conditions would otherwise qualify."""
    selector = _make_selector(_pin_day_redis(
        **{"gex:confidence": b"0.8"}
    ))
    _patch_et_time(monkeypatch, 13, 0)

    result = selector._stage1_regime_gate("volatile_bearish", True)

    # REGIME_STRATEGY_MAP["volatile_bearish"] = [debit_put_spread, long_put]
    assert "iron_butterfly" not in result
    assert result == ["debit_put_spread", "long_put"]


def test_butterfly_allowed_when_regime_is_pin_range(monkeypatch):
    """Short-circuit fires when regime == pin_range, gex_conf high,
    dist < 0.3%, time within 12:00-15:15, concentration >= 25%."""
    selector = _make_selector(_pin_day_redis(
        **{"gex:confidence": b"0.8"}
    ))
    _patch_et_time(monkeypatch, 13, 0)

    result = selector._stage1_regime_gate("pin_range", True)

    assert result == ["iron_butterfly"]


# ── CHANGE 5: time-of-day gate ────────────────────────────────────────

def test_butterfly_blocked_before_noon(monkeypatch):
    """Before 12:00 ET butterfly is forbidden; fallthrough strips it
    but iron_condor and put_credit_spread remain (Option B)."""
    selector = _make_selector(_pin_day_redis(
        **{"gex:confidence": b"0.8"}
    ))
    _patch_et_time(monkeypatch, 10, 30)

    result = selector._stage1_regime_gate("pin_range", True)

    # pin_range map = [iron_condor, iron_butterfly, put_credit_spread]
    # butterfly stripped, the other two survive
    assert "iron_butterfly" not in result
    assert "iron_condor" in result
    assert "put_credit_spread" in result


def test_butterfly_blocked_after_340pm(monkeypatch):
    """After 15:40 ET butterfly is forbidden; fallthrough strips it.

    Recalibrated in follow-up commit — the original sprint cut at 15:15
    but the 15:15-15:40 window is peak 0DTE theta decay and the highest-EV
    hold when the wall is intact, so the end was pushed to 15:40 (5min
    buffer before the D-010 3:45 PM hard-close backstop). This test
    now verifies blocking resumes just after the new 3:40 boundary."""
    selector = _make_selector(_pin_day_redis(
        **{"gex:confidence": b"0.8"}
    ))
    _patch_et_time(monkeypatch, 15, 45)

    result = selector._stage1_regime_gate("pin_range", True)

    assert "iron_butterfly" not in result
    assert "iron_condor" in result


def test_butterfly_allowed_at_330pm(monkeypatch):
    """15:30 ET is inside the new window (between 15:15 and 15:40) —
    regression guard ensuring the afternoon window expansion actually
    let peak-theta trades through. Prior sprint blocked this."""
    selector = _make_selector(_pin_day_redis(
        **{"gex:confidence": b"0.8"}
    ))
    _patch_et_time(monkeypatch, 15, 30)

    result = selector._stage1_regime_gate("pin_range", True)

    assert result == ["iron_butterfly"]


# ── CHANGE 4: GEX concentration ───────────────────────────────────────

def test_butterfly_blocked_low_gex_concentration(monkeypatch):
    """GEX spread across many strikes (top < 25% of total) = weak pin.
    Butterfly forbidden, iron_condor remains."""
    spread_out = json.dumps({
        # top strike 5200 holds 20% of positive gamma — below threshold
        "5180": 2000.0, "5185": 2000.0, "5190": 2000.0,
        "5200": 2500.0, "5205": 2000.0, "5210": 2000.0,
    })
    selector = _make_selector(_pin_day_redis(
        **{"gex:confidence": b"0.8", "gex:by_strike": spread_out}
    ))
    _patch_et_time(monkeypatch, 13, 0)

    result = selector._stage1_regime_gate("pin_range", True)

    assert "iron_butterfly" not in result
    assert "iron_condor" in result


def test_butterfly_allowed_high_gex_concentration(monkeypatch):
    """Top strike >= 25% of positive gamma mass — real pin. Butterfly fires."""
    concentrated = json.dumps({
        "5200": 7000.0,    # 70% of 10k
        "5195": 1500.0,
        "5205": 1500.0,
    })
    selector = _make_selector(_pin_day_redis(
        **{"gex:confidence": b"0.8", "gex:by_strike": concentrated}
    ))
    _patch_et_time(monkeypatch, 13, 0)

    result = selector._stage1_regime_gate("pin_range", True)

    assert result == ["iron_butterfly"]


# ── CHANGE 3: strategy_failed_today flag ──────────────────────────────

def test_strategy_failed_today_blocks_butterfly(monkeypatch):
    """Once position_monitor sets strategy_failed_today:iron_butterfly:<date>
    butterfly is forbidden for the rest of the day. Other strategies
    still trade."""
    from datetime import date
    today = date.today().isoformat()
    selector = _make_selector(_pin_day_redis(**{
        "gex:confidence": b"0.8",
        f"strategy_failed_today:iron_butterfly:{today}": b"1",
    }))
    _patch_et_time(monkeypatch, 13, 0)

    result = selector._stage1_regime_gate("pin_range", True)

    assert "iron_butterfly" not in result
    assert "iron_condor" in result


# ── CHANGE 2: IV/RV threshold ─────────────────────────────────────────

def test_iv_rv_threshold_blocks_when_vix_cheap():
    """VIX 14 < RV 15 × 1.10 = 16.5 → filter fires. rv >= 5.0 warmth guard passes."""
    from prediction_engine import PredictionEngine
    engine = PredictionEngine.__new__(PredictionEngine)

    def mock_redis(key, default=None):
        return {
            "polygon:vix:current": "14.0",
            "polygon:spx:realized_vol_20d": "15.0",
        }.get(key, default)

    engine.redis_client = None
    with patch.object(engine, "_read_redis", side_effect=mock_redis):
        no_trade, reason = engine._evaluate_no_trade(
            rcs=65.0, cv_stress=20.0, vvix_z=0.5,
            session={"session_status": "active", "consecutive_losses_today": 0},
        )

    assert no_trade is True
    assert "iv_rv_cheap_premium" in (reason or "")


def test_iv_rv_threshold_skips_when_rv_cold():
    """RV 1.29 from intraday 5-min buffer is garbage. Data-warmth guard
    skips the filter so it doesn't produce false-positives against
    obviously-wrong realized vol."""
    from prediction_engine import PredictionEngine
    engine = PredictionEngine.__new__(PredictionEngine)

    def mock_redis(key, default=None):
        return {
            "polygon:vix:current": "14.0",
            "polygon:spx:realized_vol_20d": "1.29",   # intraday garbage
        }.get(key, default)

    engine.redis_client = None
    with patch.object(engine, "_read_redis", side_effect=mock_redis):
        no_trade, reason = engine._evaluate_no_trade(
            rcs=65.0, cv_stress=20.0, vvix_z=0.5,
            session={"session_status": "active", "consecutive_losses_today": 0},
        )

    assert "iv_rv" not in (reason or "")


# ── CHANGE 6: same-strategy drawdown gate ─────────────────────────────

def _fake_exec_client_with_open_positions(open_positions: list):
    """Build a fake supabase client where:
      - .select("id", count="exact")...execute() → count=0 (no cap hit)
      - .select("current_pnl, entry_credit, contracts")...execute()
          → data = open_positions (for the drawdown check)
    Returns a MagicMock wired to dispatch both call shapes.
    """
    fake_client = MagicMock()
    fake_table = MagicMock()
    fake_client.table.return_value = fake_table

    # The drawdown query ends with .execute() returning .data = open_positions
    # The MAX_OPEN_POSITIONS query ends with .execute() returning .count = 0
    # We can't easily distinguish by selector arguments without deep
    # chain replay, so we make both paths return a response whose
    # .count = 0 AND .data = open_positions. That satisfies both.
    fake_execute_response = MagicMock()
    fake_execute_response.count = 0
    fake_execute_response.data = open_positions

    # Wire fake_table.select(...).eq(...).eq(...).in_(...).execute() etc.
    fake_table.select.return_value = fake_table
    fake_table.eq.return_value = fake_table
    fake_table.in_.return_value = fake_table
    fake_table.execute.return_value = fake_execute_response

    # insert() must still work for the actual position creation path
    fake_table.insert.return_value.execute.return_value = MagicMock(
        data=[{"id": "new-pos"}]
    )
    return fake_client


def test_same_strategy_drawdown_blocks_entry():
    """An open iron_butterfly at >= 75% of max loss must block a new
    iron_butterfly entry. max_loss = abs(entry_credit) * 1.5 * contracts * 100
    matching position_monitor's stop-loss math exactly.

    Recalibrated in follow-up commit — threshold 0.50 was too aggressive
    (a position still has 50% of stop-loss distance remaining and may be
    recovering); 0.75 flags positions that are genuinely about to stop out.

    entry_credit = 1.30, contracts = 2:
        max_profit = 1.30 * 2 * 100   = $260
        max_loss   = max_profit * 1.5 = $390
        block threshold = max_loss * 0.75 = $292.50
    current_pnl = -300 → abs(300) >= 292.50 → block.
    """
    from execution_engine import ExecutionEngine

    engine = ExecutionEngine.__new__(ExecutionEngine)
    engine.LEGS_BY_STRATEGY = ExecutionEngine.LEGS_BY_STRATEGY

    existing = [{
        "current_pnl": -300.0,
        "entry_credit": 1.30,
        "contracts": 2,
    }]

    fake_client = _fake_exec_client_with_open_positions(existing)
    fake_session = {
        "id": "sess-1",
        "session_status": "active",
        "virtual_trades_count": 0,
    }

    with patch("execution_engine.get_client", return_value=fake_client), \
            patch("execution_engine.get_today_session",
                  return_value=fake_session), \
            patch("execution_engine.update_session"), \
            patch("execution_engine.write_audit_log"), \
            patch("execution_engine.write_health_status"):
        result = engine.open_virtual_position(
            signal={
                "session_id": "sess-1",
                "strategy_type": "iron_butterfly",
                "target_credit": 1.40,
                "contracts": 2,
                "short_strike": 5200.0,
                "expiry_date": "2026-04-21",
            },
            prediction={"spx_price": 5200.0},
        )

    assert result is None, (
        "open_virtual_position must block when an existing same-strategy "
        "position is >= 50% of its max loss"
    )


def test_same_strategy_drawdown_allows_entry():
    """An open iron_butterfly at 30% of max loss should NOT block.
    entry 1.30 * 2 contracts * 100 = $260 max_profit → $390 max_loss
    → threshold $195. current_pnl = -100 → abs(100) < 195 → allow."""
    from execution_engine import ExecutionEngine

    engine = ExecutionEngine.__new__(ExecutionEngine)
    engine.LEGS_BY_STRATEGY = ExecutionEngine.LEGS_BY_STRATEGY

    existing = [{
        "current_pnl": -100.0,
        "entry_credit": 1.30,
        "contracts": 2,
    }]

    fake_client = _fake_exec_client_with_open_positions(existing)
    fake_session = {
        "id": "sess-1",
        "session_status": "active",
        "virtual_trades_count": 0,
    }

    with patch("execution_engine.get_client", return_value=fake_client), \
            patch("execution_engine.get_today_session",
                  return_value=fake_session), \
            patch("execution_engine.update_session"), \
            patch("execution_engine.write_audit_log"), \
            patch("execution_engine.write_health_status"):
        result = engine.open_virtual_position(
            signal={
                "session_id": "sess-1",
                "strategy_type": "iron_butterfly",
                "target_credit": 1.40,
                "contracts": 2,
                "short_strike": 5200.0,
                "expiry_date": "2026-04-21",
            },
            prediction={"spx_price": 5200.0},
        )

    assert result is not None, (
        "open_virtual_position should NOT block when existing position "
        "is well below the 75% drawdown threshold"
    )


# ── CHANGE 3 writer recalibration: flag is butterfly-only, 2h TTL ────

def _losing_credit_position(strategy: str, pos_id: str = "pos-1") -> dict:
    """Shape a losing credit position that will trigger the 150% stop.
      entry_credit=1.00, contracts=1  → max_profit=$100, max_loss=-$150
      current_pnl=-200                 → past the stop
    """
    return {
        "id": pos_id,
        "strategy_type": strategy,
        "position_type": "credit",
        "status": "open",
        "entry_at": "2026-04-21T14:00:00Z",
        "entry_credit": 1.00,
        "contracts": 1,
        "session_id": "sess-1",
        "current_pnl": -200.0,
        "current_cv_stress": 0.0,
        "partial_exit_done": False,
    }


def _run_monitor_with_position(pos: dict):
    """Run position_monitor.run_position_monitor with a single mocked
    open position and return (mock_redis, mock_engine) for assertion."""
    import position_monitor as pm

    mock_engine = MagicMock()
    mock_engine.close_virtual_position.return_value = True

    mock_redis = MagicMock()

    with patch("position_monitor.get_open_positions", return_value=[pos]), \
            patch("position_monitor._get_engine", return_value=mock_engine), \
            patch("position_monitor._get_redis", return_value=mock_redis), \
            patch("position_monitor.write_health_status"):
        pm.run_position_monitor()

    return mock_redis, mock_engine


def test_strategy_failed_flag_only_written_for_butterfly():
    """iron_condor stop-out must NOT write strategy_failed_today.

    The reader in strategy_selector only checks
    strategy_failed_today:iron_butterfly:<date>, so writing the flag for
    other credit strategies wastes Redis writes and muddies observability.
    """
    mock_redis, mock_engine = _run_monitor_with_position(
        _losing_credit_position("iron_condor")
    )

    # The stop-loss must have fired (sanity check — if not, the test is
    # not actually exercising the flag-write branch).
    mock_engine.close_virtual_position.assert_called_once()
    kwargs = mock_engine.close_virtual_position.call_args.kwargs
    assert kwargs["exit_reason"] == "stop_loss_150pct_credit"

    flag_writes = [
        c for c in mock_redis.setex.call_args_list
        if c.args and str(c.args[0]).startswith("strategy_failed_today:")
    ]
    assert flag_writes == [], (
        f"iron_condor stop-out must NOT write strategy_failed_today flag; "
        f"got: {flag_writes}"
    )


def test_strategy_failed_flag_2h_ttl():
    """iron_butterfly stop-out writes the flag with 2-hour TTL (7200s).

    Recalibrated in follow-up commit — original sprint used an 8h TTL
    which turned a single stop-out into a full-day lockout. 2h lets the
    afternoon pin re-open butterfly after a morning noise stop-out.
    """
    from datetime import date

    mock_redis, mock_engine = _run_monitor_with_position(
        _losing_credit_position("iron_butterfly")
    )

    mock_engine.close_virtual_position.assert_called_once()
    kwargs = mock_engine.close_virtual_position.call_args.kwargs
    assert kwargs["exit_reason"] == "stop_loss_150pct_credit"

    flag_writes = [
        c for c in mock_redis.setex.call_args_list
        if c.args and str(c.args[0]).startswith("strategy_failed_today:")
    ]
    assert len(flag_writes) == 1, (
        f"expected exactly 1 strategy_failed_today flag write, "
        f"got {len(flag_writes)}: {flag_writes}"
    )

    key, ttl, value = flag_writes[0].args
    today = date.today().isoformat()
    assert key == f"strategy_failed_today:iron_butterfly:{today}"
    assert ttl == 7200, (
        f"expected 2h TTL (7200s), got {ttl}s — recalibration regressed"
    )
    assert value == "1"


# ── AI hint override failed-today guard ───────────────────────────────
# Mirrors the butterfly_forbidden gate in _stage1_regime_gate for the
# AI hint selection path. Without this, strategy:ai_hint_override would
# silently revive iron_butterfly after a 150% stop-out, defeating the
# whole safety sprint. The fallback is ordered[0] — trading still
# happens, just with the regime-preferred strategy.

def _stub_select_dependencies(
    monkeypatch, selector, ordered_list, hint_flag_on=True
):
    """Stub select()'s inner stages so the AI hint override block is
    the only non-trivial logic under test. Downstream get_strikes()
    is made to raise so select() returns None — we assert on
    captured logger.info calls, which have already fired by that
    point.
    """
    import strategy_selector as ss_mod

    monkeypatch.setattr(
        selector, "_check_feature_flag",
        lambda key, default=False: (
            hint_flag_on
            if key == "strategy:ai_hint_override:enabled"
            else default
        ),
    )
    monkeypatch.setattr(
        selector, "_stage0_time_gate",
        lambda cv_stress: (True, "ok"),
    )
    monkeypatch.setattr(
        selector, "_stage1_regime_gate",
        lambda regime, time_gate: list(ordered_list),
    )
    monkeypatch.setattr(
        selector, "_stage2_direction_filter",
        lambda c, d, pb, pe: list(ordered_list),
    )
    monkeypatch.setattr(
        ss_mod, "check_trade_frequency",
        lambda trades, regime: (True, "ok"),
    )

    def _raise(*a, **k):
        raise RuntimeError("stub: stop select() after AI hint block")
    monkeypatch.setattr(ss_mod, "get_strikes", _raise)

    info_calls: list = []
    monkeypatch.setattr(
        ss_mod.logger, "info",
        lambda event, **kwargs: info_calls.append((event, kwargs)),
    )
    monkeypatch.setattr(ss_mod.logger, "warning", lambda *a, **k: None)
    monkeypatch.setattr(ss_mod.logger, "error", lambda *a, **k: None)
    monkeypatch.setattr(ss_mod.logger, "debug", lambda *a, **k: None)
    return info_calls


def _hint_prediction(hint="iron_butterfly", confidence=0.80):
    return {
        "regime": "pin_range",
        "direction": "neutral",
        "p_bull": 0.33,
        "p_bear": 0.33,
        "cv_stress_score": 0.0,
        "rcs": 50.0,
        "regime_agreement": True,
        "strategy_hint": hint,
        "confidence": confidence,
    }


def _hint_session():
    return {
        "id": "test",
        "virtual_trades_count": 0,
        "consecutive_losses_today": 0,
        "session_status": "active",
    }


def test_ai_hint_blocked_when_strategy_failed_today(monkeypatch):
    """When Redis has strategy_failed_today:iron_butterfly:<today>, an
    AI hint of iron_butterfly must fall back to ordered[0] (regime-
    based top pick, e.g. iron_condor). Trading is NOT skipped — the
    regime pick still goes through. Mirrors CHANGE 3 from the safety
    sprint for the AI hint selection path."""
    from datetime import date
    from strategy_selector import StrategySelector

    today = date.today().isoformat()
    failed_key = f"strategy_failed_today:iron_butterfly:{today}"

    def _redis_get(key):
        if key == "strategy:ai_hint_override:enabled":
            return b"true"
        if key == failed_key:
            return b"1"
        return None

    mock_redis = MagicMock()
    mock_redis.get.side_effect = _redis_get

    selector = StrategySelector.__new__(StrategySelector)
    selector.redis_client = mock_redis

    info_calls = _stub_select_dependencies(
        monkeypatch, selector,
        ordered_list=["iron_condor", "iron_butterfly"],
    )

    selector.select(_hint_prediction(), _hint_session())

    # The AI hint initially wins (strategy_from_ai_hint logged)...
    chosen = [c for c in info_calls if c[0] == "strategy_from_ai_hint"]
    assert len(chosen) == 1, (
        "AI hint must be selected before the failed-today check fires"
    )
    assert chosen[0][1]["hint"] == "iron_butterfly"

    # ...then the new guard reverts strategy_type to ordered[0].
    blocked = [c for c in info_calls if c[0] == "ai_hint_blocked_failed_today"]
    assert len(blocked) == 1, (
        f"expected one ai_hint_blocked_failed_today log, "
        f"got {[c[0] for c in info_calls]}"
    )
    assert blocked[0][1]["strategy"] == "iron_butterfly"
    assert blocked[0][1]["fallback"] == "iron_condor", (
        "fallback must be ordered[0] so trading continues — "
        "no trade should be skipped entirely"
    )
    assert blocked[0][1]["date"] == today


def test_ai_hint_allowed_when_no_failed_flag(monkeypatch):
    """Clean Redis (no failed-today flag) → AI hint of iron_butterfly
    proceeds untouched. The new guard is a no-op when the strategy
    has not stop-outted today."""
    from strategy_selector import StrategySelector

    def _redis_get(key):
        if key == "strategy:ai_hint_override:enabled":
            return b"true"
        return None  # no failed_today flag

    mock_redis = MagicMock()
    mock_redis.get.side_effect = _redis_get

    selector = StrategySelector.__new__(StrategySelector)
    selector.redis_client = mock_redis

    info_calls = _stub_select_dependencies(
        monkeypatch, selector,
        ordered_list=["iron_condor", "iron_butterfly"],
    )

    selector.select(_hint_prediction(), _hint_session())

    chosen = [c for c in info_calls if c[0] == "strategy_from_ai_hint"]
    assert len(chosen) == 1
    assert chosen[0][1]["hint"] == "iron_butterfly"

    # The new guard must NOT fire when no flag is set.
    blocked = [c for c in info_calls if c[0] == "ai_hint_blocked_failed_today"]
    assert blocked == [], (
        f"guard must be a no-op without the failed-today flag; "
        f"got {blocked}"
    )


def test_ai_hint_fail_open_when_redis_unavailable(monkeypatch):
    """If redis_client.get() raises during the failed-today check, the
    AI hint must proceed normally (fail-open). This preserves ROI
    during Redis outages: the hint still wins, no exception bubbles
    up to callers. Matches the try/except pass pattern used by every
    other butterfly safety gate."""
    from strategy_selector import StrategySelector

    class _FlakyRedis:
        def __init__(self):
            self._calls = 0

        def get(self, key):
            # First call (feature flag) succeeds; subsequent calls
            # (the failed-today check) raise to simulate a mid-cycle
            # Redis outage.
            self._calls += 1
            if key == "strategy:ai_hint_override:enabled":
                return b"true"
            raise ConnectionError("simulated Redis outage")

    selector = StrategySelector.__new__(StrategySelector)
    selector.redis_client = _FlakyRedis()

    info_calls = _stub_select_dependencies(
        monkeypatch, selector,
        ordered_list=["iron_condor", "iron_butterfly"],
    )

    # Must NOT raise — the inner try/except swallows the Redis error.
    selector.select(_hint_prediction(), _hint_session())

    # AI hint still selected; guard silently skipped.
    chosen = [c for c in info_calls if c[0] == "strategy_from_ai_hint"]
    assert len(chosen) == 1, (
        "AI hint selection must survive Redis errors (fail-open)"
    )
    blocked = [c for c in info_calls if c[0] == "ai_hint_blocked_failed_today"]
    assert blocked == [], (
        "Redis error must not trigger the block log — fail-open means "
        "the hint proceeds unblocked"
    )


# ── 12B: butterfly gate instrumentation counters ──────────────────────
# Pure observability — every gate outcome must increment a Redis counter
# keyed by reason (or "allowed") with a 7-day TTL. These tests lock in:
#   * correct key format `butterfly:blocked:{reason}:{YYYY-MM-DD}`
#   * incr + expire call pair (counter + TTL refresh)
#   * fail-open semantics when Redis is unavailable (no trading impact)

def _instrumentation_redis(**extra_get_values):
    """Mock redis that tracks incr/expire calls while serving configurable
    get() responses for the surrounding gate logic. Separate from
    _pin_day_redis because the instrumentation tests care about
    side_effect record-keeping, not the pin-day fixture values."""
    mock = MagicMock()
    base = {
        "strategy:iron_butterfly:enabled": b"true",
        "gex:nearest_wall": b"5200.0",
        "gex:confidence": b"0.5",
        "tradier:quotes:SPX": b'{"last": 5200.0}',
        "gex:by_strike": json.dumps({
            "5200": 5000.0,
            "5195": 2500.0,
            "5205": 2500.0,
        }),
    }
    base.update(extra_get_values)
    mock.get.side_effect = lambda k: base.get(k)
    return mock


def test_butterfly_counter_incremented_on_block(monkeypatch):
    """A blocked cycle (here: regime_mismatch — regime != pin_range) must
    increment `butterfly:blocked:regime_mismatch:{today}` with a 7-day
    TTL. This is the empirical data stream that feeds 12G threshold
    tuning — any regression would blind the recalibration pipeline."""
    from datetime import date

    mock_redis = _instrumentation_redis()
    selector = _make_selector(mock_redis)
    # Freeze to a pin-window time so the TIME gate is NOT the reason —
    # we want the regime_mismatch counter to fire cleanly.
    _patch_et_time(monkeypatch, 13, 0)

    selector._stage1_regime_gate("volatile_bearish", True)

    today = date.today().isoformat()
    expected_key = f"butterfly:blocked:regime_mismatch:{today}"

    incr_calls = [
        c for c in mock_redis.incr.call_args_list
        if c.args and c.args[0] == expected_key
    ]
    assert len(incr_calls) == 1, (
        f"expected exactly one incr on {expected_key}, "
        f"got {mock_redis.incr.call_args_list}"
    )

    # Expire must be called on the same key with 7-day TTL (86400 * 7).
    expire_calls = [
        c for c in mock_redis.expire.call_args_list
        if c.args and c.args[0] == expected_key
    ]
    assert len(expire_calls) == 1
    assert expire_calls[0].args[1] == 86400 * 7, (
        f"expected 7-day TTL, got {expire_calls[0].args[1]}s"
    )

    # And the "allowed" counter must NOT fire on the same cycle.
    allowed_key = f"butterfly:allowed:{today}"
    assert not any(
        c.args and c.args[0] == allowed_key
        for c in mock_redis.incr.call_args_list
    ), "allowed counter must not fire on a blocked cycle"


def test_butterfly_counter_incremented_on_allow(monkeypatch):
    """A clean pin-day cycle (all gates pass, regime == pin_range) must
    increment `butterfly:allowed:{today}` — NOT a blocked counter. This
    is the denominator for gate-effectiveness ratios in 12G."""
    from datetime import date

    mock_redis = _instrumentation_redis(
        **{"gex:confidence": b"0.8"}  # ensures pin-override can fire
    )
    selector = _make_selector(mock_redis)
    _patch_et_time(monkeypatch, 13, 0)

    selector._stage1_regime_gate("pin_range", True)

    today = date.today().isoformat()
    allowed_key = f"butterfly:allowed:{today}"

    incr_calls = [
        c for c in mock_redis.incr.call_args_list
        if c.args and c.args[0] == allowed_key
    ]
    assert len(incr_calls) == 1, (
        f"expected exactly one incr on {allowed_key}, "
        f"got incr calls={mock_redis.incr.call_args_list}"
    )

    expire_calls = [
        c for c in mock_redis.expire.call_args_list
        if c.args and c.args[0] == allowed_key
    ]
    assert len(expire_calls) == 1
    assert expire_calls[0].args[1] == 86400 * 7

    # No blocked counter should fire on the allowed path.
    blocked_calls = [
        c for c in mock_redis.incr.call_args_list
        if c.args and str(c.args[0]).startswith("butterfly:blocked:")
    ]
    assert blocked_calls == [], (
        f"no blocked counter must fire on an allowed cycle; "
        f"got {blocked_calls}"
    )


def test_butterfly_counter_fail_open(monkeypatch):
    """Redis incr/expire raising must NOT affect gate logic or bubble up.
    Instrumentation is strictly advisory — every counter call is inside
    a try/except pass. Regression here would mean a Redis outage could
    crash strategy selection."""
    mock_redis = _instrumentation_redis()
    mock_redis.incr.side_effect = ConnectionError("simulated Redis outage")
    mock_redis.expire.side_effect = ConnectionError("simulated Redis outage")

    selector = _make_selector(mock_redis)
    _patch_et_time(monkeypatch, 13, 0)

    # Must not raise, despite Redis incr/expire blowing up.
    result = selector._stage1_regime_gate("volatile_bearish", True)

    # Gate logic unchanged — regime map for volatile_bearish still wins.
    assert result == ["debit_put_spread", "long_put"], (
        "instrumentation failure must not distort gate output"
    )
