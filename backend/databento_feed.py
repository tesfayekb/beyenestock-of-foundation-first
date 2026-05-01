"""
Databento OPRA live feed ingestion (T-ACT-035 rewrite).

Architecture:
- Subscribes to OPRA.PILLAR trades schema for SPX + SPXW option families
  via stype_in=PARENT, symbols=["SPX.OPT", "SPXW.OPT"] (narrow, not firehose).
- Uses databento.InstrumentMap to resolve instrument_id -> raw_symbol from
  SymbolMappingMsg records that interleave with TradeMsg records in the
  live stream.
- Dispatches records by isinstance: SymbolMappingMsg feeds the map,
  TradeMsg is processed as a real trade, and all other record types
  (SystemMsg / ErrorMsg / etc.) are ignored cleanly.
- Writes parsed trades to Redis list ``databento:opra:trades``, bounded
  to the 10000 most-recent trades via LTRIM.
- Health is reported 'healthy' only when a symbol-resolved, non-zero-price
  trade has been observed within the last 30s — the old bug made 'healthy'
  mean 'the process is alive', which masked a parser that produced nothing
  but zero-filled placeholder records.

Previous bug: the old code used ``getattr(record, "symbol", "")`` on every
record. ``TradeMsg`` has no ``.symbol`` attribute in databento>=0.35, so the
default "" was always returned; the OCC regex never matched; strike stayed
0.0; and ~473k zero-filled records per session flooded Redis, starving the
GEX engine of real data while every health probe reported 'healthy'.
"""
import asyncio
import contextlib
import json
import re
import time
from datetime import datetime, timezone, date
from typing import Optional

import redis

from config import REDIS_URL
from db import write_health_status
from logger import get_logger
from market_calendar import is_market_open

logger = get_logger("databento_feed")

OCC_RE = re.compile(r"([A-Z]{1,6})(\d{6})([CP])(\d{8})")


