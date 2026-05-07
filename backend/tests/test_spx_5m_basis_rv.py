"""T-ACT-082 (Scope B): 5-min-basis SPX realized_vol_20d invariants.

Supersedes the prior `test_spx_daily_rv.py` daily-basis test file.
The 12A daily-basis writer (sqrt(252) annualization, 20-sample window)
was an over-correction to a buggy intraday-bars-with-daily-annualization
writer; T-ACT-082 reverts to a 5-min-basis writer that is byte-for-byte
aligned with the LightGBM training pipeline:

    # scripts/train_direction_model.py:292-298
    df["rv_20d"] = (
        df["return_5m"]
        .rolling(20 * 78)
        .std()
        * np.sqrt(252 * 78)
        * 100
    )

These tests lock in the new behaviour:

  * 5-min returns buffer (`_spx_5m_returns_history`) caps at 1560
    samples (= 20 trading days * 78 bars/day).
  * `polygon:spx:realized_vol_20d` is only written once the buffer
    has accumulated 1560 returns.
  * Annualization factor is sqrt(252 * 78), NOT sqrt(252) — catches
    accidental re-introduction of the deprecated daily-basis formula.
  * The Polygon /v2/aggs 5-minute backfill at startup pre-populates
    the buffer to 1560 entries so production avoids a 3-week
    cold-start window.
  * `_append_spx_daily_return_if_due` no longer writes the realized-
    vol key (regression guard against re-introduction of the
    deprecated daily-basis writer).
"""
import asyncio
import math
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest  # noqa: F401  (pytest discovery)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _make_feed():
    """Build a PolygonFeed that bypasses __init__ (no real Redis client),
    with the T-ACT-082 buffers pre-initialised to empty.
    """
    from polygon_feed import PolygonFeed

    feed = PolygonFeed.__new__(PolygonFeed)
    feed.redis_client = MagicMock()
    feed.spx_history = []
    feed._spx_5m_returns_history = []
    feed._spx_5m_history_max = 1560
    feed._spx_5m_backfill_done = False
    feed.spx_prev_session_close = None
    return feed


def _rv_writes(feed):
    """Return every setex(...) call that targeted polygon:spx:realized_vol_20d."""
    return [
        call for call in feed.redis_client.setex.call_args_list
        if call.args and call.args[0] == "polygon:spx:realized_vol_20d"
    ]


# ── Test 1: below 1560-bar warmth threshold → no realized_vol_20d write ──────

def test_rv_20d_not_written_below_1560_returns():
    """Buffer at 1559 samples after the live append must NOT trigger
    a polygon:spx:realized_vol_20d write. The training-aligned rolling
    window is exactly 1560 samples (20 trading days * 78 5-min bars/
    day). Sub-window writes would produce a different statistical
    distribution than the model was trained on."""
    feed = _make_feed()
    feed.spx_history = [4500.0, 4501.0]
    # Pre-fill 1558 returns; the live append in _compute_spx_features
    # adds the 1559th from spx_history → still < 1560.
    feed._spx_5m_returns_history = [
        0.0001 if i % 2 == 0 else -0.0001 for i in range(1558)
    ]

    asyncio.run(feed._compute_spx_features())

    assert _rv_writes(feed) == [], (
        "polygon:spx:realized_vol_20d must NOT be written below 1560 samples"
    )
    assert len(feed._spx_5m_returns_history) == 1559


# ── Test 2: at 1560 returns → RV written with 5-min annualization ────────────

def test_rv_20d_written_at_1560_returns():
    """At exactly 1560 returns the writer fires. Value must use the
    sqrt(252 * 78) annualization factor, NOT sqrt(252). 5-min returns
    of ±0.001 (~0.1%, a realistic SPX 5-min move) → ddof=1 sample std
    ≈ 1e-3 → annualized ≈ 1e-3 * sqrt(252 * 78) * 100 ≈ 14% — well
    within the realistic SPX RV band (the 12A-era target was 15-20%)."""
    feed = _make_feed()
    feed.spx_history = [4500.0, 4501.0]
    # 1559 alternating ±0.001 returns; the live append in
    # _compute_spx_features adds the 1560th from spx_history.
    feed._spx_5m_returns_history = [
        0.001 if i % 2 == 0 else -0.001 for i in range(1559)
    ]

    asyncio.run(feed._compute_spx_features())

    writes = _rv_writes(feed)
    assert len(writes) == 1, (
        "realized_vol_20d must be written exactly once at the boundary"
    )

    key, ttl, value = writes[0].args
    assert key == "polygon:spx:realized_vol_20d"
    assert ttl == 300, (
        f"TTL must be 300s (per-cycle), got {ttl}. Stale-data discipline: "
        "writers on the 5-min poll cadence use 300s so a crashed feed "
        "cannot leave a stale value past a single cycle."
    )

    rv = float(value)
    # Sanity: 0.1% std * sqrt(252*78) * 100 ≈ 14%
    assert 5.0 <= rv <= 30.0, (
        f"5-min returns of ±0.1% should annualize to ~14% RV; got {rv}. "
        "Sub-5 indicates we're using sqrt(252) (deprecated daily basis); "
        ">30 indicates outlier-sized synthetic returns."
    )


