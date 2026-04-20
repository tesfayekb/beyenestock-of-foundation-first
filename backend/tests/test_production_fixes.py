"""
Production fixes from the 2026-04-20 first-live-session post-mortem.

Bug 1 — earnings module fails with "No module named 'main_earnings'":
    Railway-side path resolution turned the relative "backend/../backend_earnings"
    into a sys.path entry that couldn't find main_earnings.py. Fix: wrap the
    sys.path.insert target in os.path.abspath() in all 5 callsites
    (3 earnings jobs + 2 economic_calendar callsites).

Bug 2 — shadow_engine crashes parsing tradier:quotes:SPX:
    The Redis key is a JSON blob, not a plain float. shadow_engine was doing
    float(raw_spx) and crashing every cycle. Fix: mirror
    prediction_engine._get_spx_price() — try JSON first, fall back defensively.
"""
import json
import os
import sys

import pytest
from unittest.mock import MagicMock


sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_shadow_redis(spx_raw):
    """Mock Redis returning `spx_raw` for SPX key and safe defaults otherwise."""
    data = {
        "polygon:vix:current": "18.0",
        "polygon:vvix:z_score": "0.0",
        "gex:net": "0",
        "gex:confidence": "0.5",
        "tradier:quotes:SPX": spx_raw,
        "gex:flip_zone": "0",
        "gex:nearest_wall": "0",
    }
    r = MagicMock()
    r.get.side_effect = lambda k: data.get(k)
    return r


# ── Bug 2: shadow_engine SPX JSON parsing ─────────────────────────────────────

def test_shadow_parses_spx_json_blob():
    """
    Primary regression: Redis stores SPX as JSON, shadow_engine must pull
    'last' rather than crash on float(json_string).
    """
    from shadow_engine import _compute_rule_based_prediction

    spx_json = json.dumps({
        "symbol": "SPX",
        "bid": 7080.82,
        "ask": 7155.65,
        "last": 7126.06,
        "volume": 0,
        "timestamp": "2026-04-20T13:44:56.713990+00:00",
    })
    redis = _make_shadow_redis(spx_json)

    result = _compute_rule_based_prediction(redis)

    assert result is not None, (
        "_compute_rule_based_prediction returned None — the JSON fix is not "
        "active; shadow_engine is still crashing on float(raw_spx)."
    )
    assert result["spx_price"] == 7126.06, (
        f"Expected spx_price=7126.06 (the 'last' field), got {result['spx_price']}"
    )


def test_shadow_prefers_last_then_ask_then_bid():
    """If 'last' is missing, fall back to 'ask', then 'bid'."""
    from shadow_engine import _compute_rule_based_prediction

    redis = _make_shadow_redis(json.dumps({"bid": 5100.0, "ask": 5110.0}))
    result = _compute_rule_based_prediction(redis)
    assert result is not None
    assert result["spx_price"] == 5110.0, (
        f"With no 'last' but 'ask' present, should use ask=5110.0; got {result['spx_price']}"
    )


def test_shadow_handles_plain_float_string_fallback():
    """
    Defensive fallback: if a legacy writer stored a plain numeric string
    (not JSON), shadow_engine should still accept it rather than crash.
    """
    from shadow_engine import _compute_rule_based_prediction

    # json.loads("5432.10") parses as float (not dict), so we hit the
    # isinstance(spx_data, dict)-False branch and fall back to float(raw).
    redis = _make_shadow_redis("5432.10")
    result = _compute_rule_based_prediction(redis)

    assert result is not None
    assert result["spx_price"] == 5432.10, (
        f"Plain float string should parse to 5432.10, got {result['spx_price']}"
    )


def test_shadow_defaults_when_spx_missing():
    """No SPX key in Redis → default to 5200.0, do not crash."""
    from shadow_engine import _compute_rule_based_prediction

    redis = _make_shadow_redis(None)
    result = _compute_rule_based_prediction(redis)

    assert result is not None
    assert result["spx_price"] == 5200.0


def test_shadow_defaults_on_malformed_spx():
    """
    Malformed/truncated JSON (e.g. "{\"symbol\":\"SPX\",\"last\":") must
    not crash the shadow cycle — just fall through to the 5200.0 default.
    """
    from shadow_engine import _compute_rule_based_prediction

    redis = _make_shadow_redis('{"symbol":"SPX","last":')  # truncated
    result = _compute_rule_based_prediction(redis)

    assert result is not None, "Malformed JSON must not return None"
    assert result["spx_price"] == 5200.0


# ── Bug 1: earnings path resolution ───────────────────────────────────────────

def test_backend_earnings_dir_exists_at_abspath():
    """
    The absolute path resolved from backend/main.py must point at a real
    backend_earnings/ directory containing main_earnings.py. If this ever
    breaks, the earnings scheduler will ImportError in production.
    """
    here = os.path.dirname(__file__)  # backend/tests
    main_py_dir = os.path.abspath(os.path.join(here, ".."))  # backend/
    earnings_path = os.path.abspath(
        os.path.join(main_py_dir, "..", "backend_earnings")
    )

    assert os.path.isdir(earnings_path), (
        f"backend_earnings/ does not exist at expected abspath: {earnings_path}"
    )
    assert os.path.isfile(os.path.join(earnings_path, "main_earnings.py")), (
        f"main_earnings.py missing from {earnings_path}"
    )


def test_main_py_uses_abspath_for_earnings_paths():
    """
    All 3 earnings sys.path.insert blocks + 2 economic_calendar blocks
    in backend/main.py must wrap the path in os.path.abspath() to guard
    against Railway's relative-__file__ edge case.
    """
    main_py = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "main.py")
    )
    with open(main_py, encoding="utf-8") as f:
        src = f.read()

    # All 5 callsites define _EARNINGS_PATH or _AGENTS_PATH with abspath.
    abspath_count = src.count("os.path.abspath(")
    assert abspath_count >= 5, (
        f"Expected ≥5 os.path.abspath() wraps for earnings/agents paths, "
        f"found {abspath_count}. The raw sys.path.insert pattern would "
        f"reintroduce the 'No module named main_earnings' crash."
    )

    # The raw sys.path.insert(0, os.path.join(..., "..", "backend_earnings"))
    # pattern must be GONE — every earnings path now flows through abspath.
    assert 'os.path.join(os.path.dirname(__file__), "..", "backend_earnings")' \
        not in src.replace("abspath(\n            os.path.join", "ABSPATH_WRAPPED"), (
            "Unwrapped os.path.join(..., 'backend_earnings') still present in "
            "main.py — at least one callsite is still using the Railway-fragile "
            "relative-path form."
        )


def test_main_py_guards_duplicate_sys_path_insertions():
    """
    The fix should also guard against pushing the same path onto sys.path
    on every job invocation (which bloats sys.path over a multi-day run).
    Verify the 'if _PATH not in sys.path' guard is present.
    """
    main_py = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "main.py")
    )
    with open(main_py, encoding="utf-8") as f:
        src = f.read()

    guard_count = src.count("not in sys.path")
    assert guard_count >= 5, (
        f"Expected ≥5 'if _PATH not in sys.path' guards, found {guard_count}. "
        f"Without them, every scheduled job invocation re-prepends the same "
        f"path and sys.path grows unbounded."
    )
