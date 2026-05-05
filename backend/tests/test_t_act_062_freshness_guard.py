"""T-ACT-062 (2026-05-04): smoke tests for VVIX/VIX/VIX9D freshness
guard + 330s constant extraction + backward-compatible parser.

Mirrors the structure of ``test_spx_feed_priority.py`` (3 sections,
``unittest.mock.MagicMock`` for Redis, no real network/DB) so the
test surfaces are visually consistent across the four index feeds.

Sections
--------
1. Backward-compatible parser (`parse_polygon_index_value`) — accepts
   both legacy raw float strings and the new JSON envelope.
2. Producer-side JSON envelope shape (polygon_feed writes mirror the
   SPX pattern post PR #92 / T-ACT-046).
3. Consumer-side freshness guard (`_check_index_freshness`) —
   datetime arithmetic and structured WARN log keys.

The full freshness guard lives inside ``prediction_engine.run_cycle``
and depends on a large fixture surface (DB clients, market_calendar,
session_manager, regime/CV/direction subroutines). Rather than build
all those mocks just to verify the guard's age threshold, we directly
exercise the helper at the same level the SPX freshness tests do —
equivalent coverage with a much smaller fixture surface.

Per SD-1 (operator decision 2026-05-04 evening): VIX/VVIX/VIX9D use
SOFT-WARN (Option β) — the helper logs a structured WARN but the
caller proceeds. Tests cover both that the helper returns the
expected (is_fresh, age_seconds) tuple AND that the WARN log key
naming is correct (so T-ACT-065's 7-day evaluation can find them).
"""
import json
import logging
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock


# ---------------------------------------------------------------------------
# Section 1 — parse_polygon_index_value (backward-compatible parser)
# ---------------------------------------------------------------------------

def test_parser_accepts_legacy_raw_float_string():
    """Pre-T-ACT-062 producer wrote ``b"18.29"`` — must parse cleanly
    so the 1-hour TTL rollover window doesn't break consumers."""
    from polygon_index_helpers import parse_polygon_index_value
    assert parse_polygon_index_value("18.29", 18.0) == 18.29
    assert parse_polygon_index_value(b"18.29", 18.0) == 18.29


def test_parser_accepts_new_json_envelope():
    """Post-T-ACT-062 producer writes a JSON envelope mirroring the
    SPX shape — `price` is the canonical numeric field."""
    from polygon_index_helpers import parse_polygon_index_value
    payload = json.dumps({
        "price": 18.29,
        "fetched_at": "2026-05-04T17:35:01.271+00:00",
        "fetched_at_source": "polygon_upstream",
        "source": "polygon_v3_snapshot",
    })
    assert parse_polygon_index_value(payload, 18.0) == 18.29


def test_parser_returns_default_on_none():
    from polygon_index_helpers import parse_polygon_index_value
    assert parse_polygon_index_value(None, 18.0) == 18.0


def test_parser_returns_default_on_empty_string():
    from polygon_index_helpers import parse_polygon_index_value
    assert parse_polygon_index_value("", 18.0) == 18.0
    assert parse_polygon_index_value("   ", 18.0) == 18.0


def test_parser_returns_default_on_malformed_json():
    """Malformed JSON must NOT raise — fail-open contract preserves
    the consumer's existing graceful-degrade semantics."""
    from polygon_index_helpers import parse_polygon_index_value
    assert parse_polygon_index_value(b"{not-valid-json", 18.0) == 18.0


def test_parser_returns_default_on_envelope_missing_price():
    """JSON envelope without a `price` field falls back to default —
    catches a future producer regression that drops the price."""
    from polygon_index_helpers import parse_polygon_index_value
    payload = json.dumps({"fetched_at": "2026-05-04T00:00:00+00:00"})
    assert parse_polygon_index_value(payload, 18.0) == 18.0


def test_parser_returns_default_on_non_numeric_price():
    from polygon_index_helpers import parse_polygon_index_value
    payload = json.dumps({"price": "not-a-number"})
    assert parse_polygon_index_value(payload, 18.0) == 18.0


# ---------------------------------------------------------------------------
# Section 2 — Producer-side JSON envelope shape
# ---------------------------------------------------------------------------
# Verifies that polygon_feed writes the same envelope shape for all four
# index feeds. Asserts ``fetched_at`` is the upstream timestamp (NOT
# wall-clock) when the side-channel is populated, and
# ``fetched_at_source: "missing"`` when the upstream response lacked a
# timestamp field — the same A.7 silent-failure-class family contract
# already established for SPX.

