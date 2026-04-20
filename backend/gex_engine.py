import json
from datetime import datetime, timezone
from math import exp, log, pi, sqrt
from typing import Dict, Optional

try:
    import redis
except ModuleNotFoundError:  # pragma: no cover
    redis = None

from config import REDIS_URL
from db import write_health_status
from logger import get_logger

logger = get_logger("gex_engine")


class _Norm:
    @staticmethod
    def pdf(value: float) -> float:
        return exp(-(value**2) / 2) / sqrt(2 * pi)


norm = _Norm()


def bs_gamma(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """
    Black-Scholes gamma for a single option.
    S: underlying price, K: strike, T: time to expiry in years,
    r: risk-free rate, sigma: implied vol
    """
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return 0.0
    d1 = (log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * sqrt(T))
    return norm.pdf(d1) / (S * sigma * sqrt(T))


def classify_trade(trade_price: float, bid: float, ask: float, prior_price: float) -> int:
    """
    Returns +1 (buyer-initiated) or -1 (seller-initiated).
    Uses tick test as tiebreaker when price == midpoint.
    """
    midpoint = (bid + ask) / 2
    if trade_price > midpoint:
        return 1
    if trade_price < midpoint:
        return -1
    return 1 if trade_price >= prior_price else -1


class GexEngine:
    def __init__(self) -> None:
        if redis is None:
            raise RuntimeError("redis dependency is required for GexEngine runtime")
        self.redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
        self.last_compute_at: Optional[datetime] = None

    def compute_gex(self) -> Dict[str, float]:
        trades_raw = self.redis_client.lrange("databento:opra:trades", 0, -1)
        trades = [json.loads(item) for item in trades_raw]
        if not trades:
            confidence = 0.0
            self.redis_client.set("gex:confidence", confidence)
            self._write_heartbeat(confidence)
            return {"gex_net": 0.0, "gex_confidence": confidence}

        # Batch all quote lookups in one Redis pipeline round-trip
        symbols = [trade.get("symbol", "") for trade in trades]
        pipe = self.redis_client.pipeline(transaction=False)
        for symbol in symbols:
            pipe.get(f"tradier:quotes:{symbol}")
        quote_raws = pipe.execute()

        # Build symbol → quote dict from pipeline results
        quote_cache: Dict[str, dict] = {}
        for symbol, raw in zip(symbols, quote_raws):
            if raw and symbol not in quote_cache:
                try:
                    quote_cache[symbol] = json.loads(raw)
                except Exception:
                    pass

        gex_by_strike: Dict[float, float] = {}
        net_gex = 0.0
        prior_price = float(trades[0].get("price", 0.0) or 0.0)

        for trade in trades:
            symbol = trade.get("symbol", "")
            quote = quote_cache.get(symbol)
            if not quote:
                # REST fallback — fetch quote synchronously for this symbol
                try:
                    import config
                    import httpx as _httpx
                    _base = (
                        "https://sandbox.tradier.com"
                        if config.TRADIER_SANDBOX
                        else "https://api.tradier.com"
                    )
                    _r = _httpx.get(
                        f"{_base}/v1/markets/quotes",
                        params={"symbols": symbol, "greeks": "false"},
                        headers={
                            "Authorization": f"Bearer {config.TRADIER_API_KEY}",
                            "Accept": "application/json",
                        },
                        timeout=3.0,
                    )
                    if _r.status_code == 200:
                        _q = _r.json().get("quotes", {}).get("quote", {})
                        if isinstance(_q, dict) and _q.get("symbol"):
                            quote = {
                                "bid": _q.get("bid", 0),
                                "ask": _q.get("ask", 0),
                                "last": _q.get("last", 0),
                            }
                            # Cache for duration of this compute cycle
                            quote_cache[symbol] = quote
                            self.redis_client.setex(
                                f"tradier:quotes:{symbol}",
                                60,
                                json.dumps(quote),
                            )
                except Exception:
                    pass  # skip symbol if REST also fails

                if not quote:
                    logger.warning("gex_quote_missing_after_rest", symbol=symbol)
                    continue
            bid = float(quote.get("bid", 0.0) or 0.0)
            ask = float(quote.get("ask", 0.0) or 0.0)
            price = float(trade.get("price", 0.0) or 0.0)
            volume = float(trade.get("volume", 0.0) or 0.0)
            S = float(trade.get("underlying_price", 0.0) or 0.0)
            K = float(trade.get("strike", 0.0) or 0.0)
            T = float(trade.get("time_to_expiry_years", 0.0) or 0.0)
            r = float(trade.get("risk_free_rate", 0.0) or 0.0)
            sigma = float(trade.get("implied_vol", 0.0) or 0.0)

            sign = classify_trade(price, bid, ask, prior_price)
            prior_price = price
            dealer_gamma = -sign * volume * bs_gamma(S, K, T, r, sigma) * 100

            gex_by_strike[K] = gex_by_strike.get(K, 0.0) + dealer_gamma
            net_gex += dealer_gamma

        # Read SPX price from Redis
        spx_price = 5200.0
        try:
            raw = self.redis_client.get("tradier:quotes:SPX")
            if raw:
                quote = json.loads(raw)
                spx_price = float(quote.get("last", 5200.0))
        except Exception:
            pass

        nearest_wall = self._nearest_positive_wall(gex_by_strike, spx_price)
        flip_zone = self._nearest_flip_zone(gex_by_strike)
        expected_trades_5min = 1000
        confidence = min(1.0, len(trades) / expected_trades_5min)

        self.redis_client.set("gex:net", net_gex)
        self.redis_client.set("gex:by_strike", json.dumps(gex_by_strike))
        self.redis_client.set("gex:nearest_wall", nearest_wall or "")
        self.redis_client.set("gex:flip_zone", flip_zone or "")
        self.redis_client.set("gex:confidence", confidence)

        # 12C: append to rolling 30-min wall history so strategy_selector
        # can block butterfly when the pin is breaking (wall drift > 0.5%
        # over the last 30 min). 2026-04-20 losses: wall moved 7115→7195
        # (80pts = 1.1%) while the system opened 3 butterflies on the old
        # wall — this gate would have caught it once 4+ samples landed.
        self._append_wall_history(nearest_wall)

        self.last_compute_at = datetime.now(timezone.utc)
        self._write_heartbeat(confidence)
        return {"gex_net": net_gex, "gex_confidence": confidence}

    def _append_wall_history(self, nearest_wall) -> None:
        """12C: append a timestamped wall entry and prune to 30 min.

        Stored at Redis key `gex:wall_history` as a JSON list of
        `{"ts": epoch_seconds, "wall": float}`. The key has a 1-hour
        TTL so a crashed engine can't leave stale entries forever;
        1h comfortably exceeds the 30-min window we read back.

        Guards:
          * `nearest_wall` may be None, "", or 0 when no positive
            gamma mass exists — skip cleanly in that case. Downstream
            only gates when there are 4+ samples anyway.
          * Fail-open: any Redis/JSON error must not affect the GEX
            computation — the wall-history key is purely advisory.
        """
        try:
            if not nearest_wall:
                return
            wall_value = float(nearest_wall)
            if wall_value <= 0:
                return
            import time as _time
            key = "gex:wall_history"
            raw = self.redis_client.get(key)
            history = json.loads(raw) if raw else []
            now_ts = _time.time()
            history.append({"ts": now_ts, "wall": wall_value})
            # Prune to last 30 minutes (1800s) so the rolling window
            # always reflects current regime, not yesterday's pin.
            history = [h for h in history if now_ts - h["ts"] < 1800]
            self.redis_client.setex(key, 3600, json.dumps(history))
        except Exception:
            pass  # purely advisory — never affect GEX computation

    def _write_heartbeat(self, confidence: float) -> None:
        staleness = 0
        if self.last_compute_at:
            staleness = int(
                (datetime.now(timezone.utc) - self.last_compute_at).total_seconds()
            )
        write_health_status(
            "gex_engine",
            "healthy",
            gex_confidence=confidence,
            gex_staleness_seconds=staleness,
        )

    @staticmethod
    def _nearest_positive_wall(
        gex_by_strike: Dict[float, float],
        spx_price: float = 5200.0,
    ) -> Optional[float]:
        """
        Return the positive GEX strike nearest to the current SPX price.
        Prefers the strike ABOVE SPX price (resistance wall).
        Falls back to nearest below if no strikes above exist.
        """
        positives = [
            strike for strike, value in gex_by_strike.items() if value > 0
        ]
        if not positives:
            return None

        # Find strikes above SPX price (resistance)
        above = [s for s in positives if s >= spx_price]
        if above:
            return min(above)  # nearest above

        # Fallback: nearest below SPX price
        below = [s for s in positives if s < spx_price]
        if below:
            return max(below)  # nearest below

        return None

    @staticmethod
    def _nearest_flip_zone(gex_by_strike: Dict[float, float]) -> Optional[float]:
        ordered = sorted(gex_by_strike.items(), key=lambda item: item[0])
        for index in range(1, len(ordered)):
            prev_value = ordered[index - 1][1]
            curr_value = ordered[index][1]
            if prev_value == 0 or curr_value == 0:
                return ordered[index][0]
            if (prev_value > 0 > curr_value) or (prev_value < 0 < curr_value):
                return ordered[index][0]
        return None
