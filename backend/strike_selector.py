"""
Strike selector — selects concrete option strikes for each strategy.
Uses Tradier option chain REST API to get current chain with Greeks.
Falls back to SPX price ± percentage if Tradier returns no data.

Called by strategy_selector before building each signal.
Returns: short_strike, long_strike, short_strike_2, long_strike_2,
         expiry_date, spread_width, target_credit.
"""
import json
from datetime import date, timedelta
from typing import Optional

import httpx

from logger import get_logger

logger = get_logger("strike_selector")

# Default spread width in points when GEX wall is not available
DEFAULT_SPREAD_WIDTH = 5.0  # Used when VIX is unavailable

# VIX-regime spread width table
# Wider spreads in high-vol regimes: more premium for same delta
VIX_SPREAD_WIDTH_TABLE = [
    (15.0, 2.50),   # VIX < 15: tight, low-premium environment
    (20.0, 5.00),   # VIX 15-20: normal
    (30.0, 7.50),   # VIX 20-30: elevated vol
    (float("inf"), 10.00),  # VIX > 30: high stress, maximum premium
]


def get_dynamic_spread_width(vix_level: float) -> float:
    """
    Return spread width in points based on current VIX level.
    Higher VIX = wider spread = more premium collected per trade.
    Falls back to DEFAULT_SPREAD_WIDTH if vix_level is invalid.
    """
    if vix_level <= 0:
        return DEFAULT_SPREAD_WIDTH
    for threshold, width in VIX_SPREAD_WIDTH_TABLE:
        if vix_level < threshold:
            return width
    return 10.00

# Target deltas by strategy
# 16 delta ≈ 1 standard deviation away (credit spread standard)
# 25 delta ≈ closer to money (debit strategies)
DELTA_BY_STRATEGY = {
    "put_credit_spread":  0.16,
    "call_credit_spread": 0.16,
    "iron_condor":        0.16,
    "iron_butterfly":     0.50,  # ATM
    "debit_put_spread":   0.25,
    "debit_call_spread":  0.25,
    "long_put":           0.25,
    "long_call":          0.25,
}

CREDIT_STRATEGIES = {
    "put_credit_spread", "call_credit_spread",
    "iron_condor", "iron_butterfly",
}


def _get_0dte_expiry() -> str:
    """
    Get today's 0DTE expiry date for SPX.
    SPX has options on Mon/Wed/Fri (plus daily since 2023).
    For simplicity: if today is a weekday, use today; else use next Monday.
    """
    today = date.today()
    if today.weekday() < 5:  # Mon-Fri
        return today.isoformat()
    # Saturday → next Monday
    days_ahead = 7 - today.weekday()
    return (today + timedelta(days=days_ahead)).isoformat()


def _get_spx_price_from_redis(redis_client) -> float:
    """Read current SPX price from Redis. Returns 5200.0 if unavailable."""
    try:
        raw = redis_client.get("tradier:quotes:SPX")
        if raw:
            data = json.loads(raw)
            return float(
                data.get("last") or data.get("ask") or data.get("bid") or 5200.0
            )
    except Exception:
        pass
    return 5200.0


