"""T-ACT-082 (Scope A subset): byte-aligned feature writer tests.

Verifies that the three new live writers added in
`polygon_feed.py` produce values that match the corresponding columns
in `scripts/train_direction_model.py` byte-for-byte (within float
rounding noise) given identical inputs:

  * polygon:spx:bb_pct_b   <- df["bb_pct_b"]   (training L242-244)
  * polygon:spx:macd_signal <- df["macd_signal"] (training L237-240)
  * polygon:vix:5d_change  <- df["vix_5d_change"] (training L274-276)

This is the consumer-side guarantee that T-ACT-082 closes the silent
feature-pipeline-incompleteness bug surfaced in the 2026-05-07 model-
quality investigation: the LightGBM model was reading these keys from
Redis and getting Python defaults (0.0, 0.0, 0.0 respectively) because
no producer wrote them. With this PR, the producer exists and the
values match training distribution.

Discretionary scope-defer: `vwap_distance`, `morning_range`,
`overnight_gap` (training feature-importances #1, #7, and #5
respectively) are NOT in this PR — they require SPX OHLC bars and
day-boundary state that the live `polygon_feed` does not currently
maintain. Deferred to T-ACT-085 per the operator-authorized Path Alpha.
"""
import asyncio
import os
import sys
from unittest.mock import MagicMock

import pytest  # noqa: F401  (pytest discovery)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _make_feed():
    """Build a PolygonFeed bypassing __init__ (no real Redis client),
    with the T-ACT-082 buffers initialised so the per-cycle 5-min-basis
    realized-vol writer doesn't fire (we only want the bb / macd /
    vix-5d branches under test in this file)."""
    from polygon_feed import PolygonFeed

    feed = PolygonFeed.__new__(PolygonFeed)
    feed.redis_client = MagicMock()
    feed.spx_history = []
    feed._spx_5m_returns_history = []
    feed._spx_5m_history_max = 1560
    feed._spx_5m_backfill_done = False
    feed.vix_history = []
    feed.vix_daily_history = []
    feed._vix_daily_date_written = None
    feed.spx_prev_session_close = None
    return feed


def _writes(feed, key):
    """Return every setex(...) call that targeted `key`."""
    return [
        call for call in feed.redis_client.setex.call_args_list
        if call.args and call.args[0] == key
    ]


# ════════════════════════════════════════════════════════════════════════════
# bb_pct_b (Bollinger Bands %B)
# ════════════════════════════════════════════════════════════════════════════

def test_bb_pct_b_not_written_below_20_closes():
    """Training computes bb_pct_b from `df["close"].rolling(20)`.
    Below 20 closes the rolling window produces NaN in pandas; the
    live writer must mirror this by skipping the write entirely."""
    feed = _make_feed()
    feed.spx_history = [4500.0 + i * 1.0 for i in range(19)]

    asyncio.run(feed._compute_spx_features())

    assert _writes(feed, "polygon:spx:bb_pct_b") == [], (
        "bb_pct_b must NOT be written below 20 closes (pandas .rolling(20) "
        "produces NaN in this regime)."
    )


def test_bb_pct_b_byte_aligned_with_training():
    """bb_pct_b at exactly 20 closes must match the closed-form
    training formula:
        sma20 = mean(closes[-20:])
        std20 = sample-std(closes[-20:])  # pandas .std() = ddof=1
        bb_pct_b = (close - (sma20 - 2*std20)) / (4*std20)
    """
    import math

    feed = _make_feed()
    closes = [4500.0 + i * 2.0 for i in range(20)]
    feed.spx_history = closes

    asyncio.run(feed._compute_spx_features())

    writes = _writes(feed, "polygon:spx:bb_pct_b")
    assert len(writes) == 1
    bb_actual = float(writes[0].args[2])

    last20 = closes[-20:]
    sma20 = sum(last20) / 20
    var20 = sum((x - sma20) ** 2 for x in last20) / 19  # ddof=1
    std20 = math.sqrt(var20)
    bb_expected = (closes[-1] - (sma20 - 2 * std20)) / (4 * std20)

    assert abs(bb_actual - bb_expected) < 1e-5, (
        f"bb_pct_b={bb_actual} does not match training formula "
        f"expected {bb_expected:.6f}. Possible regression in ddof or "
        f"window size."
    )


