"""
Trading cycle orchestrator — prediction -> strategy -> virtual execution.
Called every 5 minutes via APScheduler.
"""
from typing import Optional

from db import get_client, write_health_status
from execution_engine import ExecutionEngine
from logger import get_logger
from prediction_engine import PredictionEngine
from risk_engine import check_daily_drawdown
from session_manager import get_or_create_session
from strategy_selector import StrategySelector

logger = get_logger("trading_cycle")

# Lazy-initialized singletons — created on first cycle to avoid startup race
_prediction_engine = None
_strategy_selector = None
_execution_engine = None


def run_trading_cycle(
    account_value: float = 100_000.0,
    sizing_phase: int = 1,
) -> dict:
    """
    Full trading cycle: session -> drawdown check -> predict -> select -> execute.
    Returns result dict with prediction, signal, position, and skip reason.
    Never raises.
    """
    global _prediction_engine, _strategy_selector, _execution_engine
    if _prediction_engine is None:
        _prediction_engine = PredictionEngine()
    if _strategy_selector is None:
        _strategy_selector = StrategySelector()
    if _execution_engine is None:
        _execution_engine = ExecutionEngine()

    result: dict = {
        "prediction": None,
        "signal": None,
        "position": None,
        "skipped_reason": None,
    }

    try:
        # Ensure today's session exists
        session = get_or_create_session()
        if not session:
            result["skipped_reason"] = "no_session"
            logger.warning("trading_cycle_skipped", reason="no_session")
            return result

        # S4 / C-α: respect kill switch and session lifecycle.
        # Allowed: 'active' (normal trading), 'pending' (created but
        # market not yet open). Blocked: 'halted' (operator kill switch),
        # 'closed' (EOD reached). Position monitor and mark-to-market
        # remain unaffected so existing positions still get managed and
        # exited under any session state — only NEW entries are gated.
        session_status = session.get("session_status", "active")
        if session_status not in ("active", "pending"):
            result["skipped_reason"] = f"session_{session_status}"
            logger.info(
                "trading_cycle_skipped",
                reason=result["skipped_reason"],
                session_status=session_status,
            )
            return result

        # D-005: include unrealized MTM P&L from open positions
        realized_pnl = session.get("virtual_pnl", 0.0) or 0.0
        unrealized_pnl = 0.0
        try:
            open_result = (
                get_client()
                .table("trading_positions")
                .select("current_pnl")
                .eq("session_id", session["id"])
                .eq("status", "open")
                .execute()
            )
            if open_result is None:
                # T0-1b: None response → treat as error, halt this cycle.
                # Combined with the T0-1a fail-closed drawdown change,
                # this prevents trading on an unknown unrealized P&L.
                logger.warning(
                    "trading_cycle_mtm_fetch_none",
                    reason="supabase returned None for open positions",
                )
                result["skipped_reason"] = "mtm_fetch_failed"
                return result
            unrealized_pnl = sum(
                (p.get("current_pnl") or 0.0)
                for p in (open_result.data or [])
            )
        except Exception as mtm_exc:
            # T0-1b: MTM failure + drawdown check would use 0 unrealized.
            # If we have open positions, 0 could mask a -3%+ loss already
            # in the book. Halt this cycle rather than trade on uncertainty.
            logger.warning(
                "trading_cycle_mtm_fetch_failed",
                error=str(mtm_exc),
            )
            result["skipped_reason"] = "mtm_fetch_failed"
            return result

        daily_pnl = realized_pnl + unrealized_pnl
        # 12F: pass redis_client so the adaptive halt threshold can be read.
        # Falls back to the hardcoded -3% inside check_daily_drawdown when
        # the prediction engine has no redis_client attached.
        if check_daily_drawdown(
            session["id"],
            daily_pnl,
            account_value,
            redis_client=getattr(_prediction_engine, "redis_client", None),
        ):
            result["skipped_reason"] = "daily_drawdown_halt_d005"
            logger.warning(
                "trading_cycle_skipped", reason="daily_drawdown_halt_d005"
            )
            return result

        # Run prediction cycle
        prediction = _prediction_engine.run_cycle()
        result["prediction"] = prediction

        if not prediction:
            result["skipped_reason"] = "prediction_failed"
            return result

        # Phase 3B: Run shadow cycle (Portfolio A) alongside real prediction.
        # Silent — never interrupts or delays the real trading cycle.
        try:
            from shadow_engine import run_shadow_cycle
            run_shadow_cycle(
                redis_client=getattr(
                    _prediction_engine, "redis_client", None
                ),
                session_id=session["id"],
            )
        except Exception:
            pass  # Shadow failure must never affect real trading

        # Honour no-trade signal from prediction engine
        if prediction.get("no_trade_signal"):
            no_trade_reason = prediction.get("no_trade_reason", "unknown")
            result["skipped_reason"] = f"no_trade_{no_trade_reason}"
            logger.info(
                "trading_cycle_skipped",
                reason=result["skipped_reason"],
            )
            return result

        # Refresh session after prediction to capture latest state
        from session_manager import get_today_session
        session = get_today_session() or session

        # Select strategy
        signal = _strategy_selector.select(
            prediction=prediction,
            session=session,
            account_value=account_value,
            sizing_phase=sizing_phase,
        )
        result["signal"] = signal

        if not signal:
            result["skipped_reason"] = "no_signal_selected"
            return result

        # Open virtual position
        position = _execution_engine.open_virtual_position(signal, prediction)
        result["position"] = position

        if not position:
            result["skipped_reason"] = "position_open_failed"

        return result

    except Exception as e:
        logger.error("trading_cycle_failed", error=str(e))
        write_health_status(
            "trading_cycle",
            "error",
            last_error_message=str(e),
        )
        result["skipped_reason"] = f"unhandled_error:{e}"
        return result
