"""
Strategy selector — Stage 0-4 pipeline.
Phase 2 placeholder: real GEX strike optimizer and Monte Carlo EV in Phase 4.
Implements D-010, D-011, D-012, D-015, D-020.
"""
from datetime import datetime, timezone
from typing import Optional, Tuple, Union

from db import write_health_status
from logger import get_logger
from risk_engine import compute_position_size, check_trade_frequency

logger = get_logger("strategy_selector")

STATIC_SLIPPAGE_BY_STRATEGY = {
    "put_credit_spread": 0.10,
    "call_credit_spread": 0.10,
    "iron_condor": 0.20,
    "iron_butterfly": 0.25,
    "debit_put_spread": 0.12,
    "debit_call_spread": 0.12,
    "long_put": 0.05,
    "long_call": 0.05,
}

# Placeholder credits by strategy — Phase 2 proxy until real option pricer in Phase 4
# Based on typical SPX credit spreads at ~$5 wide with SPX ~5200
PLACEHOLDER_CREDIT_BY_STRATEGY = {
    "put_credit_spread":  1.50,
    "call_credit_spread": 1.50,
    "iron_condor":        2.50,
    "iron_butterfly":     3.00,
    "debit_put_spread":  -1.80,  # debit strategies cost money
    "debit_call_spread": -1.80,
    "long_put":          -3.00,
    "long_call":         -3.00,
}

REGIME_STRATEGY_MAP = {
    "quiet_bullish": ["call_credit_spread", "put_credit_spread", "iron_condor"],
    "volatile_bullish": ["debit_call_spread", "long_call"],
    "quiet_bearish": ["put_credit_spread", "call_credit_spread", "iron_condor"],
    "volatile_bearish": ["debit_put_spread", "long_put"],
    "pin_range": ["iron_condor", "iron_butterfly", "put_credit_spread"],
    "range": ["iron_condor", "put_credit_spread", "call_credit_spread"],
    "crisis": ["put_credit_spread"],
    "event": ["iron_condor"],
    "panic": [],
    "trend": ["debit_call_spread", "debit_put_spread", "long_call", "long_put"],
    "unknown": ["put_credit_spread"],
}

SHORT_GAMMA_STRATEGIES = {
    "put_credit_spread",
    "call_credit_spread",
    "iron_condor",
    "iron_butterfly",
}

LONG_GAMMA_STRATEGIES = {
    "debit_put_spread",
    "debit_call_spread",
    "long_put",
    "long_call",
}

_BULL_PREFERRED = {"call_credit_spread", "debit_call_spread", "long_call"}
_BEAR_PREFERRED = {"put_credit_spread", "debit_put_spread", "long_put"}
_NEUTRAL_PREFERRED = {"iron_condor", "iron_butterfly"}