def test_bb_pct_b_ttl_is_300s():
    """5-min-cycle TTL discipline: a crashed feed must not leave a
    stale bb_pct_b in Redis past one poll cycle."""
    feed = _make_feed()
    feed.spx_history = [4500.0 + i * 2.0 for i in range(20)]

    asyncio.run(feed._compute_spx_features())

    writes = _writes(feed, "polygon:spx:bb_pct_b")
    assert len(writes) == 1
    key, ttl, value = writes[0].args
    assert ttl == 300, f"bb_pct_b TTL must be 300s, got {ttl}"


# ════════════════════════════════════════════════════════════════════════════
# macd_signal (= MACD histogram per training column naming)
# ════════════════════════════════════════════════════════════════════════════

def test_macd_signal_not_written_below_35_closes():
    """The 9-bar EMA-of-MACD smoothing requires sufficient warmup for
    the initial-condition transient to decay below the 1% noise floor.
    We require >= 35 closes; below this the writer must skip."""
    feed = _make_feed()
    feed.spx_history = [4500.0 + i * 1.0 for i in range(34)]

    asyncio.run(feed._compute_spx_features())

    assert _writes(feed, "polygon:spx:macd_signal") == [], (
        "macd_signal must NOT be written below 35 closes (EMA warmup "
        "transient still material)."
    )


def test_macd_signal_byte_aligned_with_training():
    """macd_signal at >= 35 closes must match the recursive EMA chain
    from training:
        ema12 = ewm(span=12, adjust=False)
        ema26 = ewm(span=26, adjust=False)
        macd  = ema12 - ema26
        macd_signal = macd[-1] - ewm(span=9, adjust=False)(macd)[-1]
    """
    feed = _make_feed()
    # 50 closes — comfortably past the 35-bar threshold and past the
    # span=26 EMA's effective half-life (~13 bars).
    closes = [4500.0 + 5.0 * (i % 7) - 2.0 * (i % 11) for i in range(50)]
    feed.spx_history = closes

    asyncio.run(feed._compute_spx_features())

    writes = _writes(feed, "polygon:spx:macd_signal")
    assert len(writes) == 1
    macd_actual = float(writes[0].args[2])

    # Replicate pandas ewm(span=N, adjust=False) recursively.
    def ewm(values, span):
        alpha = 2.0 / (span + 1.0)
        out = [values[0]]
        for v in values[1:]:
            out.append(alpha * v + (1.0 - alpha) * out[-1])
        return out

    ema12 = ewm(closes, 12)
    ema26 = ewm(closes, 26)
    macd_line = [a - b for a, b in zip(ema12, ema26)]
    macd_smoothed = ewm(macd_line, 9)
    macd_expected = macd_line[-1] - macd_smoothed[-1]

    assert abs(macd_actual - macd_expected) < 1e-5, (
        f"macd_signal={macd_actual} does not match training formula "
        f"expected {macd_expected:.6f}. Possible drift in EMA recurrence."
    )


def test_macd_signal_ttl_is_300s():
    feed = _make_feed()
    feed.spx_history = [4500.0 + 5.0 * (i % 7) for i in range(50)]

    asyncio.run(feed._compute_spx_features())

    writes = _writes(feed, "polygon:spx:macd_signal")
    assert len(writes) == 1
    key, ttl, value = writes[0].args
    assert ttl == 300, f"macd_signal TTL must be 300s, got {ttl}"


# ════════════════════════════════════════════════════════════════════════════
# vix_5d_change
# ════════════════════════════════════════════════════════════════════════════

