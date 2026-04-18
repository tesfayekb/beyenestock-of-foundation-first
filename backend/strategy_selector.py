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
from model_retraining import get_kelly_multiplier_from_db
from strike_selector import get_strikes

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
    "long_straddle": 0.15,
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
    "long_straddle":     -4.00,  # debit — buy both ATM call and put
}

REGIME_STRATEGY_MAP = {
    "quiet_bullish": ["call_credit_spread", "put_credit_spread", "iron_condor"],
    "volatile_bullish": ["debit_call_spread", "long_call"],
    "quiet_bearish": ["put_credit_spread", "call_credit_spread", "iron_condor"],
    "volatile_bearish": ["debit_put_spread", "long_put"],
    "pin_range": ["iron_condor", "iron_butterfly", "put_credit_spread"],
    "range": ["iron_condor", "put_credit_spread", "call_credit_spread"],
    "crisis": ["put_credit_spread"],
    # Phase 2B: catalyst days favour long_straddle (capture IV expansion,
    # exit pre-announcement). iron_condor stays as fallback.
    "event": ["long_straddle", "iron_condor"],
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
_NEUTRAL_PREFERRED = {"iron_condor", "iron_butterfly", "long_straddle"}


class StrategySelector:

    def __init__(self) -> None:
        import redis as redis_lib
        from config import REDIS_URL
        self.redis_client = redis_lib.Redis.from_url(
            REDIS_URL, decode_responses=True
        )

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

            # Before 9:35 AM — opening auction noise (GEX/ZG valid at open,
            # but 5-min buffer for SPX tape to stabilize)
            if total_minutes < 9 * 60 + 35:
                return False, "before_935am"

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

    def _check_feature_flag(self, flag_key: str) -> bool:
        """Check a Redis feature flag. Returns False on any error.

        Accepts both bytes 'true' (decode_responses=False) and string 'true'
        (decode_responses=True) for forward-compatibility with both Redis
        client configurations.
        """
        try:
            if not self.redis_client:
                return False
            val = self.redis_client.get(flag_key)
            return val in ("true", b"true")
        except Exception:
            return False

    def _get_spx_price(self) -> float:
        """Read current SPX price from Redis. Returns 5200.0 fallback."""
        try:
            raw = (
                self.redis_client.get("tradier:quotes:SPX")
                if self.redis_client else None
            )
            if raw:
                import json
                data = json.loads(raw)
                return float(data.get("last") or data.get("ask") or 5200.0)
        except Exception:
            pass
        return 5200.0

    def _stage1_regime_gate(
        self,
        regime: str,
        time_gate_result: Union[bool, str],
    ) -> list:
        """
        Stage 1: get regime-appropriate strategy candidates.
        Filters to LONG_GAMMA_STRATEGIES only when time gate is restricted.

        Phase 2B: When strategy:iron_butterfly:enabled=true and SPX is
        within 0.3% of the GEX wall (pin day), short-circuit to
        iron_butterfly — pin-day market making produces highest EV here.
        """
        try:
            # Phase 2B: Gamma pin override (feature-flagged, default OFF)
            try:
                if self._check_feature_flag("strategy:iron_butterfly:enabled"):
                    nearest_wall_raw = (
                        self.redis_client.get("gex:nearest_wall")
                        if self.redis_client else None
                    )
                    gex_conf_raw = (
                        self.redis_client.get("gex:confidence")
                        if self.redis_client else None
                    )

                    if nearest_wall_raw and gex_conf_raw:
                        nearest_wall = float(nearest_wall_raw)
                        gex_conf = float(gex_conf_raw)
                        spx_price = self._get_spx_price()

                        if (
                            nearest_wall > 0
                            and spx_price > 0
                            and gex_conf >= 0.4
                        ):
                            dist_to_wall = (
                                abs(spx_price - nearest_wall) / spx_price
                            )
                            if dist_to_wall < 0.003:  # within 0.3%
                                logger.info(
                                    "gamma_pin_detected",
                                    nearest_wall=nearest_wall,
                                    spx_price=spx_price,
                                    dist_pct=round(dist_to_wall * 100, 3),
                                )
                                return ["iron_butterfly"]
            except Exception:
                pass  # Fall through to normal regime map on any pin error

            # Normal regime-based selection
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

            # Stage 2: direction filter (regime-based)
            ordered = self._stage2_direction_filter(
                candidates, direction, p_bull, p_bear
            )

            # Phase 2B: AI strategy hint override (feature-flagged, default OFF)
            # When the AI synthesis agent emits a high-confidence strategy
            # recommendation AND strategy:ai_hint_override:enabled=true,
            # use the AI hint instead of the regime-based top pick.
            # Falls back to regime-based on any error or low confidence.
            strategy_type = ordered[0]  # default: regime-based
            try:
                if self._check_feature_flag("strategy:ai_hint_override:enabled"):
                    strategy_hint = prediction.get("strategy_hint", "")
                    hint_confidence = float(prediction.get("confidence", 0.0))
                    valid_strategies = set(STATIC_SLIPPAGE_BY_STRATEGY.keys())

                    if (
                        strategy_hint
                        and hint_confidence >= 0.65
                        and strategy_hint in valid_strategies
                    ):
                        strategy_type = strategy_hint
                        logger.info(
                            "strategy_from_ai_hint",
                            hint=strategy_hint,
                            confidence=hint_confidence,
                            regime_top=ordered[0],
                        )
            except Exception as hint_err:
                logger.warning(
                    "ai_hint_override_failed", error=str(hint_err)
                )
                # strategy_type already set to regime-based above — safe

            predicted_slippage = STATIC_SLIPPAGE_BY_STRATEGY.get(
                strategy_type, 0.15
            )

            # D-012: satellite positioning after first trade
            position_type = "core" if trades_today == 0 else "satellite"

            # Get concrete strikes from Tradier option chain
            strikes = get_strikes(strategy_type, self.redis_client)
            spread_width = strikes.get("spread_width", 5.0)
            target_credit_from_chain = strikes.get("target_credit")

            # P0.5: Event-day size override — Fed/CPI/NFP days cut to 40%
            # day_type="event" is set by pre_market_scan from VVIX Z-score ≥2.5
            event_size_mult = 0.40 if session.get("day_type") == "event" else 1.0

            # B4: Kelly multiplier — cached in Redis, refreshed hourly
            # Falls back to 1.0 if insufficient trade history (<20 trades)
            kelly_mult = 1.0
            try:
                if self.redis_client:
                    cached = self.redis_client.get("kelly:multiplier")
                    if cached:
                        kelly_mult = float(cached)
                    else:
                        kelly_mult = get_kelly_multiplier_from_db()
                        self.redis_client.setex(
                            "kelly:multiplier",
                            3600,  # refresh every hour
                            str(kelly_mult),
                        )
            except Exception as kelly_err:
                logger.warning(
                    "kelly_multiplier_fetch_failed", error=str(kelly_err)
                )
                kelly_mult = 1.0

            # Risk sizing
            sizing = compute_position_size(
                account_value=account_value,
                spread_width=spread_width,  # real spread width from strike selector
                sizing_phase=sizing_phase,
                regime_agreement=regime_agreement,
                consecutive_losses_today=consecutive_losses,
                position_type=position_type,
                allocation_tier=prediction.get("allocation_tier", "full"),
                kelly_multiplier=kelly_mult,
                strategy_type=strategy_type,  # Phase 2B — debit/straddle sizing
            )

            # Apply event-day multiplier after sizing
            if event_size_mult < 1.0 and sizing["contracts"] > 0:
                original_contracts = sizing["contracts"]
                sizing = {
                    **sizing,
                    "contracts": max(1, int(sizing["contracts"] * event_size_mult)),
                    "risk_pct": round(sizing["risk_pct"] * event_size_mult, 4),
                }
                logger.info(
                    "event_day_size_cut",
                    day_type=session.get("day_type"),
                    original_contracts=original_contracts,
                    reduced_contracts=sizing["contracts"],
                    event_mult=event_size_mult,
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
                "short_strike": strikes.get("short_strike"),
                "long_strike": strikes.get("long_strike"),
                "short_strike_2": strikes.get("short_strike_2"),
                "long_strike_2": strikes.get("long_strike_2"),
                "expiry_date": strikes.get("expiry_date"),
                "target_credit": (
                    target_credit_from_chain
                    or PLACEHOLDER_CREDIT_BY_STRATEGY.get(strategy_type, 1.50)
                ),
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
                confidence=prediction.get("confidence", 0.0),
                source=(
                    "ai_hint"
                    if prediction.get("source") == "ai_synthesis"
                    else "regime"
                ),
                ai_hint_flag=self._check_feature_flag(
                    "strategy:ai_hint_override:enabled"
                ),
                butterfly_flag=self._check_feature_flag(
                    "strategy:iron_butterfly:enabled"
                ),
                straddle_flag=self._check_feature_flag(
                    "strategy:long_straddle:enabled"
                ),
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
