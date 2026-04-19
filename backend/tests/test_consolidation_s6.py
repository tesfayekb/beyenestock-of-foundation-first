"""Consolidation Sprint — Session 6 regression tests.

Locks down the data-feed correctness fixes from this session:

  E-1   _fetch_spx_price() replaces _fetch_spx_close() — live snapshot
        instead of yesterday's close, so spx_history actually contains
        intraday prices and return_5m/30m/1h/4h reflect real moves.
  E-1b  _fetch_spx_close() preserved as a thin backward-compat wrapper
        so existing tests / callers that mock it keep working.
  E-2a  vix_daily_history seeded from the same daily-aggregates
        backfill that already seeds vix_history.
  E-2b  polygon:vix:z_score_daily written whenever the daily window
        has >= 5 samples (slow regime variable, separate from the
        5-min intraday rolling window).
  E-2c  polygon:vix:z_score_intraday written from the 5-min window
        for fast intraday signals.
  E-4   databento_feed reads polygon:vix:current for implied_vol
        instead of hard-coding 0.20.
  P1-4  prediction_engine regime selection uses gex_conf >= 0.4
        (matches strategy_selector pin gate). Data-quality gate at
        0.3 preserved — they serve different purposes.
"""
import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

# Ensure backend/ is importable regardless of test runner cwd.
_BACKEND_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)


def _build_async_client_mock(status, json_payload, capture_urls=None):
    """Context-manager AsyncClient mock returning the given payload.

    If capture_urls is a list, every URL passed to .get() is appended
    so tests can assert which endpoint was hit.
    """
    mock_resp = MagicMock()
    mock_resp.status_code = status
    mock_resp.json.return_value = json_payload

    async def _get(url, *args, **kwargs):
        if capture_urls is not None:
            capture_urls.append(url)
        return mock_resp

    mock_session = MagicMock()
    mock_session.get = AsyncMock(side_effect=_get)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    return mock_session


# ── E-1: live SPX snapshot ────────────────────────────────────────────

def test_fetch_spx_price_uses_snapshot_not_prev():
    """_fetch_spx_price must hit /v3/snapshot, never /v2/aggs.../prev."""
    import config
    from polygon_feed import PolygonFeed

    feed = PolygonFeed.__new__(PolygonFeed)
    feed.last_vvix = None
    feed.redis_client = MagicMock()

    urls = []
    payload = {
        "results": [{"session": {"close": 5285.5, "last": 5285.5}}]
    }
    mock_session = _build_async_client_mock(200, payload, capture_urls=urls)

    with patch.object(config, "POLYGON_API_KEY", "fake-key"):
        with patch("httpx.AsyncClient", return_value=mock_session):
            result = asyncio.run(feed._fetch_spx_price())

    assert result == 5285.5
    assert any("snapshot" in u for u in urls), (
        f"Expected snapshot endpoint, urls hit: {urls}"
    )
    assert not any("/prev" in u for u in urls), (
        "Must NOT use /prev — that returns yesterday's close"
    )


def test_fetch_spx_close_is_backward_compat_wrapper():
    """_fetch_spx_close must delegate to _fetch_spx_price (kept for
    test compatibility — must not be removed)."""
    from polygon_feed import PolygonFeed

    feed = PolygonFeed.__new__(PolygonFeed)
    feed.redis_client = MagicMock()

    sentinel = 5300.25

    async def fake_price():
        return sentinel

    feed._fetch_spx_price = fake_price
    result = asyncio.run(feed._fetch_spx_close())
    assert result == sentinel, (
        "_fetch_spx_close must delegate to _fetch_spx_price"
    )


def test_spx_intraday_returns_reflect_history_movement():
    """With varying intraday prices in spx_history the multi-timeframe
    return features must NOT all collapse to 0.0 (the prev-close bug)."""
    from polygon_feed import PolygonFeed

    feed = PolygonFeed.__new__(PolygonFeed)
    feed.redis_client = MagicMock()
    # Simulate ~14 polls of real intraday movement.
    feed.spx_history = [
        5200.0, 5205.0, 5210.0, 5208.0, 5215.0,
        5220.0, 5218.0, 5225.0, 5230.0, 5228.0,
        5235.0, 5240.0, 5238.0, 5245.0,
    ]

    asyncio.run(feed._compute_spx_features())

    written = {
        c.args[0]: c.args[2]
        for c in feed.redis_client.setex.call_args_list
        if "polygon:spx:return" in c.args[0]
    }
    r5m = float(written.get("polygon:spx:return_5m", 0))
    r1h = float(written.get("polygon:spx:return_1h", 0))

    # With genuinely-varying prices at least one return must be non-zero.
    assert r5m != 0.0 or r1h != 0.0, (
        "All intraday returns are 0 — likely the prev-close bug"
        f" (writes: {written})"
    )


# ── E-2: VIX daily/intraday split ─────────────────────────────────────

