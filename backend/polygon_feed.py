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
        self.last_vix: Optional[float] = None
        # B-1: rolling 20-day VIX history for z-score (Signals D + F).
        self.vix_history: List[float] = []
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

                        spx_close = await self._fetch_spx_close()
                        if spx_close and spx_close > 0:
                            self.spx_history.append(spx_close)
                            self.spx_history = self.spx_history[-20:]

                        if len(self.spx_history) >= 5:
                            import math
                            log_returns = [
                                math.log(self.spx_history[i] / self.spx_history[i - 1])
                                for i in range(1, len(self.spx_history))
                            ]
                            n = len(log_returns)
                            mean_r = sum(log_returns) / n
                            variance = sum((r - mean_r) ** 2 for r in log_returns) / n
                            realized_vol = math.sqrt(variance * 252) * 100
                            self.redis_client.setex(
                                "polygon:spx:realized_vol_20d",
                                86400,
                                str(round(realized_vol, 4)),
                            )
                            logger.info(
                                "polygon_realized_vol_updated",
                                realized_vol=round(realized_vol, 2),
                                vix=vix,
                                history_len=len(self.spx_history),
                            )
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
        B-1: Compute rolling 20-day VIX z-score and write to Redis.

        Mirrors _store_baseline() for VVIX — identical rolling window
        math, different Redis keys (polygon:vix:* NOT polygon:vvix:*).
        These are separate signals consuming different data — never
        overwrite VVIX keys here.

        Minimum 5 data points required before writing z-score (avoids
        noisy early values). After 20 polling cycles the window is
        full; subsequent calls slide.

        Writes:
          polygon:vix:20d_mean
          polygon:vix:20d_std
          polygon:vix:z_score

        Called every polling cycle from _poll_loop alongside
        polygon:vix:current. After Session 2 historical backfill (plan
        addition A2), z-score will be meaningful from minute 1 of the
        first session.
        """
        self.vix_history.append(current)
        self.vix_history = self.vix_history[-20:]

        if len(self.vix_history) < 5:
            return  # Not enough data — do not write partial z-score

        n = len(self.vix_history)
        avg = sum(self.vix_history) / n
        variance = sum((x - avg) ** 2 for x in self.vix_history) / n
        std = variance ** 0.5

        if std <= 0:
            return  # Zero variance — z-score undefined

        z_score = round((current - avg) / std, 4)
        self.redis_client.set("polygon:vix:20d_mean", round(avg, 4))
        self.redis_client.set("polygon:vix:20d_std", round(std, 4))
        self.redis_client.set("polygon:vix:z_score", z_score)
        logger.debug(
            "polygon_vix_zscore_updated",
            vix=round(current, 2),
            mean=round(avg, 2),
            std=round(std, 2),
            z_score=z_score,
            history_len=n,
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

    async def _fetch_spx_close(self) -> Optional[float]:
        """
        Fetch latest SPX daily close from Polygon.
        Uses I:SPX index. Returns None on failure.
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
                    results = resp.json().get("results", [])
                    if results:
                        return float(results[0].get("c", 0.0)) or None
        except Exception as e:
            logger.warning("polygon_spx_fetch_failed", error=type(e).__name__)
        return None

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

        # Prior day return (use spx_history as daily closes)
        if len(closes) >= 2:
            prior = (closes[-1] - closes[-2]) / closes[-2] if closes[-2] else 0.0
            self.redis_client.setex("polygon:spx:prior_day_return", 86400, str(prior))

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
        import zoneinfo
        now = datetime.now(zoneinfo.ZoneInfo("America/New_York"))
        return now.weekday() < 5 and time(9, 30) <= now.time() <= time(16, 0)

    def _is_open_minute(self) -> bool:
        import zoneinfo
        now = datetime.now(zoneinfo.ZoneInfo("America/New_York"))
        return (
            now.weekday() < 5
            and now.time().hour == 9
            and now.time().minute == 30
        )
