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
#
# Phase 1 values were doubled on 2026-04-20 (core 0.005 → 0.010,
# satellite 0.0025 → 0.005) as the paired half of the SPX spread
# width recalibration (see strike_selector.VIX_SPREAD_WIDTH_TABLE).
# The widths tripled to match SPX at ~7000 price levels (wings that
# actually survive normal intraday moves) and the old risk_pct would
# have produced contracts=0 on every core+full trade under the new
# wider wings. Doubling risk_pct restores sizing while staying within
# the 2× ceiling that was the pre-existing constraint: Phase 1 max
# per-trade risk now tops out at $1,000 on a $100k account (1% of
# account), still well under the 3% daily drawdown halt.
#
# LADDER-CONSISTENCY RESOLVED 2026-04-28 (PRE-P11-3 / Action 7b):
# Only Phase 1 was touched on 2026-04-20 (paired with SPX strike-width
# widening); Phases 2-4 retained pre-widening risk-pct values
# (0.0075 / 0.010 / 0.010 core) which made Phase 2 lower than Phase 1
# — a non-monotonic ladder where calibration-engine advancement via the
# E1 gate would have reduced risk budget. Resolution: Phase 2-4 scaled
# 2× to preserve dollar-equivalent ladder structure (1.0× / 1.5× / 2.0×
# / 2.0× of new baseline 0.010, matching the pre-widening ladder
# structure with the new baseline). Monotonicity regression test added
# at backend/tests/test_risk_engine.py::test_risk_pct_ladder_monotonic.
#
# Phases 2 and 3 are reached only by the automated E1/E2 gates in
# calibration_engine.evaluate_sizing_phase (45+ live days with
# rolling 45d Sharpe >= 1.2 for phase 2; 90+ live days with rolling
# 60d Sharpe >= 1.5 for phase 3). Phase 4 is manual-only — never
# reached by auto-advance — and carries the same ceiling as phase 3
# so a stray manual flip cannot lift risk above the system's learned
# tolerance.
_RISK_PCT = {
    1: {"core": 0.010,  "satellite": 0.0050},   # Phase 1: 2× prior baseline — paired w/ 2026-04-20 width widening
    2: {"core": 0.015,  "satellite": 0.0075},   # Phase 2: E1 gate — 1.5× Phase 1 (PRE-P11-3 closed; preserves dollar-equivalent ladder post-2026-04-20 width widening)
    3: {"core": 0.020,  "satellite": 0.0100},   # Phase 3: E2 gate — 2× Phase 1 (PRE-P11-3 closed; preserves dollar-equivalent ladder post-2026-04-20 width widening)
    4: {"core": 0.020,  "satellite": 0.0100},   # Phase 4: manual only — same as Phase 3
}

# Phase 2B: Strategy-specific risk overrides
# Debit strategies risk smaller % because loss = 100% of premium paid.
# Credit strategies can risk more because max loss = spread width (known).
#
# iron_butterfly was doubled on 2026-04-20 (0.004 → 0.008) as the
# paired half of the SPX width recalibration. At widths >= 15pt (now
# the default) the old 0.004 rate produced a $400 budget against a
# $1,500+ stressed_loss — contracts=0 on every iron_butterfly trade
# regardless of tier. Doubling restores 1-contract sizing at widths
# 10-20pt in full/moderate tiers. At width=30pt (VIX>30 crisis
# regime) iron_butterfly remains blocked even at full tier, which
# is defensible: ATM gamma during a crisis regime is the first
# strategy to skip.
#
# Other debit rates (debit spreads, long options, straddle, calendar)
# were NOT adjusted — they use cost-based sizing (straddle, calendar)
# or tight debit premium that doesn't scale with spread width the way
# iron_butterfly does. Revisit on next sizing review.
_DEBIT_RISK_PCT = {
    "iron_butterfly":    0.008,   # 0.8% — 2× from 2026-04-20 paired with width widening
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
        # returns 0 above. The floor was introduced to prevent D-004 tier
        # reductions and phase-1 satellite sizing from silently dropping
        # to 0 contracts whenever int(budget/stressed_loss) == 0.
        #
        # Threshold: 0.30 of stressed loss.
        #
        # Coverage matrix @ $100k account, iron_condor (credit spread),
        # post 2026-04-20 recalibration (Phase 1 risk 2× + SPX widths 3×):
        #
        #   VIX<15 (width=10, stressed=$1000, floor=$300)
        #     core+full       $1000  1.00 ratio  1ctr  (direct, no floor)
        #     core+moderate   $700   0.70 ratio  1ctr  (floor fires)
        #     sat+full        $500   0.50 ratio  1ctr  (floor fires)
        #     sat+moderate    $350   0.35 ratio  1ctr  (floor fires)
        #
        #   VIX 15-20 (width=15, stressed=$1500, floor=$450) — today's band
        #     core+full       $1000  0.67 ratio  1ctr  (floor fires)
        #     core+moderate   $700   0.47 ratio  1ctr  (floor fires)
        #     sat+full        $500   0.33 ratio  1ctr  (floor fires)
        #     sat+moderate    $350   0.23 ratio  0ctr  (blocked — 2nd trade in moderate regime)
        #
        #   VIX 20-30 (width=20, stressed=$2000, floor=$600)
        #     core+full       $1000  0.50 ratio  1ctr  (floor fires)
        #     core+moderate   $700   0.35 ratio  1ctr  (floor fires)
        #     sat+full        $500   0.25 ratio  0ctr  (blocked)
        #     sat+moderate    $350   0.175      0ctr  (blocked)
        #
        #   VIX>30 (width=30, stressed=$3000, floor=$900)
        #     core+full       $1000  0.33 ratio  1ctr  (floor fires — last line of defense)
        #     core+moderate   $700   0.23 ratio  0ctr  (blocked — crisis regime)
        #     sat+*           all    <=$500      0ctr  (blocked)
        #
        # Low / pre_event / danger tiers: still correctly blocked at all
        # widths (budget <= $400 at width>=10pt means ratio<=0.40 at the
        # narrowest width and drops below 0.30 at widths>=14pt).
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
                # T0-10 / 2026-04-20 session-halt watchdog fix:
                # On halt, only NEW entries are gated. Open positions
                # continue to be managed by position_monitor (TP/SL
                # targets still active, 3:45 PM emergency_backstop
                # still fires). The prediction_watchdog is explicitly
                # session-halt-aware (see position_monitor.py top of
                # run_prediction_watchdog) so a halted session no
                # longer force-closes the open book as a side-effect
                # of stalled prediction rows — that bug cost real
                # dollars on 2026-04-20 before this fix landed.
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
