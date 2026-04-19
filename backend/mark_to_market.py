"""
Mark-to-market updater — prices open virtual positions every minute.
Updates trading_positions.current_pnl so take-profit and stop-loss can fire.

Pricing priority:
1. Redis option quote (tradier:quotes:{symbol}) if position has concrete strikes
2. Black-Scholes estimate using current SPX price and time-to-expiry
3. Keep current_pnl=0 if no pricing data available (safe default)
"""
import json
from datetime import date, datetime, timezone
from typing import Optional

from db import get_client, write_health_status
from logger import get_logger

logger = get_logger("mark_to_market")


def _bs_option_price(
    S: float,
    K: float,
    T: float,
    r: float = 0.05,
    sigma: float = 0.15,
    option_type: str = "P",
) -> float:
    """
    Black-Scholes option price.
    S=underlying, K=strike, T=time in years, r=rate, sigma=IV.
    Returns mid-price estimate.
    """
    import math
    if T <= 0 or K <= 0 or S <= 0:
        return 0.0
    try:
        d1 = (
            math.log(S / K) + (r + 0.5 * sigma**2) * T
        ) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt(T)

        from scipy.stats import norm
        if option_type.upper() == "C":
            price = S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)
        else:
            price = K * math.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
        return max(0.0, round(price, 4))
    except Exception:
        return 0.0


def _get_spx_price(redis_client) -> float:
    """Get current SPX price from Redis."""
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


def _get_option_quote(redis_client, symbol: str) -> Optional[float]:
    """Get option mid-price from Redis. Returns None if not available."""
    try:
        raw = redis_client.get(f"tradier:quotes:{symbol}")
        if raw:
            data = json.loads(raw)
            bid = float(data.get("bid") or 0)
            ask = float(data.get("ask") or 0)
            if bid > 0 or ask > 0:
                return round((bid + ask) / 2, 4)
    except Exception:
        pass
    return None


def _build_option_symbol(
    root: str,
    expiry: str,
    strike: float,
    option_type: str,
) -> str:
    """Build OCC-format option symbol. e.g. SPXW241220P05200000"""
    try:
        exp_date = date.fromisoformat(expiry)
        yy = exp_date.strftime("%y")
        mm = exp_date.strftime("%m")
        dd = exp_date.strftime("%d")
        strike_int = int(round(strike * 1000))
        opt_type = option_type.upper()
        return f"{root}{yy}{mm}{dd}{opt_type}{strike_int:08d}"
    except Exception:
        return ""


