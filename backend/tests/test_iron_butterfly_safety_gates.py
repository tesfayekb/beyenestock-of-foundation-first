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


def test_butterfly_blocked_after_315pm(monkeypatch):
    """After 15:15 ET butterfly is forbidden; fallthrough strips it."""
    selector = _make_selector(_pin_day_redis(
        **{"gex:confidence": b"0.8"}
    ))
    _patch_et_time(monkeypatch, 15, 30)

    result = selector._stage1_regime_gate("pin_range", True)

    assert "iron_butterfly" not in result
    assert "iron_condor" in result


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
    """An open iron_butterfly at 60% of max loss must block a new
    iron_butterfly entry. max_loss = abs(entry_credit) * 1.5 * contracts * 100
    matching position_monitor's stop-loss math exactly.

    entry_credit = 1.30, contracts = 2:
        max_profit = 1.30 * 2 * 100   = $260
        max_loss   = max_profit * 1.5 = $390
        block threshold = max_loss * 0.50 = $195
    current_pnl = -240 → abs(240) >= 195 → block.
    """
    from execution_engine import ExecutionEngine

    engine = ExecutionEngine.__new__(ExecutionEngine)
    engine.LEGS_BY_STRATEGY = ExecutionEngine.LEGS_BY_STRATEGY

    existing = [{
        "current_pnl": -240.0,
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
        "is well below the 50% drawdown threshold"
    )
