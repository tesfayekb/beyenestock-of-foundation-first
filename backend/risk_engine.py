"""
Risk engine — position sizing, capital preservation, circuit breakers.
Implements D-005, D-014, D-019, D-020, D-021, D-022, B4-Kelly.

Position size reduction stacking order in compute_position_size():
  1. D-021: regime disagreement → 50% reduction
  2. D-022: consecutive losses  → 50% reduction
  3. D-004: allocation tier     → tier multiplier
  4. B4:    Kelly multiplier    → 0.5x to 2.0x

Kelly runs last so it scales the already-conservatively-reduced risk_pct.
A 2.0x Kelly boost after a 0.5x allocation_tier reduction nets 1.0x,
which is the correct and transparent behavior.
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

# Phase 2B: Strategy-specific risk overrides
# Debit strategies risk smaller % because loss = 100% of premium paid.
# Credit strategies can risk more because max loss = spread width (known).
_DEBIT_RISK_PCT = {
    "iron_butterfly":    0.004,   # 0.4% — ATM shorts lose fast
    "debit_call_spread": 0.003,   # 0.3% — full premium at risk
    "debit_put_spread":  0.003,   # 0.3% — full premium at risk
    "long_call":         0.003,   # 0.3%
    "long_put":          0.003,   # 0.3%
    "long_straddle":     0.0025,  # 0.25% — highest uncertainty
}

# B4: Kelly normalization baseline
# Calibrated for 65% WR with 0.5 win/loss ratio → quarter-Kelly ≈ 0.0375
# Revisit if steady-state win rate drifts materially from 65%.
BASE_KELLY = 0.0375

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


def compute_kelly_multiplier(
    recent_win_rate: Optional[float],
    avg_win_dollars: Optional[float],
    avg_loss_dollars: Optional[float],
) -> float:
    """
    Compute fractional Kelly position size multiplier.

    Kelly formula: f = (p × b - q) / b
      p = win probability, q = 1-p, b = avg_win / avg_loss

    Uses quarter-Kelly (× 0.25) for safety, capped at 2.0×
    and floored at 0.5× the base risk_pct.

    Returns a multiplier to apply to base risk_pct:
    - 1.0 = no adjustment (default when data unavailable)
    - 1.5 = 50% more contracts (strong recent edge)
    - 0.5 = half contracts (weak recent edge)

    Requires at least 20 closed trades to activate.
    Falls back to 1.0 when data is unavailable or insufficient.

    CALLER CONTRACT: Caller must verify at least 20 closed trades exist
    before passing win_rate data. Passing win_rate from fewer trades
    produces statistically unreliable multipliers. strategy_selector.py
    must enforce this minimum when wiring in the follow-up task.
    """
    try:
        # Require valid inputs
        if (
            recent_win_rate is None
            or avg_win_dollars is None
            or avg_loss_dollars is None
        ):
            return 1.0

        # Require minimum sample size context (caller verifies trade count)
        if recent_win_rate <= 0 or recent_win_rate >= 1:
            return 1.0
        if avg_loss_dollars <= 0 or avg_win_dollars <= 0:
            return 1.0

        p = recent_win_rate
        q = 1.0 - p
        b = avg_win_dollars / avg_loss_dollars  # win/loss ratio

        # Full Kelly
        kelly_full = (p * b - q) / b

        if kelly_full <= 0:
            # Negative Kelly = system has no edge → minimum size
            return 0.5

        # Quarter-Kelly for safety
        kelly_quarter = kelly_full * 0.25

        # Normalize to a multiplier around 1.0 using module-level BASE_KELLY
        # (calibrated for 65% WR with 0.5 win/loss ratio)
        multiplier = kelly_quarter / BASE_KELLY

        # Clamp: never more than 2× or less than 0.5×
        multiplier = max(0.5, min(2.0, multiplier))

        return round(multiplier, 3)

    except Exception:
        return 1.0  # Never break position sizing


def compute_position_size(
    account_value: float,
    spread_width: float,
    sizing_phase: int = 1,
    regime_agreement: bool = True,
    consecutive_losses_today: int = 0,
    position_type: str = "core",
    allocation_tier: str = "full",
    kelly_multiplier: float = 1.0,
    strategy_type: str = "iron_condor",
) -> dict:
    """
    Compute number of contracts and risk metadata.
    D-014: Phase 1/2 core=0.5%, satellite=0.25%. Phase 3/4 core=1.0%, satellite=0.5%.
    D-021: regime disagreement halves risk_pct.
    D-022: 3 consecutive losses halves risk_pct.
    kelly_multiplier: Fractional Kelly multiplier from compute_kelly_multiplier().
                      1.0 = no adjustment. Capped at 2.0, floored at 0.5.
    Never raises — returns {contracts: 0} on any error.
    """
    try:
        # Phase 2B: Straddle sizing — cost-based, not spread-based.
        # For long_straddle, spread_width=0 (no spread between legs), so the
        # generic spread-based formula returns 0 contracts. Instead we size
        # by premium cost: contracts = (account_value × risk_pct) / cost_per_contract.
        # Must run BEFORE the spread_width <= 0 guard below.
        if strategy_type == "long_straddle":
            straddle_cost_per_contract = 400.0  # $4.00 × 100 = typical SPX 0DTE
            straddle_risk_pct = _DEBIT_RISK_PCT.get("long_straddle", 0.0025)
            max_risk_dollars = account_value * straddle_risk_pct
            contracts = max(1, int(max_risk_dollars / straddle_cost_per_contract))
            return {
                "contracts": contracts,
                "risk_pct": straddle_risk_pct,
                "stressed_loss_per_contract": straddle_cost_per_contract,
                "size_reduction_reason": None,
            }

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

        # Phase 2B: Override risk_pct for debit/high-risk strategies.
        # Debit strategies lose 100% of premium when wrong, so they get
        # tighter sizing than credit spreads (which lose only the spread
        # width minus credit collected).
        if strategy_type in _DEBIT_RISK_PCT:
            risk_pct = _DEBIT_RISK_PCT[strategy_type]
            logger.info(
                "debit_strategy_sizing",
                strategy_type=strategy_type,
                risk_pct=risk_pct,
            )

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

        # D-004: RCS-dynamic allocation via allocation_tier
        TIER_MULTIPLIERS = {
            "full":      1.0,
            "moderate":  0.70,
            "low":       0.40,
            "pre_event": 0.20,
            "danger":    0.0,
        }
        tier_mult = TIER_MULTIPLIERS.get(allocation_tier, 1.0)
        if tier_mult < 1.0:
            risk_pct *= tier_mult
            tier_reason = f"allocation_tier_{allocation_tier}_d004"
            size_reduction_reason = (
                f"{size_reduction_reason}+{tier_reason}"
                if size_reduction_reason else tier_reason
            )
            if tier_mult == 0.0:
                return {
                    "contracts": 0,
                    "risk_pct": 0.0,
                    "stressed_loss_per_contract": 0.0,
                    "size_reduction_reason": tier_reason,
                }

        # B4: Kelly-adjusted sizing
        if kelly_multiplier != 1.0:
            risk_pct *= kelly_multiplier
            kelly_reason = f"kelly_mult_{kelly_multiplier:.3f}"
            size_reduction_reason = (
                f"{size_reduction_reason}+{kelly_reason}"
                if size_reduction_reason else kelly_reason
            )
            logger.info(
                "position_sized_kelly",
                kelly_multiplier=kelly_multiplier,
                risk_pct_after_kelly=round(risk_pct, 6),
            )

        stressed_loss_per_contract = spread_width * 100
        max_risk_dollars = account_value * risk_pct
        contracts = int(max_risk_dollars / stressed_loss_per_contract)

        logger.info(
            "position_sized",
            spread_width=spread_width,
            contracts=contracts,
            risk_pct=risk_pct,
        )

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
