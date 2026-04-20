"""
Consolidation Session 13 — Data Quality.
T1-1: holiday polling, T1-2: pre-market timing, T1-3: SPX cap,
T1-4: prior_day_return, T1-6: VIX TTL, T1-7: daily date persistence.

Note on T1-1 patch target: the spec template patches
`polygon_feed.is_market_open`, but the spec critical-rule #1 also
mandates that the import lives INSIDE _is_market_hours() (to avoid
circular-import risk against market_calendar). With a method-local
import, the symbol resolves on every call to
`market_calendar.is_market_open` — so that is the correct mock target.
Patching `polygon_feed.is_market_open` would silently no-op because
the name doesn't exist in polygon_feed's module namespace. We patch
`market_calendar.is_market_open` here — same behavioural coverage,
no false greens.
"""
import asyncio
import os
import sys
from unittest.mock import MagicMock, patch

import pytest  # noqa: F401  (pytest discovery)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── T1-1: _is_market_hours uses calendar ─────────────────────────────────────

def test_is_market_hours_uses_is_market_open():
    """_is_market_hours must call is_market_open(), not raw weekday."""
    from polygon_feed import PolygonFeed

    feed = PolygonFeed.__new__(PolygonFeed)
    feed.redis_client = MagicMock()

    with patch("market_calendar.is_market_open") as mock_open:
        mock_open.return_value = True
        result = feed._is_market_hours()

    mock_open.assert_called_once()
    assert result is True


def test_is_market_hours_returns_false_on_holiday():
    """_is_market_hours must return False on NYSE holidays."""
    from polygon_feed import PolygonFeed

    feed = PolygonFeed.__new__(PolygonFeed)
    feed.redis_client = MagicMock()

    with patch("market_calendar.is_market_open", return_value=False):
        result = feed._is_market_hours()

    assert result is False


def test_is_market_hours_falls_back_on_calendar_error():
    """_is_market_hours must fall back to weekday check if calendar errors."""
    from polygon_feed import PolygonFeed

    feed = PolygonFeed.__new__(PolygonFeed)
    feed.redis_client = MagicMock()

    with patch(
        "market_calendar.is_market_open",
        side_effect=Exception("calendar unavailable"),
    ):
        # Must not raise — falls back gracefully to weekday + time
        try:
            feed._is_market_hours()
        except Exception as e:
            raise AssertionError(
                f"_is_market_hours must not raise on calendar error: {e}"
            )


# ── T1-2: pre_market_scan at 9:35 ────────────────────────────────────────────

def test_pre_market_scan_scheduled_at_9_35():
    """pre_market_scan must be scheduled at 9:35 AM, not 9:00 AM."""
    path = os.path.join(os.path.dirname(__file__), "..", "main.py")
    with open(path, encoding="utf-8") as f:
        src = f.read()

    scan_block_start = src.find("trading_pre_market_scan")
    assert scan_block_start > -1, "trading_pre_market_scan id not found"

    # Look at the scheduler block that REGISTERS the job
    # (the first occurrence is the SQL row select; the registration
    # block has hour=9 + minute=N nearby).
    # Walk forward until we find an `add_job` block referencing it.
    register_idx = src.find("scheduler.add_job", scan_block_start - 600)
    while register_idx != -1:
        # Wide window — comment lines explaining the change can push
        # minute=35 several hundred chars past the add_job opener.
        block = src[register_idx: register_idx + 2000]
        if (
            "trading_pre_market_scan" in block
            and "pre_market_scan," in block
            and "hour=9" in block
        ):
            assert "minute=35" in block, (
                "pre_market_scan must be scheduled at minute=35 "
                "(9:35 AM ET). VVIX TTL expires before 9:00 AM, "
                "causing wrong day_type for entire session."
            )
            # Guard against the OLD value reappearing. Strip the
            # comment line that explains the change so we only flag
            # an active code-line `minute=0,`.
            code_only = "\n".join(
                ln for ln in block.splitlines()
                if not ln.lstrip().startswith("#")
            )
            assert "minute=0," not in code_only, (
                "pre_market_scan must not be at minute=0 (9:00 AM)."
            )
            return
        register_idx = src.find(
            "scheduler.add_job", register_idx + 1
        )
    raise AssertionError(
        "Could not find scheduler.add_job(...trading_pre_market_scan...) block"
    )


# ── T1-3: spx_history cap raised to 60 ───────────────────────────────────────

def test_spx_history_cap_is_60():
    """spx_history must be capped at 60 (not 20) to enable 4h return."""
    path = os.path.join(
        os.path.dirname(__file__), "..", "polygon_feed.py"
    )
    with open(path, encoding="utf-8") as f:
        src = f.read()
    assert "self.spx_history[-60:]" in src, (
        "spx_history must be capped at 60 samples for return_4h to work. "
        "Was -20 — safe_return(48) can never produce non-zero with 20 samples."
    )
    assert "self.spx_history[-20:]" not in src, (
        "old self.spx_history[-20:] cap must be removed"
    )


