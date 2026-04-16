"""
Risk engine — position sizing, capital preservation, circuit breakers.
Implements D-005, D-014, D-019, D-020, D-021, D-022.
"""
from typing import Optional, Tuple

from db import write_health_status, write_audit_log
from logger import get_logger
from session_manager import update_session

logger = get_logger("risk_engine")

# D-014: risk percentages by sizing phase and position type
_RISK_PCT = {
    1: {"core": 0.005, "satellite": 0.0025},
    2: {"core": 0.005, "satellite": 0.0025},
    3: {"core": 0.010, "satellite": 0.005},
    4: {"core": 0.010, "satellite": 0.005},
}

# D-020: max trades per regime per session
REGIME_MAX_TRADES = {
    "trend": 2,
    "quiet_bullish": 2,
    "volatile_bullish": 2,
    "quiet_bearish": 2,
    "volatile_bearish": 2,
    "pin_range": 3,
    "range": 3,
    "event": 1,
    "crisis": 1,
    "panic": 0,
    "unknown": 1,
}


def compute_position_size(
    account_value: float,
    spread_width: float,
    sizing_phase: int = 1,
    regime_agreement: bool = True,
    consecutive_losses_today: int = 0,
    position_type: str = "core",
) -> dict:
    """
    Compute number of contracts and risk metadata.
    D-014: Phase 1/2 core=0.5%, satellite=0.25%. Phase 3/4 core=1.0%, satellite=0.5%.
    D-021: regime disagreement halves risk_pct.
    D-022: 3 consecutive losses halves risk_pct.
    Never raises — returns {contracts: 0} on any error.
    """
    try:
        if spread_width <= 0:
            return {
                "contracts": 0,
                "risk_pct": 0.0,
                "stressed_loss_per_contract": 0.0,
                "size_reduction_reason": "zero_spread_width",
            }

        phase_key = max(1, min(4, sizing_phase))
        pos_key = position_type if position_type in ("core", "satellite") else "core"
        risk_pct = _RISK_PCT[phase_key][pos_key]
        size_reduction_reason = None

        # D-021: regime disagreement → 50% size reduction
        if not regime_agreement:
            risk_pct *= 0.50
            size_reduction_reason = "regime_disagreement_d021"
            logger.info(
                "position_size_reduced_regime_disagreement",
                original_pct=risk_pct * 2,
                reduced_pct=risk_pct,
            )

        # D-022: 3+ consecutive losses → additional 50% reduction
        if consecutive_losses_today >= 3:
            risk_pct *= 0.50
            reason_d022 = "capital_preservation_d022"
            size_reduction_reason = (
                f"{size_reduction_reason}+{reason_d022}"
                if size_reduction_reason
                else reason_d022
            )
            logger.info(
                "position_size_reduced_capital_preservation",
                consecutive_losses=consecutive_losses_today,
                reduced_pct=risk_pct,
            )

        stressed_loss_per_contract = spread_width * 100
        max_risk_dollars = account_value * risk_pct
        contracts = int(max_risk_dollars / stressed_loss_per_contract)

        return {
            "contracts": contracts,
            "risk_pct": round(risk_pct, 6),
            "stressed_loss_per_contract": round(stressed_loss_per_contract, 2),
            "size_reduction_reason": size_reduction_reason,
        }

    except Exception as e:
        logger.error("compute_position_size_failed", error=str(e))
        return {
            "contracts": 0,
            "risk_pct": 0.0,
            "stressed_loss_per_contract": 0.0,
            "size_reduction_reason": f"error:{e}",
        }


def check_daily_drawdown(
    session_id: str,
    current_daily_pnl: float,
    account_value: float,
) -> bool:
    """
    D-005: if daily P&L / account_value <= -3% → halt session immediately.
    Returns True if halted, False if OK. Never raises.
    """
    try:
        if account_value <= 0:
            return False
        drawdown_pct = current_daily_pnl / account_value
        if drawdown_pct <= -0.03:
            update_session(
                session_id,
                session_status="halted",
                halt_reason="daily_drawdown_d005",
            )
            write_audit_log(
                action="trading.daily_drawdown_halt",
                metadata={
                    "session_id": session_id,
                    "daily_pnl": current_daily_pnl,
                    "account_value": account_value,
                    "drawdown_pct": round(drawdown_pct * 100, 3),
                },
            )
            write_health_status(
                "risk_engine",
                "error",
                last_error_message=f"daily_drawdown_halt:{drawdown_pct:.3%}",
            )
            logger.critical(
                "daily_drawdown_halt_d005",
                session_id=session_id,
                drawdown_pct=round(drawdown_pct * 100, 3),
            )
            return True
        return False

    except Exception as e:
        logger.error("check_daily_drawdown_failed", error=str(e))
        return False


def check_trade_frequency(
    session_virtual_trades_count: int,
    regime: str,
) -> Tuple[bool, Optional[str]]:
    """
    D-020: enforce per-regime max trade count per session.
    Returns (True, None) if trade is allowed.
    Returns (False, reason) if blocked.
    Never raises.
    """
    try:
        max_trades = REGIME_MAX_TRADES.get(regime, 1)

        if max_trades == 0:
            return False, f"panic_regime_no_trades_d020"

        if session_virtual_trades_count >= max_trades:
            return False, (
                f"trade_frequency_cap_d020:{regime}:"
                f"{session_virtual_trades_count}/{max_trades}"
            )

        return True, None

    except Exception as e:
        logger.error("check_trade_frequency_failed", error=str(e))
        return False, f"error:{e}"


def check_execution_quality(
    predicted_slippage: float,
    actual_slippage: float,
    session_id: str,
) -> dict:
    """
    D-019: if actual_slippage > predicted * 1.25 → execution degraded.
    Returns {execution_degraded, size_adjustment}.
    size_adjustment=0.70 when degraded, 1.0 otherwise.
    Never raises.
    """
    try:
        degraded = actual_slippage > predicted_slippage * 1.25
        if degraded:
            write_audit_log(
                action="trading.execution_degraded",
                metadata={
                    "session_id": session_id,
                    "predicted_slippage": predicted_slippage,
                    "actual_slippage": actual_slippage,
                    "ratio": round(
                        actual_slippage / predicted_slippage, 3
                    ) if predicted_slippage > 0 else None,
                },
            )
            logger.warning(
                "execution_degraded_d019",
                predicted=predicted_slippage,
                actual=actual_slippage,
            )
        return {
            "execution_degraded": degraded,
            "size_adjustment": 0.70 if degraded else 1.0,
        }

    except Exception as e:
        logger.error("check_execution_quality_failed", error=str(e))
        return {"execution_degraded": False, "size_adjustment": 1.0}


def write_heartbeat() -> None:
    """Write healthy heartbeat for risk_engine service."""
    try:
        write_health_status("risk_engine", "healthy")
    except Exception as e:
        logger.error("risk_engine_heartbeat_failed", error=str(e))
