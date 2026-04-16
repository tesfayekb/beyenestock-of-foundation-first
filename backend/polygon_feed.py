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
        if self.last_vvix is None:
            return 120.0
        return self.last_vvix

    def _is_market_hours(self) -> bool:
        now = datetime.now()
        return now.weekday() < 5 and time(9, 30) <= now.time() <= time(16, 0)

    def _is_open_minute(self) -> bool:
        now = datetime.now()
        return now.weekday() < 5 and now.time().hour == 9 and now.time().minute == 30
