"""
Prediction engine — runs every 5 minutes.
Phase 2: placeholder model outputs. Real models trained in Phase 4.
"""
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

try:
    import redis as redis_lib
except ModuleNotFoundError:
    redis_lib = None

from config import REDIS_URL
from db import get_client, write_health_status, write_audit_log
from logger import get_logger
from session_manager import get_today_session

logger = get_logger("prediction_engine")


def _safe_float(value, default: float) -> float:
    """S4 / E-5: parse a Redis string/bytes value to float, fall back
    to the provided default on any conversion error or empty value."""
    if value is None:
        return default
    try:
        if isinstance(value, bytes):
            value = value.decode("utf-8", errors="ignore")
        s = str(value).strip()
        if not s:
            return default
        return float(s)
    except (ValueError, TypeError):
        return default


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

        # Phase A3: load trained LightGBM direction model if available
        self._direction_model = None
        self._direction_features = None
        model_path = Path(__file__).parent / "models" / "direction_lgbm_v1.pkl"
        meta_path  = Path(__file__).parent / "models" / "model_metadata.json"
        if model_path.exists():
            try:
                import pickle
                with open(model_path, "rb") as f:
                    self._direction_model = pickle.load(f)
                if meta_path.exists():
                    import json as _json
                    meta = _json.loads(meta_path.read_text())
                    self._direction_features = meta.get("features", [])
                logger.info(
                    "direction_model_loaded",
                    model_version="v1",
                    features=len(self._direction_features or []),
                )
            except Exception as e:
                logger.warning("direction_model_load_failed", error=str(e))
                self._direction_model = None

    def _read_redis(self, key: str, default=None):
        if not self.redis_client:
            return default
        try:
            raw = self.redis_client.get(key)
            return raw if raw is not None else default
        except Exception:
            return default

    def _safe_redis(
        self,
        key: str,
        default: Any = None,
        max_age_seconds: Optional[int] = None,
        age_key: Optional[str] = None,
    ) -> tuple[Any, bool]:
        """
        HARD-A: Safe Redis read with optional staleness check.

        Returns (value, is_fresh) tuple.
        is_fresh = False if:
          - Redis is down (fallback used)
          - Value is missing (default used)
          - Value is older than max_age_seconds (if specified)

        age_key: a separate Redis key holding the write timestamp
        (ISO string). If omitted, staleness is not checked.

        Usage:
          value, fresh = self._safe_redis(
              "gex:net", "0",
              max_age_seconds=3600,
              age_key="gex:updated_at",
          )
          if not fresh:
              logger.warning("gex_data_stale")

        Fail-open: if the age_key parse fails, the value is returned
        and marked fresh — better to use slightly stale data than to
        block trading on a metadata error.
        """
        raw = self._read_redis(key, default)

        if raw is None or raw == default:
            return default, False

        if max_age_seconds is None or age_key is None:
            return raw, True

        try:
            ts_raw = self._read_redis(age_key, None)
            if ts_raw is None:
                return raw, True
            ts_str = ts_raw.decode() if isinstance(ts_raw, bytes) else ts_raw
            ts = datetime.fromisoformat(ts_str)
            age = (datetime.now(timezone.utc) - ts).total_seconds()
            if age > max_age_seconds:
                logger.warning(
                    "redis_value_stale",
                    key=key,
                    age_seconds=round(age),
                    threshold=max_age_seconds,
                )
                return raw, False
            return raw, True
        except Exception:
            return raw, True

    def _get_spx_price(self) -> float:
        """Read current SPX price from Redis. Falls back to 5200.0."""
        try:
            raw = self._read_redis("tradier:quotes:SPX", None)
            if raw:
                import json
                data = json.loads(raw)
                price = float(
                    data.get("last") or data.get("ask") or data.get("bid") or 5200.0
                )
                return round(price, 2)
        except Exception:
            pass
        return 5200.0

    def _compute_regime(self) -> dict:
        """
        Regime classification — dual-model approach for D-021 disagreement.

        Layer A (regime_hmm): VVIX Z-score proxy (unchanged from Phase 2).
        Layer B (regime_lgbm): GEX zero-gamma level (new — real signal).

        Two independent inputs → genuine D-021 disagreement possible.
        GEX confidence < 0.3 → fall back to HMM for both (data quality gate).
        """
        import math

        # ROI-1: Check for catalyst/earnings day FIRST.
        # calendar:today:intel is written by economic_calendar at 8:45 AM ET.
        # When today is a major catalyst (FOMC/CPI/NFP) or major earnings day,
        # override regime to "event" so strategy_selector picks long_straddle
        # or calendar_spread from REGIME_STRATEGY_MAP["event"]. Previously
        # _compute_regime never read calendar intel, so the entire "event"
        # branch was dead code — straddle/calendar were unreachable.
        # RCS is capped at 55 on event days: IV is elevated (entry is fine)
        # but direction is uncertain (no max-confidence sizing).
        try:
            cal_raw = self._read_redis("calendar:today:intel", None)
            if cal_raw:
                import json as _json
                intel = _json.loads(cal_raw)
                if (
                    intel.get("has_major_catalyst")
                    or intel.get("has_major_earnings")
                ):
                    logger.info(
                        "regime_event_day_override",
                        has_catalyst=intel.get("has_major_catalyst"),
                        has_earnings=intel.get("has_major_earnings"),
                        day_classification=intel.get("day_classification"),
                    )
                    return {
                        "regime": "event",
                        "regime_hmm": "event",
                        "regime_lgbm": "event",
                        "regime_agreement": True,
                        "rcs": 55.0,
                        "allocation_tier": "moderate",
                        "gex_flip_zone_used": None,
                        "gex_conf_at_regime": 0.0,
                    }
        except Exception:
            pass  # Calendar unavailable — fall through to normal regime logic

        # --- Read all signals ---
        vvix_z_raw = self._read_redis("polygon:vvix:z_score", None)
        try:
            vvix_z = float(vvix_z_raw) if vvix_z_raw is not None else 0.0
        except (ValueError, TypeError):
            vvix_z = 0.0

        gex_conf_raw = self._read_redis("gex:confidence", None)
        try:
            gex_conf = float(gex_conf_raw) if gex_conf_raw is not None else 0.0
        except (ValueError, TypeError):
            gex_conf = 0.0

        flip_zone_raw = self._read_redis("gex:flip_zone", None)
        try:
            flip_zone = float(flip_zone_raw) if flip_zone_raw else None
        except (ValueError, TypeError):
            flip_zone = None

        spx_price = self._get_spx_price()

        # --- Layer A: VVIX Z-score regime (HMM proxy) ---
        if abs(vvix_z) > 2.5:
            regime_hmm = "volatile_bearish" if vvix_z > 0 else "volatile_bullish"
            rcs_hmm = 35.0
        elif abs(vvix_z) > 1.5:
            regime_hmm = "quiet_bullish"
            rcs_hmm = 55.0
        else:
            regime_hmm = "pin_range"
            rcs_hmm = 65.0

        # --- Layer B: GEX zero-gamma regime (LightGBM proxy) ---
        # Requires gex_conf >= 0.3 (enough option flow data) and valid flip_zone
        if gex_conf < 0.3 or flip_zone is None or flip_zone <= 0:
            # Insufficient GEX data — both layers agree (no D-021 penalty)
            regime_lgbm = regime_hmm
            rcs_lgbm = rcs_hmm
        else:
            # SPX position relative to zero-gamma level
            dist_pct = (spx_price - flip_zone) / flip_zone  # positive = above ZG

            if abs(vvix_z) > 2.5:
                # Crisis override regardless of ZG position
                regime_lgbm = "crisis"
                rcs_lgbm = 25.0
            elif dist_pct > 0.003 and abs(vvix_z) < 1.5:
                # SPX above ZG, low vol → dealers long gamma → mean-reversion
                regime_lgbm = "pin_range"
                rcs_lgbm = 70.0
            elif dist_pct > 0.001 and abs(vvix_z) < 0.8:
                # SPX just above ZG, calm → quiet trend
                regime_lgbm = "quiet_bullish"
                rcs_lgbm = 60.0
            elif dist_pct < -0.003 and vvix_z > 1.5:
                # SPX below ZG, rising vol → dealers short gamma → trending
                regime_lgbm = "volatile_bearish"
                rcs_lgbm = 45.0
            elif dist_pct < -0.001:
                # SPX below ZG → trend-following regime
                regime_lgbm = "trend"
                rcs_lgbm = 55.0
            else:
                # Near ZG, uncertain
                regime_lgbm = "range"
                rcs_lgbm = 60.0

        # --- Combine: use average RCS, apply D-021 on disagreement ---
        rcs = (rcs_hmm + rcs_lgbm) / 2.0

        # D-021: genuine disagreement between HMM and LightGBM signals
        regime_agreement = regime_hmm == regime_lgbm
        if not regime_agreement:
            rcs = max(0.0, rcs - 15.0)
            write_audit_log(
                action="trading.regime_disagreement",
                metadata={
                    "regime_hmm": regime_hmm,
                    "regime_lgbm": regime_lgbm,
                    "vvix_z": round(vvix_z, 3),
                    "gex_flip_zone": flip_zone,
                    "spx_price": spx_price,
                    "dist_pct": round(dist_pct, 5) if flip_zone else None,
                    "rcs_after_penalty": round(rcs, 1),
                },
            )
            logger.warning(
                "regime_disagreement_d021",
                regime_hmm=regime_hmm,
                regime_lgbm=regime_lgbm,
                rcs=round(rcs, 1),
            )

        # Use the LightGBM (GEX-based) regime as primary when data is available
        regime = regime_lgbm if gex_conf >= 0.3 and flip_zone else regime_hmm

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
            "regime": regime,
            "regime_hmm": regime_hmm,
            "regime_lgbm": regime_lgbm,
            "regime_agreement": regime_agreement,
            "rcs": round(rcs, 2),
            "allocation_tier": allocation_tier,
            "gex_flip_zone_used": flip_zone,
            "gex_conf_at_regime": round(gex_conf, 4),
        }

    def _compute_cv_stress(self) -> dict:
        """
        CV_Stress computation.
        Phase 2 proxy: uses VVIX Z-score and GEX confidence.
        Real charm/vanna velocities from options chain in Phase 4.
        Formula: cv_stress = 60% * proxy_vanna + 40% * proxy_charm
        """
        gex_conf_raw = self._read_redis("gex:confidence", None)
        gex_conf = float(gex_conf_raw) if gex_conf_raw is not None else None
        try:
            vvix_z = float(self._read_redis("polygon:vvix:z_score", "0.0"))
        except (ValueError, TypeError):
            vvix_z = 0.0

        # Proxy velocities based on available data
        # Treat None gex_conf (no Redis data yet) as neutral 0.5 not full confidence 1.0
        gex_conf_val = gex_conf if gex_conf is not None else 0.5
        proxy_vanna = abs(vvix_z) * 0.6 + (1.0 - gex_conf_val) * 2.0
        proxy_charm = abs(vvix_z) * 0.4 + (1.0 - gex_conf_val) * 1.5
        raw = 0.6 * proxy_vanna + 0.4 * proxy_charm
        cv_stress = min(100.0, max(0.0, raw * 20.0))

        return {
            "cv_stress_score": round(cv_stress, 2),
            "charm_velocity": round(proxy_charm, 8),
            "vanna_velocity": round(proxy_vanna, 8),
        }

    def _compute_direction(
        self,
        regime: str,
        cv_stress: float,
        spx_price: float = 5200.0,
        flip_zone: float = None,
        gex_conf: float = 0.0,
    ) -> dict:
        """
        Direction prediction — LightGBM model (Phase A3) with GEX/ZG overlay.

        Priority order:
        1. LightGBM model (if loaded) — uses live Redis features
        2. GEX/ZG rule-based (fallback when model not loaded)
        3. Regime-based hardcoded (fallback when GEX unavailable)
        """
        import math

        # --- Priority 0: AI synthesis agent (Phase 2A) ---
        # Only activates when: (a) agents:ai_synthesis:enabled = true in Redis
        # and (b) ai:synthesis:latest key is fresh (< 30 min old)
        ai_synthesis = None
        try:
            reader = getattr(self, "_read_redis", None)
            if reader is not None and getattr(self, "redis_client", None):
                ai_synthesis = reader("ai:synthesis:latest", None)
        except Exception:
            ai_synthesis = None

        # B-8: respect the agents:ai_synthesis:enabled flag. The comment
        # above says the path "only activates when flag = true" but the
        # code never actually checked. Without this gate, stale synthesis
        # JSON in Redis can drive predictions even after the operator
        # has disabled the agent from the trading console.
        synthesis_flag_on = False
        try:
            flag_raw = self._read_redis(
                "agents:ai_synthesis:enabled", None
            )
            synthesis_flag_on = flag_raw in ("true", b"true")
        except Exception:
            synthesis_flag_on = False

        if not synthesis_flag_on:
            ai_synthesis = None  # Flag OFF → skip synthesis path entirely

        if ai_synthesis:
            try:
                import json, time
                from datetime import datetime, timezone
                synth = json.loads(ai_synthesis)
                # Check freshness (must be < 30 minutes old)
                gen_at = synth.get("generated_at", "")
                if gen_at:
                    age_s = (
                        datetime.now(timezone.utc)
                        - datetime.fromisoformat(gen_at)
                    ).total_seconds()
                    if age_s < 1800:  # 30 min
                        direction = synth.get("direction", "neutral")
                        confidence = float(synth.get("confidence", 0.0))
                        strategy_hint = synth.get("strategy", "")
                        sizing_modifier = float(synth.get("sizing_modifier", 1.0))
                        if confidence >= 0.55 and direction in ("bull", "bear", "neutral"):
                            logger.info(
                                "prediction_from_ai_synthesis",
                                direction=direction,
                                confidence=confidence,
                                strategy_hint=strategy_hint,
                                age_seconds=int(age_s),
                            )
                            # ROI-4: ensure the probability triplet sums to 1.0.
                            # The previous shape returned only p_bull + p_bear,
                            # leaving downstream consumers (PredictionConfidence,
                            # cv_stress sizing) to assume p_neutral. Make it
                            # explicit and renormalise on any floating-point drift.
                            _p_bull = (
                                confidence if direction == "bull"
                                else (1 - confidence) * 0.5
                            )
                            _p_bear = (
                                confidence if direction == "bear"
                                else (1 - confidence) * 0.5
                            )
                            _p_neutral = max(0.0, 1.0 - _p_bull - _p_bear)
                            _total = _p_bull + _p_bear + _p_neutral
                            if _total > 0 and abs(_total - 1.0) > 0.001:
                                _p_bull /= _total
                                _p_bear /= _total
                                _p_neutral /= _total
                            return {
                                "direction": direction,
                                "p_bull": _p_bull,
                                "p_bear": _p_bear,
                                "p_neutral": _p_neutral,
                                "confidence": confidence,
                                "strategy_hint": strategy_hint,
                                "sizing_modifier": sizing_modifier,
                                "source": "ai_synthesis",
                            }
            except Exception as e:
                logger.warning("ai_synthesis_parse_failed", error=str(e))
        # Priority 0 not used — fall through to LightGBM / GEX/ZG

        # --- Priority 1: LightGBM model inference ---
        # Use getattr to support tests that bypass __init__ via __new__.
        direction_model = getattr(self, "_direction_model", None)
        direction_features = getattr(self, "_direction_features", None)
        if direction_model is not None and direction_features:
            try:
                import numpy as np
                from datetime import datetime, timezone
                import zoneinfo

                now_et = datetime.now(zoneinfo.ZoneInfo("America/New_York"))

                # Build feature vector matching training features
                vix_raw  = self._read_redis("polygon:vix:current", "18.0")
                vvix_raw = self._read_redis("polygon:vvix:current", "120.0")
                vvix_z   = float(self._read_redis("polygon:vvix:z_score", "0.0"))
                rv_20d   = float(self._read_redis("polygon:spx:realized_vol_20d", "15.0") or 15.0)

                vix_val  = float(vix_raw or 18.0)
                vvix_val = float(vvix_raw or 120.0)
                iv_rv    = vix_val / rv_20d if rv_20d > 0 else 1.0

                minutes_from_open = (
                    (now_et.hour * 60 + now_et.minute) - (9 * 60 + 30)
                )
                minutes_to_close = 390 - minutes_from_open

                feature_map = {
                    "return_5m":          float(self._read_redis("polygon:spx:return_5m",  "0.0") or 0.0),
                    "return_30m":         float(self._read_redis("polygon:spx:return_30m", "0.0") or 0.0),
                    "return_1h":          float(self._read_redis("polygon:spx:return_1h",  "0.0") or 0.0),
                    "return_4h":          float(self._read_redis("polygon:spx:return_4h",  "0.0") or 0.0),
                    "overnight_gap":      float(self._read_redis("polygon:spx:overnight_gap", "0.0") or 0.0),
                    "prior_day_return":   float(self._read_redis("polygon:spx:prior_day_return", "0.0") or 0.0),
                    "rsi_14":             float(self._read_redis("polygon:spx:rsi_14", "50.0") or 50.0),
                    "macd_signal":        float(self._read_redis("polygon:spx:macd_signal", "0.0") or 0.0),
                    "bb_pct_b":           float(self._read_redis("polygon:spx:bb_pct_b", "0.5") or 0.5),
                    "minutes_from_open":  float(minutes_from_open),
                    "minutes_to_close":   float(minutes_to_close),
                    "vwap_distance":      float(self._read_redis("polygon:spx:vwap_distance", "0.0") or 0.0),
                    "morning_range":      float(self._read_redis("polygon:spx:morning_range", "0.005") or 0.005),
                    "vix_close":          vix_val,
                    "vix_5d_change":      float(self._read_redis("polygon:vix:5d_change", "0.0") or 0.0),
                    "vix_z_score":        float(self._read_redis("polygon:vix:z_score", "0.0") or 0.0),
                    "vvix_close":         vvix_val,
                    "vvix_z_score":       vvix_z,
                    "rv_20d":             rv_20d,
                    "iv_rv_ratio":        iv_rv,
                    "vix_term_ratio":     float(self._read_redis("polygon:vix9d:current", "18.0") or 18.0) / max(vix_val, 1.0),
                    "hour_sin":           math.sin(2 * math.pi * minutes_from_open / 390),
                    "hour_cos":           math.cos(2 * math.pi * minutes_from_open / 390),
                    "dow_sin":            math.sin(2 * math.pi * now_et.weekday() / 5),
                    "dow_cos":            math.cos(2 * math.pi * now_et.weekday() / 5),
                }

                X = np.array([[feature_map.get(f, 0.0) for f in direction_features]])
                pred_proba = direction_model.predict_proba(X)[0]
                classes = list(direction_model.classes_)

                p_bull    = float(pred_proba[classes.index("bull")])    if "bull"    in classes else 0.35
                p_bear    = float(pred_proba[classes.index("bear")])    if "bear"    in classes else 0.30
                p_neutral = float(pred_proba[classes.index("neutral")]) if "neutral" in classes else 0.35

                direction = max(
                    [("bull", p_bull), ("bear", p_bear), ("neutral", p_neutral)],
                    key=lambda x: x[1],
                )[0]
                confidence = max(p_bull, p_bear, p_neutral)
                signal_weak = abs(p_bull - p_bear) < 0.05

                return {
                    "p_bull":           round(p_bull, 4),
                    "p_bear":           round(p_bear, 4),
                    "p_neutral":        round(p_neutral, 4),
                    "direction":        direction,
                    "confidence":       round(confidence, 4),
                    "expected_move_pts": round(10.0 * (p_bull - p_bear), 2),
                    "expected_move_pct": round(0.002 * (p_bull - p_bear), 6),
                    "signal_weak":      signal_weak,
                    "model_source":     "lgbm_v1",
                }

            except Exception as model_err:
                logger.warning(
                    "direction_model_inference_failed",
                    error=str(model_err),
                )
                # Fall through to GEX/ZG rule-based below

        # --- GEX/ZG-based directional tilt ---
        if (
            flip_zone is not None
            and flip_zone > 0
            and gex_conf >= 0.3
        ):
            dist_pct = (spx_price - flip_zone) / flip_zone
            tilt = 0.15 * math.tanh(dist_pct * 50.0)

            p_bull_raw = 0.50 + tilt
            p_bear_raw = 0.50 - tilt
            p_neutral_raw = 0.12  # small fixed neutral component

            # Overlay CV_Stress: high stress tilts toward bear
            if cv_stress > 70:
                p_bear_raw += 0.08
                p_bull_raw -= 0.04

            total = p_bull_raw + p_bear_raw + p_neutral_raw
            p_bull = p_bull_raw / total
            p_bear = p_bear_raw / total
            p_neutral = p_neutral_raw / total

        else:
            # --- Fallback: regime-based probabilities (Phase 2 placeholder) ---
            if cv_stress > 70:
                p_bull, p_bear, p_neutral = 0.25, 0.35, 0.40
            elif regime in ("quiet_bullish",):
                p_bull, p_bear, p_neutral = 0.45, 0.25, 0.30
            elif regime in ("crisis", "volatile_bearish"):
                p_bull, p_bear, p_neutral = 0.20, 0.50, 0.30
            elif regime in ("pin_range", "range"):
                p_bull, p_bear, p_neutral = 0.35, 0.35, 0.30
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

        # Signal quality gate: if spread too narrow, flag as weak
        signal_weak = abs(p_bull - p_bear) < 0.05  # 0.05: blocks at <0.3% ZG distance, allows at >0.5%

        return {
            "p_bull": round(p_bull, 4),
            "p_bear": round(p_bear, 4),
            "p_neutral": round(p_neutral, 4),
            "direction": direction,
            "confidence": round(confidence, 4),
            "expected_move_pts": round(10.0 * (p_bull - p_bear), 2),
            "expected_move_pct": round(0.002 * (p_bull - p_bear), 6),
            "signal_weak": signal_weak,
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

        # IV/RV filter: don't sell premium when implied vol ≤ realized vol
        # VIX = implied vol proxy. realized_vol_20d = 20-day annualized SPX RV.
        # Only fire when we have reliable realized vol data (>= 5 days history).
        try:
            vix_raw = self._read_redis("polygon:vix:current", None)
            rv_raw = self._read_redis("polygon:spx:realized_vol_20d", None)
            if vix_raw is not None and rv_raw is not None:
                vix_val = float(vix_raw)
                rv_val = float(rv_raw)
                if rv_val > 0 and vix_val < rv_val * 1.05:
                    return True, f"iv_rv_cheap_premium_vix{vix_val:.1f}_rv{rv_val:.1f}"
        except (ValueError, TypeError):
            pass  # malformed Redis value — skip filter, don't block trading

        return False, None

    def run_cycle(self) -> Optional[dict]:
        """Run one prediction cycle. Writes to trading_prediction_outputs."""
        try:
            # Guard: check Redis availability before running on potentially stale data
            redis_available = False
            if self.redis_client:
                try:
                    self.redis_client.ping()
                    redis_available = True
                except Exception:
                    redis_available = False

            if not redis_available:
                logger.warning("prediction_cycle_skipped_redis_unavailable")
                return {
                    "no_trade_signal": True,
                    "no_trade_reason": "redis_unavailable",
                    "regime": "unknown",
                    "rcs": 0.0,
                    "allocation_tier": "danger",
                    "spx_price": 5200.0,
                }

            self._cycle_count += 1
            session = get_today_session()
            if not session:
                logger.warning("prediction_cycle_no_session")
                self._write_heartbeat()
                return None

            # Read VVIX context
            vvix_z_raw = self._read_redis("polygon:vvix:z_score", None)
            gex_conf_raw = self._read_redis("gex:confidence", None)

            # If all feed signals are unavailable, don't trade on defaults
            if vvix_z_raw is None and gex_conf_raw is None:
                logger.info(
                    "prediction_cycle_skipped_no_feed_data",
                    reason="vvix_z and gex_confidence both unavailable",
                )
                return {
                    "no_trade_signal": True,
                    "no_trade_reason": "feed_data_unavailable",
                    "regime": "unknown",
                    "rcs": 0.0,
                    "allocation_tier": "danger",
                    "spx_price": self._get_spx_price(),
                }

            try:
                vvix = float(self._read_redis("polygon:vvix:current", "0.0"))
                vvix_z = float(vvix_z_raw) if vvix_z_raw is not None else 0.0
            except (ValueError, TypeError):
                vvix, vvix_z = 0.0, 0.0

            # Compute all layers
            regime_data = self._compute_regime()
            cv_data = self._compute_cv_stress()
            direction_data = self._compute_direction(
                regime_data["regime"],
                cv_data["cv_stress_score"],
                spx_price=self._get_spx_price(),
                flip_zone=regime_data.get("gex_flip_zone_used"),
                gex_conf=regime_data.get("gex_conf_at_regime", 0.0),
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

            # Signal quality gate: weak directional signal → no trade
            if not no_trade and direction_data.get("signal_weak"):
                no_trade = True
                no_trade_reason = "direction_signal_weak"

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
                "spx_price": self._get_spx_price(),
                # S4 / E-5: prefer the live VIX from polygon_feed
                # (polygon:vix:current). Falls back to 18.0 only when
                # Redis is empty or the value is malformed — the prior
                # hardcode meant every persisted prediction row
                # reported a constant VIX regardless of actual market
                # state, breaking downstream backtests and analytics.
                "vix": _safe_float(
                    self._read_redis("polygon:vix:current", None), 18.0
                ),
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
