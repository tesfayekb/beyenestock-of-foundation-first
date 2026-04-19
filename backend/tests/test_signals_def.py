"""Tests for Signal-D (market breadth), Signal-E (earnings proximity),
Signal-F (IV rank).

These signals share a single VIX z-score read in select() — D and F
both consume it from the caller, while E reads calendar:today:intel
on its own. All three default ON via reverse-polarity feature flags.
"""
from unittest.mock import MagicMock


def _make_selector(flags: dict = None, redis_data: dict = None):
    """
    Build a StrategySelector with a mocked Redis client.

    flags: maps flag_key → "true"/"false" (matches _check_feature_flag,
        which compares against the string 'true' or bytes b'true').
    redis_data: maps any other Redis key → string payload (e.g. JSON).

    Mock returns bytes for present keys and None for absent keys, which
    mirrors a real redis-py client with decode_responses=False.
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


# ── Signal-D: Market Breadth ─────────────────────────────────────────

def test_breadth_normal_vix_z_returns_1():
    sel = _make_selector({"signal:market_breadth:enabled": "true"})
    mult, status = sel._market_breadth_modifier(0.3)
    assert mult == 1.0 and status == "normal"


def test_breadth_elevated_reduces_25():
    sel = _make_selector({"signal:market_breadth:enabled": "true"})
    mult, status = sel._market_breadth_modifier(1.8)
    assert mult == 0.75 and status == "elevated_anxiety"


def test_breadth_severe_reduces_50():
    sel = _make_selector({"signal:market_breadth:enabled": "true"})
    mult, status = sel._market_breadth_modifier(3.0)
    assert mult == 0.50 and status == "severe_anxiety"


def test_breadth_strong_boosts():
    sel = _make_selector({"signal:market_breadth:enabled": "true"})
    mult, status = sel._market_breadth_modifier(-1.0)
    assert mult == 1.05 and status == "strong_breadth"


def test_breadth_flag_off_returns_1():
    sel = _make_selector({"signal:market_breadth:enabled": "false"})
    mult, status = sel._market_breadth_modifier(3.0)
    assert mult == 1.0 and status == "flag_off"


# ── Signal-E: Earnings Proximity ─────────────────────────────────────

def test_earnings_prox_no_earnings_returns_1():
    import json
    intel = {"has_major_earnings": False, "earnings": []}
    sel = _make_selector(
        flags={"signal:earnings_proximity:enabled": "true"},
        redis_data={"calendar:today:intel": json.dumps(intel)},
    )
    mult, status = sel._earnings_proximity_modifier("iron_condor")
    assert mult == 1.0 and status == "no_major_earnings"


def test_earnings_prox_major_earnings_reduces_25():
    import json
    intel = {
        "has_major_earnings": True,
        "earnings": [{"symbol": "NVDA"}],
    }
    sel = _make_selector(
        flags={"signal:earnings_proximity:enabled": "true"},
        redis_data={"calendar:today:intel": json.dumps(intel)},
    )
    mult, status = sel._earnings_proximity_modifier("iron_condor")
    assert mult == 0.75 and status == "major_earnings_today"


def test_earnings_prox_not_applicable_for_straddle():
    import json
    intel = {
        "has_major_earnings": True,
        "earnings": [{"symbol": "AAPL"}],
    }
    sel = _make_selector(
        flags={"signal:earnings_proximity:enabled": "true"},
        redis_data={"calendar:today:intel": json.dumps(intel)},
    )
    mult, status = sel._earnings_proximity_modifier("long_straddle")
    assert mult == 1.0 and status == "not_applicable"


def test_earnings_prox_no_redis_data_returns_1():
    sel = _make_selector({"signal:earnings_proximity:enabled": "true"})
    mult, status = sel._earnings_proximity_modifier("iron_condor")
    assert mult == 1.0 and status == "no_calendar_data"


def test_earnings_prox_flag_off_returns_1():
    import json
    intel = {
        "has_major_earnings": True,
        "earnings": [{"symbol": "META"}],
    }
    sel = _make_selector(
        flags={"signal:earnings_proximity:enabled": "false"},
        redis_data={"calendar:today:intel": json.dumps(intel)},
    )
    mult, status = sel._earnings_proximity_modifier("iron_condor")
    assert mult == 1.0 and status == "flag_off"


# ── Signal-F: IV Rank ────────────────────────────────────────────────

def test_iv_rank_normal_returns_1():
    sel = _make_selector({"signal:iv_rank_filter:enabled": "true"})
    mult, status = sel._iv_rank_modifier(0.3)
    assert mult == 1.0 and status == "normal"


def test_iv_rank_thin_reduces_25():
    sel = _make_selector({"signal:iv_rank_filter:enabled": "true"})
    mult, status = sel._iv_rank_modifier(-1.6)
    assert mult == 0.75 and status == "thin_premium"


def test_iv_rank_very_thin_skips():
    sel = _make_selector({"signal:iv_rank_filter:enabled": "true"})
    mult, status = sel._iv_rank_modifier(-2.5)
    assert mult == 0.0 and "skip" in status


def test_iv_rank_rich_boosts():
    sel = _make_selector({"signal:iv_rank_filter:enabled": "true"})
    mult, status = sel._iv_rank_modifier(1.0)
    assert mult == 1.05 and status == "rich_premium"


def test_iv_rank_high_z_neutral_not_double_cut():
    """When vix_z >= _BREADTH_HIGH (1.5), Signal-F returns 1.0.
    Signal-D handles the cut — Signal-F must not double-cut."""
    sel = _make_selector({"signal:iv_rank_filter:enabled": "true"})
    mult, status = sel._iv_rank_modifier(2.0)
    assert mult == 1.0 and status == "normal"


def test_iv_rank_flag_off_returns_1():
    sel = _make_selector({"signal:iv_rank_filter:enabled": "false"})
    mult, status = sel._iv_rank_modifier(-3.0)
    assert mult == 1.0 and status == "flag_off"


# ── Redis helper ─────────────────────────────────────────────────────

def test_read_redis_float_returns_default_on_none():
    sel = _make_selector()
    sel.redis_client = None
    val = sel._read_redis_float("any:key", 99.0)
    assert val == 99.0


def test_read_redis_float_parses_bytes():
    sel = _make_selector(redis_data={"polygon:vix:z_score": "1.23"})
    val = sel._read_redis_float("polygon:vix:z_score", 0.0)
    assert abs(val - 1.23) < 0.001
