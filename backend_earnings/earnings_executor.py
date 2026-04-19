"""
Phase 5A: Earnings position recorder (virtual paper trading).

Records straddle entries and exits to the earnings_positions table.
Uses the same Supabase client as the rest of the system. No Tradier
orders in Phase 5A — virtual positions only. Live mode is gated
behind position_mode='live' in the schema for a future phase.

Mirrors the insert/update pattern from
backend/execution_engine.open_virtual_position(): try/except wrapper,
build dict, insert via supabase, return result.data[0] if data else
the local dict so callers always get a usable record back.
"""

from __future__ import annotations

import os
import sys
from datetime import date, datetime, timedelta, timezone
from typing import Optional

# Sibling-of-backend path insert — same pattern as earnings_calendar.py
# and option_pricer.py. We need backend/db.py and backend/logger.py
# only — never the trading-engine modules.
_BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..", "backend")
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from db import get_client  # noqa: E402  (path insert above)
from logger import get_logger  # noqa: E402

logger = get_logger("earnings_executor")


def open_earnings_straddle(
    ticker: str,
    earnings_date: date,
    announce_time: str,
    pricing: dict,
    contracts: int,
    account_allocation_pct: float,
    edge_score: float,
) -> Optional[dict]:
    """
    Record a new virtual earnings straddle position.

    Returns the created position row (from Supabase if available,
    else the local dict) or None on failure. Never raises.
    """
    try:
        expiry = _find_earnings_expiry(earnings_date, announce_time)

        total_debit = pricing["straddle_cost"] * 100 * contracts

        position = {
            "ticker": ticker,
            "earnings_date": earnings_date.isoformat(),
            "announce_time": announce_time,
            "position_mode": "virtual",
            "strategy_type": "earnings_straddle",
            "entry_date": date.today().isoformat(),
            "call_strike": pricing["call_strike"],
            "put_strike": pricing["put_strike"],
            "stock_price_at_entry": pricing["stock_price"],
            "call_premium": pricing["call_premium"],
            "put_premium": pricing["put_premium"],
            "total_debit": round(total_debit, 2),
            "contracts": contracts,
            "account_allocation_pct": account_allocation_pct,
            "expiry_date": expiry.isoformat(),
            "implied_move_pct": pricing["implied_move_pct"],
            "historical_edge_score": edge_score,
            "status": "open",
        }

        result = (
            get_client()
            .table("earnings_positions")
            .insert(position)
            .execute()
        )
        created = result.data[0] if result.data else position

        logger.info(
            "earnings_straddle_opened",
            ticker=ticker,
            earnings_date=earnings_date.isoformat(),
            contracts=contracts,
            total_debit=total_debit,
            implied_move_pct=pricing.get("implied_move_pct"),
        )
        return created

    except Exception as exc:
        logger.error(
            "earnings_straddle_open_failed",
            ticker=ticker,
            error=str(exc),
        )
        return None


def close_earnings_position(
    position_id: str,
    exit_value: float,  # total exit proceeds (call_exit + put_exit) × 100 × contracts
    exit_reason: str,
    actual_move_pct: Optional[float] = None,
) -> bool:
    """
    Close an open earnings position.

    Reads the existing row first (per spec rule — never update
    blindly) so we can compute net P&L from the recorded total_debit
    and verify the row is in 'open' state before mutating.

    Returns True on success, False on any failure (missing row,
    closed row, DB error, etc.). Never raises.
    """
    try:
        pos_result = (
            get_client()
            .table("earnings_positions")
            .select("*")
            .eq("id", position_id)
            .eq("status", "open")
            .maybe_single()
            .execute()
        )
        pos = pos_result.data if pos_result else None
        if not pos:
            logger.warning(
                "earnings_close_position_not_found",
                position_id=position_id,
            )
            return False

        total_debit = float(pos.get("total_debit") or 0)
        net_pnl = round(exit_value - total_debit, 2)
        net_pnl_pct = (
            round(net_pnl / total_debit, 4) if total_debit > 0 else 0.0
        )

        update = {
            "status": "closed",
            "exit_date": date.today().isoformat(),
            "exit_value": round(exit_value, 2),
            "exit_reason": exit_reason,
            "net_pnl": net_pnl,
            "net_pnl_pct": net_pnl_pct,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if actual_move_pct is not None:
            update["actual_move_pct"] = round(actual_move_pct, 4)

        (
            get_client()
            .table("earnings_positions")
            .update(update)
            .eq("id", position_id)
            .execute()
        )

        logger.info(
            "earnings_straddle_closed",
            ticker=pos.get("ticker"),
            exit_reason=exit_reason,
            net_pnl=net_pnl,
            net_pnl_pct=f"{net_pnl_pct:.1%}",
        )
        return True

    except Exception as exc:
        logger.error(
            "earnings_close_failed",
            position_id=position_id,
            error=str(exc),
        )
        return False


def get_open_earnings_positions() -> list[dict]:
    """
    Fetch all currently open virtual earnings positions, oldest first.
    Returns [] on any failure.
    """
    try:
        result = (
            get_client()
            .table("earnings_positions")
            .select("*")
            .eq("status", "open")
            .eq("position_mode", "virtual")
            .order("entry_date", desc=False)
            .execute()
        )
        return result.data or []
    except Exception as exc:
        logger.warning(
            "get_open_earnings_positions_failed", error=str(exc)
        )
        return []


def _find_earnings_expiry(earnings_date: date, announce_time: str) -> date:
    """
    Find the appropriate options expiration date for a straddle.

    Uses the Friday of the earnings week as the standard weekly
    expiry. If earnings are post-market on a Friday (so the move
    happens after expiry) we roll forward to the following Friday.

    Mirrors the Mon-Fri arithmetic used in
    earnings_calendar._trading_days_before() — pure calendar
    math, no exchange-holiday awareness (good enough for the
    weekly options chain on these 6 mega-cap tickers).
    """
    weekday = earnings_date.weekday()
    days_to_friday = (4 - weekday) % 7
    friday = earnings_date + timedelta(days=days_to_friday)

    if announce_time == "post" and days_to_friday == 0:
        # Earnings on Friday post-market → use next Friday so the
        # contracts are still alive when the post-announcement move
        # plays out the following Monday morning.
        friday += timedelta(days=7)

    return friday
