"""
Trading cycle orchestrator — prediction -> strategy -> virtual execution.
Called every 5 minutes via APScheduler.
"""
from typing import Optional

from db import write_health_status
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

        # D-005: check daily drawdown before any new entry
        daily_pnl = session.get("virtual_pnl", 0.0) or 0.0
        if check_daily_drawdown(session["id"], daily_pnl, account_value):
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
