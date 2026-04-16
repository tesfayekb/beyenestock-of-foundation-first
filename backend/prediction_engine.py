"""
Prediction engine — runs every 5 minutes.
Phase 2: placeholder model outputs. Real models trained in Phase 4.
"""
from datetime import datetime, timezone
from typing import Optional

try:
    import redis as redis_lib
except ModuleNotFoundError:
    redis_lib = None

from config import REDIS_URL
from db import get_client, write_health_status, write_audit_log
from logger import get_logger
from session_manager import get_today_session

logger = get_logger("prediction_engine")


def _is_market_hours() -> bool:
    try:
        import zoneinfo
        from datetime import datetime
        et = zoneinfo.ZoneInfo("America/New_York")
        now = datetime.now(et)
        if now.weekday() >= 5:
            return False
        minutes = now.hour * 60 + now.minute
        return 9 * 60 + 30 <= minutes <= 16 * 60
    except Exception:
        return False


class PredictionEngine:

    def __init__(self) -> None:
        if redis_lib is None:
            raise RuntimeError(
                "redis dependency required for PredictionEngine"
            )
        try:
            self.redis_client = redis_lib.Redis.from_url(
                REDIS_URL, decode_responses=True
            )
        except Exception as e:
            logger.error("prediction_engine_redis_failed", error=str(e))
            self.redis_client = None
        self._cycle_count = 0

    def _read_redis(self, key: str, default=None):
        if not self.redis_client:
            return default
        try:
            raw = self.redis_client.get(key)
            return raw if raw is not None else default
        except Exception:
            return default

    def _compute_regime(self) -> dict:
        """
        Layer A: Regime classification placeholder.
        Uses VVIX Z-score as proxy. Real HMM + LightGBM in Phase 4.
        D-021: regime disagreement guard implemented here.
        """
        vvix_z_raw = self._read_redis("polygon:vvix:z_score", "0.0")
        try:
            vvix_z = float(vvix_z_raw)
        except (ValueError, TypeError):
            vvix_z = 0.0

        if abs(vvix_z) > 2.5:
            regime_hmm = "volatile_bearish" if vvix_z > 0 else "volatile_bullish"
            regime_lgbm = "crisis" if vvix_z > 2.5 else "volatile_bullish"
            rcs = 35.0
        elif abs(vvix_z) > 1.5:
            regime_hmm = "quiet_bullish"
            regime_lgbm = "quiet_bullish"
            rcs = 55.0
        else:
            regime_hmm = "pin_range"
            regime_lgbm = "pin_range"
            rcs = 65.0

        # D-021: detect disagreement and apply penalty
        regime_agreement = regime_hmm == regime_lgbm
        if not regime_agreement:
            rcs = max(0.0, rcs - 15.0)
            write_audit_log(
                action="trading.regime_disagreement",
                metadata={
                    "regime_hmm": regime_hmm,
                    "regime_lgbm": regime_lgbm,
                    "rcs_after_penalty": rcs,
                },
            )
            logger.warning(
                "regime_disagreement",
                regime_hmm=regime_hmm,
                regime_lgbm=regime_lgbm,
                rcs=rcs,
            )

        if rcs >= 80:
            allocation_tier = "full"
        elif rcs >= 60:
            allocation_tier = "moderate"
        elif rcs >= 40:
            allocation_tier = "low"
        elif rcs >= 20:
            allocation_tier = "pre_event"
        else:
            allocation_tier = "danger"

        return {
            "regime": regime_lgbm,
            "regime_hmm": regime_hmm,
            "regime_lgbm": regime_lgbm,
            "regime_agreement": regime_agreement,
            "rcs": round(rcs, 2),
            "allocation_tier": allocation_tier,
        }

    def _compute_cv_stress(self) -> dict:
        """
        CV_Stress computation.
        Phase 2 proxy: uses VVIX Z-score and GEX confidence.
        Real charm/vanna velocities from options chain in Phase 4.
        Formula: cv_stress = 60% * proxy_vanna + 40% * proxy_charm
        """
        try:
            gex_conf = float(self._read_redis("gex:confidence", "1.0"))
        except (ValueError, TypeError):
            gex_conf = 1.0
        try:
            vvix_z = float(self._read_redis("polygon:vvix:z_score", "0.0"))
        except (ValueError, TypeError):
            vvix_z = 0.0

        # Proxy velocities based on available data
        proxy_vanna = abs(vvix_z) * 0.6 + (1.0 - gex_conf) * 2.0
        proxy_charm = abs(vvix_z) * 0.4 + (1.0 - gex_conf) * 1.5
        raw = 0.6 * proxy_vanna + 0.4 * proxy_charm
        cv_stress = min(100.0, max(0.0, raw * 20.0))

        return {
            "cv_stress_score": round(cv_stress, 2),
            "charm_velocity": round(proxy_charm, 8),
            "vanna_velocity": round(proxy_vanna, 8),
        }

    def _compute_direction(self, regime: str, cv_stress: float) -> dict:
        """
        Layer B: Direction prediction placeholder.
        Returns calibrated probabilities based on regime + CV_Stress.
        Real LightGBM on 93 features in Phase 4.
        """
        if cv_stress > 70:
            p_bull, p_bear, p_neutral = 0.25, 0.35, 0.40
        elif regime in ("quiet_bullish",):
            p_bull, p_bear, p_neutral = 0.45, 0.25, 0.30
        elif regime in ("crisis", "volatile_bearish"):
            p_bull, p_bear, p_neutral = 0.20, 0.50, 0.30
        else:
            p_bull, p_bear, p_neutral = 0.35, 0.30, 0.35

        total = p_bull + p_bear + p_neutral
        p_bull /= total
        p_bear /= total
        p_neutral /= total

        direction = max(
            [("bull", p_bull), ("bear", p_bear), ("neutral", p_neutral)],
            key=lambda x: x[1],
        )[0]
        confidence = max(p_bull, p_bear, p_neutral)

        return {
            "p_bull": round(p_bull, 4),
            "p_bear": round(p_bear, 4),
            "p_neutral": round(p_neutral, 4),
            "direction": direction,
            "confidence": round(confidence, 4),
            "expected_move_pts": round(10.0 * (p_bull - p_bear), 2),
            "expected_move_pct": round(0.002 * (p_bull - p_bear), 6),
        }

    def _evaluate_no_trade(
        self,
        rcs: float,
        cv_stress: float,
        vvix_z: float,
        session: dict,
    ) -> tuple:
        """
        Returns (no_trade: bool, reason: Optional[str]).
        Implements D-018 (VVIX), D-022 (capital preservation), RCS gate.
        """
        if session and session.get("session_status") == "halted":
            return True, "session_halted"

        # D-018: VVIX emergency threshold
        if vvix_z >= 3.0:
            return True, f"vvix_emergency_z_{vvix_z:.2f}"

        # RCS too low
        if rcs < 40:
            return True, f"rcs_too_low_{rcs:.0f}"

        # CV_Stress critical
        if cv_stress > 85:
            return True, f"cv_stress_critical_{cv_stress:.0f}"

        # D-022: 5 consecutive losses = halt
        if session:
            consecutive = session.get("consecutive_losses_today", 0)
            if consecutive >= 5:
                return True, "capital_preservation_halt_5_losses"

        return False, None

    def run_cycle(self) -> Optional[dict]:
        """Run one prediction cycle. Writes to trading_prediction_outputs."""
        try:
            self._cycle_count += 1
            session = get_today_session()
            if not session:
                logger.warning("prediction_cycle_no_session")
                self._write_heartbeat()
                return None

            # Read VVIX context
            try:
                vvix = float(self._read_redis("polygon:vvix:current", "0.0"))
                vvix_z = float(self._read_redis("polygon:vvix:z_score", "0.0"))
            except (ValueError, TypeError):
                vvix, vvix_z = 0.0, 0.0

            # Compute all layers
            regime_data = self._compute_regime()
            cv_data = self._compute_cv_stress()
            direction_data = self._compute_direction(
                regime_data["regime"], cv_data["cv_stress_score"]
            )

            def _safe_float(key, default=0.0):
                try:
                    return float(self._read_redis(key, str(default)))
                except (ValueError, TypeError):
                    return default

            gex_net = _safe_float("gex:net")
            gex_nearest_wall = _safe_float("gex:nearest_wall") or None
            gex_flip_zone = _safe_float("gex:flip_zone") or None
            gex_confidence = _safe_float("gex:confidence")

            # D-022: capital preservation mode flag
            consecutive = session.get("consecutive_losses_today", 0)
            cap_pres = consecutive >= 3

            # No-trade evaluation
            no_trade, no_trade_reason = self._evaluate_no_trade(
                regime_data["rcs"],
                cv_data["cv_stress_score"],
                vvix_z,
                session,
            )

            output = {
                "session_id": session["id"],
                "predicted_at": datetime.now(timezone.utc).isoformat(),
                **direction_data,
                "gex_net": gex_net,
                "gex_nearest_wall": gex_nearest_wall,
                "gex_flip_zone": gex_flip_zone,
                "gex_confidence": round(gex_confidence, 4),
                **cv_data,
                **regime_data,
                # placeholders until real price feed in Phase 2B
                "spx_price": 5000.0,
                "vix": 18.0,
                "vvix": vvix,
                "vvix_z_score": round(vvix_z, 3),
                "no_trade_signal": no_trade,
                "no_trade_reason": no_trade_reason,
                "capital_preservation_mode": cap_pres,
                "execution_degraded": False,
            }

            result = (
                get_client()
                .table("trading_prediction_outputs")
                .insert(output)
                .execute()
            )

            if no_trade:
                write_audit_log(
                    action="trading.no_trade_signal",
                    metadata={
                        "reason": no_trade_reason,
                        "rcs": regime_data["rcs"],
                        "cv_stress": cv_data["cv_stress_score"],
                    },
                )
                logger.info("no_trade_signal", reason=no_trade_reason)
            else:
                logger.info(
                    "prediction_cycle_complete",
                    direction=direction_data["direction"],
                    confidence=direction_data["confidence"],
                    regime=regime_data["regime"],
                    rcs=regime_data["rcs"],
                    cv_stress=cv_data["cv_stress_score"],
                )

            self._write_heartbeat()
            return result.data[0] if result.data else output

        except Exception as e:
            logger.error("prediction_cycle_failed", error=str(e), exc_info=True)
            write_health_status(
                "prediction_engine",
                "error",
                last_error_message=str(e),
            )
            return None

    def _write_heartbeat(self) -> None:
        write_health_status(
            "prediction_engine",
            "healthy",
            is_market_hours=_is_market_hours(),
        )
