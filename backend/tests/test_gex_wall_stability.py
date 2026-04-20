"""12C: GEX wall stability (30-minute rolling check).

2026-04-20 root cause: the GEX wall moved 7115 → 7195 (80pts, 1.1% at
SPX ≈ 7130) over the course of the session while the system kept
opening iron butterflies on the stale level. This gate reads the last
30 minutes of wall history and blocks butterfly when the max-min range
exceeds 0.5% of SPX — the pin is breaking.

Option B semantics: butterfly is stripped from candidates; iron_condor
and put_credit_spread remain available via REGIME_STRATEGY_MAP.
No trade is skipped entirely.

Two test groups:
  1. gex_engine._append_wall_history writer behaviour (tests 1-3)
  2. strategy_selector._stage1_regime_gate reader behaviour (tests 4-8)
"""
import json
import os
import sys
import time
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── Writer tests (gex_engine) ─────────────────────────────────────────

def _make_gex_engine(initial_history=None):
    """Build a GexEngine with mock Redis, bypassing __init__ so we
    don't need a live Redis URL. Seeds gex:wall_history if provided."""
    from gex_engine import GexEngine

    engine = GexEngine.__new__(GexEngine)
    mock_redis = MagicMock()

    store = {}
    if initial_history is not None:
        store["gex:wall_history"] = json.dumps(initial_history)

    def _get(key):
        return store.get(key)

    def _setex(key, ttl, value):
        store[key] = value
        return True

    mock_redis.get.side_effect = _get
    mock_redis.setex.side_effect = _setex
    engine.redis_client = mock_redis
    return engine, mock_redis, store


def test_wall_history_written_on_gex_compute():
    """After compute_gex() runs the writer helper, gex:wall_history
    must hold at least one entry with ts + wall fields."""
    engine, mock_redis, store = _make_gex_engine()

    engine._append_wall_history(7150.0)

    assert "gex:wall_history" in store, (
        "gex:wall_history must be written on every wall compute"
    )
    history = json.loads(store["gex:wall_history"])
    assert len(history) == 1
    assert history[0]["wall"] == 7150.0
    assert "ts" in history[0]
    assert isinstance(history[0]["ts"], (int, float))

    # TTL must be 1 hour (3600s) — setex args = (key, ttl, value)
    setex_call = mock_redis.setex.call_args_list[0]
    assert setex_call.args[0] == "gex:wall_history"
    assert setex_call.args[1] == 3600


def test_wall_history_pruned_to_30_minutes():
    """Entries with ts older than 1800s must be dropped on each append.
    Locks in the rolling-window behaviour — without pruning the key
    would grow unbounded and old pins would skew the range check."""
    now = time.time()
    old_entries = [
        {"ts": now - 2000, "wall": 7100.0},   # > 30 min → drop
        {"ts": now - 1900, "wall": 7110.0},   # > 30 min → drop
        {"ts": now - 1000, "wall": 7150.0},   # < 30 min → keep
    ]
    engine, _, store = _make_gex_engine(initial_history=old_entries)

    engine._append_wall_history(7160.0)

    history = json.loads(store["gex:wall_history"])
    # Keep the one recent entry + the new one = 2.
    assert len(history) == 2, (
        f"expected 2 entries after pruning, got {len(history)}: {history}"
    )
    walls = [h["wall"] for h in history]
    assert 7150.0 in walls
    assert 7160.0 in walls
    assert 7100.0 not in walls
    assert 7110.0 not in walls


def test_wall_history_max_age_respected():
    """All entries within the 30-min window must be kept — the prune
    must not accidentally drop fresh samples. Separately validates
    the lower bound of pruning (1800s exclusive)."""
    now = time.time()
    fresh_entries = [
        {"ts": now - 1700, "wall": 7100.0},   # < 30 min → keep
        {"ts": now - 900, "wall": 7105.0},    # < 30 min → keep
        {"ts": now - 300, "wall": 7110.0},    # < 30 min → keep
    ]
    engine, _, store = _make_gex_engine(initial_history=fresh_entries)

    engine._append_wall_history(7115.0)

    history = json.loads(store["gex:wall_history"])
    assert len(history) == 4, (
        f"all fresh entries + new one must be kept; got {len(history)}"
    )
    walls = sorted(h["wall"] for h in history)
    assert walls == [7100.0, 7105.0, 7110.0, 7115.0]