def test_vix_5d_change_not_written_below_6_daily_samples():
    """Training computes vix_5d_change as `daily_vix.pct_change(5)` —
    requires at least 6 daily samples (pct_change(5) at index 5 looks
    back to index 0). Below this the writer must skip."""
    feed = _make_feed()
    feed.vix_daily_history = [18.0, 18.5, 19.0, 18.8, 19.2]  # 5 samples

    feed._store_vix_baseline(19.5)

    assert _writes(feed, "polygon:vix:5d_change") == [], (
        "vix_5d_change must NOT be written below 6 daily samples "
        "(pct_change(5) requires t-5 lookback)."
    )


def test_vix_5d_change_byte_aligned_with_training():
    """vix_5d_change must equal (vix[-1] - vix[-6]) / vix[-6]."""
    feed = _make_feed()
    feed.vix_daily_history = [18.0, 18.5, 19.0, 18.8, 19.2]
    # _store_vix_baseline appends `current` to vix_daily_history at
    # 19:00 UTC, so we orchestrate via the public entry point below.
    # For determinism here we set the daily history directly to 6
    # samples then drive the function with the current=last sample.

    feed.vix_daily_history = [18.0, 18.5, 19.0, 18.8, 19.2, 20.5]
    # vix_daily_history was already populated above; now skip the
    # 19:00 UTC append by setting _vix_daily_date_written = today_str
    # so only the z-score / 5d_change branch fires.
    from datetime import datetime, timezone
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    feed._vix_daily_date_written = today_str

    feed._store_vix_baseline(20.5)

    writes = _writes(feed, "polygon:vix:5d_change")
    assert len(writes) == 1
    delta_actual = float(writes[0].args[2])

    delta_expected = (20.5 - 18.0) / 18.0
    assert abs(delta_actual - delta_expected) < 1e-5, (
        f"vix_5d_change={delta_actual} does not match training "
        f"pct_change(5) expected {delta_expected:.6f}."
    )


def test_vix_5d_change_ttl_is_7200s():
    """vix_5d_change is a daily-cadence signal computed from daily-
    history. 7200s TTL = 2h, matching other daily-sourced VIX keys
    (z_score, 20d_mean, 20d_std)."""
    feed = _make_feed()
    feed.vix_daily_history = [18.0, 18.5, 19.0, 18.8, 19.2, 20.5]
    from datetime import datetime, timezone
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    feed._vix_daily_date_written = today_str

    feed._store_vix_baseline(20.5)

    writes = _writes(feed, "polygon:vix:5d_change")
    assert len(writes) == 1
    key, ttl, value = writes[0].args
    assert ttl == 7200, (
        f"vix_5d_change TTL must be 7200s (matches sibling daily VIX "
        f"keys); got {ttl}"
    )


# ════════════════════════════════════════════════════════════════════════════
# Helper: _ewm_adjust_false byte-alignment with pandas
# ════════════════════════════════════════════════════════════════════════════

def test_ewm_adjust_false_matches_pandas():
    """The static helper used by macd_signal must match
    pandas.Series.ewm(span=N, adjust=False).mean() within float noise.
    This guards the recursive implementation against accidental drift
    (e.g. someone changing the alpha formula or initial condition)."""
    try:
        import pandas as pd
    except ImportError:
        pytest.skip("pandas not available")

    from polygon_feed import PolygonFeed

    values = [100.0 + 2.5 * (i % 5) - 1.0 * (i % 3) for i in range(40)]
    expected = pd.Series(values).ewm(span=12, adjust=False).mean().tolist()
    actual = PolygonFeed._ewm_adjust_false(values, 12)

    assert len(actual) == len(expected)
    for i, (a, e) in enumerate(zip(actual, expected)):
        assert abs(a - e) < 1e-9, (
            f"_ewm_adjust_false at i={i}: actual={a}, pandas={e}, "
            f"diff={abs(a-e):.2e}"
        )
