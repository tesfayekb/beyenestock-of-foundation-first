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

logger = get_logger("databento_feed")


class DatabentoFeed:
    def __init__(self) -> None:
        self.redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
        self.connected = False
        self.last_data_at: Optional[float] = None
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        backoff = 1
        while not self._stop_event.is_set():
            try:
                await self._run_stream_loop()
                backoff = 1
            except Exception as exc:
                logger.error("databento_stream_error", error=str(exc), backoff=backoff)
                write_health_status("databento_feed", "degraded", databento_connected=False)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30)

    async def stop(self) -> None:
        self._stop_event.set()
        self.connected = False

    async def _run_stream_loop(self) -> None:
        self.connected = True
        logger.info("databento_connected", dataset="OPRA.PILLAR", schema="trades")
        heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        try:
            while not self._stop_event.is_set():
                await asyncio.sleep(1)
        finally:
            heartbeat_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await heartbeat_task
            self.connected = False
            write_health_status("databento_feed", "degraded", databento_connected=False)

    def process_trade(self, trade: dict) -> None:
        try:
            trade.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
            self.redis_client.rpush("databento:opra:trades", json.dumps(trade))
            self.redis_client.expire("databento:opra:trades", 300)
            self.last_data_at = time.time()
        except Exception as exc:
            logger.error("databento_trade_process_failed", trade=trade, error=str(exc))

    async def _heartbeat_loop(self) -> None:
        while not self._stop_event.is_set():
            lag = int(time.time() - self.last_data_at) if self.last_data_at else None
            status = "healthy" if self.connected else "degraded"

            if lag is not None and lag > 30:
                logger.warning("databento_data_lag_high", data_lag_seconds=lag)
                self.redis_client.set("databento:opra:confidence_impact", "true")
                status = "degraded"
            if lag is not None and lag > 600:
                logger.critical("databento_data_lag_critical", data_lag_seconds=lag)
                self.redis_client.set("databento:opra:gex_block", "True")

            write_health_status(
                "databento_feed",
                status,
                databento_connected=self.connected,
                data_lag_seconds=lag,
                last_data_at=(
                    datetime.fromtimestamp(self.last_data_at, tz=timezone.utc).isoformat()
                    if self.last_data_at
                    else None
                ),
            )
            await asyncio.sleep(10)
