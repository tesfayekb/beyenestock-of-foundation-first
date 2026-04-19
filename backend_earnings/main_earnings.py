"""
Phase 5A: Earnings system orchestrator.

Called from backend/main.py via sys.path.insert (same pattern as
backend_agents/economic_calendar). Three entry points, each
scheduled by APScheduler in main.py:

  run_earnings_scan(redis)    -> 8:45 AM ET — scan calendar, write
                                  earnings:upcoming_events
  run_earnings_entry(redis)   -> 9:50 AM ET — open at most ONE new
                                  straddle if today is the entry day
                                  for an upcoming event AND we have
                                  no other open earnings position
  run_earnings_monitor(redis) -> every 15 min, 9-15 ET — exit logic

Every entry point is fully wrapped in try/except so a failure here
never affects the SPX trading engine in backend/.
"""

from __future__ import annotations

import os
import sys
from datetime import date
from typing import Optional

# Sibling-of-backend path insert — exact same pattern as the other
# backend_earnings/ modules. We only ever import from backend/
# logger.py and backend/config.py here (config is optional).
_BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..", "backend")
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from logger import get_logger  # noqa: E402

from earnings_calendar import (  # noqa: E402
    get_upcoming_events,
    scan_upcoming_earnings,
)
from earnings_executor import (  # noqa: E402
    get_open_earnings_positions,
    open_earnings_straddle,
)
from earnings_monitor import monitor_earnings_positions  # noqa: E402
from option_pricer import get_atm_straddle_price  # noqa: E402
from edge_calculator import (  # noqa: E402
    compute_edge_score,
    has_sufficient_edge,
    get_position_size_pct,
)

logger = get_logger("main_earnings")

# Default account size when config does not expose one. Phase 5A
# uses virtual sizing only, so this is just a notional anchor for
# the per-position dollar allocation math.
MAX_ACCOUNT_VALUE = 200_000.0


def run_earnings_scan(redis_client) -> dict:
    """8:45 AM ET — refresh upcoming earnings events from Finnhub."""
    try:
        events = scan_upcoming_earnings(redis_client) or []
        logger.info("earnings_scan_done", count=len(events))
        return {"count": len(events), "events": events}
    except Exception as exc:
        logger.error("earnings_scan_failed", error=str(exc))
        return {"count": 0, "events": []}


def run_earnings_entry(redis_client) -> dict:
    """
    9:50 AM ET — if today is the preferred entry day for an upcoming
    earnings event and we have no open position, open at most ONE
    new straddle.

    Per spec rule: ONE position at a time. We early-return when
    get_open_earnings_positions() is non-empty, regardless of the
    candidate's edge score.
    """
    try:
        if get_open_earnings_positions():
            logger.info("earnings_entry_skipped_position_open")
            return {"opened": False, "reason": "position_already_open"}

        events = get_upcoming_events(redis_client) or []
        today = date.today()

        # Pick the first event whose entry_date is today AND that
        # passes the edge filter. Events are sorted by entry_date
        # ascending in scan_upcoming_earnings(), so the first match
        # is the earliest one ripe for entry.
        candidate: Optional[dict] = None
        for ev in events:
            entry_date_str = ev.get("entry_date")
            if not entry_date_str:
                continue
            entry_d = (
                entry_date_str
                if isinstance(entry_date_str, date)
                else date.fromisoformat(str(entry_date_str))
            )
            if entry_d != today:
                continue
            if not ev.get("should_enter"):
                continue
            candidate = ev
            break

        if not candidate:
            logger.info("earnings_entry_no_candidate", events=len(events))
            return {"opened": False, "reason": "no_candidate_today"}

        ticker = candidate["ticker"]
        earnings_date_str = candidate["earnings_date"]
        earnings_d = (
            earnings_date_str
            if isinstance(earnings_date_str, date)
            else date.fromisoformat(str(earnings_date_str))
        )
        announce_time = candidate.get("announce_time", "post")

        expiry_str = _find_expiry_str(earnings_d, announce_time)
        pricing = get_atm_straddle_price(ticker, expiry_str)

        # Re-check edge using the freshly observed implied move so
        # we do not enter when the market has already priced in the
        # full historical move.
        if not has_sufficient_edge(ticker, pricing["implied_move_pct"]):
            logger.info(
                "earnings_entry_skipped_insufficient_edge",
                ticker=ticker,
                implied_move_pct=pricing.get("implied_move_pct"),
            )
            return {"opened": False, "reason": "insufficient_edge"}

        size_pct = get_position_size_pct(ticker, MAX_ACCOUNT_VALUE)
        # size_pct is a fraction (0.05 - 0.15) per edge_calculator.
        dollar_alloc = size_pct * MAX_ACCOUNT_VALUE
        per_contract_cost = max(pricing["straddle_cost"] * 100, 1.0)
        contracts = max(1, int(dollar_alloc // per_contract_cost))

        edge = compute_edge_score(ticker)
        position = open_earnings_straddle(
            ticker=ticker,
            earnings_date=earnings_d,
            announce_time=announce_time,
            pricing=pricing,
            contracts=contracts,
            account_allocation_pct=round(size_pct, 4),
            edge_score=round(edge, 4),
        )
        if not position:
            return {"opened": False, "reason": "insert_failed"}

        logger.info(
            "earnings_entry_opened",
            ticker=ticker,
            contracts=contracts,
            allocation_pct=size_pct,
            edge=edge,
        )
        return {
            "opened": True,
            "ticker": ticker,
            "contracts": contracts,
            "position_id": position.get("id"),
        }

    except Exception as exc:
        logger.error("earnings_entry_failed", error=str(exc))
        return {"opened": False, "reason": "exception"}


def run_earnings_monitor(redis_client) -> dict:
    """Every 15 min during market hours — exit logic for open positions."""
    try:
        return monitor_earnings_positions(redis_client)
    except Exception as exc:
        logger.error("earnings_monitor_failed", error=str(exc))
        return {"checked": 0, "closed": 0, "errors": 1}


def _find_expiry_str(earnings_date: date, announce_time: str) -> str:
    """Local mirror of _find_earnings_expiry, returning ISO string."""
    from earnings_executor import _find_earnings_expiry
    return _find_earnings_expiry(earnings_date, announce_time).isoformat()