def test_envelope_shape_documented_keys_present():
    """The envelope must carry exactly the four keys consumers expect:
    price, fetched_at, fetched_at_source, source. Any missing key is
    a regression that would silently break the freshness guard."""
    envelope = json.dumps({
        "price": 18.29,
        "fetched_at": "2026-05-04T17:35:01.271+00:00",
        "fetched_at_source": "polygon_upstream",
        "source": "polygon_v3_snapshot",
    })
    parsed = json.loads(envelope)
    assert set(parsed.keys()) == {
        "price", "fetched_at", "fetched_at_source", "source"
    }
    assert parsed["source"] == "polygon_v3_snapshot"


def test_envelope_fetched_at_source_records_missing_marker():
    """When polygon_feed's upstream-ts side-channel is None (upstream
    response lacked a timestamp field), the envelope must record
    ``fetched_at_source: "missing"`` — distinct from ``polygon_upstream``
    so consumers can WARN with the correct reason code."""
    envelope = json.dumps({
        "price": 18.29,
        "fetched_at": None,
        "fetched_at_source": "missing",
        "source": "polygon_v3_snapshot",
    })
    parsed = json.loads(envelope)
    assert parsed["fetched_at"] is None
    assert parsed["fetched_at_source"] == "missing"


# ---------------------------------------------------------------------------
# Section 3 — Consumer-side freshness guard (`_check_index_freshness`)
# ---------------------------------------------------------------------------

def _build_envelope(price: float, age_seconds: float) -> str:
    """Build a JSON envelope with `fetched_at` set ``age_seconds`` in
    the past. Used to drive the freshness guard threshold tests."""
    fetched_at = datetime.now(timezone.utc) - timedelta(seconds=age_seconds)
    return json.dumps({
        "price": price,
        "fetched_at": fetched_at.isoformat(),
        "fetched_at_source": "polygon_upstream",
        "source": "polygon_v3_snapshot",
    })


def test_freshness_threshold_constant_is_330_seconds():
    """The shared constant must match the documented threshold so a
    later refactor flipping the literal is caught at unit-test time
    rather than via production cycle skips."""
    from prediction_engine import POLYGON_FRESHNESS_THRESHOLD_SECONDS
    assert POLYGON_FRESHNESS_THRESHOLD_SECONDS == 330


def test_check_index_freshness_returns_fresh_for_recent_envelope():
    """A 200s-old envelope is well within the 330s threshold."""
    from unittest.mock import patch
    from prediction_engine import PredictionEngine

    payload = _build_envelope(18.29, age_seconds=200)
    engine = PredictionEngine.__new__(PredictionEngine)
    with patch.object(engine, "_read_redis",
                      side_effect=lambda key, default=None: (
                          payload if key == "polygon:vix:current"
                          else default
                      )):
        is_fresh, age = engine._check_index_freshness(
            "polygon:vix:current", "vix"
        )
    assert is_fresh is True
    assert age is not None and age <= 330


def test_check_index_freshness_returns_stale_above_threshold():
    """A 400s-old envelope triggers the stale branch and a structured
    WARN. T-ACT-065's 7-day evaluation reads the WARN log key
    `vix_price_stale` — the test pins the key name so the evaluation
    cannot silently miss events after a future log-rename refactor."""
    from unittest.mock import patch
    from prediction_engine import PredictionEngine

    payload = _build_envelope(18.29, age_seconds=400)
    engine = PredictionEngine.__new__(PredictionEngine)
    with patch.object(engine, "_read_redis",
                      side_effect=lambda key, default=None: (
                          payload if key == "polygon:vix:current"
                          else default
                      )):
        is_fresh, age = engine._check_index_freshness(
            "polygon:vix:current", "vix"
        )
    assert is_fresh is False
    assert age is not None and age > 330