# ── Reader tests (strategy_selector) ──────────────────────────────────

def _make_selector_with_wall_history(history_entries, spx_price=7100.0):
    """Build a StrategySelector with mock Redis wired to:
      * serve gex:wall_history from the provided entries
      * serve tradier:quotes:SPX for _get_spx_price()
      * allow butterfly gate to pass the other gates (feature flag,
        concentration, nearest_wall, confidence)
    """
    from strategy_selector import StrategySelector

    selector = StrategySelector.__new__(StrategySelector)

    # Default fixture values so only wall_history drives the outcome.
    redis_store = {
        "strategy:iron_butterfly:enabled": "true",
        "gex:nearest_wall": str(spx_price),
        "gex:confidence": "0.8",
        "tradier:quotes:SPX": json.dumps({"last": spx_price}),
        "gex:by_strike": json.dumps({
            str(spx_price): 5000.0,
            str(spx_price - 5): 2500.0,
            str(spx_price + 5): 2500.0,
        }),
        "gex:wall_history": json.dumps(history_entries),
    }

    mock_redis = MagicMock()

    def _get(key):
        return redis_store.get(key)

    mock_redis.get.side_effect = _get
    selector.redis_client = mock_redis
    return selector, mock_redis


def _patch_et_13(monkeypatch):
    """Freeze ET to 13:00 so the time gate (12:00-15:40) always passes."""
    from datetime import datetime as real_dt

    class _FrozenDT(real_dt):
        @classmethod
        def now(cls, tz=None):
            return real_dt(2026, 4, 21, 13, 0, 0, tzinfo=tz)

    import datetime as dt_module
    monkeypatch.setattr(dt_module, "datetime", _FrozenDT)


def test_butterfly_blocked_when_wall_moved_35_points(monkeypatch):
    """Wall history 7100 → 7150 = 50pt range over 20 min.
    50 / 7100 = 0.704% > 0.5% threshold → butterfly forbidden.
    iron_butterfly must be stripped from candidates; iron_condor
    remains (Option B)."""
    _patch_et_13(monkeypatch)

    now = time.time()
    history = [
        {"ts": now - 1200, "wall": 7100.0},
        {"ts": now - 900,  "wall": 7115.0},
        {"ts": now - 600,  "wall": 7135.0},
        {"ts": now - 300,  "wall": 7150.0},
    ]
    selector, _ = _make_selector_with_wall_history(history, spx_price=7100.0)

    result = selector._stage1_regime_gate("pin_range", True)

    assert "iron_butterfly" not in result, (
        "wall drifted 50pt (0.7%) — butterfly must be stripped"
    )
    assert "iron_condor" in result, (
        "Option B: iron_condor must remain when butterfly is forbidden"
    )


def test_butterfly_allowed_when_wall_stable(monkeypatch):
    """Wall history all within 7120-7125 range = 5pt / 7120 ≈ 0.07%.
    Well under 0.5% threshold → butterfly remains in candidates.
    Since all other gates pass on a clean pin day with feature flag
    ON, the short-circuit fires and returns [iron_butterfly]."""
    _patch_et_13(monkeypatch)

    now = time.time()
    history = [
        {"ts": now - 1200, "wall": 7120.0},
        {"ts": now - 900,  "wall": 7122.0},
        {"ts": now - 600,  "wall": 7124.0},
        {"ts": now - 300,  "wall": 7125.0},
    ]
    # spx_price matches nearest_wall fixture — pin criteria satisfied.
    selector, _ = _make_selector_with_wall_history(history, spx_price=7120.0)

    result = selector._stage1_regime_gate("pin_range", True)

    assert result == ["iron_butterfly"], (
        f"stable wall + clean pin day must short-circuit to butterfly; "
        f"got {result}"
    )