class DatabentoFeed:
    def __init__(self) -> None:
        self.redis_client = redis.Redis.from_url(
            REDIS_URL, decode_responses=True
        )
        self.connected = False
        self.last_valid_trade_at: Optional[float] = None
        self._stop_event = asyncio.Event()
        self._imap = None

        try:
            self.redis_client.delete("databento:opra:trades")
            logger.info("databento_stale_key_flushed")
        except Exception as exc:
            logger.warning(
                "databento_stale_flush_failed", error=str(exc)
            )

    async def start(self) -> None:
        backoff = 1
        while not self._stop_event.is_set():
            try:
                if self._imap is not None:
                    self._imap.clear()
                await self._run_stream_loop()
                backoff = 1
            except Exception as exc:
                logger.error(
                    "databento_stream_error",
                    error=str(exc),
                    backoff=backoff,
                )
                # Only write 'degraded' during market hours.
                # Outside hours the feed is expected to be quiet — write 'idle'.
                _status = "degraded" if is_market_open() else "idle"
                write_health_status(
                    "databento_feed",
                    _status,
                    databento_connected=False,
                )
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30)

    async def stop(self) -> None:
        self._stop_event.set()
        self.connected = False

    async def _run_stream_loop(self) -> None:
        """Narrow-subscribe to SPX/SPXW options and dispatch records by type."""
        import databento as db
        import config

        if self._imap is None:
            self._imap = db.InstrumentMap()

        logger.info(
            "databento_connecting",
            dataset="OPRA.PILLAR",
            schema="trades",
            symbols=["SPX.OPT", "SPXW.OPT"],
            stype_in="PARENT",
        )

        loop = asyncio.get_event_loop()

        def _run_live_blocking() -> None:
            client = db.Live(key=config.DATABENTO_API_KEY)
            client.subscribe(
                dataset="OPRA.PILLAR",
                schema="trades",
                symbols=["SPX.OPT", "SPXW.OPT"],
                stype_in=db.SType.PARENT,
            )

            self.connected = True
            write_health_status(
                "databento_feed",
                "healthy",
                databento_connected=True,
            )
            logger.info("databento_subscribed")

            # Outer try/except over the blocking for-record loop.
            # Pre-0.39 databento had a C-extension segfault in
            # protocol.py::_process_dbn that hard-killed the Railway
            # worker. The library pin at >=0.39.3,<0.50.0 contains
            # the upstream fix, but we also keep this defensive
            # boundary so any non-fatal stream error (RuntimeError /
            # SystemError / connection reset) surfaces as a normal
            # exception instead of bringing the supervisor down —
            # the outer reconnect loop in start() then handles it.
            # The per-record try/except is preserved so a single
            # malformed record still can't take out the loop.
            try:
                for record in client:
                    if self._stop_event.is_set():
                        break
                    try:
                        self._dispatch_record(record)
                    except Exception as exc:
                        logger.warning(
                            "databento_record_parse_failed",
                            error=str(exc),
                        )
            except Exception as exc:
                logger.error(
                    "databento_stream_loop_error",
                    error=str(exc),
                    error_type=type(exc).__name__,
                )
                raise  # re-raise so _run_stream_loop reconnect fires
            finally:
                # Best-effort client teardown on any exit path. Swallow
                # errors here — we cannot let a cleanup failure mask
                # the original stream exception the caller needs.
                try:
                    client.stop()
                except Exception:
                    pass

        heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        try:
            await loop.run_in_executor(None, _run_live_blocking)
        finally:
            heartbeat_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await heartbeat_task
            self.connected = False
            # Same idle-vs-degraded logic on stream teardown.
            _status = "degraded" if is_market_open() else "idle"
            write_health_status(
                "databento_feed",
                _status,
                databento_connected=False,
            )

    def _dispatch_record(self, record) -> None:
        """
        Route one live record to the right handler by isinstance check.

        - SymbolMappingMsg -> feed the InstrumentMap
        - TradeMsg         -> _handle_trade()
        - anything else    -> silently ignored (SystemMsg / ErrorMsg etc.
          are normal protocol traffic, not errors for our purposes)
        """
        import databento as db

        if isinstance(record, db.SymbolMappingMsg):
            self._imap.insert_symbol_mapping_msg(record)
            return
        if isinstance(record, db.TradeMsg):
            self._handle_trade(record)
            return
        # All other record types are intentionally ignored.

    def _handle_trade(self, record) -> None:
        """
        Parse a TradeMsg into our trade dict and rpush it to Redis.

        Drops cleanly (no exception, no placeholder write) when:
        - instrument_id cannot be resolved to a raw symbol yet
        - raw symbol doesn't match OCC format
        - expiry or strike fails to parse
        - pretty_price is non-positive (busted print)
        """
        ts_ns = int(getattr(record, "ts_event", 0) or 0)
        event_date = (
            datetime.fromtimestamp(ts_ns / 1e9, tz=timezone.utc).date()
            if ts_ns > 0
            else date.today()
        )

        raw_symbol = None
        try:
            raw_symbol = self._imap.resolve(
                int(record.instrument_id), event_date
            )
        except Exception as exc:
            logger.debug(
                "databento_resolve_failed",
                instrument_id=getattr(record, "instrument_id", None),
                error=str(exc),
            )

        if not raw_symbol:
            return

        sym_clean = raw_symbol.replace(" ", "")
        occ_match = OCC_RE.match(sym_clean)
        if not occ_match:
            logger.debug(
                "databento_occ_parse_failed", symbol=sym_clean
            )
            return

        _root, date_str, opt_type, strike_str = occ_match.groups()
        try:
            year = int("20" + date_str[:2])
            month = int(date_str[2:4])
            day = int(date_str[4:6])
            expiry = date(year, month, day)
            expiry_date = expiry.isoformat()
            days_to_expiry = max(0, (expiry - date.today()).days)
            time_to_expiry = max(0.0001, days_to_expiry / 365.0)
        except ValueError:
            return

        try:
            strike = float(strike_str) / 1000.0
        except ValueError:
            return

        try:
            price = float(record.pretty_price)
        except (TypeError, ValueError, AttributeError):
            return

        if price <= 0:
            return

        size = int(getattr(record, "size", 0) or 0)
        ts_dt = datetime.fromtimestamp(
            ts_ns / 1e9, tz=timezone.utc
        ).isoformat() if ts_ns > 0 else datetime.now(timezone.utc).isoformat()

        underlying_price = self._get_underlying_price()

        # E-4: read live VIX (written by polygon_feed every 5 min) and
        # convert to a decimal vol. The previous hard-coded 0.20 made
        # GEX (bs_gamma) magnitudes and the nearest-wall calculation
        # systematically wrong whenever realised IV was meaningfully
        # different from 20% — i.e., on every interesting trading day.
        # Sanity clamp [0.05, 2.0] guards against a malformed
        # polygon:vix:current write or a freak VIX spike.
        try:
            vix_raw = (
                self.redis_client.get("polygon:vix:current")
                if self.redis_client else None
            )
            implied_vol = (
                float(vix_raw) / 100.0 if vix_raw else 0.20
            )
            implied_vol = max(0.05, min(implied_vol, 2.0))
        except Exception:
            implied_vol = 0.20

        trade = {
            "symbol": sym_clean,
            "price": price,
            "volume": size,
            "underlying_price": underlying_price,
            "strike": strike,
            "option_type": opt_type,
            "time_to_expiry_years": time_to_expiry,
            "expiry_date": expiry_date,
            "implied_vol": implied_vol,
            "risk_free_rate": 0.05,
            "timestamp": ts_dt,
        }
        self._push_trade(trade)

    def _get_underlying_price(self) -> float:
        """Read SPX spot from Redis.

        PRIMARY:   polygon:spx:current  (real-time; written by polygon_feed).
        FALLBACK:  tradier:quotes:SPX   (15-min delayed in sandbox).
        SENTINEL:  5200.0.

        Per 2026-05-01 SPX-real-time-feed fix: this Databento internal
        SPX reference now matches the Polygon-first priority chain used
        by all 6 prod live-decision-path readers; previously inherited
        Tradier's 15-min delay.
        """
        try:
            poly_raw = self.redis_client.get("polygon:spx:current")
            if poly_raw:
                poly_data = json.loads(poly_raw)
                price = float(poly_data.get("price") or 0)
                if price > 0:
                    return round(price, 2)
        except Exception:
            pass

        try:
            spx_raw = self.redis_client.get("tradier:quotes:SPX")
        except Exception:
            return 5200.0
        if not spx_raw:
            return 5200.0
        try:
            spx_data = json.loads(spx_raw)
            return float(
                spx_data.get("last")
                or spx_data.get("ask")
                or 5200.0
            )
        except Exception:
            return 5200.0

    def process_trade(self, trade: dict) -> None:
        """
        Back-compat wrapper around _push_trade.

        Preserved so external callers / legacy tests can inject a
        pre-built trade dict without going through _handle_trade.
        New code should prefer _handle_trade (full parse pipeline)
        or _push_trade (already-validated trade).
        """
        self._push_trade(trade)

    def _push_trade(self, trade: dict) -> None:
        """
        rpush a fully-validated trade and advance the valid-trade heartbeat.

        Only called from _handle_trade after every field has been real-valued,
        so ``last_valid_trade_at`` truly means 'a resolvable OPRA trade was
        processed within the last N seconds'.
        """
        try:
            trade.setdefault(
                "timestamp", datetime.now(timezone.utc).isoformat()
            )
            self.redis_client.rpush(
                "databento:opra:trades", json.dumps(trade)
            )
            # Bound list to the most recent 10000 trades (replaces broken
            # EXPIRE pattern that reset TTL on every push and caused
            # unbounded growth; observed 180K elements 2026-04-24 mid-RTH).
            # 10000 ≈ 15-20 min of RTH activity at observed ~30K/hour rate.
            self.redis_client.ltrim("databento:opra:trades", -10000, -1)
            self.last_valid_trade_at = time.time()
        except Exception as exc:
            logger.error(
                "databento_trade_push_failed", error=str(exc)
            )

    async def _heartbeat_loop(self) -> None:
        """
        Report health every 10s. Status is 'healthy' only when a
        symbol-resolved, non-zero-price trade was observed within 30s.
        Mere connection is insufficient.

        Note: outside market hours this correctly reports 'degraded'
        because no real trades arrive — that's the intended behavior,
        and the old false-positive 'healthy' under a broken parser is
        exactly what T-ACT-035 fixes.
        """
        while not self._stop_event.is_set():
            lag = (
                int(time.time() - self.last_valid_trade_at)
                if self.last_valid_trade_at
                else None
            )

            if not self.connected or lag is None or lag > 30:
                # Outside market hours, no trades are expected — 'idle'
                # is the correct neutral state, not 'degraded'.
                status = "degraded" if is_market_open() else "idle"
            else:
                status = "healthy"

            # Bug 3: clear gex_block / confidence_impact when feed recovers.
            # Old behavior set these on lag spikes but never cleared them,
            # leaving the GEX engine permanently blocked after one bad window.
            if status == "healthy":
                try:
                    self.redis_client.delete("databento:opra:gex_block")
                    self.redis_client.delete(
                        "databento:opra:confidence_impact"
                    )
                except Exception:
                    pass

            # Bug 2: only log lag warnings during US market hours
            # (Mon-Fri 09:30-16:15 ET). Outside market hours, no trades
            # arrive by design; logging warnings/criticals there pollutes
            # logs with false alarms.
            from datetime import datetime as dt
            import pytz
            et = pytz.timezone("America/New_York")
            now_et = dt.now(et)
            is_market_hours = (
                now_et.weekday() < 5
                and (now_et.hour, now_et.minute) >= (9, 30)
                and (now_et.hour, now_et.minute) < (16, 15)
            )

            if (
                lag is not None
                and lag > 30
                and self.connected
                and is_market_hours
            ):
                logger.warning(
                    "databento_data_lag_high", data_lag_seconds=lag
                )
                try:
                    self.redis_client.set(
                        "databento:opra:confidence_impact", "true"
                    )
                except Exception:
                    pass
            if lag is not None and lag > 600 and is_market_hours:
                logger.critical(
                    "databento_data_lag_critical", data_lag_seconds=lag
                )
                try:
                    self.redis_client.set("databento:opra:gex_block", "True")
                except Exception:
                    pass

            # Bug 1B: only include last_valid_trade_at when set, so a
            # missing column or null value can never crash the heartbeat
            # write. Migration 20260418_add_last_valid_trade_at adds the
            # column; this guard keeps writes safe pre-migration too.
            health_kwargs = {
                "databento_connected": self.connected,
                "data_lag_seconds": lag,
            }
            if self.last_valid_trade_at:
                health_kwargs["last_valid_trade_at"] = (
                    datetime.fromtimestamp(
                        self.last_valid_trade_at, tz=timezone.utc
                    ).isoformat()
                )
            write_health_status("databento_feed", status, **health_kwargs)
            await asyncio.sleep(10)
