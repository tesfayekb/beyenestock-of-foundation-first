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
_redis_client = None


def _get_engine() -> ExecutionEngine:
    global _execution_engine
    if _execution_engine is None:
        _execution_engine = ExecutionEngine()
    return _execution_engine


def _get_redis():
    """Lazy Redis client for Phase 2B pre-event straddle exits.
    Returns None on any failure — never raises."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        import redis as redis_lib
        from config import REDIS_URL
        _redis_client = redis_lib.Redis.from_url(
            REDIS_URL, decode_responses=True
        )
        return _redis_client
    except Exception as e:
        logger.warning("position_monitor_redis_init_failed", error=str(e))
        return None


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


def run_emergency_backstop() -> dict:
    """
    HARD-A: Emergency position backstop.

    Runs at 3:55 PM ET — 10 minutes after the 3:45 PM time stop.
    Closes ANY position still marked 'open' in the DB.

    This catches:
    - 3:45 PM time stop job crashed or hung
    - Execution engine failed to write exit_at to DB
    - Scheduler missed the 3:45 PM window (timezone issue, restart)

    exit_reason = 'emergency_backstop' for audit trail.
    Positions closed here indicate a prior failure — investigate logs.
    """
    try:
        positions = get_open_positions()
        if not positions:
            logger.info("emergency_backstop_no_open_positions")
            return {"closed": 0, "triggered": False}

        engine = _get_engine()
        closed = 0
        for pos in positions:
            ok = engine.close_virtual_position(
                position_id=pos["id"],
                exit_reason="emergency_backstop",
            )
            if ok:
                closed += 1
                logger.warning(
                    "emergency_backstop_closed_position",
                    position_id=pos["id"],
                    strategy=pos.get("strategy_type"),
                    entry_at=pos.get("entry_at"),
                )

        if closed > 0:
            write_audit_log(
                action="trading.emergency_backstop_triggered",
                metadata={
                    "positions_closed": closed,
                    "reason": "positions_still_open_at_355pm",
                },
            )
            logger.error(
                "emergency_backstop_triggered",
                positions_closed=closed,
                message=(
                    "Time stop failure detected — positions were open at 3:55 PM"
                ),
            )
            # HARD-B: external alert on backstop trigger (indicates
            # the 3:45 PM time stop failed for some reason). Imported
            # lazily inside the try block to avoid circular imports.
            try:
                from alerting import send_alert, CRITICAL
                send_alert(
                    CRITICAL,
                    "emergency_backstop_triggered",
                    f"{closed} position(s) were still open at 3:55 PM ET. "
                    f"The 3:45 PM time stop may have failed. "
                    f"Check Railway logs for time_stop_345pm_failed.",
                )
            except Exception:
                pass

        return {"closed": closed, "triggered": closed > 0}

    except Exception as exc:
        logger.error("emergency_backstop_failed", error=str(exc))
        return {"closed": 0, "triggered": False, "error": str(exc)}


def run_prediction_watchdog() -> dict:
    """
    HARD-A: Dead man's switch for the prediction engine.

    Runs every 5 minutes during market hours (9:35 AM - 3:45 PM ET).
    If the prediction engine has not written a prediction in the last
    12 minutes, something is wrong.

    Response:
    - Write critical health status for prediction_engine
    - If open positions exist: close all immediately
      (cannot safely manage positions without current predictions)
    - Log trading.prediction_watchdog_triggered for audit

    12-minute window rationale: prediction_engine writes every ~5 min
    during market hours. 12 minutes = 2.4 missed cycles — enough to
    distinguish a slow cycle from a genuine failure.
    """
    from datetime import timedelta

    STALE_THRESHOLD_MINUTES = 12

    try:
        result = (
            get_client()
            .table("trading_prediction_outputs")
            .select("predicted_at")
            .order("predicted_at", desc=True)
            .limit(1)
            .execute()
        )
        rows = result.data or []

        if not rows:
            logger.debug("prediction_watchdog_no_predictions_yet")
            return {"status": "no_predictions", "action": "none"}

        last_predicted_at = datetime.fromisoformat(
            rows[0]["predicted_at"].replace("Z", "+00:00")
        )
        age_minutes = (
            datetime.now(timezone.utc) - last_predicted_at
        ).total_seconds() / 60

        if age_minutes <= STALE_THRESHOLD_MINUTES:
            logger.debug(
                "prediction_watchdog_ok", age_minutes=round(age_minutes, 1)
            )
            return {"status": "healthy", "age_minutes": round(age_minutes, 1)}

        # Prediction engine is silent — take action
        logger.error(
            "prediction_engine_silent",
            age_minutes=round(age_minutes, 1),
            threshold=STALE_THRESHOLD_MINUTES,
        )

        open_positions = get_open_positions()
        closed = 0
        if open_positions:
            engine = _get_engine()
            for pos in open_positions:
                ok = engine.close_virtual_position(
                    position_id=pos["id"],
                    exit_reason="watchdog_engine_silent",
                )
                if ok:
                    closed += 1
                    logger.warning(
                        "watchdog_closed_position",
                        position_id=pos["id"],
                        strategy=pos.get("strategy_type"),
                    )

        write_audit_log(
            action="trading.prediction_watchdog_triggered",
            metadata={
                "age_minutes": round(age_minutes, 1),
                "positions_closed": closed,
            },
        )
        # HARD-B: external alert on watchdog trigger. Imported
        # lazily inside the try block to avoid circular imports.
        try:
            from alerting import send_alert, CRITICAL
            send_alert(
                CRITICAL,
                "prediction_watchdog_triggered",
                f"Prediction engine silent for "
                f"{round(age_minutes, 1)} minutes. "
                f"{closed} open position(s) were closed as a precaution. "
                f"Check Railway logs for prediction_engine errors.",
            )
        except Exception:
            pass

        return {
            "status": "triggered",
            "age_minutes": round(age_minutes, 1),
            "positions_closed": closed,
        }

    except Exception as exc:
        logger.error("prediction_watchdog_failed", error=str(exc))
        return {"status": "error", "error": str(exc)}


def run_eod_position_reconciliation() -> dict:
    """
    HARD-A: End-of-day position reconciliation.

    Runs at 4:15 PM ET after market close.
    Finds any positions in DB with status='open' that should be closed.

    For paper trading, Tradier is the source of truth for fills.
    A position marked 'open' at 4:15 PM is definitively stale:
    - Either the time stop fired but DB write failed
    - Or the position was never properly closed
    Either way: force-close in DB and log for investigation.

    This also catches positions from prior sessions that were somehow
    not closed (e.g., server restart mid-session).
    """
    try:
        positions = get_open_positions()

        if not positions:
            logger.info("eod_reconciliation_clean")
            return {"mismatches": 0, "force_closed": 0}

        engine = _get_engine()
        force_closed = 0
        mismatches = []

        for pos in positions:
            mismatches.append({
                "position_id": pos["id"],
                "strategy": pos.get("strategy_type"),
                "entry_at": pos.get("entry_at"),
                "session_id": pos.get("session_id"),
            })
            ok = engine.close_virtual_position(
                position_id=pos["id"],
                exit_reason="eod_reconciliation_stale_open",
            )
            if ok:
                force_closed += 1
                logger.warning(
                    "eod_reconciliation_force_closed",
                    position_id=pos["id"],
                    strategy=pos.get("strategy_type"),
                    entry_at=pos.get("entry_at"),
                )

        write_audit_log(
            action="trading.eod_reconciliation_mismatch",
            metadata={
                "stale_positions_found": len(positions),
                "force_closed": force_closed,
                "positions": mismatches,
            },
        )
        logger.error(
            "eod_reconciliation_mismatch_detected",
            stale_positions=len(positions),
            force_closed=force_closed,
        )

        return {
            "mismatches": len(positions),
            "force_closed": force_closed,
        }

    except Exception as exc:
        logger.error("eod_reconciliation_failed", error=str(exc))
        return {"mismatches": 0, "force_closed": 0, "error": str(exc)}


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

            # Phase 2B: Pre-event straddle exit
            # Close long_straddle 30 minutes before a major catalyst (Fed/CPI/NFP).
            # Captures IV expansion without taking announcement-direction risk.
            straddle_closed = False
            try:
                if strategy_type == "long_straddle":
                    redis_client = _get_redis()
                    cal_raw = (
                        redis_client.get("calendar:today:intel")
                        if redis_client else None
                    )
                    if cal_raw:
                        import json as _json
                        intel = _json.loads(cal_raw)
                        for event in intel.get("events", []):
                            event_time_str = event.get("time", "")
                            if not (event_time_str and event.get("is_major")):
                                continue
                            try:
                                import zoneinfo
                                now_et = datetime.now(
                                    zoneinfo.ZoneInfo("America/New_York")
                                )
                                # Event time format: "HH:MM:SS"
                                parts = event_time_str.split(":")
                                h = int(parts[0])
                                m = int(parts[1]) if len(parts) > 1 else 0
                                event_dt = now_et.replace(
                                    hour=h, minute=m, second=0, microsecond=0
                                )
                                mins_to_event = (
                                    event_dt - now_et
                                ).total_seconds() / 60
                                if 0 < mins_to_event <= 30:
                                    ok = engine.close_virtual_position(
                                        position_id=pos["id"],
                                        exit_reason="straddle_pre_event_exit",
                                    )
                                    if ok:
                                        closed += 1
                                        straddle_closed = True
                                        logger.info(
                                            "straddle_closed_pre_event",
                                            mins_to_event=round(mins_to_event, 1),
                                            event=event.get("event"),
                                        )
                                    break
                            except Exception:
                                continue
            except Exception as straddle_err:
                logger.warning(
                    "straddle_pre_event_check_failed",
                    pos_id=pos.get("id"),
                    error=str(straddle_err),
                )

            # If the straddle was closed by pre-event exit, skip P&L checks.
            # Otherwise fall through to normal debit-strategy P&L exits.
            if straddle_closed:
                continue

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
                        # D-019 fix: update local contracts so subsequent exit checks
                        # use the correct remaining count, not the original stale value
                        contracts = remaining_contracts
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
                        # D-018 fix: book partial P&L into session so drawdown check
                        # sees the gain immediately, not only at full close
                        try:
                            from session_manager import update_session
                            if session_id := pos.get("session_id"):
                                session = (
                                    get_client()
                                    .table("trading_sessions")
                                    .select("virtual_pnl, virtual_trades_count")
                                    .eq("id", session_id)
                                    .maybe_single()
                                    .execute()
                                )
                                if session.data:
                                    current_pnl = session.data.get("virtual_pnl") or 0.0
                                    update_session(
                                        session_id,
                                        virtual_pnl=round(current_pnl + partial_pnl, 2),
                                    )
                                    logger.info(
                                        "partial_exit_session_pnl_updated",
                                        session_id=session_id,
                                        partial_pnl=partial_pnl,
                                    )
                        except Exception as pnl_err:
                            logger.warning(
                                "partial_exit_session_pnl_update_failed",
                                error=str(pnl_err),
                            )
                        # Note: virtual_trades_count is NOT incremented here.
                        # A partial exit is not a completed trade — only full close increments it.
                    except Exception as partial_err:
                        logger.error(
                            "partial_exit_failed",
                            pos_id=pos["id"],
                            error=str(partial_err),
                        )

                # B3: Credit strategy: take profit at 40% of credit collected
                # B3: 40% profit target (was 50%) — captures gains before
                # theta-decay reversal on 0DTE, improves hit rate
                if max_profit > 0 and current_pnl >= max_profit * 0.40:
                    ok = engine.close_virtual_position(
                        position_id=pos["id"],
                        exit_reason="take_profit_40pct",
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
                    # CV_Stress > 70 AND P&L ≥ 40% of max profit → exit (B3)
                    if cv_stress > 70.0 and pct_profit >= 0.40:
                        ok = engine.close_virtual_position(
                            position_id=pos["id"],
                            exit_reason="cv_stress_exit_d017",
                        )
                        if ok:
                            closed += 1
                            continue

                # B3: Stop loss: loss exceeds 150% of credit collected
                # (tighter than prior 200% — reduces avg loss from ~$296 to ~$222)
                # B3: 150% stop loss (was 200%) — tighter stop reduces
                # avg loss from ~$296 to ~$222 per contract
                stop_loss_threshold = -(max_profit * 1.5)
                if current_pnl <= stop_loss_threshold:
                    ok = engine.close_virtual_position(
                        position_id=pos["id"],
                        exit_reason="stop_loss_150pct_credit",
                    )
                    if ok:
                        closed += 1

        write_health_status("execution_engine", "healthy")
        return {"checked": len(positions), "closed": closed}

    except Exception as e:
        logger.error("position_monitor_failed", error=str(e))
        return {"checked": 0, "closed": 0, "error": str(e)}
