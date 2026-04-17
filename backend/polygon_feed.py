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
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
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

                    await self._write_daily_open_if_needed(current)
                except Exception as exc:
                    logger.warning("polygon_vvix_poll_failed", error=str(exc))
            await asyncio.sleep(300)

    async def _heartbeat_loop(self) -> None:
        while not self._stop_event.is_set():
            write_health_status(
                "data_ingestor",
                "healthy",
                latency_ms=0,
                data_lag_seconds=0,
            )
            await asyncio.sleep(10)

    def _store_baseline(self, current: float) -> None:
        self.redis_client.set("polygon:vvix:current", current)
        if len(self.history) < 20:
            self.redis_client.set("polygon:vvix:baseline_ready", "False")
            self.redis_client.set(
                "polygon:vvix:fallback_thresholds", json.dumps([120, 140, 160])
            )
            return

        avg = mean(self.history)
        std = pstdev(self.history) or 0.0
        z_score = (current - avg) / std if std > 0 else 0.0

        self.redis_client.set("polygon:vvix:20d_mean", avg)
        self.redis_client.set("polygon:vvix:20d_std", std)
        self.redis_client.set("polygon:vvix:z_score", z_score)
        self.redis_client.set("polygon:vvix:baseline_ready", "True")

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
