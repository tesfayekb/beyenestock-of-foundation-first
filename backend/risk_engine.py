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

# Lazy Redis client used only for HARD-B alert sentinels (the
# pre-halt -1.5% drawdown warning fires once per session and uses
# Redis to remember it already fired). Returning None on any failure
# is intentional — alerting must never block risk management.
_redis_client = None


def _get_redis():
    """Lazy singleton Redis client. Returns None on any failure."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        import redis as _redis_lib
        from config import REDIS_URL
        _redis_client = _redis_lib.Redis.from_url(
            REDIS_URL, decode_responses=True
        )
        return _redis_client
    except Exception as exc:
        logger.warning("risk_engine_redis_init_failed", error=str(exc))
        return None


# D-014: risk percentages by sizing phase and position type.
# Phase 1 values (0.005 / 0.0025) are the current paper-trading baseline
# and MUST remain unchanged. Phases 2 and 3 are reached only by the
# automated E1/E2 gates in calibration_engine.evaluate_sizing_phase
# (45+ live days with rolling 45d Sharpe >= 1.2 for phase 2; 90+ live
# days with rolling 60d Sharpe >= 1.5 for phase 3). Phase 4 is
# manual-only — never reached by auto-advance — and carries the same
# ceiling as phase 3 so a stray manual flip cannot lift risk above
# the system's learned tolerance.
_RISK_PCT = {
    1: {"core": 0.005,  "satellite": 0.0025},    # Phase 1: unchanged — current paper trading
    2: {"core": 0.0075, "satellite": 0.00375},   # Phase 2: E1 gate passed — +50% sizing
    3: {"core": 0.010,  "satellite": 0.0050},    # Phase 3: E2 gate passed — 2× phase 1
    4: {"core": 0.010,  "satellite": 0.0050},    # Phase 4: manual only — same as phase 3
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
    "calendar_spread":   0.003,   # 0.3% — defined risk, two-leg structure
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


def _apply_sizing_gates(
    base_risk_pct: float,
    regime_agreement: bool,
    consecutive_losses_today: int,
    allocation_tier: str,
) -> Tuple[float, Optional[str]]:
    """T0-3: shared D-021 / D-022 / D-004 gate logic.

    Extracted so EVERY strategy branch — including the long_straddle
    and calendar_spread early-return paths — runs through the same
    safety gates. Previously straddle/calendar bypassed all three on
    event days and could get full sizing while the rest of the book
    was in capital-preservation mode.

    Returns (effective_risk_pct, size_reduction_reason).
    Same math, same constants, same log lines as the original
    inline block in compute_position_size().
    """
    risk_pct = base_risk_pct
    reason: Optional[str] = None

    # D-021: regime disagreement -> 50% size reduction.
    if not regime_agreement:
        risk_pct *= 0.50
        reason = "regime_disagreement_d021"
        logger.info(
            "position_size_reduced_regime_disagreement",
            original_pct=risk_pct * 2,
            reduced_pct=risk_pct,
        )

    # D-022: 3+ consecutive losses -> additional 50% reduction.
    if consecutive_losses_today >= 3:
        risk_pct *= 0.50
        d022_reason = "capital_preservation_d022"
        reason = f"{reason}+{d022_reason}" if reason else d022_reason
        logger.info(
            "position_size_reduced_capital_preservation",
            consecutive_losses=consecutive_losses_today,
            reduced_pct=risk_pct,
        )

    # D-004: RCS-dynamic allocation tier (danger -> 0).
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
        reason = f"{reason}+{tier_reason}" if reason else tier_reason

    return risk_pct, reason


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
            base_risk_pct = _DEBIT_RISK_PCT.get("long_straddle", 0.0025)

            # T0-3: run through D-021 / D-022 / D-004 gates (was bypassed).
            # On event days a straddle could previously get full sizing
            # while the rest of the book was in capital-preservation mode.
            effective_risk_pct, reduction_reason = _apply_sizing_gates(
                base_risk_pct,
                regime_agreement,
                consecutive_losses_today,
                allocation_tier,
            )

            max_risk_dollars = account_value * effective_risk_pct
            contracts = max(
                1, int(max_risk_dollars / straddle_cost_per_contract)
            )
            # Danger tier (effective_risk_pct == 0) overrides the
            # max(1, ...) floor so we genuinely refuse to enter.
            if effective_risk_pct == 0.0:
                contracts = 0
            return {
                "contracts": contracts,
                "risk_pct": round(effective_risk_pct, 6),
                "stressed_loss_per_contract": straddle_cost_per_contract,
                "size_reduction_reason": reduction_reason,
            }

        # Phase 3C: Calendar spread sizing — cost-based, not spread-based.
        # Net cost per contract ≈ $1.50 × 100 = $150 typical post-catalyst.
        # Same pattern as long_straddle: must run BEFORE the spread_width <= 0
        # guard since calendar spread reports spread_width=0.
        if strategy_type == "calendar_spread":
            calendar_cost_per_contract = 150.0
            base_risk_pct = _DEBIT_RISK_PCT.get("calendar_spread", 0.003)

            # T0-3: same gate pattern as straddle.
            effective_risk_pct, reduction_reason = _apply_sizing_gates(
                base_risk_pct,
                regime_agreement,
                consecutive_losses_today,
                allocation_tier,
            )

            max_risk_dollars = account_value * effective_risk_pct
            contracts = max(
                1, int(max_risk_dollars / calendar_cost_per_contract)
            )
            if effective_risk_pct == 0.0:
                contracts = 0
            return {
                "contracts": contracts,
                "risk_pct": round(effective_risk_pct, 6),
                "stressed_loss_per_contract": calendar_cost_per_contract,
                "size_reduction_reason": reduction_reason,
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

        # T0-3: D-021 / D-022 / D-004 gates now flow through the same
        # _apply_sizing_gates helper that the straddle / calendar
        # branches use. Single source of truth, no duplicate logic to
        # drift out of sync.
        risk_pct, size_reduction_reason = _apply_sizing_gates(
            risk_pct,
            regime_agreement,
            consecutive_losses_today,
            allocation_tier,
        )

        # D-004 danger short-circuit preserved exactly as before:
        # zero out contracts so we never even attempt the entry.
        if allocation_tier == "danger":
            return {
                "contracts": 0,
                "risk_pct": 0.0,
                "stressed_loss_per_contract": 0.0,
                "size_reduction_reason": "allocation_tier_danger_d004",
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

        # T0-7 floor: never size to zero when risk budget allows a meaningful
        # fraction of one contract — except danger tier which explicitly
        # returns 0 above. Without this, any D-004 moderate reduction
        # (0.70×) on Phase 1 produces budgets below $500/contract and
        # drops every single-contract trade regardless of signal quality.
        #
        # Threshold: 0.30 of stressed loss.
        # - Phase 1 core + moderate:      $100k × 0.005  × 0.70 = $350 → 0.70 ratio → fires (was firing)
        # - Phase 1 satellite + full:     $100k × 0.0025 × 1.00 = $250 → 0.50 ratio → fires (was firing)
        # - Phase 1 satellite + moderate: $100k × 0.0025 × 0.70 = $175 → 0.35 ratio → fires (was MISSING at 0.50 threshold)
        # - Phase 1 satellite + low:      $100k × 0.0025 × 0.40 = $100 → 0.20 ratio → correctly skipped
        # - Any tier + pre_event/danger:  short-circuited upstream, unaffected
        #
        # The satellite+moderate row was blocking every non-first trade of
        # the day when RCS was in moderate regime. Loosening from 0.50 to
        # 0.30 preserves the skip behaviour for genuinely-underfunded cases
        # (low/pre_event/danger) while unblocking the common case.
        if contracts == 0 and max_risk_dollars >= stressed_loss_per_contract * 0.30:
            contracts = 1

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
    redis_client=None,
) -> bool:
    """
    D-005: if daily P&L / account_value <= halt_threshold → halt session.
    Returns True if halted, False if OK. Never raises.

    12F (Phase C): halt_threshold is read from Redis key
    `risk:halt_threshold_pct` when present (written by the weekly
    calibration job once closed_trades >= 100). Falls back to -0.03
    on missing key, parse failure, or Redis error. Never loosens the
    halt on read failure — if anything is wrong we use the default.
    """
    try:
        if account_value <= 0:
            return False
        drawdown_pct = current_daily_pnl / account_value

        # 12F: adaptive halt threshold. Fall back to the hardcoded -3%
        # whenever Redis is unavailable, the key is absent, or the value
        # cannot be parsed. The warning band upper bound also uses this
        # value so the "approaching halt" relationship stays intact.
        halt_threshold = -0.03
        threshold_source = "default"
        try:
            _effective_redis = redis_client or _get_redis()
            raw_threshold = (
                _effective_redis.get("risk:halt_threshold_pct")
                if _effective_redis
                else None
            )
            if raw_threshold is not None:
                parsed = float(raw_threshold)
                # Defensive clamp: keep within the sane band even if a
                # bad value leaked into Redis. Matches calibration bounds.
                if -0.05 <= parsed <= -0.02:
                    halt_threshold = parsed
                    threshold_source = "adaptive"
        except Exception:
            halt_threshold = -0.03
            threshold_source = "default"

        logger.debug(
            "halt_threshold_applied",
            threshold=halt_threshold,
            source=threshold_source,
            daily_pnl=current_daily_pnl,
            account_value=account_value,
        )

        # HARD-B: WARNING band at -1.5% (approaching the halt threshold).
        # Purely informational — does NOT influence sizing or halt logic.
        # Sent at most once per trading session via a Redis sentinel
        # so the operator gets one heads-up rather than one per cycle.
        if halt_threshold < drawdown_pct <= -0.015:
            try:
                from alerting import send_alert, WARNING
                _alert_redis = redis_client or _get_redis()
                warning_key = "alert:drawdown_warning_sent_today"
                if _alert_redis and not _alert_redis.get(warning_key):
                    _alert_redis.setex(warning_key, 86400, "1")
                    send_alert(
                        WARNING,
                        "drawdown_warning_approaching_halt",
                        f"Daily drawdown at {drawdown_pct:.2%}. "
                        f"Halt triggers at {halt_threshold:.2%}. "
                        f"Monitor closely. "
                        f"Session P&L: ${current_daily_pnl:.2f}.",
                    )
            except Exception:
                pass  # Never let alerting block risk management

        if drawdown_pct <= halt_threshold:
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
            # HARD-B: external alert on -3% daily halt.
            # Imported lazily inside the try block to avoid any
            # circular-import risk at module load time.
            try:
                from alerting import send_alert, CRITICAL
                # T0-10: alert copy was wrong — positions are NOT
                # auto-closed on halt. position_monitor continues
                # to manage them (TP/SL still active). Corrected copy
                # reflects what actually happens: only NEW entries
                # are gated; the open book is unaffected.
                send_alert(
                    CRITICAL,
                    "daily_halt_triggered",
                    f"Daily drawdown reached {drawdown_pct:.2%}. "
                    f"New entries halted for today. "
                    f"Existing positions continue to be managed "
                    f"(stops and TP still active). "
                    f"Session P&L: ${current_daily_pnl:.2f}.",
                )
            except Exception:
                pass  # Never let alerting block risk management
            return True
        return False

    except Exception as e:
        # T0-1a: fail CLOSED — if we can't check drawdown we must not trade.
        # Returning False here was silently allowing trading during DB outages.
        # The -3% halt is the last line of defense; it must never fail open.
        logger.error(
            "check_daily_drawdown_failed_halting",
            error=str(e),
        )
        return True  # Treat as halted — cannot verify drawdown, do not trade


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