def test_vix_daily_history_seeded_by_backfill():
    """_backfill_vix_history must seed vix_daily_history alongside
    vix_history so the slow-regime z-score is meaningful from minute 1."""
    import config
    from polygon_feed import PolygonFeed

    feed = PolygonFeed.__new__(PolygonFeed)
    feed.vix_history = []
    feed.vix_daily_history = []
    feed.redis_client = MagicMock()

    fake_results = [{"c": 17.0 + i * 0.2} for i in range(22)]
    mock_session = _build_async_client_mock(200, {"results": fake_results})

    with patch.object(config, "POLYGON_API_KEY", "fake-key"):
        with patch("httpx.AsyncClient", return_value=mock_session):
            asyncio.run(feed._backfill_vix_history())

    assert len(feed.vix_daily_history) == 20, (
        f"Expected 20 daily samples after backfill, got "
        f"{len(feed.vix_daily_history)}"
    )
    # Both series should start identical — they only diverge live.
    assert feed.vix_history == feed.vix_daily_history


def test_z_score_daily_key_written_when_daily_history_present():
    """polygon:vix:z_score_daily MUST be written when vix_daily_history
    has >= 5 samples — that's the key strategy_selector now reads."""
    from polygon_feed import PolygonFeed

    feed = PolygonFeed.__new__(PolygonFeed)
    feed.redis_client = MagicMock()
    feed.vix_history = []
    feed.vix_daily_history = [17.0 + i * 0.1 for i in range(20)]
    feed._vix_daily_date_written = None

    feed._store_vix_baseline(20.0)

    written_keys = [c.args[0] for c in feed.redis_client.set.call_args_list]
    assert "polygon:vix:z_score_daily" in written_keys, (
        f"polygon:vix:z_score_daily not written. Keys: {written_keys}"
    )
    # Legacy key must still be written for backward compat during rollout.
    assert "polygon:vix:z_score" in written_keys, (
        "Legacy polygon:vix:z_score must still be written"
    )


def test_z_score_intraday_key_written_from_5min_window():
    """polygon:vix:z_score_intraday MUST be written from the 5-min
    rolling vix_history (separate from the slow daily z-score)."""
    from polygon_feed import PolygonFeed

    feed = PolygonFeed.__new__(PolygonFeed)
    feed.redis_client = MagicMock()
    # 5 varying intraday samples already collected (will become 6 after append).
    feed.vix_history = [18.0, 18.2, 18.5, 18.3, 18.7]
    feed.vix_daily_history = []
    feed._vix_daily_date_written = None

    feed._store_vix_baseline(19.1)

    written_keys = [c.args[0] for c in feed.redis_client.set.call_args_list]
    assert "polygon:vix:z_score_intraday" in written_keys, (
        f"polygon:vix:z_score_intraday not written. Keys: {written_keys}"
    )


# ── E-4: live VIX in databento implied_vol ────────────────────────────

def test_databento_trade_uses_live_vix_not_hardcoded():
    """databento_feed must read polygon:vix:current for implied_vol
    instead of the previous hard-coded 0.20."""
    path = os.path.join(_BACKEND_DIR, "databento_feed.py")
    with open(path, encoding="utf-8") as f:
        src = f.read()

    assert '"implied_vol": 0.20' not in src, (
        'Hard-coded "implied_vol": 0.20 still present in databento_feed.py'
    )
    assert "polygon:vix:current" in src, (
        "databento_feed must read polygon:vix:current for implied_vol"
    )
    # Sanity clamp should also be present — VIX/100 can occasionally
    # spike to extreme values on a malformed write.
    assert "max(0.05" in src and "min(implied_vol" in src, (
        "Sanity clamp max(0.05, min(implied_vol, 2.0)) is required"
    )


# ── P1-4: gex_conf threshold alignment ────────────────────────────────

def test_regime_selection_uses_04_threshold():
    """prediction_engine regime selection must use gex_conf >= 0.4
    (matches strategy_selector pin gate). Data-quality gate at 0.3
    must still exist — they serve different purposes."""
    path = os.path.join(_BACKEND_DIR, "prediction_engine.py")
    with open(path, encoding="utf-8") as f:
        src = f.read()

    assert "gex_conf >= 0.4" in src, (
        "Regime selection must use gex_conf >= 0.4 (line ~317)"
    )
    assert "gex_conf < 0.3" in src, (
        "Data-quality gate gex_conf < 0.3 (line ~257) must be preserved"
    )


def test_strategy_selector_pin_still_uses_04_threshold():
    """strategy_selector pin override must still use gex_conf >= 0.4
    (this is the gate prediction_engine is now aligned to)."""
    path = os.path.join(_BACKEND_DIR, "strategy_selector.py")
    with open(path, encoding="utf-8") as f:
        src = f.read()
    assert "gex_conf >= 0.4" in src, (
        "strategy_selector pin override must use gex_conf >= 0.4"
    )


def test_strategy_selector_prefers_z_score_daily():
    """strategy_selector must prefer polygon:vix:z_score_daily over
    the legacy polygon:vix:z_score key for Signals D + F."""
    path = os.path.join(_BACKEND_DIR, "strategy_selector.py")
    with open(path, encoding="utf-8") as f:
        src = f.read()
    assert "polygon:vix:z_score_daily" in src, (
        "strategy_selector must read polygon:vix:z_score_daily"
        " for Signals D + F"
    )
