"""12A: True 20-day SPX daily realized vol tests.

The prior implementation wrote polygon:spx:realized_vol_20d from
self.spx_history (5-min intraday bars) annualized with the daily
factor 252, producing 1.05-1.29% instead of the true ~15-20% SPX
daily RV. These tests lock in the new behaviour:

  * EOD append path sources from polygon:spx:prior_day_return
  * realized_vol_20d is only written once >= 5 daily samples exist
  * Redis-backed date guard prevents double-append on restart
  * The rolling window is capped at 20 trading days
  * Typical SPX daily move magnitudes produce sensible RV (5-40%)
"""
import math
import os
import sys
from unittest.mock import MagicMock

import pytest  # noqa: F401  (pytest discovery)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _make_feed(prior_day_return: str = "0.001"):
    """Build a PolygonFeed with just enough state for the daily RV
    path — bypass __init__ to avoid instantiating a real Redis
    client, then wire a MagicMock that returns the requested
    prior_day_return string (decode_responses=True semantics).
    """
    from polygon_feed import PolygonFeed

    feed = PolygonFeed.__new__(PolygonFeed)
    feed.redis_client = MagicMock()

    def _fake_get(key):
        if key == "polygon:spx:prior_day_return":
            return prior_day_return
        return None

    feed.redis_client.get.side_effect = _fake_get
    feed.spx_daily_returns = []
    feed._spx_daily_date_written = None
    return feed


def _rv_writes(feed):
    """Return every setex(...) call that targeted polygon:spx:realized_vol_20d."""
    return [
        call for call in feed.redis_client.setex.call_args_list
        if call.args and call.args[0] == "polygon:spx:realized_vol_20d"
    ]


# ── Test 1: below warmth threshold → no realized_vol_20d write ────────────────

def test_spx_daily_rv_not_written_below_5_days():
    """4 daily returns must NOT trigger a polygon:spx:realized_vol_20d
    write — the downstream IV/RV filter's rv_val >= 5.0 warmth guard
    tolerates the missing key during cold-start."""
    feed = _make_feed("0.001")
    # Pre-seed 3 returns; the function call adds a 4th → total = 4.
    feed.spx_daily_returns = [0.001, -0.001, 0.001]

    feed._append_spx_daily_return_if_due("2026-04-16")

    assert len(feed.spx_daily_returns) == 4, (
        "append must run regardless of count; only the RV write is gated"
    )
    assert _rv_writes(feed) == [], (
        "polygon:spx:realized_vol_20d must NOT be written below 5 samples"
    )


# ── Test 2: at 5 days → RV written with sensible value ────────────────────────

def test_spx_daily_rv_written_at_5_days():
    """5 mixed ±0.001 daily returns → RV written, value in 1.0-3.0%."""
    feed = _make_feed("0.001")
    # Pre-seed 4 mixed-sign returns; append adds the 5th.
    feed.spx_daily_returns = [-0.001, 0.001, -0.001, 0.001]

    feed._append_spx_daily_return_if_due("2026-04-16")

    assert len(feed.spx_daily_returns) == 5

    writes = _rv_writes(feed)
    assert len(writes) == 1, "realized_vol_20d must be written exactly once"

    key, ttl, value = writes[0].args
    assert key == "polygon:spx:realized_vol_20d"
    assert ttl == 86400, f"TTL must be 24h, got {ttl}"

    rv = float(value)
    assert 1.0 <= rv <= 3.0, (
        f"5 samples of ±0.1% daily moves → RV ~1.5%; got {rv}"
    )


# ── Test 3: realistic daily returns → RV in 5-40% range ───────────────────────

