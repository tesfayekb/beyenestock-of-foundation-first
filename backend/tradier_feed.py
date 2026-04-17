import asyncio
import contextlib
import json
import time
from datetime import datetime, timezone
from typing import Optional

import httpx

try:
    import redis
except ModuleNotFoundError:  # pragma: no cover
    redis = None

from config import REDIS_URL
from db import write_health_status
from logger import get_logger

logger = get_logger("tradier_feed")


class TradierFeed:
    def __init__(self) -> None:
        if redis is None:
            raise RuntimeError("redis dependency required")
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
        """
        Real Tradier feed implementation.
        In SANDBOX mode: uses REST polling (SSE not supported in sandbox).
        In PRODUCTION mode: uses SSE streaming.
        """
        import config as _config
        if _config.TRADIER_SANDBOX:
            await self._run_rest_poll_loop()
        else:
            await self._run_sse_stream_loop()

    async def _run_sse_stream_loop(self) -> None:
        """
        Real Tradier SSE stream implementation.
        Step 1: Create a streaming session to get sessionid.
        Step 2: Subscribe to SSE stream with target symbols.
        Writes quotes to Redis as tradier:quotes:{symbol} with 60s TTL.
        """
        import config

        base_url = (
            "https://sandbox.tradier.com"
            if config.TRADIER_SANDBOX
            else "https://api.tradier.com"
        )
        headers = {
            "Authorization": f"Bearer {config.TRADIER_API_KEY}",
            "Accept": "application/json",
        }

        # Step 1: Create streaming session
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{base_url}/v1/markets/events/session",
                headers=headers,
            )
            resp.raise_for_status()
            session_data = resp.json()
            sessionid = session_data["stream"]["sessionid"]
            logger.info("tradier_session_created", sessionid=sessionid[:8] + "...")

        # Step 2: Build symbol list — SPX index + today's 0DTE SPXW options
        symbols = ["SPX"]
        try:
            from strike_selector import _get_0dte_expiry, _get_option_chain_tradier
            expiry = _get_0dte_expiry()
            chain = _get_option_chain_tradier(expiry, None)
            option_syms = [
                opt.get("symbol", "")
                for opt in chain
                if opt.get("symbol")
            ]
            # Cap at 200 symbols to stay within Tradier SSE limits
            symbols.extend(option_syms[:200])
            logger.info(
                "tradier_sse_option_symbols_added",
                count=len(option_syms),
                capped=len(option_syms) > 200,
            )
        except Exception as chain_err:
            logger.warning(
                "tradier_sse_option_chain_failed",
                error=str(chain_err),
            )
            # Continue with SPX-only — GEX will use REST fallback per symbol

        # Step 3: Open SSE stream
        stream_url = f"{base_url}/v1/markets/events"
        stream_params = {
            "sessionid": sessionid,
            "symbols": ",".join(symbols),
            "filter": "quote",
            "linebreak": "true",
        }

        self.connected = True
        self.disconnect_started_at = None
        write_health_status("tradier_websocket", "healthy")
        logger.info("tradier_sse_stream_started", symbols=len(symbols))

        heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        try:
            async with httpx.AsyncClient(timeout=None) as stream_client:
                async with stream_client.stream(
                    "GET",
                    stream_url,
                    params=stream_params,
                    headers={
                        "Authorization": f"Bearer {config.TRADIER_API_KEY}",
                        "Accept": "application/json",
                    },
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if self._stop_event.is_set():
                            break
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            event = json.loads(line)
                            event_type = event.get("type")
                            if event_type == "quote":
                                self.process_quote(event)
                            elif event_type == "summary":
                                # Summary events contain bid/ask/last — treat as quote
                                self.process_quote(event)
                            elif event_type == "heartbeat":
                                self.last_data_at = time.time()
                        except json.JSONDecodeError:
                            pass  # Skip non-JSON lines (SSE metadata)
                        except Exception as exc:
                            logger.warning(
                                "tradier_event_process_error", error=str(exc)
                            )
        finally:
            heartbeat_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await heartbeat_task
            await self._mark_disconnected()

    async def _run_rest_poll_loop(self) -> None:
        """
        REST polling fallback for Tradier sandbox.
        Sandbox does not support SSE streaming.
        Polls /v1/markets/quotes every 10 seconds for SPX price.
        Writes tradier:quotes:SPX to Redis so mark_to_market has current price.
        """
        import config as _config
        base_url = "https://sandbox.tradier.com"
        headers = {
            "Authorization": f"Bearer {_config.TRADIER_API_KEY}",
            "Accept": "application/json",
        }

        self.connected = True
        self.disconnect_started_at = None
        write_health_status(
            "tradier_websocket",
            "healthy",
            last_error_message="sandbox_rest_polling",
        )
        logger.info("tradier_sandbox_rest_polling_started")

        heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        try:
            while not self._stop_event.is_set():
                try:
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        resp = await client.get(
                            f"{base_url}/v1/markets/quotes",
                            params={"symbols": "SPX", "greeks": "false"},
                            headers=headers,
                        )
                        if resp.status_code == 200:
                            data = resp.json()
                            quotes = data.get("quotes", {}).get("quote", {})
                            if isinstance(quotes, dict) and quotes.get("symbol"):
                                self.process_quote(quotes)
                            elif isinstance(quotes, list):
                                for q in quotes:
                                    self.process_quote(q)
                except Exception as poll_err:
                    logger.warning(
                        "tradier_rest_poll_failed", error=str(poll_err)
                    )

                await asyncio.sleep(10)
        finally:
            heartbeat_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await heartbeat_task
            await self._mark_disconnected()

    async def fetch_quote_rest(self, symbol: str) -> None:
        """
        Fetch a single quote via REST for symbols not yet in Redis.
        Used as fallback when SSE hasn't delivered a quote yet.
        """
        try:
            import config
            base_url = (
                "https://sandbox.tradier.com"
                if config.TRADIER_SANDBOX
                else "https://api.tradier.com"
            )
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{base_url}/v1/markets/quotes",
                    params={"symbols": symbol, "greeks": "false"},
                    headers={
                        "Authorization": f"Bearer {config.TRADIER_API_KEY}",
                        "Accept": "application/json",
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    quotes = data.get("quotes", {}).get("quote", {})
                    if isinstance(quotes, dict):
                        self.process_quote(quotes)
                    elif isinstance(quotes, list):
                        for q in quotes:
                            self.process_quote(q)
        except Exception as exc:
            logger.warning(
                "tradier_rest_quote_failed", symbol=symbol, error=str(exc)
            )

    async def _mark_disconnected(self) -> None:
        self.connected = False
        if self.disconnect_started_at is None:
            self.disconnect_started_at = time.time()
        # Don't write error on clean stop
        if self._stop_event.is_set():
            return
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