# ── Test 3: realistic 5-min returns → RV in 5-40% range ───────────────────────

def test_rv_20d_value_reasonable():
    """1560 realistic SPX 5-min returns (~±0.05% per bar typical) →
    RV in 5-40% range, matching real-world equity-index realized vol."""
    import random
    random.seed(42)

    feed = _make_feed()
    feed.spx_history = [4500.0, 4501.0]
    feed._spx_5m_returns_history = [
        random.uniform(-0.001, 0.001) for _ in range(1559)
    ]

    asyncio.run(feed._compute_spx_features())

    writes = _rv_writes(feed)
    assert len(writes) == 1
    rv = float(writes[0].args[2])

    assert 5.0 <= rv <= 40.0, (
        f"Realistic SPX 5-min returns should produce RV in 5-40%; "
        f"got {rv}. Sub-5 may indicate sqrt(252) annualization "
        "(deprecated daily basis); >40 indicates outlier-sized "
        "synthetic returns."
    )


# ── Test 4: annualization math is sqrt(252 * 78), not sqrt(252) ───────────────

def test_rv_20d_annualization_factor_is_5min_basis():
    """Sanity check: 1560 returns with known stddev should produce
    RV ≈ stddev * sqrt(252 * 78) * 100 (NOT stddev * sqrt(252) * 100).
    Catches accidental re-introduction of the 12A daily-basis formula
    OR the original buggy intraday-bars-with-daily-annualization
    formula."""
    feed = _make_feed()
    feed.spx_history = [4500.0, 4501.0]
    feed._spx_5m_returns_history = [
        0.001 if i % 2 == 0 else -0.001 for i in range(1559)
    ]

    asyncio.run(feed._compute_spx_features())

    writes = _rv_writes(feed)
    rv_actual = float(writes[0].args[2])

    final = feed._spx_5m_returns_history[-1560:]
    n = len(final)
    mean_r = sum(final) / n
    # ddof=1 sample std (matches pandas .std() default)
    variance = sum((r - mean_r) ** 2 for r in final) / (n - 1)
    rv_expected_5m = math.sqrt(variance) * math.sqrt(252 * 78) * 100
    rv_expected_daily = math.sqrt(variance) * math.sqrt(252) * 100

    assert abs(rv_actual - rv_expected_5m) < 0.01, (
        f"RV={rv_actual} does not match expected 5-min-basis "
        f"{rv_expected_5m:.4f}. Annualization factor may be wrong."
    )
    # Hard regression guard: the daily-basis value must NOT match.
    # If they happen to be equal something is structurally broken.
    assert abs(rv_actual - rv_expected_daily) > 1.0, (
        f"RV={rv_actual} matches the deprecated daily-basis "
        f"value {rv_expected_daily:.4f}. The factor sqrt(252) was "
        "re-introduced. T-ACT-082 (Scope B) requires sqrt(252 * 78)."
    )


# ── Test 5: rolling buffer caps at 1560 (FIFO eviction) ───────────────────────

def test_rv_20d_buffer_caps_at_1560():
    """Pre-fill buffer to 1559 + drive 50 more cycles → final length
    must be exactly 1560 (oldest sample evicted on each subsequent
    cycle)."""
    feed = _make_feed()
    feed.spx_history = [4500.0, 4501.0]
    feed._spx_5m_returns_history = [0.0001] * 1559

    for i in range(50):
        # spawn new spx_history close to vary the appended return
        feed.spx_history.append(4501.0 + i * 0.5)
        asyncio.run(feed._compute_spx_features())

    assert len(feed._spx_5m_returns_history) == 1560, (
        f"5-min returns buffer must cap at 1560; got "
        f"{len(feed._spx_5m_returns_history)}"
    )