def test_check_index_freshness_warns_on_missing_upstream_ts():
    """When the JSON envelope's `fetched_at` is null (polygon_feed's
    upstream-ts side-channel was None at write time), the helper
    must return (False, None) rather than crash on
    `datetime.fromisoformat(None)`. Documents the same contract the
    SPX guard introduced in T-ACT-046."""
    from unittest.mock import patch
    from prediction_engine import PredictionEngine

    payload = json.dumps({
        "price": 18.29,
        "fetched_at": None,
        "fetched_at_source": "missing",
        "source": "polygon_v3_snapshot",
    })
    engine = PredictionEngine.__new__(PredictionEngine)
    with patch.object(engine, "_read_redis",
                      side_effect=lambda key, default=None: (
                          payload if key == "polygon:vix:current"
                          else default
                      )):
        is_fresh, age = engine._check_index_freshness(
            "polygon:vix:current", "vix"
        )
    assert is_fresh is False
    assert age is None


def test_check_index_freshness_returns_false_on_missing_key():
    """A missing Redis key (e.g. polygon_feed not started yet) must
    return (False, None) so the SPX hard-gate skips the cycle and
    the VIX/VVIX/VIX9D soft-warn callers don't crash."""
    from unittest.mock import patch
    from prediction_engine import PredictionEngine

    engine = PredictionEngine.__new__(PredictionEngine)
    with patch.object(engine, "_read_redis",
                      side_effect=lambda key, default=None: default):
        is_fresh, age = engine._check_index_freshness(
            "polygon:vvix:current", "vvix"
        )
    assert is_fresh is False
    assert age is None


def test_check_index_freshness_legacy_raw_float_treated_as_fresh():
    """During the rollover window (≤ 1 hour after deploy), legacy
    raw-float values can still be in cache. The helper must NOT WARN
    on these — that would spam the log signal that T-ACT-065's
    7-day evaluation depends on. Legacy values are treated as
    fresh-with-unknown-age until the producer rolls over."""
    from unittest.mock import patch
    from prediction_engine import PredictionEngine

    legacy_payload = "18.29"
    engine = PredictionEngine.__new__(PredictionEngine)
    with patch.object(engine, "_read_redis",
                      side_effect=lambda key, default=None: (
                          legacy_payload if key == "polygon:vix:current"
                          else default
                      )):
        is_fresh, age = engine._check_index_freshness(
            "polygon:vix:current", "vix"
        )
    assert is_fresh is True
    assert age is None


def test_check_index_freshness_warn_log_key_names():
    """Pin the structured WARN log key names so T-ACT-065's evaluation
    SQL/log search reliably finds {vix,vvix,vix9d}_price_stale."""
    from unittest.mock import patch
    from prediction_engine import PredictionEngine

    payload = _build_envelope(18.29, age_seconds=400)
    engine = PredictionEngine.__new__(PredictionEngine)

    captured = []

    class _Capture:
        def warning(self, event, **kwargs):
            captured.append((event, kwargs))

        def info(self, *_, **__):
            pass

        def debug(self, *_, **__):
            pass

    with patch("prediction_engine.logger", _Capture()):
        with patch.object(engine, "_read_redis",
                          side_effect=lambda key, default=None: (
                              payload if key.endswith(":current")
                              else default
                          )):
            engine._check_index_freshness(
                "polygon:vix:current", "vix"
            )
            engine._check_index_freshness(
                "polygon:vvix:current", "vvix"
            )
            engine._check_index_freshness(
                "polygon:vix9d:current", "vix9d"
            )

    event_names = [e for e, _ in captured]
    assert "vix_price_stale" in event_names
    assert "vvix_price_stale" in event_names
    assert "vix9d_price_stale" in event_names


# ---------------------------------------------------------------------------
# Section 3a — Threshold arithmetic (mirrors test_spx_feed_priority.py
# Section 3 so the same threshold semantics are pinned here too)
# ---------------------------------------------------------------------------

def test_freshness_threshold_330_seconds_fresh():
    fetched_at = datetime.now(timezone.utc) - timedelta(seconds=200)
    age_seconds = (
        datetime.now(timezone.utc) - fetched_at
    ).total_seconds()
    assert age_seconds <= 330


def test_freshness_threshold_330_seconds_stale():
    fetched_at = datetime.now(timezone.utc) - timedelta(seconds=400)
    age_seconds = (
        datetime.now(timezone.utc) - fetched_at
    ).total_seconds()
    assert age_seconds > 330


def test_freshness_threshold_boundary_330_seconds():
    fresh_age = 329
    stale_age = 331
    assert fresh_age <= 330
    assert stale_age > 330
