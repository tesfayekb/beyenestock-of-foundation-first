import asyncio
import contextlib
import json
import time
from datetime import datetime, timezone
from typing import Optional

import redis

from config import REDIS_URL
from db import write_health_status
from logger import get_logger

logger = get_logger("tradier_feed")


class TradierFeed:
    def __init__(self) -> None:
        self.redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
        self.connected = False
        self.last_data_at: Optional[float] = None
        self.disconnect_started_at: Optional[float] = None
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        backoff = 1
        while not self._stop_event.is_set():
            try:
                await self._run_stream_loop()
                backoff = 1
            except Exception as exc:
                logger.error("tradier_stream_error", error=str(exc), backoff=backoff)
                await self._mark_disconnected()
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30)

    async def stop(self) -> None:
        self._stop_event.set()
        self.connected = False

    async def _run_stream_loop(self) -> None:
        self.connected = True
        self.disconnect_started_at = None
        write_health_status("tradier_websocket", "healthy")
        logger.info("tradier_connected")

        heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        try:
            while not self._stop_event.is_set():
                await asyncio.sleep(1)
        finally:
            heartbeat_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await heartbeat_task
            await self._mark_disconnected()

    async def _mark_disconnected(self) -> None:
        self.connected = False
        if self.disconnect_started_at is None:
            self.disconnect_started_at = time.time()
        write_health_status(
            "tradier_websocket",
            "degraded",
            last_error_message="disconnected",
        )

    def process_quote(self, quote: dict) -> None:
        try:
            symbol = quote["symbol"]
            payload = {
                "symbol": symbol,
                "bid": quote.get("bid"),
                "ask": quote.get("ask"),
                "last": quote.get("last"),
                "volume": quote.get("volume"),
                "timestamp": quote.get("timestamp")
                or datetime.now(timezone.utc).isoformat(),
            }
            key = f"tradier:quotes:{symbol}"
            self.redis_client.setex(key, 60, json.dumps(payload))
            self.last_data_at = time.time()
        except Exception as exc:
            logger.error("tradier_quote_process_failed", quote=quote, error=str(exc))

    async def _heartbeat_loop(self) -> None:
        while not self._stop_event.is_set():
            now_ts = time.time()
            lag = None
            if self.last_data_at is not None:
                lag = int(now_ts - self.last_data_at)

            status = "healthy"
            if lag is not None and lag >= 30:
                status = "degraded"

            if self.disconnect_started_at is not None:
                disconnect_age = int(now_ts - self.disconnect_started_at)
                if disconnect_age >= 120:
                    status = "offline"
                    logger.critical(
                        "tradier_disconnect_persistent",
                        disconnect_age_seconds=disconnect_age,
                    )

            write_health_status(
                "tradier_websocket",
                status,
                latency_ms=0,
                data_lag_seconds=lag,
                tradier_ws_connected=self.connected,
                last_data_at=(
                    datetime.fromtimestamp(self.last_data_at, tz=timezone.utc).isoformat()
                    if self.last_data_at
                    else None
                ),
            )
            await asyncio.sleep(10)