def test_spx_daily_rv_value_reasonable():
    """20 realistic SPX daily returns (±0.5-1.5%) → RV in 5-40% range,
    matching real-world equity index realized vol."""
    import random
    random.seed(42)

    # The Redis-sourced 20th return caps the move at ~0.8%.
    feed = _make_feed("0.008")
    # Pre-seed 19 returns from the [-1.5%, +1.5%] range.
    feed.spx_daily_returns = [
        random.uniform(-0.015, 0.015) for _ in range(19)
    ]

    feed._append_spx_daily_return_if_due("2026-04-16")

    writes = _rv_writes(feed)
    assert len(writes) == 1
    rv = float(writes[0].args[2])

    assert 5.0 <= rv <= 40.0, (
        f"Realistic SPX daily returns should produce RV in 5-40%; got {rv}. "
        "Sub-5% indicates we're still annualizing intraday bars; >40% "
        "indicates outlier-sized fake returns."
    )


# ── Test 4: same-date guard prevents double-append ────────────────────────────

def test_spx_daily_date_guard_prevents_double_append():
    """Calling the EOD append twice with the same today_str must NOT
    re-append. Locks in the in-memory guard that prevents the 5-min
    poll loop from spamming daily samples into the rolling window."""
    feed = _make_feed("0.001")
    feed.spx_daily_returns = [0.001, -0.001, 0.001]

    feed._append_spx_daily_return_if_due("2026-04-16")
    first_len = len(feed.spx_daily_returns)
    assert first_len == 4

    feed._append_spx_daily_return_if_due("2026-04-16")
    assert len(feed.spx_daily_returns) == first_len, (
        "second same-date call must not re-append"
    )


# ── Test 5: rolling window capped at 20 trading days ──────────────────────────

def test_spx_daily_rv_capped_at_20():
    """25 appends across 25 distinct dates → final length exactly 20.
    The rolling window must slide, not grow unbounded."""
    feed = _make_feed("0.001")

    for i in range(1, 26):
        feed._append_spx_daily_return_if_due(f"2026-01-{i:02d}")

    assert len(feed.spx_daily_returns) == 20, (
        f"rolling window must cap at 20; got {len(feed.spx_daily_returns)}"
    )


# ── Bonus: Redis restart-guard key is written with correct TTL ────────────────

def test_spx_daily_last_date_persisted_to_redis():
    """polygon:spx:daily_returns:last_date must be written with 25-day
    TTL so a process restart can restore the guard across long
    holiday weekends."""
    feed = _make_feed("0.001")

    feed._append_spx_daily_return_if_due("2026-04-16")

    last_date_writes = [
        call for call in feed.redis_client.setex.call_args_list
        if call.args and call.args[0] == "polygon:spx:daily_returns:last_date"
    ]
    assert len(last_date_writes) == 1
    key, ttl, value = last_date_writes[0].args
    assert ttl == 86400 * 25, f"TTL must be 25 days, got {ttl}"
    assert value == "2026-04-16"


# ── Bonus: math sanity — confirm daily annualization is correct ───────────────

def test_spx_daily_rv_annualization_math():
    """Sanity check: 20 daily returns with known stddev should produce
    RV ≈ stddev * sqrt(252) * 100. Catches accidental re-introduction
    of intraday annualization factors (sqrt(252 * 78) etc.)."""
    feed = _make_feed("0.01")
    # Pre-seed 19 alternating ±1% returns; add 20th at +1%.
    feed.spx_daily_returns = [0.01 if i % 2 == 0 else -0.01 for i in range(19)]

    feed._append_spx_daily_return_if_due("2026-04-16")

    writes = _rv_writes(feed)
    rv_actual = float(writes[0].args[2])

    # Manually compute expected RV on the final 20-sample window.
    final = feed.spx_daily_returns
    mean_r = sum(final) / len(final)
    variance = sum((r - mean_r) ** 2 for r in final) / len(final)
    rv_expected = math.sqrt(variance * 252) * 100

    assert abs(rv_actual - rv_expected) < 0.01, (
        f"RV={rv_actual} does not match expected {rv_expected:.4f}. "
        "Annualization factor may be wrong."
    )
    # And the absolute magnitude should look like a real equity vol —
    # 1% daily moves → ~16% annualized.
    assert 10.0 <= rv_actual <= 25.0, (
        f"1% daily moves should annualize near 16%; got {rv_actual}"
    )
