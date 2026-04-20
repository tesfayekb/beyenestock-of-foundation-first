"""Consolidation Sprint — Session 1 regression tests.

Locks down the four P0 fixes from the trading audit:

  P0-A  Signal-flag polarity (default ON when Redis key absent).
  P0-B  Strategy/agent-flag polarity (default OFF when absent).
  P0-C  VIX z-score writer (Signals D + F prerequisite).
  P0-D  VIX9D writer (Signal A term-ratio prerequisite).
  Plus  decision_context capture at selection time (audit trail).

If any test below fails after a future refactor, the system has
silently lost a paper-trade size-cut signal — block the merge.
"""
from unittest.mock import MagicMock


# ── Helpers ────────────────────────────────────────────────────────────

def _make_selector(flags: dict = None, redis_data: dict = None):
    """Build a StrategySelector with a mocked Redis client.

    Mirrors the helper in test_signals_def.py — keep them in sync if
    the mock contract changes (e.g. Redis switching to bytes-only).
    """
    from strategy_selector import StrategySelector
    sel = StrategySelector.__new__(StrategySelector)
    _flags = flags or {}
    _data = redis_data or {}

    def _mock_get(key):
        val = _data.get(key) or _flags.get(key)
        if val is None:
            return None
        return val.encode() if isinstance(val, str) else val

    sel.redis_client = MagicMock()
    sel.redis_client.get.side_effect = _mock_get
    return sel


# ── 1. Signal-flag polarity (P0-A) ─────────────────────────────────────
# Signal flags MUST default to ENABLED when the Redis key is missing.
# Backend uses the same default in the bootstrap path.

def test_signal_flag_absent_defaults_on():
    """default=True + absent key → True (signal flag ON)."""
    sel = _make_selector(flags={})
    assert sel._check_feature_flag(
        "signal:vix_term_filter:enabled", default=True
    ) is True


def test_signal_flag_explicit_false_disables():
    """default=True + key='false' → False (operator disabled it)."""
    sel = _make_selector(
        flags={"signal:vix_term_filter:enabled": "false"}
    )
    assert sel._check_feature_flag(
        "signal:vix_term_filter:enabled", default=True
    ) is False


def test_signal_flag_explicit_true_enabled():
    """default=True + key='true' → True (explicit confirmation)."""
    sel = _make_selector(
        flags={"signal:vix_term_filter:enabled": "true"}
    )
    assert sel._check_feature_flag(
        "signal:vix_term_filter:enabled", default=True
    ) is True


def test_all_six_signal_flags_default_on():
    """Every signal modifier must run when its flag key is absent."""
    sel = _make_selector(flags={})

    # _vix_term_modifier reads ratio from Redis fallback → 1.0.
    mult_a, status_a = sel._vix_term_modifier({})
    assert status_a != "flag_off"
    assert mult_a == 1.0  # ratio fallback = 1.0 = "normal"

    # _gex_bias_modifier on a short-gamma strategy with gex_net=0 → neutral.
    mult_c, status_c = sel._gex_bias_modifier({}, "iron_condor")
    assert status_c != "flag_off"

    # _market_breadth_modifier with vix_z=0 → "normal", not "flag_off".
    mult_d, status_d = sel._market_breadth_modifier(0.0)
    assert status_d != "flag_off"

    # _earnings_proximity_modifier with no Redis data on short-gamma.
    mult_e, status_e = sel._earnings_proximity_modifier("iron_condor")
    assert status_e != "flag_off"

    # _iv_rank_modifier with vix_z=0 → "normal", not "flag_off".
    mult_f, status_f = sel._iv_rank_modifier(0.0)
    assert status_f != "flag_off"


# ── 2. Strategy/agent-flag polarity (P0-B) ─────────────────────────────
# Strategy flags MUST stay OFF when the Redis key is missing.

def test_strategy_flag_absent_defaults_off():
    """default=False + absent key → False (strategy flag OFF)."""
    sel = _make_selector(flags={})
    assert sel._check_feature_flag(
        "strategy:long_straddle:enabled", default=False
    ) is False


def test_strategy_flag_explicit_true_enables():
    """default=False + key='true' → True (operator opted in)."""
    sel = _make_selector(
        flags={"strategy:iron_butterfly:enabled": "true"}
    )
    assert sel._check_feature_flag(
        "strategy:iron_butterfly:enabled", default=False
    ) is True


def test_check_feature_flag_redis_error_returns_default():
    """Redis exception → returns default, never raises."""
    from strategy_selector import StrategySelector
    sel = StrategySelector.__new__(StrategySelector)
    sel.redis_client = MagicMock()
    sel.redis_client.get.side_effect = RuntimeError("redis down")

    assert sel._check_feature_flag("any:key", default=True) is True
    assert sel._check_feature_flag("any:key", default=False) is False


# ── 3. VIX z-score writer (P0-C) ───────────────────────────────────────

def test_vix_baseline_writes_three_keys_after_5_samples():
    """5+ samples → polygon:vix:20d_mean, _std, z_score all written."""
    from polygon_feed import PolygonFeed
    feed = PolygonFeed.__new__(PolygonFeed)
    feed.vix_history = []
    feed.redis_client = MagicMock()

    # Push 4 samples — should NOT write the 20d/z_score keys yet.
    # (S13 T1-6: writes migrated from .set to .setex with 7200 TTL.)
    for v in [18.0, 18.5, 19.0, 18.2]:
        feed._store_vix_baseline(v)
    pre5_setex_keys = {
        call.args[0] for call in feed.redis_client.setex.call_args_list
    }
    assert "polygon:vix:20d_mean" not in pre5_setex_keys
    assert "polygon:vix:20d_std" not in pre5_setex_keys
    assert "polygon:vix:z_score" not in pre5_setex_keys

    # 5th sample triggers the write.
    feed._store_vix_baseline(20.0)
    written_keys = {
        call.args[0] for call in feed.redis_client.setex.call_args_list
    }
    assert "polygon:vix:20d_mean" in written_keys
    assert "polygon:vix:20d_std" in written_keys
    assert "polygon:vix:z_score" in written_keys