def test_return_4h_can_be_nonzero_with_60_samples():
    """With 60 varying prices in history, return_4h must be non-zero."""
    from polygon_feed import PolygonFeed

    feed = PolygonFeed.__new__(PolygonFeed)
    feed.redis_client = MagicMock()
    feed.spx_prev_session_close = None

    prices = [5200.0 + i * 0.5 for i in range(60)]
    feed.spx_history = prices

    asyncio.run(feed._compute_spx_features())

    written = {
        c.args[0]: c.args[2]
        for c in feed.redis_client.setex.call_args_list
        if "polygon:spx:return" in c.args[0]
    }
    r4h = float(written.get("polygon:spx:return_4h", "0"))
    assert r4h != 0.0, (
        "return_4h must be non-zero with 60 samples. "
        "Got 0.0 — history cap is still too small."
    )


# ── T1-4: prior_day_return uses session-over-session ─────────────────────────

def test_prior_day_return_uses_prev_session_close():
    """prior_day_return must use spx_prev_session_close, not 5-min bar."""
    from polygon_feed import PolygonFeed

    feed = PolygonFeed.__new__(PolygonFeed)
    feed.redis_client = MagicMock()
    feed.spx_prev_session_close = 5200.0  # Yesterday's close
    feed.spx_history = [5200.0] * 10 + [5252.0]  # Current ~+1%

    asyncio.run(feed._compute_spx_features())

    written = {
        c.args[0]: float(c.args[2])
        for c in feed.redis_client.setex.call_args_list
        if "prior_day_return" in c.args[0]
    }
    assert "polygon:spx:prior_day_return" in written, (
        "prior_day_return key not written"
    )
    assert abs(written["polygon:spx:prior_day_return"] - 0.01) < 0.001, (
        "prior_day_return should be ~0.01 (1%), got "
        f"{written['polygon:spx:prior_day_return']}"
    )


def test_prior_day_return_not_written_without_prev_close():
    """prior_day_return must NOT be written when prev_session_close absent."""
    from polygon_feed import PolygonFeed

    feed = PolygonFeed.__new__(PolygonFeed)
    feed.redis_client = MagicMock()
    feed.spx_prev_session_close = None
    feed.spx_history = [5200.0] * 10 + [5252.0]

    asyncio.run(feed._compute_spx_features())

    written_keys = [
        c.args[0] for c in feed.redis_client.setex.call_args_list
    ]
    assert "polygon:spx:prior_day_return" not in written_keys, (
        "prior_day_return must not be written with 5-min bar return when "
        "prev session close is unavailable"
    )


# ── T1-6: VIX z-score keys have TTL ──────────────────────────────────────────

def test_vix_zscore_keys_use_setex():
    """All polygon:vix:z_score* / 20d_* keys must use setex (with TTL)."""
    path = os.path.join(
        os.path.dirname(__file__), "..", "polygon_feed.py"
    )
    with open(path, encoding="utf-8") as f:
        src = f.read()

    bare_set_keys = [
        '"polygon:vix:z_score"',
        '"polygon:vix:z_score_daily"',
        '"polygon:vix:z_score_intraday"',
        '"polygon:vix:20d_mean"',
        '"polygon:vix:20d_std"',
    ]

    for key in bare_set_keys:
        idx = 0
        while True:
            pos = src.find(key, idx)
            if pos == -1:
                break
            # Look back ~50 chars for either .set( or .setex(
            context = src[max(0, pos - 50): pos]
            if ".set(" in context and ".setex(" not in context:
                raise AssertionError(
                    f"{key} uses bare .set() without TTL. "
                    "Must use .setex(7200, ...) to prevent stale "
                    "values after crash."
                )
            idx = pos + 1


# ── T1-7: daily date persisted to Redis ─────────────────────────────────────

def test_vix_daily_date_persisted_to_redis():
    """_store_vix_baseline must persist last_date to Redis."""
    path = os.path.join(
        os.path.dirname(__file__), "..", "polygon_feed.py"
    )
    with open(path, encoding="utf-8") as f:
        src = f.read()
    assert "daily_history:last_date" in src, (
        "VIX daily append date must be persisted to Redis key "
        "'polygon:vix:daily_history:last_date' to prevent double-"
        "append on restart."
    )


def test_vix_daily_date_redis_guard_prevents_double_append():
    """When Redis says today is already written, in-memory must sync but
    NO new append should land in vix_daily_history."""
    from polygon_feed import PolygonFeed
    import polygon_feed as pf_mod

    feed = PolygonFeed.__new__(PolygonFeed)
    feed.redis_client = MagicMock()
    feed.vix_history = [18.0] * 5
    # Pre-seed daily history at 19 entries; if a double-append happens
    # we'd see 20.
    feed.vix_daily_history = [18.0] * 19
    feed._vix_daily_date_written = None  # Simulate restart

    today_str = "2026-04-20"
    feed.redis_client.get.return_value = today_str  # decode_responses=True

    # Section 13 Batch 1: EOD gate moved 19:00 → 21:00 UTC so the
    # VIX/SPX daily samples are taken after the 16:00 ET cash close
    # and the IV/RV comparison is like-for-like close-to-close.
    fixed_now = pf_mod.datetime(
        2026, 4, 20, 21, 30, tzinfo=pf_mod.timezone.utc
    )

    class _DT:
        @staticmethod
        def now(tz=None):
            return fixed_now

    with patch.object(pf_mod, "datetime", _DT):
        feed._store_vix_baseline(19.0)

    assert len(feed.vix_daily_history) == 19, (
        "Redis-guarded double-append must NOT add a new sample. "
        f"Got {len(feed.vix_daily_history)} entries (expected 19)."
    )
    assert feed._vix_daily_date_written == today_str, (
        "in-memory _vix_daily_date_written must sync to today_str"
    )
