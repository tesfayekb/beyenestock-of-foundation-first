"""
Position monitor — closes open virtual positions.
Implements D-010 (close short-gamma by 2:30 PM ET),
D-011 (close ALL positions by 3:45 PM ET).
Called every minute during market hours via APScheduler.
"""
from datetime import datetime, date, timezone
from typing import Optional

from db import get_client, write_health_status, write_audit_log
from execution_engine import ExecutionEngine
from logger import get_logger

logger = get_logger("position_monitor")

# Import strategy gamma classification
SHORT_GAMMA_STRATEGIES = {
    "put_credit_spread", "call_credit_spread",
    "iron_condor", "iron_butterfly",
}

_execution_engine: Optional[ExecutionEngine] = None


def _get_engine() -> ExecutionEngine:
    global _execution_engine
    if _execution_engine is None:
        _execution_engine = ExecutionEngine()
    return _execution_engine


def get_open_positions() -> list:
    """Fetch all open virtual positions. Returns empty list on error."""
    try:
        result = (
            get_client()
            .table("trading_positions")
            .select(
                "id, strategy_type, position_type, status, "
                "entry_at, entry_credit, contracts, session_id"
            )
            .eq("status", "open")
            .eq("position_mode", "virtual")
            .execute()
        )
        return result.data or []
    except Exception as e:
        logger.error("get_open_positions_failed", error=str(e))
        return []


def run_time_stop_230pm() -> dict:
    """
    D-010: Close all SHORT-GAMMA positions by 2:30 PM ET.
    Called at 2:30 PM ET by scheduler.
    Short-gamma = put_credit_spread, call_credit_spread,
    iron_condor, iron_butterfly.
    """
    try:
        positions = get_open_positions()
        short_gamma = [
            p for p in positions
            if p.get("strategy_type") in SHORT_GAMMA_STRATEGIES
        ]

        if not short_gamma:
            logger.info("time_stop_230pm_no_short_gamma_positions")
            return {"closed": 0, "skipped": 0}

        engine = _get_engine()
        closed = 0
        for pos in short_gamma:
            ok = engine.close_virtual_position(
                position_id=pos["id"],
                exit_reason="time_stop_230pm_d010",
            )
            if ok:
                closed += 1
                logger.info(
                    "time_stop_230pm_closed",
                    position_id=pos["id"],
                    strategy=pos.get("strategy_type"),
                )

        write_audit_log(
            action="trading.time_stop_230pm_executed",
            metadata={
                "positions_closed": closed,
                "positions_found": len(short_gamma),
            },
        )
        logger.info("time_stop_230pm_complete", closed=closed)
        return {"closed": closed, "skipped": len(short_gamma) - closed}

    except Exception as e:
        logger.error("time_stop_230pm_failed", error=str(e))
        return {"closed": 0, "error": str(e)}


def run_time_stop_345pm() -> dict:
    """
    D-011: Close ALL open positions by 3:45 PM ET.
    Called at 3:45 PM ET by scheduler. No exceptions.
    """
    try:
        positions = get_open_positions()

        if not positions:
            logger.info("time_stop_345pm_no_open_positions")
            return {"closed": 0}

        engine = _get_engine()
        closed = 0
        for pos in positions:
            ok = engine.close_virtual_position(
                position_id=pos["id"],
                exit_reason="time_stop_345pm_d011",
            )
            if ok:
                closed += 1
                logger.info(
                    "time_stop_345pm_closed",
                    position_id=pos["id"],
                    strategy=pos.get("strategy_type"),
                )

        write_audit_log(
            action="trading.time_stop_345pm_executed",
            metadata={
                "positions_closed": closed,
                "positions_found": len(positions),
            },
        )
        logger.info("time_stop_345pm_complete", closed=closed)
        return {"closed": closed}

    except Exception as e:
        logger.error("time_stop_345pm_failed", error=str(e))
        return {"closed": 0, "error": str(e)}


def run_position_monitor() -> dict:
    """
    Runs every minute during market hours.
    Checks for positions that should be closed based on:
    - P&L reaching 50% of max profit (take profit)
    - P&L reaching -100% of entry credit (stop loss)
    Returns summary dict. Never raises.
    """
    try:
        positions = get_open_positions()
        if not positions:
            return {"checked": 0, "closed": 0}

        engine = _get_engine()
        closed = 0

        for pos in positions:
            entry_credit = pos.get("entry_credit") or 0.0
            if entry_credit <= 0:
                continue

            # Get current P&L from Supabase
            try:
                full = (
                    get_client()
                    .table("trading_positions")
                    .select("current_pnl, entry_credit, contracts")
                    .eq("id", pos["id"])
                    .maybeSingle()
                    .execute()
                )
                if not full.data:
                    continue
                current_pnl = full.data.get("current_pnl") or 0.0
                entry_credit_full = full.data.get("entry_credit") or 0.0
                contracts = full.data.get("contracts") or 1
            except Exception:
                continue

            # Take profit: 50% of max profit
            max_profit = entry_credit_full * contracts * 100
            if max_profit > 0 and current_pnl >= max_profit * 0.50:
                ok = engine.close_virtual_position(
                    position_id=pos["id"],
                    exit_reason="take_profit_50pct",
                )
                if ok:
                    closed += 1
                    continue

            # Stop loss: loss exceeds 100% of entry credit collected
            max_loss = entry_credit_full * contracts * 100
            if current_pnl <= -max_loss:
                ok = engine.close_virtual_position(
                    position_id=pos["id"],
                    exit_reason="stop_loss_100pct",
                )
                if ok:
                    closed += 1

        write_health_status("execution_engine", "healthy")
        return {"checked": len(positions), "closed": closed}

    except Exception as e:
        logger.error("position_monitor_failed", error=str(e))
        return {"checked": 0, "closed": 0, "error": str(e)}