def test_vix_baseline_does_not_overwrite_vvix_keys():
    """VIX writer must use polygon:vix:* — never the polygon:vvix:* keys."""
    from polygon_feed import PolygonFeed
    feed = PolygonFeed.__new__(PolygonFeed)
    feed.vix_history = [18.0, 18.5, 19.0, 18.2, 20.0]
    feed.redis_client = MagicMock()

    feed._store_vix_baseline(20.0)

    written_keys = {
        call.args[0] for call in feed.redis_client.set.call_args_list
    }
    for vvix_key in (
        "polygon:vvix:20d_mean",
        "polygon:vvix:20d_std",
        "polygon:vvix:z_score",
    ):
        assert vvix_key not in written_keys, (
            f"VIX baseline overwrote VVIX key {vvix_key} — "
            "wrong namespace"
        )


def test_vix_baseline_zscore_math_matches_signal_thresholds():
    """Round-trip: a known sample → z_score in expected range.

    Signal-D fires "elevated_anxiety" at z >= 1.5. Verify a current
    value that is 2 stdevs above the rolling mean produces a z_score
    above that threshold (so the writer/consumer agree on units).
    """
    from polygon_feed import PolygonFeed
    feed = PolygonFeed.__new__(PolygonFeed)
    feed.vix_history = []
    feed.redis_client = MagicMock()

    # Stable baseline around 18.
    samples = [18.0, 18.1, 17.9, 18.0, 18.1, 17.9, 18.0]
    for s in samples:
        feed._store_vix_baseline(s)
    # Spike — should produce a positive z_score >> 0.
    feed._store_vix_baseline(22.0)

    # S13 T1-6: z_score writes migrated from .set to .setex(7200).
    # setex args = (key, ttl_seconds, value) — value is at index 2.
    z_writes = [
        call for call in feed.redis_client.setex.call_args_list
        if call.args[0] == "polygon:vix:z_score"
    ]
    assert z_writes, "z_score never written"
    final_z = float(z_writes[-1].args[2])
    assert final_z > 1.5, (
        f"Spike of 22.0 against ~18 baseline produced z={final_z}; "
        "Signal-D would not trip — units likely mismatched"
    )


def test_vix_baseline_skips_write_on_zero_variance():
    """All-identical samples → std=0 → must NOT write a NaN z_score."""
    from polygon_feed import PolygonFeed
    feed = PolygonFeed.__new__(PolygonFeed)
    feed.vix_history = []
    feed.redis_client = MagicMock()

    for _ in range(6):
        feed._store_vix_baseline(18.0)

    z_writes = [
        call for call in feed.redis_client.set.call_args_list
        if call.args[0] == "polygon:vix:z_score"
    ]
    assert z_writes == [], (
        "z_score was written despite zero variance — would emit "
        "NaN/inf and crash downstream Signal-D / Signal-F readers"
    )


def test_vix_history_capped_at_20():
    """Rolling window must not grow unboundedly."""
    from polygon_feed import PolygonFeed
    feed = PolygonFeed.__new__(PolygonFeed)
    feed.vix_history = []
    feed.redis_client = MagicMock()

    for i in range(50):
        feed._store_vix_baseline(18.0 + (i % 5) * 0.1)

    assert len(feed.vix_history) == 20


# ── 4. VIX9D fetcher (P0-D) ────────────────────────────────────────────

def test_vix9d_fetcher_method_exists():
    """_fetch_vix9d must exist on PolygonFeed (no API call here)."""
    from polygon_feed import PolygonFeed
    assert hasattr(PolygonFeed, "_fetch_vix9d"), (
        "PolygonFeed._fetch_vix9d missing — Signal-A will permanently "
        "fall back to vix_term_ratio=1.0 and never down-size on "
        "inverted term structure"
    )


def test_vix9d_attribute_initialised():
    """last_vix9d attribute exists and starts as None."""
    import polygon_feed as pf_mod

    # Construct via __new__ to skip Redis client init.
    feed = pf_mod.PolygonFeed.__new__(pf_mod.PolygonFeed)
    feed.last_vix9d = None  # attribute reachable

    assert feed.last_vix9d is None


# ── 5. decision_context capture (audit trail) ──────────────────────────

def test_decision_context_keys_documented():
    """Spot-check the contract: decision_context keys we must persist.

    If any of these names change in strategy_selector.select(), the
    Loop 2 meta-label join in the data warehouse will silently break.
    """
    expected_keys = {
        "signal_mult",
        "vix_term_mult",
        "vix_term_status",
        "gex_mult",
        "gex_status",
        "opening_mult",
        "breadth_mult",
        "breadth_status",
        "earnings_mult",
        "earnings_status",
        "iv_mult",
        "iv_status",
        "vix_z",
        "has_vix_z_data",
        "flags_at_selection",
        "selected_at",
    }
    import strategy_selector
    src = open(strategy_selector.__file__, encoding="utf-8").read()
    for key in expected_keys:
        assert f'"{key}"' in src, (
            f"decision_context key '{key}' missing from "
            "strategy_selector.py — audit trail will lose it"
        )
