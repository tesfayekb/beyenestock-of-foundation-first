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

        gex_by_strike: Dict[float, float] = {}
        net_gex = 0.0
        prior_price = float(trades[0].get("price", 0.0) or 0.0)

        for trade in trades:
            symbol = trade.get("symbol", "")
            quote_raw = self.redis_client.get(f"tradier:quotes:{symbol}")
            if not quote_raw:
                logger.warning("gex_quote_missing", symbol=symbol)
                continue
            quote = json.loads(quote_raw)
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

        nearest_wall = self._nearest_positive_wall(gex_by_strike)
        flip_zone = self._nearest_flip_zone(gex_by_strike)
        # TODO T-ACT-004: replace with rolling 20-day average once learning engine is live (Phase 6)
        expected_trades_5min = 1000
        confidence = min(1.0, len(trades) / expected_trades_5min)

        self.redis_client.set("gex:net", net_gex)
        self.redis_client.set("gex:by_strike", json.dumps(gex_by_strike))
        self.redis_client.set("gex:nearest_wall", nearest_wall or "")
        self.redis_client.set("gex:flip_zone", flip_zone or "")
        self.redis_client.set("gex:confidence", confidence)
        self.redis_client.set("gex:computed_at", datetime.now(timezone.utc).isoformat())

        regime = self.redis_client.get("trading:regime")
        if regime == "trend" and confidence < 0.70:
            self.redis_client.set("gex:block_new_entries", "True")
            logger.warning("gex_trend_block_enabled", gex_confidence=confidence)

        self.last_compute_at = datetime.now(timezone.utc)
        self._write_heartbeat(confidence)
        return {"gex_net": net_gex, "gex_confidence": confidence}

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
    def _nearest_positive_wall(gex_by_strike: Dict[float, float]) -> Optional[float]:
        positives = [strike for strike, value in gex_by_strike.items() if value > 0]
        if not positives:
            return None
        return sorted(positives)[0]

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