class StrategySelector:

    def _stage0_time_gate(
        self, cv_stress: float
    ) -> Tuple[Union[bool, str], Optional[str]]:
        """
        Stage 0: time and volatility gate.
        D-010: after 2:30 PM — short-gamma strategies blocked.
        D-011: after 3:45 PM — all new entries blocked.
        Returns (True, None) if fully open.
        Returns ("long_gamma_only", reason) if partially restricted.
        Returns (False, reason) if fully blocked.
        """
        try:
            import zoneinfo
            et = zoneinfo.ZoneInfo("America/New_York")
            now = datetime.now(et)
            hour = now.hour
            minute = now.minute
            total_minutes = hour * 60 + minute

            # D-011: after 3:45 PM — no new entries
            if total_minutes >= 15 * 60 + 45:
                return False, "after_345pm_d011"

            # Before 10:00 AM — too early for reliable signals
            if total_minutes < 10 * 60:
                return False, "before_1000am"

            # D-010: after 2:30 PM — long-gamma only
            if total_minutes >= 14 * 60 + 30:
                return "long_gamma_only", "after_230pm_d010"

            # CV_Stress override — high stress favours long-gamma protection
            if cv_stress > 70:
                return "long_gamma_only", "cv_stress_high"

            return True, None

        except Exception as e:
            logger.error("stage0_time_gate_failed", error=str(e))
            return False, f"error:{e}"

    def _stage1_regime_gate(
        self,
        regime: str,
        time_gate_result: Union[bool, str],
    ) -> list:
        """
        Stage 1: get regime-appropriate strategy candidates.
        Filters to LONG_GAMMA_STRATEGIES only when time gate is restricted.
        """
        try:
            candidates = list(REGIME_STRATEGY_MAP.get(regime, ["put_credit_spread"]))
            if time_gate_result == "long_gamma_only":
                candidates = [s for s in candidates if s in LONG_GAMMA_STRATEGIES]
            return candidates
        except Exception as e:
            logger.error("stage1_regime_gate_failed", error=str(e))
            return []

    def _stage2_direction_filter(
        self,
        candidates: list,
        direction: str,
        p_bull: float,
        p_bear: float,
    ) -> list:
        """
        Stage 2: order candidates by directional preference.
        Bullish → call-side strategies first.
        Bearish → put-side strategies first.
        Neutral → condor/butterfly first.
        """
        try:
            if direction == "bull":
                preferred = _BULL_PREFERRED
            elif direction == "bear":
                preferred = _BEAR_PREFERRED
            else:
                preferred = _NEUTRAL_PREFERRED

            preferred_list = [s for s in candidates if s in preferred]
            others = [s for s in candidates if s not in preferred]
            return preferred_list + others

        except Exception as e:
            logger.error("stage2_direction_filter_failed", error=str(e))
            return candidates

    def select(
        self,
        prediction: dict,
        session: dict,
        account_value: float = 100_000.0,
        sizing_phase: int = 1,
    ) -> Optional[dict]:
        """
        Full Stage 0-4 pipeline: select strategy and compute sizing.
        Returns signal dict or None if no trade is selected.
        Never raises.
        """
        try:
            regime = prediction.get("regime", "unknown")
            direction = prediction.get("direction", "neutral")
            p_bull = prediction.get("p_bull", 0.35)
            p_bear = prediction.get("p_bear", 0.30)
            cv_stress = prediction.get("cv_stress_score", 0.0)
            rcs = prediction.get("rcs", 0.0)
            regime_agreement = prediction.get("regime_agreement", True)
            session_id = session.get("id", "")
            trades_today = session.get("virtual_trades_count", 0)
            consecutive_losses = session.get("consecutive_losses_today", 0)

            # D-020: trade frequency gate
            allowed, freq_reason = check_trade_frequency(trades_today, regime)
            if not allowed:
                logger.info("strategy_blocked_frequency", reason=freq_reason)
                return None

            # Stage 0: time + volatility gate
            time_gate_result, time_gate_reason = self._stage0_time_gate(cv_stress)
            if time_gate_result is False:
                logger.info(
                    "strategy_blocked_time_gate", reason=time_gate_reason
                )
                return None

            # Stage 1: regime candidates
            candidates = self._stage1_regime_gate(regime, time_gate_result)
            if not candidates:
                logger.info("strategy_blocked_no_candidates", regime=regime)
                return None

            # Stage 2: direction filter
            ordered = self._stage2_direction_filter(
                candidates, direction, p_bull, p_bear
            )

            strategy_type = ordered[0]
            predicted_slippage = STATIC_SLIPPAGE_BY_STRATEGY.get(
                strategy_type, 0.15
            )

            # D-012: satellite positioning after first trade
            position_type = "core" if trades_today == 0 else "satellite"

            # Risk sizing
            sizing = compute_position_size(
                account_value=account_value,
                spread_width=5.0,  # placeholder width — real GEX strike calc in Phase 4
                sizing_phase=sizing_phase,
                regime_agreement=regime_agreement,
                consecutive_losses_today=consecutive_losses,
                position_type=position_type,
                allocation_tier=prediction.get("allocation_tier", "full"),
            )

            is_short_gamma = strategy_type in SHORT_GAMMA_STRATEGIES

            signal = {
                "session_id": session_id,
                "signal_at": datetime.now(timezone.utc).isoformat(),
                "instrument": "SPX",
                "strategy_type": strategy_type,
                "position_type": position_type,
                "predicted_slippage": predicted_slippage,
                "regime_at_signal": regime,
                "rcs_at_signal": rcs,
                "cv_stress_at_signal": cv_stress,
                "contracts": sizing["contracts"],
                "position_size_pct": sizing["risk_pct"],
                "signal_status": "pending",
                "is_short_gamma": is_short_gamma,
                "short_strike": None,
                "long_strike": None,
                "expiry_date": None,
                "target_credit": PLACEHOLDER_CREDIT_BY_STRATEGY.get(strategy_type, 1.50),
                "stop_loss_level": None,
                "profit_target": None,
                "ev_net": None,
            }

            logger.info(
                "strategy_selected",
                strategy=strategy_type,
                regime=regime,
                direction=direction,
                contracts=sizing["contracts"],
            )
            self.write_heartbeat()
            return signal

        except Exception as e:
            logger.error("strategy_select_failed", error=str(e))
            write_health_status(
                "strategy_selector",
                "error",
                last_error_message=str(e),
            )
            return None

    def write_heartbeat(self) -> None:
        """Write healthy heartbeat for strategy_selector service."""
        try:
            write_health_status("strategy_selector", "healthy")
        except Exception as e:
            logger.error("strategy_selector_heartbeat_failed", error=str(e))