def _price_position(
    pos: dict,
    spx_price: float,
    redis_client,
) -> Optional[float]:
    """
    Price a single open position. Returns current net P&L or None if
    pricing is not possible.
    """
    strategy_type = pos.get("strategy_type", "unknown")
    entry_credit = pos.get("entry_credit") or 0.0
    contracts = pos.get("contracts") or 1
    short_strike = pos.get("short_strike")
    long_strike = pos.get("long_strike")
    expiry = pos.get("expiry_date")
    is_debit = entry_credit < 0

    # Time to expiry
    T = 0.002  # default ~0.5 trading days
    if expiry:
        try:
            exp_date = date.fromisoformat(str(expiry))
            days = max(0, (exp_date - date.today()).days)
            T = max(0.0001, days / 365.0)
        except Exception:
            pass

    # Need short_strike to price
    if not short_strike:
        return None

    # Determine option type from strategy. long_straddle and
    # calendar_spread don't have a single "option type" (straddle is
    # both C and P; calendar is a stub), so they bypass this block —
    # see S4 / A-2 branches below.
    if strategy_type in ("put_credit_spread", "long_put", "debit_put_spread"):
        short_type = "P"
    elif strategy_type in ("call_credit_spread", "long_call", "debit_call_spread"):
        short_type = "C"
    elif strategy_type in ("iron_condor", "iron_butterfly"):
        short_type = "P"  # handle put leg; add call leg separately below
    elif strategy_type in ("long_straddle", "calendar_spread"):
        short_type = None  # not used by these branches
    else:
        return None

    # Try live quote first, fall back to Black-Scholes
    def get_leg_price(strike: float, opt_type: str) -> float:
        if not strike:
            return 0.0
        symbol = _build_option_symbol("SPXW", expiry or "", strike, opt_type)
        live = _get_option_quote(redis_client, symbol)
        if live is not None:
            return live
        # Black-Scholes fallback
        return _bs_option_price(spx_price, strike, T, option_type=opt_type)

    # Calculate current spread value
    current_spread_value = 0.0

    if strategy_type in ("put_credit_spread", "call_credit_spread"):
        short_price = get_leg_price(short_strike, short_type)
        long_price = (
            get_leg_price(long_strike, short_type) if long_strike else 0.0
        )
        # Credit spread value = short leg - long leg
        current_spread_value = short_price - long_price

    elif strategy_type in ("iron_condor", "iron_butterfly"):
        put_short_price = get_leg_price(short_strike, "P")
        put_long_price = (
            get_leg_price(pos.get("long_strike"), "P") if long_strike else 0.0
        )
        call_short_price = (
            get_leg_price(pos.get("short_strike_2"), "C")
            if pos.get("short_strike_2") else 0.0
        )
        call_long_price = (
            get_leg_price(pos.get("long_strike_2"), "C")
            if pos.get("long_strike_2") else 0.0
        )
        current_spread_value = (
            (put_short_price - put_long_price)
            + (call_short_price - call_long_price)
        )

    elif strategy_type in ("long_put", "long_call"):
        # S4 / A-3: positive value of the option we hold (NOT negative).
        # Combined with A-1 storing entry_credit as negative for debits,
        # the is_debit branch below correctly computes:
        #   pnl = (current_value - paid_premium) * contracts * 100
        # Prior bug: current_spread_value was -opt_price; the is_debit
        # formula then evaluated to -(opt_price + abs_entry)*c*100 —
        # always negative, so debit winners were booked as losses.
        opt_price = get_leg_price(short_strike, short_type)
        current_spread_value = opt_price

    elif strategy_type in ("debit_put_spread",):
        long_price = get_leg_price(short_strike, "P")
        short_price = get_leg_price(long_strike, "P") if long_strike else 0.0
        current_spread_value = long_price - short_price  # net debit value

    elif strategy_type in ("debit_call_spread",):
        long_price = get_leg_price(short_strike, "C")
        short_price = get_leg_price(long_strike, "C") if long_strike else 0.0
        current_spread_value = long_price - short_price

    elif strategy_type == "long_straddle":
        # S4 / A-2: ATM straddle MTM. The selector stores the ATM
        # strike in short_strike for straddles. Live quote is preferred,
        # BS fallback uses default sigma=0.15 — adequate for 0DTE
        # exit-trigger purposes; precision-sensitive paths should
        # consume Tradier mid via get_leg_price.
        call_price = get_leg_price(short_strike, "C")
        put_price = get_leg_price(short_strike, "P")
        # Same convention as debit spreads: positive value of the
        # premium we hold; the is_debit branch below subtracts abs_entry.
        current_spread_value = call_price + put_price

    elif strategy_type == "calendar_spread":
        # S4 / A-2: intentional stub. Real far/near differential pricing
        # requires multi-expiry chain handling deferred to S6. Holding
        # entry value forever pins current_pnl at zero, which means only
        # time stops will close calendar_spread — the 40% take-profit
        # and 150% stop-loss never fire on these positions until S6.
        # This is preferable to returning None (skipped) which would
        # leave current_pnl undefined.
        current_spread_value = abs(entry_credit)

    if current_spread_value == 0.0:
        return None

    # P&L for credit: entry_credit received - current_value_to_close
    # P&L for debit: current_value - |entry_credit| paid
    abs_entry = abs(entry_credit)
    if is_debit:
        pnl = (current_spread_value - abs_entry) * contracts * 100
    else:
        pnl = (abs_entry - current_spread_value) * contracts * 100

    return round(pnl, 2)


def run_mark_to_market(redis_client) -> dict:
    """
    Price all open virtual positions and update current_pnl.
    Called every minute during market hours from position_monitor.
    Returns {updated, skipped, errors}.
    Never raises.
    """
    try:
        # Fetch open positions with strike/expiry data
        result = (
            get_client()
            .table("trading_positions")
            .select(
                "id, strategy_type, entry_credit, contracts, expiry_date, "
                "short_strike, long_strike, short_strike_2, long_strike_2, "
                "current_pnl, peak_pnl"
            )
            .eq("status", "open")
            .eq("position_mode", "virtual")
            .execute()
        )
        positions = result.data or []

        if not positions:
            return {"updated": 0, "skipped": 0, "errors": 0}

        spx_price = _get_spx_price(redis_client)
        updated = skipped = errors = 0

        for pos in positions:
            try:
                new_pnl = _price_position(pos, spx_price, redis_client)

                if new_pnl is None:
                    skipped += 1
                    continue

                # Update peak_pnl (high-water mark)
                peak_pnl = max(
                    pos.get("peak_pnl") or 0.0,
                    new_pnl,
                )

                get_client().table("trading_positions").update({
                    "current_pnl": new_pnl,
                    "peak_pnl": peak_pnl,
                }).eq("id", pos["id"]).execute()

                updated += 1

            except Exception as e:
                logger.error(
                    "mtm_position_failed",
                    pos_id=pos.get("id"),
                    error=str(e),
                )
                errors += 1

        write_health_status("execution_engine", "healthy")
        logger.info(
            "mark_to_market_complete",
            updated=updated,
            skipped=skipped,
            errors=errors,
            spx_price=spx_price,
        )
        return {"updated": updated, "skipped": skipped, "errors": errors}

    except Exception as e:
        logger.error("mark_to_market_failed", error=str(e))
        return {"updated": 0, "skipped": 0, "errors": 1}
