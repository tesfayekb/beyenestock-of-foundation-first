"""
Phase 5A: Option price fetcher for earnings straddle sizing.

Fetches ATM call and put prices from Polygon options reference +
last-trade endpoints. Two-step lookup:
  1. /v3/reference/options/{ticker}?strike_price=...&expiration_date=...
     → resolves the contract ticker symbol (e.g. O:NVDA260417C00900000)
  2. /v2/last/trade/{contract_ticker}
     → last trade price for that specific contract

Used to compute:
  1. Total straddle cost (call + put premium × 100 × contracts)
  2. Current implied move (straddle / stock price ≈ expected 1σ move)

Rate limit: ~100 req/min on Polygon Starter plan. We call once per
entry decision (3 HTTP calls per ticker: stock + call + put).
Falls back to placeholder cost if Polygon is unavailable.
"""

from __future__ import annotations

import os
import sys
from typing import Optional

import httpx

# Sibling-of-backend path insert — same pattern as earnings_calendar.py
# so we can `from logger import get_logger` (and `import config`) without
# coupling to any trading-engine module.
_BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..", "backend")
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from logger import get_logger  # noqa: E402  (path insert above)

logger = get_logger("option_pricer")

REQUEST_TIMEOUT = 10.0

# Fallback straddle costs when Polygon is unavailable (approximate
# total straddle cost per share, not per leg). Based on typical
# ATM straddle prices at ~1 month IV for each ticker.
FALLBACK_STRADDLE_COST = {
    "NVDA": 45.0,   # ~5% of ~$900 stock
    "META": 28.0,
    "AAPL": 8.5,
    "TSLA": 22.0,
    "AMZN": 14.0,
    "GOOGL": 9.5,
}

# Fallback implied moves (historical averages, fraction of stock price).
FALLBACK_IMPLIED_MOVE = {
    "NVDA": 0.062,
    "META": 0.058,
    "AAPL": 0.032,
    "TSLA": 0.091,
    "AMZN": 0.054,
    "GOOGL": 0.049,
}


def get_atm_straddle_price(
    ticker: str,
    earnings_expiry: str,  # "YYYY-MM-DD" of the options expiration
) -> dict:
    """
    Fetch ATM straddle price for a ticker around its earnings date.

    Returns dict with:
      stock_price:       float
      call_strike:       float
      put_strike:        float (== call_strike at the ATM straddle)
      call_premium:      float (per share)
      put_premium:       float (per share)
      straddle_cost:     float (call_premium + put_premium per share)
      implied_move_pct:  float (fraction, e.g. 0.062 for 6.2%)
      source:            "polygon" | "fallback"

    Never raises — any error path returns the fallback dict so
    callers can always size a position.
    """
    try:
        import config
        if not config.POLYGON_API_KEY:
            return _fallback_price(ticker)

        stock_price = _fetch_stock_price(ticker, config.POLYGON_API_KEY)
        if not stock_price or stock_price <= 0:
            return _fallback_price(ticker)

        atm_strike = _round_to_nearest_strike(stock_price)
        call = _fetch_option_price(
            ticker, atm_strike, "call", earnings_expiry,
            config.POLYGON_API_KEY,
        )
        put = _fetch_option_price(
            ticker, atm_strike, "put", earnings_expiry,
            config.POLYGON_API_KEY,
        )

        if call is None or put is None:
            logger.warning(
                "option_price_fetch_partial",
                ticker=ticker,
                call=call,
                put=put,
            )
            return _fallback_price(ticker)

        straddle_cost = call + put
        implied_move_pct = (
            straddle_cost / stock_price if stock_price > 0 else 0.0
        )

        logger.info(
            "atm_straddle_priced",
            ticker=ticker,
            strike=atm_strike,
            call=call,
            put=put,
            straddle=straddle_cost,
            implied_move_pct=round(implied_move_pct * 100, 2),
        )

        return {
            "stock_price": round(stock_price, 2),
            "call_strike": atm_strike,
            "put_strike": atm_strike,
            "call_premium": round(call, 4),
            "put_premium": round(put, 4),
            "straddle_cost": round(straddle_cost, 4),
            "implied_move_pct": round(implied_move_pct, 4),
            "source": "polygon",
        }

    except Exception as exc:
        logger.warning(
            "atm_straddle_price_failed", ticker=ticker, error=str(exc)
        )
        return _fallback_price(ticker)


def _fetch_stock_price(ticker: str, api_key: str) -> Optional[float]:
    """Fetch last trade price for a stock. Returns None on any failure."""
    try:
        url = (
            f"https://api.polygon.io/v2/last/trade/{ticker}"
            f"?apiKey={api_key}"
        )
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            resp = client.get(url)
        if resp.status_code != 200:
            return None
        data = resp.json()
        price = float(data.get("results", {}).get("p") or 0)
        return price if price > 0 else None
    except Exception:
        return None


def _fetch_option_price(
    ticker: str,
    strike: float,
    option_type: str,  # "call" or "put"
    expiry: str,
    api_key: str,
) -> Optional[float]:
    """
    Fetch last trade price for a specific option contract.

    Two HTTP calls: first resolves the contract ticker symbol
    (e.g. "O:NVDA260417C00900000"), then fetches the last trade
    for that contract. Returns None if either step fails so the
    caller can fall back to placeholder pricing.
    """
    try:
        params = (
            f"?strike_price={strike}"
            f"&expiration_date={expiry}"
            f"&contract_type={option_type}"
            f"&limit=1"
            f"&apiKey={api_key}"
        )
        url = (
            f"https://api.polygon.io/v3/reference/options/"
            f"{ticker}{params}"
        )
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            resp = client.get(url)
        if resp.status_code != 200:
            return None
        data = resp.json()
        results = data.get("results", []) or []
        if not results:
            return None
        contract_ticker = results[0].get("ticker")
        if not contract_ticker:
            return None

        quote_url = (
            f"https://api.polygon.io/v2/last/trade/"
            f"{contract_ticker}?apiKey={api_key}"
        )
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            qresp = client.get(quote_url)
        if qresp.status_code != 200:
            return None
        qdata = qresp.json()
        price = float(qdata.get("results", {}).get("p") or 0)
        return price if price > 0 else None
    except Exception:
        return None


def _round_to_nearest_strike(price: float) -> float:
    """Round to the nearest standard strike increment for the price band."""
    if price >= 500:
        increment = 10.0
    elif price >= 200:
        increment = 5.0
    elif price >= 50:
        increment = 2.5
    else:
        increment = 1.0
    return round(price / increment) * increment


def _fallback_price(ticker: str) -> dict:
    """
    Return realistic fallback pricing when live data unavailable.

    Splits the fallback total straddle cost evenly across call/put
    legs (per the spec rule). Derives stock_price from the
    straddle/implied-move ratio so the dict is internally consistent
    with the Polygon-sourced shape.
    """
    sym = ticker.upper()
    straddle = FALLBACK_STRADDLE_COST.get(sym, 15.0)
    implied = FALLBACK_IMPLIED_MOVE.get(sym, 0.05)
    stock = straddle / implied if implied > 0 else 500.0
    strike = _round_to_nearest_strike(stock)
    half_leg = round(straddle / 2, 4)
    return {
        "stock_price": round(stock, 2),
        "call_strike": strike,
        "put_strike": strike,
        "call_premium": half_leg,
        "put_premium": half_leg,
        "straddle_cost": round(straddle, 4),
        "implied_move_pct": round(implied, 4),
        "source": "fallback",
    }
