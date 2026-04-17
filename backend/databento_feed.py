import asyncio
import contextlib
import json
import re
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
        """
        Real Databento Live OPRA feed implementation.
        Subscribes to OPRA.PILLAR trades schema.
        Parses DBN records into the trade dict format expected by process_trade().
        """
        import databento as db
        import config
        from datetime import date

        logger.info("databento_connecting", dataset="OPRA.PILLAR", schema="trades")

        # Run Databento Live in a thread (it's a blocking synchronous iterator)
        loop = asyncio.get_event_loop()

        def _run_live_blocking():
            """Runs in thread pool — Databento Live is synchronous."""
            client = db.Live(key=config.DATABENTO_API_KEY)
            client.subscribe(
                dataset="OPRA.PILLAR",
                schema="trades",
                stype_in="raw_symbol",
            )

            self.connected = True
            write_health_status(
                "databento_feed", "healthy", databento_connected=True
            )
            logger.info("databento_subscribed", dataset="OPRA.PILLAR")

            for record in client:
                if self._stop_event.is_set():
                    break

                try:
                    # Extract fields from DBN trade record
                    raw_symbol = getattr(record, "symbol", "") or ""
                    price_raw = getattr(record, "price", 0)
                    size = int(getattr(record, "size", 0))
                    ts_ns = getattr(record, "ts_event", 0)

                    # DBN prices are fixed-point with 9 decimal places
                    price = float(price_raw) / 1e9 if price_raw else 0.0
                    ts_dt = datetime.fromtimestamp(
                        ts_ns / 1e9, tz=timezone.utc
                    ).isoformat()

                    # Parse option symbol — format: ROOT  YYMMDD{C/P}STRIKE
                    # e.g. "SPXW  241220P05200000" → strike=5200, expiry=2024-12-20
                    strike = 0.0
                    expiry_date = date.today().isoformat()
                    time_to_expiry = 0.002  # ~0.5 trading days default
                    option_type = "P"

                    # Normalize raw_symbol — strip spaces
                    sym_clean = raw_symbol.replace(" ", "")

                    # Parse OCC symbology: 6-char root + 6-char date + C/P + 8-char strike
                    occ_match = re.match(
                        r"([A-Z]{1,6})(\d{6})([CP])(\d{8})", sym_clean
                    )
                    if occ_match:
                        root, date_str, opt_type, strike_str = occ_match.groups()
                        option_type = opt_type
                        try:
                            year = int("20" + date_str[:2])
                            month = int(date_str[2:4])
                            day = int(date_str[4:6])
                            expiry = date(year, month, day)
                            expiry_date = expiry.isoformat()
                            days_to_expiry = max(0, (expiry - date.today()).days)
                            time_to_expiry = max(0.0001, days_to_expiry / 365.0)
                        except ValueError:
                            pass
                        try:
                            strike = float(strike_str) / 1000.0
                        except ValueError:
                            pass

                    # Get underlying SPX price from Redis
                    spx_raw = self.redis_client.get("tradier:quotes:SPX")
                    underlying_price = 5200.0  # fallback
                    if spx_raw:
                        try:
                            spx_data = json.loads(spx_raw)
                            underlying_price = float(
                                spx_data.get("last")
                                or spx_data.get("ask")
                                or 5200.0
                            )
                        except Exception:
                            pass

                    trade = {
                        "symbol": sym_clean,
                        "price": price,
                        "volume": size,
                        "underlying_price": underlying_price,
                        "strike": strike,
                        "option_type": option_type,
                        "time_to_expiry_years": time_to_expiry,
                        "expiry_date": expiry_date,
                        "implied_vol": 0.20,   # Phase 2 placeholder
                        "risk_free_rate": 0.05,
                        "timestamp": ts_dt,
                    }
                    self.process_trade(trade)

                except Exception as exc:
                    logger.warning(
                        "databento_record_parse_failed", error=str(exc)
                    )

        heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        try:
            # Run the blocking Databento loop in a thread executor
            await loop.run_in_executor(None, _run_live_blocking)
        finally:
            heartbeat_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await heartbeat_task
            self.connected = False
            write_health_status(
                "databento_feed", "degraded", databento_connected=False
            )

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