def _get_option_chain_tradier(
    expiry: str,
    redis_client,
) -> list:
    """
    Fetch SPX option chain from Tradier REST API.
    Returns list of option dicts with strike, delta, bid, ask.
    Returns [] on any error (caller falls back to SPX±pct method).
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

    try:
        resp = httpx.get(
            f"{base_url}/v1/markets/options/chains",
            params={
                "symbol": "SPX",
                "expiration": expiry,
                "greeks": "true",
            },
            headers=headers,
            timeout=10.0,
        )
        if resp.status_code != 200:
            logger.warning(
                "tradier_chain_non200",
                status=resp.status_code,
                expiry=expiry,
            )
            return []
        data = resp.json()
        options = data.get("options", {}).get("option", [])
        if isinstance(options, dict):
            options = [options]
        return options or []
    except Exception as e:
        logger.warning("tradier_chain_failed", error=str(e), expiry=expiry)
        return []


def _find_strike_by_delta(
    chain: list,
    target_delta: float,
    option_type: str,  # "put" or "call"
    above_spx: bool,   # True = OTM call side, False = OTM put side
) -> Optional[float]:
    """
    Find the strike whose absolute delta is closest to target_delta.
    option_type: "put" or "call"
    """
    candidates = [
        opt for opt in chain
        if opt.get("option_type", "").lower() == option_type
        and opt.get("greeks") is not None
    ]
    if not candidates:
        return None

    def delta_distance(opt):
        greeks = opt.get("greeks") or {}
        delta = abs(float(greeks.get("delta") or 0.0))
        return abs(delta - target_delta)

    best = min(candidates, key=delta_distance)
    return float(best.get("strike", 0.0)) or None


def _fallback_strikes(
    spx_price: float,
    strategy_type: str,
    spread_width: float = DEFAULT_SPREAD_WIDTH,
) -> dict:
    """
    Fallback strike selection when Tradier chain is unavailable.
    Uses SPX price ± percentage approximation.
    16 delta ≈ SPX ± 1.5% for 0DTE.
    25 delta ≈ SPX ± 0.8% for 0DTE.
    """
    expiry = _get_0dte_expiry()
    target_delta = DELTA_BY_STRATEGY.get(strategy_type, 0.16)

    # Approximate distance for target delta (0DTE rough rule of thumb)
    pct_away = 0.015 if target_delta <= 0.16 else 0.008

    put_short = round(spx_price * (1 - pct_away) / 5) * 5   # round to $5
    call_short = round(spx_price * (1 + pct_away) / 5) * 5
    put_long = put_short - spread_width
    call_long = call_short + spread_width

    result = {
        "expiry_date": expiry,
        "spread_width": spread_width,
        "short_strike": None,
        "long_strike": None,
        "short_strike_2": None,
        "long_strike_2": None,
        "target_credit": None,
    }

    if strategy_type == "put_credit_spread":
        result.update({"short_strike": put_short, "long_strike": put_long})
    elif strategy_type == "call_credit_spread":
        result.update({"short_strike": call_short, "long_strike": call_long})
    elif strategy_type in ("iron_condor", "iron_butterfly"):
        result.update({
            "short_strike": put_short,
            "long_strike": put_long,
            "short_strike_2": call_short,
            "long_strike_2": call_long,
        })
    elif strategy_type == "debit_put_spread":
        result.update({"short_strike": put_short - 5, "long_strike": put_short})
    elif strategy_type == "debit_call_spread":
        result.update({"short_strike": call_short + 5, "long_strike": call_short})
    elif strategy_type in ("long_put",):
        result.update({"short_strike": put_short, "long_strike": None})
    elif strategy_type in ("long_call",):
        result.update({"short_strike": call_short, "long_strike": None})

    return result


def get_strikes(
    strategy_type: str,
    redis_client,
) -> dict:
    """
    Main entry point. Returns strike dict for the given strategy.
    Tries Tradier chain first, falls back to SPX±pct approximation.

    Returns dict with:
      short_strike, long_strike, short_strike_2, long_strike_2,
      expiry_date, spread_width, target_credit (from chain mid-price or None)
    """
    spx_price = _get_spx_price_from_redis(redis_client)
    expiry = _get_0dte_expiry()

    # Read current VIX for dynamic spread width
    vix_level = 18.0
    try:
        if redis_client:
            vix_raw = redis_client.get("polygon:vix:current")
            if vix_raw:
                vix_level = float(vix_raw)
    except Exception:
        pass  # Use default VIX if Redis unavailable

    dynamic_width = get_dynamic_spread_width(vix_level)

    result = {
        "expiry_date": expiry,
        "spread_width": dynamic_width,
        "vix_level_used": round(vix_level, 1),
        "short_strike": None,
        "long_strike": None,
        "short_strike_2": None,
        "long_strike_2": None,
        "target_credit": None,
    }

    try:
        chain = _get_option_chain_tradier(expiry, redis_client)

        if not chain:
            logger.info(
                "strike_selector_fallback",
                strategy=strategy_type,
                reason="empty_chain",
            )
            return _fallback_strikes(spx_price, strategy_type, dynamic_width)

        target_delta = DELTA_BY_STRATEGY.get(strategy_type, 0.16)

        if strategy_type == "put_credit_spread":
            short = _find_strike_by_delta(chain, target_delta, "put", False)
            if short:
                result["short_strike"] = short
                result["long_strike"] = short - dynamic_width
                # Get mid-price for target_credit
                opt = next(
                    (o for o in chain if float(o.get("strike", 0)) == short
                     and o.get("option_type", "").lower() == "put"), None
                )
                if opt:
                    bid = float(opt.get("bid") or 0)
                    ask = float(opt.get("ask") or 0)
                    result["target_credit"] = round((bid + ask) / 2, 2)

        elif strategy_type == "call_credit_spread":
            short = _find_strike_by_delta(chain, target_delta, "call", True)
            if short:
                result["short_strike"] = short
                result["long_strike"] = short + dynamic_width
                opt = next(
                    (o for o in chain if float(o.get("strike", 0)) == short
                     and o.get("option_type", "").lower() == "call"), None
                )
                if opt:
                    bid = float(opt.get("bid") or 0)
                    ask = float(opt.get("ask") or 0)
                    result["target_credit"] = round((bid + ask) / 2, 2)

        elif strategy_type in ("iron_condor", "iron_butterfly"):
            put_short = _find_strike_by_delta(chain, target_delta, "put", False)
            call_short = _find_strike_by_delta(chain, target_delta, "call", True)
            if put_short and call_short:
                result.update({
                    "short_strike": put_short,
                    "long_strike": put_short - dynamic_width,
                    "short_strike_2": call_short,
                    "long_strike_2": call_short + dynamic_width,
                })

        elif strategy_type in ("long_put", "debit_put_spread"):
            short = _find_strike_by_delta(chain, target_delta, "put", False)
            if short:
                result["short_strike"] = short
                if strategy_type == "debit_put_spread":
                    result["long_strike"] = short + dynamic_width

        elif strategy_type in ("long_call", "debit_call_spread"):
            short = _find_strike_by_delta(chain, target_delta, "call", True)
            if short:
                result["short_strike"] = short
                if strategy_type == "debit_call_spread":
                    result["long_strike"] = short - dynamic_width

        # If strikes still None (chain had no greeks), use fallback
        if result["short_strike"] is None:
            return _fallback_strikes(spx_price, strategy_type, dynamic_width)

        logger.info(
            "strikes_selected",
            strategy=strategy_type,
            short=result["short_strike"],
            long=result["long_strike"],
            expiry=expiry,
            spx=spx_price,
        )
        return result

    except Exception as e:
        logger.error("strike_selector_failed", error=str(e), strategy=strategy_type)
        return _fallback_strikes(spx_price, strategy_type, dynamic_width)
