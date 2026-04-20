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
    "calendar_spread": 0.30,  # two legs across two expiries → wider slippage
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
    "calendar_spread":    1.50,  # net credit: near IV premium minus far cost
}

REGIME_STRATEGY_MAP = {
    "quiet_bullish": ["call_credit_spread", "put_credit_spread", "iron_condor"],
    "volatile_bullish": ["debit_call_spread", "long_call"],
    "quiet_bearish": ["put_credit_spread", "call_credit_spread", "iron_condor"],
    "volatile_bearish": ["debit_put_spread", "long_put"],
    "pin_range": ["iron_condor", "iron_butterfly", "put_credit_spread"],
    "range": ["iron_condor", "put_credit_spread", "call_credit_spread"],
    "crisis": ["put_credit_spread"],
    # Phase 2B/3C: catalyst days favour long_straddle (capture IV expansion,
    # exit pre-announcement); calendar_spread only fires AFTER announcement
    # (post-catalyst IV crush). iron_condor stays as fallback.
    "event": ["long_straddle", "calendar_spread", "iron_condor"],
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
_NEUTRAL_PREFERRED = {
    "iron_condor", "iron_butterfly", "long_straddle", "calendar_spread",
}

# ── Signal enhancement constants (module scope) ─────────────────────────────
# Kept at module scope (not inside the class) so they can be tuned without
# touching the class body and so tests can import them directly.

# Signal-A: VIX term structure thresholds.
# vix_term_ratio = VIX9D / VIX. Above 1.0 = inverted (near-term vol >
# medium-term) = elevated near-term event risk → condors face higher
# blowout risk and should be sized down or skipped entirely.
_VIX_TERM_SKIP        = 1.35   # skip trade (strong near-term risk event)
_VIX_TERM_REDUCE_HARD = 1.20   # 50% size reduction
_VIX_TERM_REDUCE_SOFT = 1.10   # 25% size reduction
_VIX_TERM_THIN_FLOOR  = 0.80   # 15% reduction (thin 0DTE premium)

# Signal-C: GEX directional bias thresholds.
# gex_net > 0: market makers long gamma → mean-reversion → good for condors.
# gex_net < 0: market makers short gamma → trending → bad for condors.
_GEX_TRENDING_HARD    = -1_000_000_000   # strongly trending → 50% size cut
_GEX_TRENDING_SOFT    =   -500_000_000   # mildly trending → 25% size cut
_GEX_MEAN_REVERT      =  1_000_000_000   # strong mean-revert → 10% boost

# Signal-D: Market breadth thresholds (via VIX z-score).
# vix_z_score = (VIX_current - VIX_20d_mean) / VIX_20d_std
# HIGH z = VIX elevated vs recent history = market anxiety = condor blowout risk.
_BREADTH_SEVERE    = 2.5    # 50% size cut (extreme fear)
_BREADTH_HIGH      = 1.5    # 25% size cut (elevated anxiety)
_BREADTH_STRONG    = -0.5   # 5% boost (calm market, strong breadth)

# Signal-E: Earnings proximity (post-market major earnings day).
_EARNINGS_PROX_CUT = 0.75   # 25% size reduction on earnings day

# Signal-F: IV rank thresholds (also via VIX z-score — same Redis read as D).
# LOW z = thin premium = not worth selling condors for small credit.
# MODERATE elevation = rich premium = slight condor boost.
_IV_VERY_THIN      = -2.0   # skip trade entirely (premium too thin)
_IV_THIN           = -1.5   # 25% reduction
_IV_SOMEWHAT_THIN  = -0.8   # 10% reduction
_IV_RICH           =  0.8   # 5% boost (premium is relatively rich)


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

            # Signal-B: 9:45 AM floor (was 9:35).
            # Opening auction settles by 9:35 but bid/ask spreads on
            # 0DTE options remain elevated until ~9:45. GEX data also
            # needs 10-15 min post-open to stabilize.
            # Feature flag: signal:entry_time_gate:enabled (default ON).
            if self._check_feature_flag(
                "signal:entry_time_gate:enabled", default=True
            ):
                open_floor = 9 * 60 + 45
            else:
                open_floor = 9 * 60 + 35  # original floor when flag off

            if total_minutes < open_floor:
                return (
                    False,
                    f"before_{open_floor // 60:02d}{open_floor % 60:02d}am",
                )

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

    def _check_feature_flag(
        self,
        flag_key: str,
        default: bool = False,
    ) -> bool:
        """Check a Redis feature flag.

        POLARITY RULES (must match backend/main.py _SIGNAL_FLAGS):
          default=False  - strategy/agent flags (default OFF):
                           absent key = disabled, "true" = enabled
          default=True   - signal flags (default ON):
                           absent key = enabled, "false" = disabled

        The `default` parameter MUST be passed explicitly at every call
        site. Missing key returns `default`, not False.

        Accepts both bytes 'true' (decode_responses=False) and string
        'true' (decode_responses=True) for forward-compatibility with
        both Redis client configurations.
        """
        try:
            if not self.redis_client:
                return default
            val = self.redis_client.get(flag_key)
            if val is None:
                return default
            return val in ("true", b"true")
        except Exception:
            return default

    def _check_time_window(
        self, cv_stress: float = 0.0
    ) -> Tuple[Union[bool, str], Optional[str]]:
        """
        Public alias for _stage0_time_gate. Signal-B uses this name and
        the test surface in test_signal_enhancements.py also calls it.
        Behavior identical to _stage0_time_gate.
        """
        return self._stage0_time_gate(cv_stress)

    def _vix_term_modifier(
        self, prediction: dict
    ) -> Tuple[float, str]:
        """
        Signal-A: VIX term structure sizing modifier.
        Returns (multiplier, status_label).

        vix_term_ratio = VIX9D / VIX. High ratio (> 1.0) = inverted term
        structure = elevated near-term uncertainty = condors face higher
        blowout risk.

        Reads vix_term_ratio from prediction dict; if absent, falls back
        to computing it from polygon:vix9d:current / polygon:vix:current
        in Redis. Final fallback is 1.0 (treated as normal).

        Returns (1.0, "normal") when flag is off or ratio is in range.
        Never raises.
        """
        try:
            if not self._check_feature_flag(
                "signal:vix_term_filter:enabled", default=True
            ):
                return 1.0, "flag_off"

            ratio_raw = prediction.get("vix_term_ratio")
            if ratio_raw is None:
                # Fallback: compute from Redis (prediction_engine writes
                # VIX9D and VIX, but doesn't always emit the ratio).
                try:
                    v9 = (
                        self.redis_client.get("polygon:vix9d:current")
                        if self.redis_client else None
                    )
                    v = (
                        self.redis_client.get("polygon:vix:current")
                        if self.redis_client else None
                    )
                    if v9 is not None and v is not None:
                        ratio = float(v9) / max(float(v), 1.0)
                    else:
                        ratio = 1.0
                except Exception:
                    ratio = 1.0
            else:
                ratio = float(ratio_raw)

            if ratio >= _VIX_TERM_SKIP:
                logger.info(
                    "signal_vix_term_skip",
                    ratio=round(ratio, 3),
                    threshold=_VIX_TERM_SKIP,
                )
                return 0.0, "strongly_inverted_skip"

            if ratio >= _VIX_TERM_REDUCE_HARD:
                logger.info(
                    "signal_vix_term_reduce_hard", ratio=round(ratio, 3)
                )
                return 0.50, "strongly_inverted"

            if ratio >= _VIX_TERM_REDUCE_SOFT:
                logger.info(
                    "signal_vix_term_reduce_soft", ratio=round(ratio, 3)
                )
                return 0.75, "inverted"

            if ratio <= _VIX_TERM_THIN_FLOOR:
                # Thin near-term premium — slight reduction
                return 0.85, "thin_premium"

            return 1.0, "normal"

        except Exception as exc:
            logger.warning("vix_term_modifier_failed", error=str(exc))
            return 1.0, "error"

    def _gex_bias_modifier(
        self, prediction: dict, strategy_type: str
    ) -> Tuple[float, str]:
        """
        Signal-C: GEX directional bias sizing modifier.
        Returns (multiplier, status_label).

        Negative GEX = market makers short gamma = trending behavior.
        Iron condors perform poorly in trending markets — reduce size.
        Positive GEX = mean-reversion — slight boost for condors.

        Only applies to short-gamma strategies (condors, butterflies,
        credit spreads). Long-gamma strategies are unaffected.
        Never raises.
        """
        try:
            if not self._check_feature_flag(
                "signal:gex_directional_bias:enabled", default=True
            ):
                return 1.0, "flag_off"

            short_gamma = {
                "iron_condor", "iron_butterfly",
                "put_credit_spread", "call_credit_spread",
            }
            if strategy_type not in short_gamma:
                return 1.0, "not_applicable"

            gex_net = float(prediction.get("gex_net") or 0.0)

            if gex_net <= _GEX_TRENDING_HARD:
                logger.info(
                    "signal_gex_trending_hard",
                    gex_net=gex_net,
                    strategy=strategy_type,
                )
                return 0.50, "strongly_trending"

            if gex_net <= _GEX_TRENDING_SOFT:
                logger.info(
                    "signal_gex_trending_soft",
                    gex_net=gex_net,
                    strategy=strategy_type,
                )
                return 0.75, "trending"

            if gex_net >= _GEX_MEAN_REVERT:
                # Strong mean-reversion regime → slight condor boost.
                # Capped at 1.10 to keep risk bounded.
                return 1.10, "strong_mean_reversion"

            return 1.0, "neutral"

        except Exception as exc:
            logger.warning("gex_bias_modifier_failed", error=str(exc))
            return 1.0, "error"

    def _read_redis_float(self, key: str, default: float = 0.0) -> float:
        """
        Read a float value from Redis. Returns default on any error.
        Used by Signal-D (breadth) and Signal-F (IV rank) to read
        vix_z_score without duplicating error handling.
        """
        try:
            if not self.redis_client:
                return default
            raw = self.redis_client.get(key)
            return float(raw) if raw is not None else default
        except Exception:
            return default

    def _market_breadth_modifier(
        self, vix_z: float
    ) -> Tuple[float, str]:
        """
        Signal-D: Market breadth sizing modifier via VIX z-score.

        HIGH vix_z = VIX elevated above its recent norm = broad market
        anxiety = condors at risk of blowout from gap moves = reduce size.

        LOW vix_z = VIX below recent norm = calm market = slight condor
        boost.

        vix_z_score source: Redis key 'polygon:vix:z_score'
        (written by polygon_feed, 20-day rolling mean/std).
        Never raises.
        """
        try:
            if not self._check_feature_flag(
                "signal:market_breadth:enabled", default=True
            ):
                return 1.0, "flag_off"

            if vix_z >= _BREADTH_SEVERE:
                logger.info(
                    "signal_d_breadth_severe",
                    vix_z=round(vix_z, 2),
                    threshold=_BREADTH_SEVERE,
                )
                return 0.50, "severe_anxiety"

            if vix_z >= _BREADTH_HIGH:
                logger.info(
                    "signal_d_breadth_high",
                    vix_z=round(vix_z, 2),
                )
                return 0.75, "elevated_anxiety"

            if vix_z <= _BREADTH_STRONG:
                return 1.05, "strong_breadth"

            return 1.0, "normal"

        except Exception as exc:
            logger.warning(
                "market_breadth_modifier_failed", error=str(exc)
            )
            return 1.0, "error"

    def _earnings_proximity_modifier(
        self, strategy_type: str
    ) -> Tuple[float, str]:
        """
        Signal-E: Earnings proximity guard.

        If a major SPX-moving stock reports earnings TODAY, SPX options
        IV is elevated and the market can gap unexpectedly. Reduces
        condor size by 25% as a precaution.

        Data source: Redis key 'calendar:today:intel'
        (written 8:45 AM daily by economic_calendar agent).
        Only affects short-gamma strategies — long gamma benefits from
        moves. Never raises.
        """
        try:
            if not self._check_feature_flag(
                "signal:earnings_proximity:enabled", default=True
            ):
                return 1.0, "flag_off"

            _short_gamma = {
                "iron_condor", "iron_butterfly",
                "put_credit_spread", "call_credit_spread",
            }
            if strategy_type not in _short_gamma:
                return 1.0, "not_applicable"

            import json as _json
            raw = None
            try:
                if self.redis_client:
                    raw = self.redis_client.get("calendar:today:intel")
            except Exception:
                pass

            if not raw:
                return 1.0, "no_calendar_data"

            intel = _json.loads(raw)
            if not intel.get("has_major_earnings", False):
                return 1.0, "no_major_earnings"

            earnings_list = intel.get("earnings", [])
            tickers = [e.get("symbol", "") for e in earnings_list]
            logger.info(
                "signal_e_earnings_proximity",
                tickers=tickers,
                strategy=strategy_type,
            )
            return _EARNINGS_PROX_CUT, "major_earnings_today"

        except Exception as exc:
            logger.warning(
                "earnings_proximity_modifier_failed", error=str(exc)
            )
            return 1.0, "error"

    def _iv_rank_modifier(self, vix_z: float) -> Tuple[float, str]:
        """
        Signal-F: IV rank sizing modifier via VIX z-score.

        Uses the SAME vix_z_score value as Signal-D (computed once and
        passed in — no duplicate Redis reads).

        LOW vix_z = VIX below recent norm = thin premium = not worth
        selling condors for small credit = reduce size.

        MODERATE elevation (0.8 to <1.5) = premium relatively rich =
        slight boost for short-premium strategies.

        HIGH vix_z (>= 1.5) = blowout risk dominates = handled by
        Signal-D. Signal-F is neutral above the rich threshold to avoid
        double-cutting. Never raises.
        """
        try:
            if not self._check_feature_flag(
                "signal:iv_rank_filter:enabled", default=True
            ):
                return 1.0, "flag_off"

            if vix_z <= _IV_VERY_THIN:
                logger.info(
                    "signal_f_iv_very_thin",
                    vix_z=round(vix_z, 2),
                )
                return 0.0, "skip_very_thin_premium"

            if vix_z <= _IV_THIN:
                return 0.75, "thin_premium"

            if vix_z <= _IV_SOMEWHAT_THIN:
                return 0.90, "somewhat_thin_premium"

            if vix_z >= _IV_RICH and vix_z < _BREADTH_HIGH:
                return 1.05, "rich_premium"

            return 1.0, "normal"

        except Exception as exc:
            logger.warning("iv_rank_modifier_failed", error=str(exc))
            return 1.0, "error"

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

        P-day butterfly safety sprint (6 gates) — reviewed by Opus 4.7
        after 2026-04-20 live losses (3 iron butterflies, all stopped out
        as GEX wall drifted 80pts intraday):
          CHANGE 1: short-circuit only when regime == "pin_range"
          CHANGE 3: block when strategy_failed_today:iron_butterfly flag set
          CHANGE 4: require GEX concentration >= 25% at top wall strike
          CHANGE 5: restrict to 12:00-15:40 ET window
        Any failed safety gate sets `butterfly_forbidden`, which both
        blocks the pin-override short-circuit AND strips iron_butterfly
        from REGIME_STRATEGY_MAP fallthrough candidates. Other strategies
        (iron_condor, put_credit_spread) remain available on fallthrough.
        """
        try:
            # ==== butterfly safety gates (apply universally) ====
            butterfly_forbidden = False
            forbidden_reason: Optional[str] = None

            # CHANGE 5: time-of-day gate — butterfly only safe 12:00-15:40 ET.
            # Morning (pre-12:00) is too volatile for short-gamma — the
            # pin has not yet demonstrated stability. Original sprint cut
            # at 3:15 PM, but the final 25 minutes of 0DTE is peak theta
            # decay and the highest-EV hold window when the wall is
            # intact — the 3:40 end gives back that window while still
            # leaving a 5-minute buffer before the D-010 3:45 PM
            # hard-close backstop runs.
            try:
                from datetime import datetime as _dt
                from zoneinfo import ZoneInfo as _ZI
                now_et = _dt.now(_ZI("America/New_York"))
                time_minutes = now_et.hour * 60 + now_et.minute
                butterfly_start = 12 * 60           # 12:00 PM ET
                butterfly_end = 15 * 60 + 40        # 3:40 PM ET
                if time_minutes < butterfly_start or time_minutes > butterfly_end:
                    butterfly_forbidden = True
                    forbidden_reason = (
                        f"time_gate_outside_12_1540_et_"
                        f"{now_et.hour:02d}{now_et.minute:02d}"
                    )
            except Exception:
                pass  # fail open on time-check error

            # CHANGE 3: strategy_failed_today flag — position_monitor
            # writes this 8h-TTL key when a butterfly hits the 150%
            # credit stop. One full stop-out ends butterfly for the day.
            if not butterfly_forbidden:
                try:
                    from datetime import date as _date
                    today = _date.today().isoformat()
                    failed_key = f"strategy_failed_today:iron_butterfly:{today}"
                    if self.redis_client and self.redis_client.get(failed_key):
                        butterfly_forbidden = True
                        forbidden_reason = "strategy_failed_today"
                except Exception:
                    pass  # fail open on flag-check error

            # CHANGE 4: GEX wall concentration — require >= 25% of
            # positive gamma mass at the top strike. Spread gamma across
            # many strikes = weak/false pin; real pins concentrate.
            if not butterfly_forbidden:
                try:
                    import json as _json
                    by_strike_raw = (
                        self.redis_client.get("gex:by_strike")
                        if self.redis_client else None
                    )
                    if by_strike_raw:
                        by_strike = _json.loads(by_strike_raw)
                        positives = [
                            float(v) for v in by_strike.values()
                            if float(v) > 0
                        ]
                        if positives:
                            total_positive_gex = sum(positives)
                            top_gex = max(positives)
                            wall_concentration = (
                                top_gex / total_positive_gex
                                if total_positive_gex > 0 else 0.0
                            )
                            if wall_concentration < 0.25:
                                butterfly_forbidden = True
                                forbidden_reason = (
                                    f"low_concentration_"
                                    f"{wall_concentration:.3f}"
                                )
                except Exception:
                    pass  # fail open on concentration-check error

            if butterfly_forbidden:
                logger.info(
                    "butterfly_forbidden",
                    reason=forbidden_reason,
                    regime=regime,
                )

            # Phase 2B: Gamma pin override (feature-flagged, default OFF).
            # CHANGE 1: short-circuit requires regime == "pin_range"
            # (previously bypassed the regime classifier entirely).
            try:
                if (
                    not butterfly_forbidden
                    and regime == "pin_range"
                    and self._check_feature_flag(
                        "strategy:iron_butterfly:enabled", default=False
                    )
                ):
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
            candidates = list(
                REGIME_STRATEGY_MAP.get(regime, ["put_credit_spread"])
            )

            # Option B: when any butterfly safety gate failed, strip
            # iron_butterfly from the fallthrough candidate list too.
            # iron_condor and put_credit_spread stay available.
            if butterfly_forbidden and "iron_butterfly" in candidates:
                candidates = [s for s in candidates if s != "iron_butterfly"]

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
                if self._check_feature_flag(
                    "strategy:ai_hint_override:enabled", default=False
                ):
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

                        # Never allow AI hint to revive a strategy that
                        # already stop-outted today. Mirrors the CHANGE 3
                        # butterfly_forbidden gate in _stage1_regime_gate
                        # so same-strategy re-entry is blocked regardless
                        # of whether selection came from regime map or
                        # AI hint override. Without this, the hint path
                        # silently reintroduces iron_butterfly after a
                        # 150% stop, defeating the whole safety sprint.
                        #
                        # Fail-open: Redis error → hint proceeds (no
                        # regression vs. pre-guard behaviour). The
                        # fallback is ordered[0] (regime top pick), so
                        # trading still happens on this cycle — just
                        # with the regime-preferred strategy instead of
                        # the failed one. No trade is skipped entirely.
                        try:
                            from datetime import date as _date
                            _today = _date.today().isoformat()
                            _failed_key = (
                                f"strategy_failed_today:{strategy_type}:{_today}"
                            )
                            if (
                                self.redis_client
                                and self.redis_client.get(_failed_key)
                            ):
                                logger.info(
                                    "ai_hint_blocked_failed_today",
                                    strategy=strategy_type,
                                    date=_today,
                                    fallback=ordered[0],
                                )
                                strategy_type = ordered[0]
                        except Exception:
                            pass  # fail open — never block trades on flag check
            except Exception as hint_err:
                logger.warning(
                    "ai_hint_override_failed", error=str(hint_err)
                )
                # strategy_type already set to regime-based above — safe

            # Phase 3C: Calendar spread only fires AFTER catalyst announcement.
            # Placed BEFORE get_strikes()/sizing so the eventual strategy_type
            # is final by the time strikes and contracts are computed.
            # If calendar_spread is selected but the announcement hasn't
            # happened yet, fall back to the next viable candidate
            # (long_straddle preferred, otherwise iron_condor).
            if strategy_type == "calendar_spread":
                try:
                    cal_flag = self._check_feature_flag(
                        "strategy:calendar_spread:enabled", default=False
                    )
                    if not cal_flag:
                        ordered_remaining = [
                            s for s in ordered if s != "calendar_spread"
                        ]
                        strategy_type = (
                            ordered_remaining[0]
                            if ordered_remaining else "iron_condor"
                        )
                    else:
                        cal_raw = (
                            self.redis_client.get("calendar:today:intel")
                            if self.redis_client else None
                        )
                        if cal_raw:
                            import json
                            import zoneinfo
                            cal = json.loads(cal_raw)
                            now_et = datetime.now(
                                zoneinfo.ZoneInfo("America/New_York")
                            )
                            event_passed = False
                            for ev in cal.get("events", []):
                                if ev.get("is_major") and ev.get("time"):
                                    try:
                                        h, m, *_ = map(
                                            int, ev["time"].split(":")
                                        )
                                        event_et = now_et.replace(
                                            hour=h, minute=m, second=0
                                        )
                                        if (
                                            now_et >= event_et
                                            and now_et.hour >= 14
                                        ):
                                            event_passed = True
                                            break
                                    except Exception:
                                        pass
                            if not event_passed:
                                # C-4: enforce strategy:long_straddle:enabled.
                                # Mirrors the iron_butterfly flag check pattern
                                # at line ~555: signal: prefix flags default
                                # ON, strategy:/agent: prefix default OFF.
                                # Falls back to iron_condor when the flag is
                                # OFF so the calendar-too-early branch still
                                # produces a tradeable strategy.
                                _straddle_allowed = self._check_feature_flag(
                                    "strategy:long_straddle:enabled",
                                    default=False,
                                )
                                strategy_type = (
                                    "long_straddle"
                                    if (
                                        "long_straddle" in ordered
                                        and _straddle_allowed
                                    )
                                    else "iron_condor"
                                )
                                logger.info(
                                    "calendar_spread_too_early_using_straddle",
                                    selected=strategy_type,
                                    straddle_flag=_straddle_allowed,
                                )
                except Exception:
                    strategy_type = "iron_condor"

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

            # ── Signal enhancements (Signal-A, Signal-B, Signal-C) ────
            # Each returns a multiplier in [0.0, 1.1]. Combined multiplier
            # is the product, capped at 1.1. 0.0 = skip this trade.

            # Signal-A: VIX term structure
            vix_term_mult, vix_term_status = self._vix_term_modifier(
                prediction
            )
            if vix_term_mult == 0.0:
                logger.info(
                    "signal_a_skip_trade",
                    reason="vix_term_strongly_inverted",
                    ratio=prediction.get("vix_term_ratio"),
                )
                return None  # Skip — strong near-term event risk

            # Signal-B: opening volatility window (9:45-10:00 AM ET)
            opening_mult = 1.0
            try:
                if self._check_feature_flag(
                    "signal:entry_time_gate:enabled", default=True
                ):
                    import zoneinfo
                    _et = zoneinfo.ZoneInfo("America/New_York")
                    _now = datetime.now(_et)
                    _mins = _now.hour * 60 + _now.minute
                    # 9:45-10:00 AM: opening vol residue → 25% reduction
                    if 9 * 60 + 45 <= _mins < 10 * 60:
                        opening_mult = 0.75
                        logger.debug(
                            "signal_b_opening_window_reduction",
                            time=f"{_now.hour}:{_now.minute:02d}",
                        )
            except Exception:
                pass

            # Signal-C: GEX directional bias
            gex_mult, gex_status = self._gex_bias_modifier(
                prediction, strategy_type
            )

            # Signal-D + F: read VIX z-score ONCE and share between
            # both signals — one Redis round-trip, not two.
            #
            # E-2: prefer the slow-regime daily z-score
            # (polygon:vix:z_score_daily, written by polygon_feed from
            # vix_daily_history). The legacy polygon:vix:z_score key
            # was previously a 100-min intraday rolling window mis-
            # labelled "20d" — using it for regime-level signals D + F
            # injected intraday noise into a slow variable. We fall
            # back to the legacy key during rollout so this works even
            # if polygon_feed hasn't written the new key yet.
            #
            # NOTE: VVIX (self.history in polygon_feed) has the same
            # bug and is deferred to S7 — it requires the same
            # backfill + daily-history split.
            try:
                raw_daily = (
                    self.redis_client.get("polygon:vix:z_score_daily")
                    if self.redis_client else None
                )
                if raw_daily is not None:
                    vix_z = float(raw_daily)
                else:
                    vix_z = self._read_redis_float(
                        "polygon:vix:z_score", 0.0
                    )
            except (TypeError, ValueError):
                vix_z = self._read_redis_float(
                    "polygon:vix:z_score", 0.0
                )

            # Signal-D: Market breadth
            breadth_mult, breadth_status = (
                self._market_breadth_modifier(vix_z)
            )

            # Signal-E: Earnings proximity guard (reads Redis intel)
            earnings_mult, earnings_status = (
                self._earnings_proximity_modifier(strategy_type)
            )

            # Signal-F: IV rank filter (reuses vix_z from Signal-D)
            iv_mult, iv_status = self._iv_rank_modifier(vix_z)

            # Signal-F skip (very thin premium) — same pattern as
            # Signal-A skip on a strongly inverted VIX term.
            if iv_mult == 0.0:
                logger.info(
                    "signal_f_skip_trade",
                    reason="iv_very_thin_premium",
                    vix_z=round(vix_z, 2),
                )
                return None  # Skip — premium too thin to sell

            signal_mult = round(
                min(
                    1.1,
                    vix_term_mult * opening_mult * gex_mult
                    * breadth_mult * earnings_mult * iv_mult,
                ),
                4,
            )

            if signal_mult != 1.0:
                logger.info(
                    "signal_sizing_applied",
                    signal_mult=signal_mult,
                    vix_term=vix_term_status,
                    gex_bias=gex_status,
                    opening_mult=opening_mult,
                    breadth=breadth_status,
                    earnings=earnings_status,
                    iv_rank=iv_status,
                )

            # A5: Production observability smoke signal.
            # has_vix_z_data=False means polygon:vix:z_score was never
            # written. Check Railway logs on Day 1 after deploy — if this
            # is False for every cycle, the VIX z-score writer didn't
            # start (e.g., polygon_feed needs to collect 5 cycles or the
            # service didn't restart).
            logger.info(
                "signal_mult_audit",
                signal_mult=signal_mult,
                vix_z=round(vix_z, 3),
                has_vix_z_data=(vix_z != 0.0),
                breadth=breadth_status,
                iv_rank=iv_status,
                vix_term=vix_term_status,
                gex_bias=gex_status,
                earnings=earnings_status,
            )

            # Apply signal multiplier to sizing (mirrors event_size_mult)
            if signal_mult != 1.0 and sizing["contracts"] > 0:
                original = sizing["contracts"]
                sizing = {
                    **sizing,
                    "contracts": max(
                        1, int(sizing["contracts"] * signal_mult)
                    ),
                    "risk_pct": round(
                        sizing["risk_pct"] * signal_mult, 4
                    ),
                }
                if sizing["contracts"] != original:
                    logger.info(
                        "signal_contracts_adjusted",
                        original=original,
                        adjusted=sizing["contracts"],
                        multiplier=signal_mult,
                    )
            # ── End signal enhancements ───────────────────────────────

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

            # A2: Capture decision context at SELECTION TIME for the
            # Loop 2 meta-label audit trail. Captures flag state and
            # signal multipliers at the exact moment the strategy was
            # selected — not when the order was placed (which can lag
            # by seconds and reflect a different flag state).
            #
            # ExecutionEngine persists whatever is in
            # signal["decision_context"] into the trading_positions
            # JSONB column. No ExecutionEngine changes needed here.
            _SIGNAL_FLAG_DEFAULTS = {
                "signal:vix_term_filter:enabled": True,
                "signal:entry_time_gate:enabled": True,
                "signal:gex_directional_bias:enabled": True,
                "signal:market_breadth:enabled": True,
                "signal:earnings_proximity:enabled": True,
                "signal:iv_rank_filter:enabled": True,
            }
            _decision_context = {
                "signal_mult": signal_mult,
                "vix_term_mult": vix_term_mult,
                "vix_term_status": vix_term_status,
                "gex_mult": gex_mult,
                "gex_status": gex_status,
                "opening_mult": opening_mult,
                "breadth_mult": breadth_mult,
                "breadth_status": breadth_status,
                "earnings_mult": earnings_mult,
                "earnings_status": earnings_status,
                "iv_mult": iv_mult,
                "iv_status": iv_status,
                "vix_z": round(vix_z, 3),
                "has_vix_z_data": (vix_z != 0.0),
                "flags_at_selection": {
                    k: self._check_feature_flag(k, default=v)
                    for k, v in _SIGNAL_FLAG_DEFAULTS.items()
                },
                "selected_at": datetime.now(timezone.utc).isoformat(),
            }

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
                "far_expiry_date": strikes.get("far_expiry"),
                "target_credit": (
                    target_credit_from_chain
                    or PLACEHOLDER_CREDIT_BY_STRATEGY.get(strategy_type, 1.50)
                ),
                "stop_loss_level": None,
                "profit_target": None,
                "ev_net": None,
                "decision_context": _decision_context,
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
                    "strategy:ai_hint_override:enabled", default=False
                ),
                butterfly_flag=self._check_feature_flag(
                    "strategy:iron_butterfly:enabled", default=False
                ),
                straddle_flag=self._check_feature_flag(
                    "strategy:long_straddle:enabled", default=False
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