def test_butterfly_skips_gate_when_fewer_than_4_samples(monkeypatch):
    """Only 3 history entries → gate is skipped entirely, regardless
    of the range. This protects the first ~20 min of each session
    while gex_engine is warming the history list."""
    _patch_et_13(monkeypatch)

    now = time.time()
    # Only 3 entries with a wild 100-point range that WOULD block
    # butterfly if the gate activated. Proof the gate self-gates.
    history = [
        {"ts": now - 900, "wall": 7100.0},
        {"ts": now - 600, "wall": 7200.0},
        {"ts": now - 300, "wall": 7150.0},
    ]
    selector, _ = _make_selector_with_wall_history(history, spx_price=7100.0)

    result = selector._stage1_regime_gate("pin_range", True)

    # Butterfly must still short-circuit — wall gate hasn't activated.
    assert result == ["iron_butterfly"], (
        f"gate must self-gate below 4 samples; got {result}"
    )


def test_butterfly_fail_open_on_redis_error(monkeypatch):
    """redis.get('gex:wall_history') raising → the gate must silently
    skip and leave butterfly_forbidden=False. Instrumentation failure
    must never block trading or crash the selector."""
    from strategy_selector import StrategySelector
    _patch_et_13(monkeypatch)

    selector = StrategySelector.__new__(StrategySelector)

    class _FlakyRedis:
        def get(self, key):
            if key == "gex:wall_history":
                raise ConnectionError("simulated Redis outage")
            # Serve the other gates' keys with sane pin-day values.
            return {
                "strategy:iron_butterfly:enabled": "true",
                "gex:nearest_wall": "7100.0",
                "gex:confidence": "0.8",
                "tradier:quotes:SPX": json.dumps({"last": 7100.0}),
                "gex:by_strike": json.dumps({
                    "7100": 5000.0, "7095": 2500.0, "7105": 2500.0,
                }),
            }.get(key)

    selector.redis_client = _FlakyRedis()

    # Must NOT raise, even though wall_history read blows up.
    result = selector._stage1_regime_gate("pin_range", True)

    # Butterfly still fires because the other gates all pass and
    # wall_unstable silently skipped.
    assert result == ["iron_butterfly"], (
        f"fail-open: Redis error must not block butterfly; got {result}"
    )


def test_wall_stability_counter_incremented(monkeypatch):
    """When wall_unstable fires, the 12B counter key
    butterfly:blocked:wall_unstable:{today} must be incremented with
    the standard 7-day TTL. Validates the integration between 12C's
    block reason and 12B's shared counter infrastructure — no double
    counting, no missing counter."""
    from datetime import date
    _patch_et_13(monkeypatch)

    now = time.time()
    # Same unstable history as the blocked test above.
    history = [
        {"ts": now - 1200, "wall": 7100.0},
        {"ts": now - 900,  "wall": 7115.0},
        {"ts": now - 600,  "wall": 7135.0},
        {"ts": now - 300,  "wall": 7150.0},
    ]
    selector, mock_redis = _make_selector_with_wall_history(
        history, spx_price=7100.0
    )

    selector._stage1_regime_gate("pin_range", True)

    today = date.today().isoformat()
    expected_key = f"butterfly:blocked:wall_unstable:{today}"

    incr_calls = [
        c for c in mock_redis.incr.call_args_list
        if c.args and c.args[0] == expected_key
    ]
    assert len(incr_calls) == 1, (
        f"expected exactly one incr on {expected_key}, "
        f"got {mock_redis.incr.call_args_list}"
    )

    expire_calls = [
        c for c in mock_redis.expire.call_args_list
        if c.args and c.args[0] == expected_key
    ]
    assert len(expire_calls) == 1
    assert expire_calls[0].args[1] == 86400 * 7, (
        f"wall_unstable counter must use 7-day TTL; "
        f"got {expire_calls[0].args[1]}s"
    )
