"""
Phase 5A: Earnings position monitor and exit logic.

Checks open earnings positions and exits when conditions are met:
  1. Doubled (100% profit)             -> close immediately (lock gains)
  2. 75% loss                          -> cut (stop out, premium decay won)
  3. 30 minutes after announcement opens-> hard exit
  4. Day of earnings at 3:45 PM ET     -> time stop if still open

Runs every 15 minutes during market hours.

NOTE: The P&L check uses an APPROXIMATE current value derived from
get_atm_straddle_price() — we do not have live option fills in
Phase 5A. This is intentional: the goal is virtual paper validation
of the earnings edge, not microsecond exit precision. When Phase 5B
adds live Tradier fills, swap _approximate_current_value() for the
broker mark.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import date, datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

# Sibling-of-backend path insert — same pattern as the other
# backend_earnings modules. Imports stay limited to logger plus
# this directory's siblings so the isolation guard keeps passing.
_BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..", "backend")
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from logger import get_logger  # noqa: E402

from earnings_executor import (  # noqa: E402
    close_earnings_position,
    get_open_earnings_positions,
)
from option_pricer import get_atm_straddle_price  # noqa: E402

logger = get_logger("earnings_monitor")

DOUBLE_PROFIT_THRESHOLD = 1.0  # 100% gain on debit -> double -> close
STOP_LOSS_THRESHOLD = -0.75    # 75% loss on debit -> cut
POST_ANNOUNCE_MINUTES = 30     # minutes after open to hold post-announce
TIME_STOP_HOUR = 15            # 3 PM ET hour
TIME_STOP_MINUTE = 45          # :45  (3:45 PM ET hard time stop)

_ET = ZoneInfo("America/New_York")


def monitor_earnings_positions(redis_client) -> dict:
    """
    Inspect every open virtual earnings position and close any that
    hit an exit condition. Returns a small summary dict.

    Updates the `earnings:active_position` Redis key with the most
    recent still-open position (or clears it when nothing is open)
    so dashboards have a fast read path. Never raises.
    """
    summary = {"checked": 0, "closed": 0, "errors": 0}
    try:
        positions = get_open_earnings_positions()
        summary["checked"] = len(positions)
        today = date.today()

        still_open: list[dict] = []
        for pos in positions:
            try:
                exit_reason = _should_exit(pos, today, redis_client)
                if exit_reason:
                    pricing = _approximate_current_value(pos)
                    exit_value = pricing["current_value"]
                    ok = close_earnings_position(
                        position_id=pos["id"],
                        exit_value=exit_value,
                        exit_reason=exit_reason,
                        actual_move_pct=pricing.get("actual_move_pct"),
                    )
                    if ok:
                        summary["closed"] += 1
                        # 12J: label the closed outcome for the earnings
                        # learning loop. close_earnings_position returns
                        # bool (not the closed row) so we compute net_pnl
                        # here from the pre-close debit + freshly
                        # computed exit_value. Fail-open: any labeling
                        # failure is swallowed inside
                        # label_earnings_outcome and must not affect
                        # the monitor summary.
                        try:
                            from edge_calculator import (
                                label_earnings_outcome,
                            )
                            total_debit = float(pos.get("total_debit") or 0)
                            net_pnl = round(exit_value - total_debit, 2)
                            label_input = {
                                **pos,
                                "net_pnl": net_pnl,
                                "exit_at": datetime.now(
                                    timezone.utc
                                ).isoformat(),
                                "actual_move_pct": pricing.get(
                                    "actual_move_pct"
                                ),
                            }
                            label_earnings_outcome(
                                label_input, redis_client
                            )
                        except Exception as label_exc:
                            logger.warning(
                                "earnings_outcome_label_outer_failed",
                                position_id=pos.get("id"),
                                error=str(label_exc),
                            )
                    else:
                        summary["errors"] += 1
                else:
                    still_open.append(pos)
            except Exception as exc:
                summary["errors"] += 1
                logger.warning(
                    "earnings_position_check_failed",
                    position_id=pos.get("id"),
                    error=str(exc),
                )

        # Reflect the most recently entered open position into Redis
        # for dashboards. None when nothing is open.
        active = still_open[-1] if still_open else None
        _update_redis_active(redis_client, active)

        logger.info("earnings_monitor_done", **summary)
        return summary

    except Exception as exc:
        logger.error("earnings_monitor_failed", error=str(exc))
        return summary


def _should_exit(
    pos: dict, today: date, redis_client
) -> Optional[str]:
    """
    Return an exit_reason string if the position should close now,
    else None. Order of checks matters: profit-take first, then
    stop-loss, then time-based exits.
    """
    try:
        total_debit = float(pos.get("total_debit") or 0)
        if total_debit <= 0:
            return None

        pricing = _approximate_current_value(pos)
        current_value = pricing["current_value"]
        pnl_pct = (current_value - total_debit) / total_debit

        if pnl_pct >= DOUBLE_PROFIT_THRESHOLD:
            return "doubled_take_profit"
        if pnl_pct <= STOP_LOSS_THRESHOLD:
            return "stopped_out_75pct_loss"

        # Time-based exits keyed off the earnings_date column.
        edate_str = pos.get("earnings_date")
        if not edate_str:
            return None
        edate = (
            edate_str
            if isinstance(edate_str, date)
            else date.fromisoformat(str(edate_str))
        )

        now_et = datetime.now(_ET)

        # 30 minutes after the announcement opens. Pre-market
        # announcements (announce_time='pre') -> exit at 10:00 AM ET
        # the same day. Post-market (announce_time='post') -> exit
        # at 10:00 AM ET the next trading day.
        announce = (pos.get("announce_time") or "unknown").lower()
        if today == edate and announce == "pre":
            ten_am = now_et.replace(
                hour=10, minute=0, second=0, microsecond=0
            )
            if now_et >= ten_am + timedelta(minutes=0):
                # 9:30 open + 30 min = 10:00 ET
                return "post_announcement_30min"
        if today > edate and announce == "post":
            return "post_announcement_30min"

        # 3:45 PM ET hard time stop on the day of earnings.
        if today == edate:
            stop = now_et.replace(
                hour=TIME_STOP_HOUR,
                minute=TIME_STOP_MINUTE,
                second=0,
                microsecond=0,
            )
            if now_et >= stop:
                return "time_stop_eod"

        return None
    except Exception as exc:
        logger.warning(
            "should_exit_check_failed",
            position_id=pos.get("id"),
            error=str(exc),
        )
        return None


def _approximate_current_value(pos: dict) -> dict:
    """
    Approximate the current dollar value of a straddle position.

    Uses get_atm_straddle_price() to refresh the call/put mid prices
    at the original strike. This is intentionally approximate:
      - We re-quote at the same expiry, same strike.
      - Polygon last-trade can lag a few minutes intraday.
      - Falls back to the entry pricing × decayed_theta heuristic
        (50% remaining premium on day-of-earnings) when live
        pricing is unavailable.
    Returns dict with current_value (total $), and optionally
    actual_move_pct when stock_price is available.
    """
    try:
        ticker = pos["ticker"]
        expiry = pos.get("expiry_date") or pos["earnings_date"]
        if isinstance(expiry, date):
            expiry = expiry.isoformat()

        pricing = get_atm_straddle_price(ticker, str(expiry))
        contracts = int(pos.get("contracts") or 1)

        # Re-mark using the refreshed straddle cost at the original
        # strike. This is approximate — Polygon does not let us
        # filter by the original strike here, but for ATM straddles
        # held only a few days the call+put total at the new ATM is
        # the best proxy we have without a broker mark.
        current_value = pricing["straddle_cost"] * 100 * contracts

        actual_move_pct = None
        entry_stock = float(pos.get("stock_price_at_entry") or 0)
        cur_stock = float(pricing.get("stock_price") or 0)
        if entry_stock > 0 and cur_stock > 0:
            actual_move_pct = round(
                (cur_stock - entry_stock) / entry_stock, 4
            )

        return {
            "current_value": round(current_value, 2),
            "actual_move_pct": actual_move_pct,
            "source": pricing.get("source", "unknown"),
        }
    except Exception:
        # Last-resort fallback: assume 50% of original debit remains.
        # Better to mark conservatively than to crash the monitor.
        total_debit = float(pos.get("total_debit") or 0)
        return {
            "current_value": round(total_debit * 0.5, 2),
            "actual_move_pct": None,
            "source": "decay_heuristic",
        }


def _update_redis_active(redis_client, position: Optional[dict]) -> None:
    """Best-effort write of `earnings:active_position`. Never raises."""
    try:
        if not redis_client:
            return
        if position is None:
            redis_client.delete("earnings:active_position")
            return
        # Slim payload — strip large/unused fields before publishing.
        payload = {
            k: v for k, v in position.items()
            if k in {
                "id", "ticker", "earnings_date", "announce_time",
                "entry_date", "expiry_date",
                "call_strike", "put_strike",
                "stock_price_at_entry", "total_debit",
                "contracts", "implied_move_pct",
                "historical_edge_score", "status",
            }
        }
        # Dates may come back as date objects from supabase-py; coerce.
        for k, v in list(payload.items()):
            if isinstance(v, (date, datetime)):
                payload[k] = v.isoformat()
        redis_client.setex(
            "earnings:active_position", 86_400, json.dumps(payload)
        )
    except Exception:
        pass
