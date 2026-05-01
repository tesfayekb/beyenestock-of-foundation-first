import asyncio
import json
from datetime import datetime, time, timezone
from statistics import mean, pstdev
from typing import List, Optional

import redis

from config import REDIS_URL
from db import get_client, write_health_status
from logger import get_logger

logger = get_logger("polygon_feed")


class PolygonFeed:
    def __init__(self) -> None:
        self.redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
        self.last_vvix: Optional[float] = None
        self.history: List[float] = []
        self.spx_history: List[float] = []
        # T1-4: true previous-session SPX close, fetched once per
        # session from /v2/aggs/ticker/I:SPX/prev. Used by
        # _compute_spx_features() to write a real session-over-session
        # prior_day_return instead of the 5-min-bar return that the
        # original implementation accidentally wrote under the same key.
        self.spx_prev_session_close: Optional[float] = None
        self.last_vix: Optional[float] = None
        # B-1: 5-min intraday rolling VIX window (~100 min when full).
        # Used for the fast intraday z-score and realised-vol calc.
        self.vix_history: List[float] = []
        # E-2: separate slow-regime VIX history — one sample per
        # trading day, seeded from the daily-aggregates backfill on
        # startup and appended once per session at/after 21:00 UTC
        # (~5 PM ET, after NYSE close at 16:00 ET). The close-to-close
        # timing matters: VIX and SPX daily samples must both be taken
        # after the cash close so the IV/RV comparison in the regime
        # engine compares like-for-like sessions. _vix_daily_date_written
        # guarantees one append per UTC date so multiple polls in the
        # same session can't over-saturate the rolling window.
        self.vix_daily_history: List[float] = []
        self._vix_daily_date_written: Optional[str] = None
        # 12A: True 20-day SPX daily realized vol. The prior
        # implementation read self.spx_history (5-minute intraday
        # bars, 60 samples max) and wrote the variance-of-5-min-log-
        # returns * sqrt(252) to polygon:spx:realized_vol_20d. The
        # annualization factor 252 is for *daily* returns, so
        # annualizing 5-min returns that way underestimates by a
        # factor of sqrt(78) ≈ 8.8 — producing 1.05-1.29% instead of
        # the true ~15-20% SPX daily RV. Every downstream consumer
        # (P0.4 IV/RV filter, LightGBM iv_rv_ratio feature, butterfly
        # threshold tuning) read garbage.
        #
        # The new series is appended once per trading day in the same
        # 19:00 UTC EOD gate as the VIX daily history (T1-7 pattern),
        # sourcing each sample from polygon:spx:prior_day_return (the
        # session-over-session return fixed by T1-4 in S13). Capped at
        # 20 trading days.
        self.spx_daily_returns: List[float] = []
        self._spx_daily_date_written: Optional[str] = None
        # T1-7 pattern: restore last-append date from Redis so a
        # process restart near EOD can't double-append the same
        # calendar day. Independent of the VIX guard — SPX may have
        # appended today even if VIX hasn't, or vice versa. Best-
        # effort: if Redis is unavailable at startup, fall back to
        # the in-memory guard only (matches VIX's graceful degrade).
        try:
            _last_spx_date = self.redis_client.get(
                "polygon:spx:daily_returns:last_date"
            )
            if _last_spx_date:
                self._spx_daily_date_written = (
                    _last_spx_date.decode()
                    if isinstance(_last_spx_date, bytes)
                    else _last_spx_date
                )
        except Exception:
            pass  # Redis unavailable — in-memory guard only
        # B-2: latest VIX9D value (Signal A term ratio numerator).
        self.last_vix9d: Optional[float] = None
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        # A-startup: seed vix_history from Polygon daily aggregates so
        # the rolling z-score is meaningful from minute 1. Without this,
        # the first 5 polling cycles (~25 min) return z_score=0.0 and
        # Signals D/F see has_vix_z_data=False during that window.
        # Failure here is non-fatal — we log and continue with an empty
        # history (the original cold-start behaviour).
        try:
            await self._backfill_vix_history()
        except Exception as exc:
            logger.warning("vix_history_backfill_skipped", error=str(exc))

        heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        poll_task = asyncio.create_task(self._poll_loop())
        await asyncio.gather(heartbeat_task, poll_task)

    async def stop(self) -> None:
        self._stop_event.set()

    async def _poll_loop(self) -> None:
        while not self._stop_event.is_set():
            if self._is_market_hours():
                try:
                    current = await self._fetch_vvix()
                    self.last_vvix = current
                    self.history.append(current)
                    self.history = self.history[-20:]
                    self._store_baseline(current)

                    # Fetch VIX and SPX close for IV/RV filter
                    try:
                        vix = await self._fetch_vix()
                        self.redis_client.setex(
                            "polygon:vix:current", 3600, str(vix)
                        )

                        # B-1: 20-day rolling VIX z-score for Signals D + F.
                        # Writes polygon:vix:z_score (and 20d_mean / 20d_std).
                        # Without this, Signal-D and Signal-F always read 0.0
                        # and stay neutral — defeating the size-cut logic.
                        try:
                            self._store_vix_baseline(vix)
                        except Exception as bl_exc:
                            logger.warning(
                                "vix_baseline_store_failed",
                                error=str(bl_exc),
                            )

                        # B-2: VIX9D (9-day implied vol) for Signal-A term
                        # ratio. Without this, vix_term_ratio falls back
                        # to 1.0 and Signal-A stays neutral.
                        try:
                            vix9d = await self._fetch_vix9d()
                            if vix9d is not None and vix9d > 0:
                                self.redis_client.setex(
                                    "polygon:vix9d:current",
                                    3600,
                                    str(vix9d),
                                )
                        except Exception as v9_exc:
                            logger.warning(
                                "vix9d_fetch_failed",
                                error=str(v9_exc),
                            )

                        # E-1: live intraday SPX price (was prev-day close).
                        spx_price = await self._fetch_spx_price()
                        if spx_price and spx_price > 0:
                            self.spx_history.append(spx_price)
                            # T1-3: was -20. safe_return(48) for the
                            # 4-hour intraday return needs >48 samples;
                            # 20 is mathematically incapable of producing
                            # a non-zero return_4h. 60 = 5h of 5-min
                            # bars (full RTH session) — covers all
                            # multi-timeframe LightGBM features.
                            self.spx_history = self.spx_history[-60:]

                            # 2026-05-01 SPX-real-time-feed fix: write the
                            # real-time SPX spot price to a dedicated Redis
                            # key for live-decision-path consumers
                            # (prediction_engine, mark_to_market,
                            # strike_selector, strategy_selector,
                            # shadow_engine, gex_engine, databento_feed).
                            # Previously these all read tradier:quotes:SPX
                            # which is 15-min delayed in Tradier sandbox per
                            # empirical verification (Polygon 13:45 SPX bar
                            # 7244.80-7249.24 vs system-recorded 7209.01).
                            # TTL = 600s (2x the 5-min poll period above)
                            # so the key spans 2 poll cycles; downstream
                            # freshness guard uses 330s threshold.
                            try:
                                self.redis_client.setex(
                                    "polygon:spx:current",
                                    600,
                                    json.dumps({
                                        "price": float(spx_price),
                                        "fetched_at": datetime.now(
                                            timezone.utc
                                        ).isoformat(),
                                        "source": "polygon_v3_snapshot",
                                    }),
                                )
                            except Exception as spx_write_err:
                                logger.warning(
                                    "polygon_spx_current_write_failed",
                                    error=str(spx_write_err),
                                )

                        # T1-4: fetch true prior-session close once per
                        # day. Re-fetch at the open minute (9:30) so a
                        # process that was already running yesterday
                        # picks up the new prior close on the new day.
                        if (
                            self.spx_prev_session_close is None
                            or self._is_open_minute()
                        ):
                            try:
                                prev = await self._fetch_spx_prev_close()
                                if prev:
                                    self.spx_prev_session_close = prev
                            except Exception as prev_exc:
                                logger.debug(
                                    "polygon_spx_prev_close_skipped",
                                    error=type(prev_exc).__name__,
                                )

                        # 12A: polygon:spx:realized_vol_20d is now
                        # written once per trading day in
                        # _append_spx_daily_return_if_due (called from
                        # _store_vix_baseline's 19:00 UTC gate).
                        # Writing it here from 5-minute intraday bars
                        # annualized with the daily factor 252 was the
                        # root cause of the 1.05-1.29% garbage values
                        # that poisoned every downstream consumer —
                        # see __init__ for the full analysis.
                    except Exception as exc:
                        logger.warning("polygon_iv_rv_update_failed", error=str(exc))

                    # Compute and store SPX technical features for LightGBM
                    try:
                        await self._compute_spx_features()
                    except Exception as feat_exc:
                        logger.warning("spx_features_update_failed", error=str(feat_exc))

                    await self._write_daily_open_if_needed(current)
                except Exception as exc:
                    logger.warning("polygon_vvix_poll_failed", error=str(exc))
            await asyncio.sleep(300)

    async def _heartbeat_loop(self) -> None:
        while not self._stop_event.is_set():
            # C-3: emit health under this feed's own service name. The
            # generic ingestor name is reserved for the orchestrator
            # startup write in main.py.on_startup; emitting it from
            # here masked polygon_feed's true health on the dashboard.
            write_health_status(
                "polygon_feed",
                "healthy",
                latency_ms=0,
                data_lag_seconds=0,
            )
            await asyncio.sleep(10)

    def _store_baseline(self, current: float) -> None:
        # P1-16: every polygon:vvix:* write uses setex(3600) so a crashed
        # poller can never leave stale VVIX values in Redis indefinitely.
        # 1-hour TTL is comfortably longer than the 10-second polling
        # cadence — under healthy operation each key is overwritten well
        # before expiry; under an outage the keys vanish and downstream
        # readers (regime, prediction) cleanly fall back to defaults
        # instead of trading on yesterday's vol.
        self.redis_client.setex("polygon:vvix:current", 3600, str(current))
        if len(self.history) < 20:
            self.redis_client.setex(
                "polygon:vvix:baseline_ready", 3600, "False"
            )
            self.redis_client.setex(
                "polygon:vvix:fallback_thresholds",
                3600,
                json.dumps([120, 140, 160]),
            )
            return

        avg = mean(self.history)
        std = pstdev(self.history) or 0.0
        z_score = (current - avg) / std if std > 0 else 0.0

        self.redis_client.setex("polygon:vvix:20d_mean", 3600, str(avg))
        self.redis_client.setex("polygon:vvix:20d_std", 3600, str(std))
        self.redis_client.setex("polygon:vvix:z_score", 3600, str(z_score))
        self.redis_client.setex(
            "polygon:vvix:baseline_ready", 3600, "True"
        )

    def _store_vix_baseline(self, current: float) -> None:
        """
        Compute VIX z-scores — daily (slow regime) and intraday (fast).

        E-2 fix: separate daily vs intraday histories.
          * vix_history          — 5-min rolling window, 20 samples (~100 min).
                                   Used for the FAST intraday z-score
                                   (polygon:vix:z_score_intraday).
          * vix_daily_history    — one sample per trading day, seeded from
                                   the daily-aggregates backfill and appended
                                   once per session at/after 19:00 UTC.
                                   Used for the SLOW regime z-score
                                   (polygon:vix:z_score_daily).

        polygon:vix:z_score is also written for backward compatibility
        with callers that still read the legacy key. It mirrors the
        daily z-score whenever the daily window has at least 5 samples,
        and falls back to the intraday window otherwise so the key is
        never blank during cold-start.
        """
        # --- Intraday: 5-min rolling window (unchanged from B-1) ---
        self.vix_history.append(current)
        self.vix_history = self.vix_history[-20:]

        if len(self.vix_history) >= 5:
            n_i = len(self.vix_history)
            avg_i = sum(self.vix_history) / n_i
            var_i = sum((x - avg_i) ** 2 for x in self.vix_history) / n_i
            std_i = var_i ** 0.5
            if std_i > 0:
                z_intraday = round((current - avg_i) / std_i, 4)
                # T1-6: 2-hour TTL — 24x the 5-min poll cadence so the
                # key is always overwritten under healthy operation,
                # but expires within 2h if the feed crashes (instead
                # of persisting a stale z-score forever).
                self.redis_client.setex(
                    "polygon:vix:z_score_intraday",
                    7200,
                    str(z_intraday),
                )

        # --- Daily: one append per trading day, after 19:00 UTC (~3 PM ET) ---
        # Backfill seeds 20 days at startup; the live append fires only
        # once per session (guarded by _vix_daily_date_written) so the
        # rolling 20-day window genuinely slides one sample per day,
        # not one per 5-minute poll.
        #
        # Lazy-init the daily attributes so older callers / tests that
        # construct PolygonFeed via __new__ and only populate vix_history
        # keep working without modification.
        if not hasattr(self, "vix_daily_history"):
            self.vix_daily_history = []
        if not hasattr(self, "_vix_daily_date_written"):
            self._vix_daily_date_written = None

        now = datetime.now(timezone.utc)
        today_str = now.strftime("%Y-%m-%d")
        if (
            now.hour >= 21
            and self._vix_daily_date_written != today_str
        ):
            # T1-7: cross-check Redis so a process restart near EOD
            # cannot double-append the same calendar day. The
            # in-memory _vix_daily_date_written guard is wiped on
            # every restart; without this Redis check, deploying at
            # (say) 7:05 PM UTC after the daily append already ran at
            # 7:00 PM UTC would land a second sample for the same
            # date — biasing the rolling 20-day window for the next
            # 20 sessions.
            try:
                redis_last = self.redis_client.get(
                    "polygon:vix:daily_history:last_date"
                )
                # Production redis client uses decode_responses=True
                # (returns str), but be defensive in case the client
                # is constructed differently in tests.
                if isinstance(redis_last, bytes):
                    redis_last = redis_last.decode()

                if redis_last == today_str:
                    # Already appended today (likely in a prior
                    # process). Sync the in-memory guard but FALL
                    # THROUGH so we still recompute and write the
                    # z-score with the current sample — only the
                    # history append is skipped.
                    self._vix_daily_date_written = today_str
                else:
                    self.vix_daily_history.append(current)
                    self.vix_daily_history = self.vix_daily_history[-20:]
                    self._vix_daily_date_written = today_str
                    # 48h TTL = survives a long weekend; the next
                    # 19:00 UTC append on the following session
                    # overwrites it cleanly.
                    self.redis_client.setex(
                        "polygon:vix:daily_history:last_date",
                        86400 * 2,
                        today_str,
                    )
            except Exception:
                # Redis failure — degrade to the original in-memory-
                # only guard. Worst case is one duplicated append
                # after a restart while Redis is down; better than
                # silently skipping the daily sample entirely.
                self.vix_daily_history.append(current)
                self.vix_daily_history = self.vix_daily_history[-20:]
                self._vix_daily_date_written = today_str

        # 12A: SPX daily realized vol — share the same 21:00 UTC EOD
        # gate as VIX (but with an INDEPENDENT date-written guard so a
        # VIX-only skip in the block above doesn't block SPX, and vice
        # versa). Co-locating both daily updates here means a single
        # code path runs after the 16:00 ET cash close; _poll_loop no
        # longer touches polygon:spx:realized_vol_20d.
        if now.hour >= 21:
            self._append_spx_daily_return_if_due(today_str)

        # --- Compute the regime z-score (daily preferred, intraday fallback) ---
        # Need at least 5 samples either way. If the daily window hasn't
        # reached 5 entries yet (cold start before backfill landed) we
        # transparently fall back to the intraday window so downstream
        # consumers always have a value.
        if len(self.vix_daily_history) >= 5:
            hist = self.vix_daily_history
            source = "daily"
        elif len(self.vix_history) >= 5:
            hist = self.vix_history
            source = "intraday_fallback"
        else:
            return  # Not enough data anywhere yet

        n = len(hist)
        avg = sum(hist) / n
        variance = sum((x - avg) ** 2 for x in hist) / n
        std = variance ** 0.5

        if std <= 0:
            return  # Zero variance — z-score undefined

        z_score = round((current - avg) / std, 4)
        # T1-6: every VIX z-score / stat key now uses setex(7200).
        # Bare .set() left these keys in Redis indefinitely — if the
        # poller crashed mid-session the regime engine would keep
        # reading yesterday's z-score for hours/days until manual
        # intervention. 2h TTL = 24x the 5-min poll cadence, so the
        # key is overwritten well before expiry under healthy ops.
        self.redis_client.setex(
            "polygon:vix:20d_mean", 7200, str(round(avg, 4))
        )
        self.redis_client.setex(
            "polygon:vix:20d_std", 7200, str(round(std, 4))
        )
        # Legacy key — kept for backward compat during the rollout.
        # New callers should read polygon:vix:z_score_daily instead.
        self.redis_client.setex(
            "polygon:vix:z_score", 7200, str(z_score)
        )
        self.redis_client.setex(
            "polygon:vix:z_score_daily", 7200, str(z_score)
        )
        logger.debug(
            "polygon_vix_zscore_updated",
            vix=round(current, 2),
            mean=round(avg, 2),
            std=round(std, 2),
            z_score=z_score,
            history_source=source,
            daily_days=len(self.vix_daily_history),
            history_len=n,
        )

    def _append_spx_daily_return_if_due(self, today_str: str) -> None:
        """12A: Append today's SPX session return to the 20-day rolling
        window and recompute true daily realized vol.

        Source: polygon:spx:prior_day_return, set once per poll in
        _compute_spx_features() as
            (live_price - prior_session_close) / prior_session_close
        — the genuine session-over-session return fixed by T1-4 in S13.

        Guards:
          * In-memory: _spx_daily_date_written prevents re-append within
            the same process after the first EOD pass.
          * Redis: polygon:spx:daily_returns:last_date (25-day TTL,
            restored in __init__) survives process restarts so a
            restart at 19:05 UTC after an append at 19:00 UTC cannot
            double-count. Mirrors T1-7's VIX daily history guard.

        Writes (best-effort, never raises):
          * polygon:spx:realized_vol_20d     — 24h TTL. Only when
            len(spx_daily_returns) >= 5. Downstream readers
            (prediction_engine IV/RV filter) already apply a
            rv_val >= 5.0 warmth guard, so the 1-4 day cold-start
            window is explicitly tolerated.
          * polygon:spx:daily_returns:last_date — 25-day TTL restart
            guard (comfortably covers long holiday weekends).
        """
        # Lazy-init for callers that bypass __init__ via __new__ (tests).
        if not hasattr(self, "spx_daily_returns"):
            self.spx_daily_returns = []
        if not hasattr(self, "_spx_daily_date_written"):
            self._spx_daily_date_written = None

        if self._spx_daily_date_written == today_str:
            return  # already appended today

        try:
            spx_return_raw = self.redis_client.get(
                "polygon:spx:prior_day_return"
            )
            if spx_return_raw is None:
                # prior_day_return hasn't landed yet (cold start, or
                # _fetch_spx_prev_close failed). Skip cleanly — next
                # session will retry.
                return

            daily_return = float(spx_return_raw)
            self.spx_daily_returns.append(daily_return)

            # Cap the rolling window at 20 trading days.
            if len(self.spx_daily_returns) > 20:
                self.spx_daily_returns = self.spx_daily_returns[-20:]

            self._spx_daily_date_written = today_str

            # Persist last-date to Redis (25-day TTL).
            self.redis_client.setex(
                "polygon:spx:daily_returns:last_date",
                86400 * 25,
                today_str,
            )

            if len(self.spx_daily_returns) >= 5:
                import math
                n = len(self.spx_daily_returns)
                mean_r = sum(self.spx_daily_returns) / n
                variance = sum(
                    (r - mean_r) ** 2 for r in self.spx_daily_returns
                ) / n
                realized_vol = math.sqrt(variance * 252) * 100
                self.redis_client.setex(
                    "polygon:spx:realized_vol_20d",
                    86400,
                    str(round(realized_vol, 4)),
                )
                logger.info(
                    "polygon_spx_daily_rv_updated",
                    realized_vol=round(realized_vol, 2),
                    daily_days=n,
                    latest_return=round(daily_return, 4),
                )
        except Exception as exc:
            logger.warning(
                "polygon_spx_daily_rv_failed",
                error=str(exc),
            )

    async def _write_daily_open_if_needed(self, vvix_open: float) -> None:
        if not self._is_open_minute():
            return
        today = datetime.now(timezone.utc).date().isoformat()
        get_client().table("trading_sessions").update({"vvix_open": vvix_open}).eq(
            "session_date", today
        ).execute()

    async def _fetch_vvix(self) -> float:
        """
        Fetch current VVIX from Polygon.io indices API.
        Uses I:VVIX namespace (not stock VVIX).
        Uses Authorization header to prevent key leaking in logs.
        Falls back to last known value or 120.0 if unavailable.
        """
        try:
            import config
            api_key = config.POLYGON_API_KEY
            if not api_key:
                return self.last_vvix if self.last_vvix is not None else 120.0

            import httpx
            # Use indices endpoint — I:VVIX is the correct Polygon namespace
            # /v2/aggs/ticker/{ticker}/prev returns previous session close
            # For intraday, use snapshot: /v3/snapshot?ticker.any_of=I:VVIX
            # Use snapshot for most current value during market hours
            url = "https://api.polygon.io/v3/snapshot"
            headers = {"Authorization": f"Bearer {api_key}"}
            params = {"ticker.any_of": "I:VVIX"}

            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=headers, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    results = data.get("results", [])
                    if results:
                        # Extract last value from snapshot
                        session = results[0].get("session", {})
                        vvix = float(
                            session.get("close")
                            or session.get("prev_close")
                            or 120.0
                        )
                        self.last_vvix = vvix
                        logger.info("polygon_vvix_fetched", vvix=vvix)
                        return vvix
                elif resp.status_code == 403:
                    # Plan may not cover indices snapshot — fall back to prev close
                    url_fallback = (
                        "https://api.polygon.io/v2/aggs/ticker/I:VVIX/prev"
                    )
                    resp2 = await client.get(url_fallback, headers=headers)
                    if resp2.status_code == 200:
                        data2 = resp2.json()
                        results2 = data2.get("results", [])
                        if results2:
                            vvix = float(results2[0].get("c", 120.0))
                            self.last_vvix = vvix
                            return vvix
        except Exception as e:
            # Scrub exception message to avoid leaking API key
            logger.warning("polygon_vvix_fetch_failed", error=type(e).__name__)

        return self.last_vvix if self.last_vvix is not None else 120.0

    async def _fetch_vix(self) -> float:
        """
        Fetch current VIX from Polygon.io.
        Uses I:VIX index. Falls back to last known value or 18.0.
        """
        try:
            import config
            api_key = config.POLYGON_API_KEY
            if not api_key:
                return self.last_vix if self.last_vix is not None else 18.0

            import httpx
            headers = {"Authorization": f"Bearer {api_key}"}

            # Try snapshot first
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://api.polygon.io/v3/snapshot",
                    headers=headers,
                    params={"ticker.any_of": "I:VIX"},
                )
                if resp.status_code == 200:
                    results = resp.json().get("results", [])
                    if results:
                        session_data = results[0].get("session", {})
                        vix = float(
                            session_data.get("close")
                            or session_data.get("prev_close")
                            or 18.0
                        )
                        self.last_vix = vix
                        return vix

                # Fallback: previous day aggregate
                resp2 = await client.get(
                    "https://api.polygon.io/v2/aggs/ticker/I:VIX/prev",
                    headers=headers,
                )
                if resp2.status_code == 200:
                    results2 = resp2.json().get("results", [])
                    if results2:
                        vix = float(results2[0].get("c", 18.0))
                        self.last_vix = vix
                        return vix
        except Exception as e:
            logger.warning("polygon_vix_fetch_failed", error=type(e).__name__)

        return self.last_vix if self.last_vix is not None else 18.0

    async def _fetch_vix9d(self) -> Optional[float]:
        """
        B-2: Fetch VIX9D (9-day implied volatility) from Polygon.io.
        Ticker: I:VIX9D

        VIX9D is the numerator of the term ratio used by Signal-A:
            vix_term_ratio = VIX9D / VIX
        ratio > 1.0 = inverted term structure = elevated near-term risk.

        Returns None on failure (caller skips Redis write).
        Mirrors _fetch_vix() structure exactly.
        """
        try:
            import config
            api_key = config.POLYGON_API_KEY
            if not api_key:
                return None

            import httpx
            headers = {"Authorization": f"Bearer {api_key}"}

            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://api.polygon.io/v3/snapshot",
                    headers=headers,
                    params={"ticker.any_of": "I:VIX9D"},
                )
                if resp.status_code == 200:
                    results = resp.json().get("results", [])
                    if results:
                        session_data = results[0].get("session", {})
                        vix9d = float(
                            session_data.get("close")
                            or session_data.get("prev_close")
                            or 0
                        )
                        if vix9d > 0:
                            self.last_vix9d = vix9d
                            return vix9d

                # Fallback: previous day aggregate
                resp2 = await client.get(
                    "https://api.polygon.io/v2/aggs/ticker/I:VIX9D/prev",
                    headers=headers,
                )
                if resp2.status_code == 200:
                    results2 = resp2.json().get("results", [])
                    if results2:
                        vix9d = float(results2[0].get("c", 0.0))
                        if vix9d > 0:
                            self.last_vix9d = vix9d
                            return vix9d
        except Exception as e:
            logger.debug(
                "polygon_vix9d_fetch_failed",
                error=type(e).__name__,
            )
        return None

    async def _backfill_vix_history(self) -> None:
        """
        A-startup: backfill vix_history with up to 20 trading days of
        historical VIX closes from Polygon, called once at startup.

        Without this, the first 5 polling cycles return z_score=0.0
        and Signal-D/F log has_vix_z_data=False until vix_history
        organically reaches 5 entries (~25 min after first poll).

        Uses the Polygon daily aggregates endpoint for I:VIX. Requests
        a 35-calendar-day window so we end up with ~22-25 trading-day
        closes after weekends/holidays drop out, then we keep the last
        20 (matching _store_vix_baseline's window).

        Fails silently — never blocks startup if Polygon is down or the
        API key is missing.
        """
        try:
            import config
            if not getattr(config, "POLYGON_API_KEY", ""):
                logger.debug("vix_history_backfill_no_api_key")
                return

            from datetime import date, timedelta
            import httpx

            end_date = date.today()
            # 35 calendar days ≈ 25 trading days after weekends/holidays
            start_date = end_date - timedelta(days=35)

            url = (
                f"https://api.polygon.io/v2/aggs/ticker/I:VIX/range/1/day"
                f"/{start_date.isoformat()}/{end_date.isoformat()}"
            )
            params = {
                "adjusted": "true",
                "sort": "asc",
                "limit": "30",
                "apiKey": config.POLYGON_API_KEY,
            }

            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url, params=params)

            if resp.status_code != 200:
                logger.warning(
                    "vix_history_backfill_failed",
                    status=resp.status_code,
                )
                return

            results = resp.json().get("results", []) or []
            closes = [float(r["c"]) for r in results if "c" in r]

            if len(closes) < 5:
                logger.warning(
                    "vix_history_backfill_insufficient",
                    days_returned=len(closes),
                )
                return

            self.vix_history = closes[-20:]
            # E-2: seed the slow-regime daily history from the same
            # daily-aggregates backfill so polygon:vix:z_score_daily
            # is meaningful from minute 1 of the first session, instead
            # of waiting ~20 trading days for the live EOD appends to
            # accumulate. vix_history (intraday) and vix_daily_history
            # are independent series with the same starting point; the
            # intraday window is overwritten by 5-min samples while the
            # daily window only advances once per session.
            self.vix_daily_history = closes[-20:]
            logger.info(
                "vix_history_backfilled",
                days=len(self.vix_history),
                latest_vix=round(self.vix_history[-1], 2),
            )

        except Exception as exc:
            logger.warning(
                "vix_history_backfill_error",
                error=type(exc).__name__,
            )

    async def _fetch_spx_price(self) -> Optional[float]:
        """
        E-1: Fetch live intraday SPX index price from the Polygon snapshot
        endpoint, replacing the prior _fetch_spx_close() implementation
        that hit /v2/aggs/ticker/I:SPX/prev.

        The /prev endpoint returns yesterday's daily close — a value
        that does not change throughout the trading day. Appending it
        to spx_history every 5-minute poll meant every "intraday"
        return feature fed to LightGBM (return_5m / 30m / 1h / 4h)
        was either zero or a constant tiny number — the model was
        effectively training and inferring on noise.

        Now uses /v3/snapshot?ticker.any_of=I:SPX (same pattern as
        _fetch_vix / _fetch_vvix) so spx_history actually contains
        intraday prices and the multi-timeframe returns reflect real
        intraday moves. Falls back to None on error.
        """
        try:
            import config
            api_key = config.POLYGON_API_KEY
            if not api_key:
                return None

            import httpx
            headers = {"Authorization": f"Bearer {api_key}"}

            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://api.polygon.io/v3/snapshot",
                    headers=headers,
                    params={"ticker.any_of": "I:SPX"},
                )
                if resp.status_code == 200:
                    results = resp.json().get("results", [])
                    if results:
                        session_data = results[0].get("session", {})
                        price = float(
                            session_data.get("close")
                            or session_data.get("last")
                            or 0.0
                        )
                        if price > 0:
                            return price
        except Exception as e:
            logger.warning(
                "polygon_spx_price_fetch_failed",
                error=type(e).__name__,
            )
        return None

    async def _fetch_spx_prev_close(self) -> Optional[float]:
        """T1-4: fetch the previous trading session's SPX close.

        Uses /v2/aggs/ticker/I:SPX/prev — the same endpoint
        _fetch_spx_close() used before S6 replaced live SPX with the
        snapshot endpoint. We now bring it back, but only for the
        prior_day_return feature, NOT for spx_history (which must
        stay intraday-snapshot-driven for return_5m / 30m / 1h / 4h).

        Returns None on failure; caller leaves spx_prev_session_close
        unchanged so prior_day_return is simply not written that cycle.
        """
        try:
            import config
            api_key = config.POLYGON_API_KEY
            if not api_key:
                return None

            import httpx
            headers = {"Authorization": f"Bearer {api_key}"}
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://api.polygon.io/v2/aggs/ticker/I:SPX/prev",
                    headers=headers,
                )
            if resp.status_code == 200:
                results = resp.json().get("results", []) or []
                if results:
                    close = float(results[0].get("c", 0.0) or 0.0)
                    if close > 0:
                        return close
        except Exception as e:
            logger.debug(
                "polygon_spx_prev_close_failed",
                error=type(e).__name__,
            )
        return None

    async def _fetch_spx_close(self) -> Optional[float]:
        """Deprecated — use _fetch_spx_price().

        Retained as a thin wrapper so existing tests that mock
        _fetch_spx_close keep working. New callers should use
        _fetch_spx_price directly.
        """
        return await self._fetch_spx_price()

    async def _compute_spx_features(self) -> None:
        """
        Compute SPX technical features from recent price history.
        Stores to Redis for LightGBM model inference.
        Requires >= 2 SPX close values in self.spx_history.
        """
        if len(self.spx_history) < 2:
            return

        closes = self.spx_history
        c = closes[-1]  # current close

        # Multi-timeframe returns
        def safe_return(n: int) -> float:
            if len(closes) > n:
                return (c - closes[-(n + 1)]) / closes[-(n + 1)] if closes[-(n + 1)] else 0.0
            return 0.0

        self.redis_client.setex("polygon:spx:return_5m",  300, str(safe_return(1)))
        self.redis_client.setex("polygon:spx:return_30m", 300, str(safe_return(6)))
        self.redis_client.setex("polygon:spx:return_1h",  300, str(safe_return(12)))
        self.redis_client.setex("polygon:spx:return_4h",  300, str(safe_return(48)))

        # T1-4: prior_day_return = TRUE session-over-session return.
        # The previous code computed (closes[-1] - closes[-2]) / closes[-2]
        # over self.spx_history — but spx_history is a 5-minute intraday
        # series, so this was actually a 5-minute bar return mislabeled
        # as a daily return. LightGBM was learning from a feature that
        # never matched its name.
        # We now use the dedicated spx_prev_session_close value
        # populated by _fetch_spx_prev_close() in the poll loop. If it
        # has not landed yet (cold start) we deliberately SKIP the
        # write rather than fall back to the wrong-by-construction
        # 5-min return. Downstream readers already tolerate a missing
        # key.
        # Lazy-init guard for older callers / tests that construct
        # PolygonFeed via __new__ and only populate spx_history (matches
        # the same defensiveness used for vix_daily_history above).
        if not hasattr(self, "spx_prev_session_close"):
            self.spx_prev_session_close = None
        if self.spx_prev_session_close and self.spx_prev_session_close > 0:
            current_price = closes[-1] if closes else 0.0
            if current_price > 0:
                prior = (
                    (current_price - self.spx_prev_session_close)
                    / self.spx_prev_session_close
                )
                self.redis_client.setex(
                    "polygon:spx:prior_day_return", 86400, str(prior)
                )

        # RSI-14 (simplified from available history)
        if len(closes) >= 15:
            diffs = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
            gains = [max(d, 0) for d in diffs[-14:]]
            losses = [abs(min(d, 0)) for d in diffs[-14:]]
            avg_gain = sum(gains) / 14
            avg_loss = sum(losses) / 14
            rs = avg_gain / avg_loss if avg_loss > 0 else 100
            rsi = 100 - (100 / (1 + rs))
            self.redis_client.setex("polygon:spx:rsi_14", 300, str(round(rsi, 2)))

    def _is_market_hours(self) -> bool:
        """T1-1: calendar-aware market-hours check.

        The original weekday < 5 + time-range check happily polled on
        NYSE holidays (e.g. Good Friday, Thanksgiving) and on early-
        close days (1 PM ET on the day after Thanksgiving, day before
        July 4 etc.). On those days we appended stale or non-session
        data to vix_history and spx_history, biasing the z-scores for
        the next 1-2 sessions until the bad samples rolled out.

        market_calendar.is_market_open() honours the NYSE holiday
        calendar, early-close schedule, and timezone correctly.

        Import is method-local to avoid circular-import risk —
        market_calendar must remain a leaf module that does not pull
        in any data-feed code.
        """
        try:
            from market_calendar import is_market_open
            return is_market_open()
        except Exception:
            # Fail open to the legacy weekday + time-range check so a
            # broken calendar import can never silently disable polling
            # during regular market hours.
            import zoneinfo
            now = datetime.now(zoneinfo.ZoneInfo("America/New_York"))
            return (
                now.weekday() < 5
                and time(9, 30) <= now.time() <= time(16, 0)
            )

    def _is_open_minute(self) -> bool:
        import zoneinfo
        now = datetime.now(zoneinfo.ZoneInfo("America/New_York"))
        return (
            now.weekday() < 5
            and now.time().hour == 9
            and now.time().minute == 30
        )