# ── Test 6: backfill populates _spx_5m_returns_history from Polygon ──────────

def test_spx_5m_backfill_populates_buffer():
    """`_backfill_spx_5m_history` should populate the buffer with up to
    1560 returns from Polygon's /v2/aggs 5-minute response. Without
    this backfill, production runs with `realized_vol_20d` falling back
    to the prediction-engine default 15.0 for ~21 trading days post-
    deploy — operationally activating the same regression T-ACT-082
    fixes."""
    feed = _make_feed()

    # 1700 close values span > 1560 returns, to verify the cap.
    fake_closes = [{"c": 4500.0 + i * 0.5} for i in range(1700)]

    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_response.json.return_value = {"results": fake_closes}

    fake_client = MagicMock()
    fake_client.__aenter__ = AsyncMock(return_value=fake_client)
    fake_client.__aexit__ = AsyncMock(return_value=False)
    fake_client.get = AsyncMock(return_value=fake_response)

    with patch("httpx.AsyncClient", return_value=fake_client), \
         patch("config.POLYGON_API_KEY", "fake-key", create=True):
        asyncio.run(feed._backfill_spx_5m_history())

    assert feed._spx_5m_backfill_done is True, (
        "backfill must set _spx_5m_backfill_done flag"
    )
    assert len(feed._spx_5m_returns_history) == 1560, (
        "backfill must cap buffer at 1560 (= _spx_5m_history_max)"
    )
    # Also verifies the seed-spx_history side effect (last 60 closes)
    assert len(feed.spx_history) == 60, (
        "backfill must seed spx_history with last 60 closes for "
        "warm-start of macd_signal / safe_return(48)"
    )


# ── Test 7: regression guard — daily-basis writer no longer fires ────────────

def test_append_spx_daily_return_does_not_write_realized_vol():
    """Under T-ACT-082 the daily-basis realized_vol_20d writer in
    `_append_spx_daily_return_if_due` is removed. This is a structural
    regression guard: any future change that re-introduces the
    deprecated daily-basis write path will fail this test, forcing the
    author to revisit the 5-min-basis migration rationale documented in
    the polygon_feed `__init__` block."""
    from polygon_feed import PolygonFeed

    feed = PolygonFeed.__new__(PolygonFeed)
    feed.redis_client = MagicMock()
    feed.spx_daily_returns = []
    feed._spx_daily_date_written = None

    def _fake_get(key):
        if key == "polygon:spx:prior_day_return":
            return "0.001"
        return None
    feed.redis_client.get.side_effect = _fake_get

    feed._append_spx_daily_return_if_due("2026-04-16")

    rv_writes = [
        call for call in feed.redis_client.setex.call_args_list
        if call.args and call.args[0] == "polygon:spx:realized_vol_20d"
    ]
    assert rv_writes == [], (
        "_append_spx_daily_return_if_due must NOT write "
        "polygon:spx:realized_vol_20d under T-ACT-082. The 5-min-basis "
        "writer in _compute_spx_features is the SOLE producer."
    )


# ── Test 8: regression guard — date guard preserved on no-realized-vol path ──

def test_daily_return_date_guard_still_persisted():
    """Even though T-ACT-082 removes the realized-vol write, the Redis
    restart-guard `polygon:spx:daily_returns:last_date` must still be
    written so a future daily-basis sibling can plug back in without
    re-introducing the deprecated semantics."""
    from polygon_feed import PolygonFeed

    feed = PolygonFeed.__new__(PolygonFeed)
    feed.redis_client = MagicMock()
    feed.spx_daily_returns = []
    feed._spx_daily_date_written = None

    def _fake_get(key):
        if key == "polygon:spx:prior_day_return":
            return "0.001"
        return None
    feed.redis_client.get.side_effect = _fake_get

    feed._append_spx_daily_return_if_due("2026-04-16")

    last_date_writes = [
        call for call in feed.redis_client.setex.call_args_list
        if call.args
        and call.args[0] == "polygon:spx:daily_returns:last_date"
    ]
    assert len(last_date_writes) == 1, (
        "Date guard write count regression"
    )
    key, ttl, value = last_date_writes[0].args
    assert ttl == 86400 * 25, (
        f"Date guard TTL regression: expected 25 days, got {ttl}"
    )
    assert value == "2026-04-16"
