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
                "entry_at, entry_credit, contracts, session_id, "
                "current_pnl, current_cv_stress, partial_exit_done"
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
    - Credit strategies: take profit at 50% of credit, stop at 200% of credit
    - Debit strategies: take profit at 100% gain, stop at 100% loss
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
            strategy_type = pos.get("strategy_type", "unknown")

            # Determine if this is a debit or credit strategy
            # Debit strategies have negative entry_credit (cost paid)
            is_debit = entry_credit < 0
            abs_entry = abs(entry_credit)

            if abs_entry == 0:
                continue

            # Get current P&L from Supabase (use data already in pos if available)
            current_pnl = pos.get("current_pnl") or 0.0
            contracts = pos.get("contracts") or 1

            if current_pnl == 0.0:
                # Fetch fresh data only if current_pnl not populated
                try:
                    full = (
                        get_client()
                        .table("trading_positions")
                        .select("current_pnl, entry_credit, contracts")
                        .eq("id", pos["id"])
                        .maybe_single()
                        .execute()
                    )
                    if not full.data:
                        continue
                    current_pnl = full.data.get("current_pnl") or 0.0
                    abs_entry = abs(full.data.get("entry_credit") or abs_entry)
                    contracts = full.data.get("contracts") or contracts
                except Exception:
                    continue

            max_profit = abs_entry * contracts * 100

            if is_debit:
                # Debit strategy: take profit at 2× debit paid (100% gain)
                take_profit_threshold = max_profit  # 100% of debit paid
                # Stop loss at 100% of debit paid (full loss of premium)
                stop_loss_threshold = -max_profit

                if current_pnl >= take_profit_threshold:
                    ok = engine.close_virtual_position(
                        position_id=pos["id"],
                        exit_reason="take_profit_debit_100pct",
                    )
                    if ok:
                        closed += 1
                        continue

                if current_pnl <= stop_loss_threshold:
                    ok = engine.close_virtual_position(
                        position_id=pos["id"],
                        exit_reason="stop_loss_debit_100pct",
                    )
                    if ok:
                        closed += 1
            else:
                # P0.6: Partial exit — close 30% of contracts at 25% of max profit
                # Only fires once per position (partial_exit_done flag).
                # Requires >= 3 contracts to be worth splitting.
                if (
                    max_profit > 0
                    and current_pnl >= max_profit * 0.25
                    and not pos.get("partial_exit_done")
                    and contracts >= 3
                ):
                    try:
                        partial_contracts = max(1, int(contracts * 0.30))
                        remaining_contracts = contracts - partial_contracts
                        # Book partial P&L proportionally
                        partial_pnl = round(
                            current_pnl * (partial_contracts / contracts), 4
                        )
                        # Mark position: reduce contracts, set partial_exit_done
                        get_client().table("trading_positions").update({
                            "contracts": remaining_contracts,
                            "partial_exit_done": True,
                        }).eq("id", pos["id"]).execute()
                        # Write audit log for partial exit
                        write_audit_log(
                            action="trading.partial_exit_25pct",
                            target_type="trading_positions",
                            target_id=str(pos["id"]),
                            metadata={
                                "original_contracts": contracts,
                                "partial_contracts_closed": partial_contracts,
                                "remaining_contracts": remaining_contracts,
                                "partial_pnl": partial_pnl,
                                "pct_max_profit": round(
                                    current_pnl / max_profit, 4
                                ),
                                "strategy_type": strategy_type,
                            },
                        )
                        logger.info(
                            "partial_exit_fired",
                            pos_id=pos["id"],
                            partial=partial_contracts,
                            remaining=remaining_contracts,
                            partial_pnl=partial_pnl,
                        )
                    except Exception as partial_err:
                        logger.error(
                            "partial_exit_failed",
                            pos_id=pos["id"],
                            error=str(partial_err),
                        )

                # Credit strategy: take profit at 50% of credit collected
                if max_profit > 0 and current_pnl >= max_profit * 0.50:
                    ok = engine.close_virtual_position(
                        position_id=pos["id"],
                        exit_reason="take_profit_50pct",
                    )
                    if ok:
                        closed += 1
                        continue

                # D-017: CV_Stress exit — only when P&L ≥ 50% of max profit
                if not is_debit and max_profit > 0:
                    cv_stress = pos.get("current_cv_stress") or 0.0
                    pct_profit = (
                        current_pnl / max_profit if max_profit > 0 else 0.0
                    )
                    # CV_Stress > 70 AND P&L ≥ 50% of max profit → exit
                    if cv_stress > 70.0 and pct_profit >= 0.50:
                        ok = engine.close_virtual_position(
                            position_id=pos["id"],
                            exit_reason="cv_stress_exit_d017",
                        )
                        if ok:
                            closed += 1
                            continue

                # Stop loss: loss exceeds 200% of credit collected
                # (correct for ~$5 spread: credit $1.50, max loss $3.50 ≈ 2.3×)
                stop_loss_threshold = -(max_profit * 2.0)
                if current_pnl <= stop_loss_threshold:
                    ok = engine.close_virtual_position(
                        position_id=pos["id"],
                        exit_reason="stop_loss_200pct_credit",
                    )
                    if ok:
                        closed += 1

        write_health_status("execution_engine", "healthy")
        return {"checked": len(positions), "closed": closed}

    except Exception as e:
        logger.error("position_monitor_failed", error=str(e))
        return {"checked": 0, "closed": 0, "error": str(e)}
