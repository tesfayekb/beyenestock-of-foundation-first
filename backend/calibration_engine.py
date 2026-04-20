"""
Calibration engine — weekly model calibration.
TPLAN-PAPER-004-B: Predictive slippage model (LightGBM, needs >= 200 observations)
TPLAN-PAPER-004-C: CV_Stress CWER calibration
TPLAN-PAPER-004-D: Touch probability Brier score calibration
Writes results to trading_model_performance.
"""
from datetime import datetime, timezone, date, timedelta
from typing import Optional

from db import get_client, write_health_status, write_audit_log
from logger import get_logger

logger = get_logger("calibration_engine")

MIN_SLIPPAGE_OBS = 200   # GLC-011 target
MIN_TOUCH_OBS = 50       # Minimum for Brier score
MIN_CVSTRESS_OBS = 20    # Minimum for CWER


def compute_slippage_mae() -> dict:
    """
    Compute Mean Absolute Error between predicted and actual slippage.
    Phase 4B: uses static slippage fallback until >= 200 observations.
    Returns dict with mae, observations, model_ready flag.
    """
    try:
        from datetime import date, timedelta
        cutoff = (date.today() - timedelta(days=90)).isoformat()
        result = (
            get_client()
            .table("trading_calibration_log")
            .select("predicted_slippage, actual_slippage")
            .not_.is_("predicted_slippage", "null")
            .not_.is_("actual_slippage", "null")
            .gte("created_at", cutoff)
            .execute()
        )
        rows = result.data or []
        n = len(rows)

        if n < 5:
            return {"mae": None, "observations": n, "model_ready": False}

        mae = sum(
            abs((r["actual_slippage"] or 0) - (r["predicted_slippage"] or 0))
            for r in rows
        ) / n

        model_ready = n >= MIN_SLIPPAGE_OBS
        logger.info(
            "slippage_mae_computed",
            mae=round(mae, 4),
            observations=n,
            model_ready=model_ready,
        )
        return {
            "mae": round(mae, 4),
            "observations": n,
            "model_ready": model_ready,
        }
    except Exception as e:
        logger.error("slippage_mae_failed", error=str(e))
        return {"mae": None, "observations": 0, "model_ready": False}


def compute_cv_stress_cwer() -> dict:
    """
    CV_Stress CWER: Classification-Weighted Error Rate.
    Measures how often CV_Stress correctly predicts short-gamma exit triggers.
    fn_flag = false negative (CV_Stress low but exit triggered)
    fp_flag = false positive (CV_Stress high but no exit)
    Returns dict with fn_rate, fp_rate, observations.
    """
    try:
        result = (
            get_client()
            .table("trading_calibration_log")
            .select("cv_stress_score, exit_triggered, fn_flag, fp_flag")
            .not_.is_("cv_stress_score", "null")
            .execute()
        )
        rows = result.data or []
        n = len(rows)

        if n < MIN_CVSTRESS_OBS:
            return {
                "fn_rate": None, "fp_rate": None,
                "observations": n,
                "calibrated": False,
            }

        fn = sum(1 for r in rows if r.get("fn_flag") is True)
        fp = sum(1 for r in rows if r.get("fp_flag") is True)
        fn_rate = round(fn / n, 4)
        fp_rate = round(fp / n, 4)

        logger.info(
            "cv_stress_cwer_computed",
            fn_rate=fn_rate,
            fp_rate=fp_rate,
            observations=n,
        )
        return {
            "fn_rate": fn_rate,
            "fp_rate": fp_rate,
            "observations": n,
            "calibrated": True,
        }
    except Exception as e:
        logger.error("cv_stress_cwer_failed", error=str(e))
        return {
            "fn_rate": None, "fp_rate": None,
            "observations": 0, "calibrated": False,
        }


def compute_touch_probability_brier() -> dict:
    """
    Touch probability Brier score.
    Measures calibration of the touch probability model.
    Lower is better (0 = perfect, 1 = worst).
    Phase 4B: placeholder until real touch prob model trained.
    """
    try:
        result = (
            get_client()
            .table("trading_calibration_log")
            .select("put_touched_by_exit, call_touched_by_exit")
            .not_.is_("put_touched_by_exit", "null")
            .execute()
        )
        rows = result.data or []
        n = len(rows)

        if n < MIN_TOUCH_OBS:
            return {"brier_score": None, "observations": n, "calibrated": False}

        # Placeholder touch probability is 0.05 (entry_touch_prob default)
        # Actual outcome: put_touched_by_exit OR call_touched_by_exit
        placeholder_prob = 0.05
        touched = sum(
            1 for r in rows
            if r.get("put_touched_by_exit") or r.get("call_touched_by_exit")
        )
        actual_rate = touched / n
        # Brier score = mean((forecast - outcome)^2)
        brier = sum(
            (
                placeholder_prob
                - (
                    1 if (
                        r.get("put_touched_by_exit")
                        or r.get("call_touched_by_exit")
                    ) else 0
                )
            ) ** 2
            for r in rows
        ) / n

        logger.info(
            "touch_prob_brier_computed",
            brier=round(brier, 4),
            actual_touch_rate=round(actual_rate, 4),
            observations=n,
        )
        return {
            "brier_score": round(brier, 4),
            "actual_touch_rate": round(actual_rate, 4),
            "observations": n,
            "calibrated": True,
        }
    except Exception as e:
        logger.error("touch_brier_failed", error=str(e))
        return {"brier_score": None, "observations": 0, "calibrated": False}


def write_model_performance(
    slippage: dict,
    cv_stress: dict,
    touch: dict,
    session_id: Optional[str] = None,
) -> bool:
    """Write all calibration results to trading_model_performance."""
    try:
        payload = {
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "session_id": session_id,
            "slippage_mae": slippage.get("mae"),
            "slippage_observations": slippage.get("observations", 0),
            "cv_stress_fn_rate": cv_stress.get("fn_rate"),
            "cv_stress_fp_rate": cv_stress.get("fp_rate"),
            "touch_prob_brier": touch.get("brier_score"),
            "touch_prob_observations": touch.get("observations", 0),
            # Accuracy fields filled by model_retraining.py
        }
        get_client().table("trading_model_performance").insert(payload).execute()
        return True
    except Exception as e:
        logger.error("model_performance_write_failed", error=str(e))
        return False


def run_weekly_calibration() -> dict:
    """
    Run full weekly calibration. Called every Sunday at 6 PM ET.
    Returns summary dict. Never raises.
    """
    try:
        logger.info("weekly_calibration_started")

        slippage = compute_slippage_mae()
        cv_stress = compute_cv_stress_cwer()
        touch = compute_touch_probability_brier()

        # Get today's session id if available
        session_id = None
        try:
            s = (
                get_client()
                .table("trading_sessions")
                .select("id")
                .eq("session_date", date.today().isoformat())
                .maybe_single()
                .execute()
            )
            if s.data:
                session_id = s.data["id"]
        except Exception:
            pass

        write_model_performance(slippage, cv_stress, touch, session_id)

        summary = {
            "slippage_mae": slippage.get("mae"),
            "slippage_observations": slippage.get("observations", 0),
            "slippage_model_ready": slippage.get("model_ready", False),
            "cv_stress_calibrated": cv_stress.get("calibrated", False),
            "touch_prob_calibrated": touch.get("calibrated", False),
        }

        write_audit_log(
            action="trading.weekly_calibration_complete",
            metadata=summary,
        )
        logger.info("weekly_calibration_complete", **summary)
        write_health_status("prediction_engine", "healthy")
        return summary

    except Exception as e:
        logger.error("weekly_calibration_failed", error=str(e), exc_info=True)
        return {"error": str(e)}


# 12F: Phase C adaptive halt threshold
#
# Replaces the hardcoded -3% daily halt with a volatility-scaled value
# computed from real trade history. Formula: halt_at = -2.5 * stddev of
# daily P&L (as a fraction of account equity).
#
# Auto-gates on closed_trades >= 100. Below that, the Redis key is not
# written and risk_engine.check_daily_drawdown falls back to -0.03.
_MIN_CLOSED_TRADES_FOR_HALT_CALIBRATION = 100
_MIN_SESSIONS_FOR_HALT_CALIBRATION = 20
_HALT_FLOOR = -0.02   # never looser than -2% (closest to 0)
_HALT_CEILING = -0.05  # never tighter than -5% (most negative)
_HALT_STDDEV_MULTIPLE = 2.5
_HALT_DEFAULT_EQUITY = 100_000.0


def calibrate_halt_threshold(redis_client) -> dict:
    """
    Compute a volatility-scaled daily halt threshold from recent session
    history and write it to risk:halt_threshold_pct. Never raises — any
    error returns a dict with the failure reason and leaves the Redis
    key untouched, which causes risk_engine to fall back to -0.03.
    """
    try:
        import math

        count_result = (
            get_client()
            .table("trading_positions")
            .select("id", count="exact")
            .eq("status", "closed")
            .eq("position_mode", "virtual")
            .execute()
        )
        closed_trades = count_result.count or 0

        if closed_trades < _MIN_CLOSED_TRADES_FOR_HALT_CALIBRATION:
            logger.info(
                "halt_threshold_calibration_skipped",
                closed_trades=closed_trades,
                required=_MIN_CLOSED_TRADES_FOR_HALT_CALIBRATION,
                fallback=-0.03,
            )
            return {
                "calibrated": False,
                "closed_trades": closed_trades,
                "fallback": -0.03,
            }

        cutoff = (date.today() - timedelta(days=90)).isoformat()
        sessions_result = (
            get_client()
            .table("trading_sessions")
            .select("session_date, virtual_pnl")
            .gte("session_date", cutoff)
            .not_.is_("virtual_pnl", "null")
            .order("session_date", desc=False)
            .limit(60)
            .execute()
        )
        sessions = sessions_result.data or []

        if len(sessions) < _MIN_SESSIONS_FOR_HALT_CALIBRATION:
            logger.info(
                "halt_threshold_calibration_skipped_insufficient_sessions",
                session_count=len(sessions),
                required=_MIN_SESSIONS_FOR_HALT_CALIBRATION,
            )
            return {
                "calibrated": False,
                "session_count": len(sessions),
            }

        # Use live equity as the normaliser so stddev is expressed as a
        # fraction of account value (same units as the halt threshold).
        account_equity = _HALT_DEFAULT_EQUITY
        try:
            raw_equity = redis_client.get("capital:live_equity") if redis_client else None
            if raw_equity:
                account_equity = float(raw_equity)
        except Exception:
            account_equity = _HALT_DEFAULT_EQUITY

        daily_pnl_fractions = [
            float(s["virtual_pnl"]) / account_equity
            for s in sessions
            if float(s.get("virtual_pnl") or 0) != 0
        ]

        if len(daily_pnl_fractions) < _MIN_SESSIONS_FOR_HALT_CALIBRATION:
            return {
                "calibrated": False,
                "reason": "insufficient_nonzero_sessions",
                "nonzero_sessions": len(daily_pnl_fractions),
            }

        n = len(daily_pnl_fractions)
        mean_pnl = sum(daily_pnl_fractions) / n
        variance = sum((x - mean_pnl) ** 2 for x in daily_pnl_fractions) / n
        stddev = math.sqrt(variance)

        raw_threshold = -(_HALT_STDDEV_MULTIPLE * stddev)

        # Clamp: never looser than floor (-0.02), never tighter than ceiling (-0.05).
        # Note FLOOR is closer to 0 than CEILING; the max(CEILING, min(FLOOR, x))
        # sandwich handles both boundaries.
        threshold = max(_HALT_CEILING, min(_HALT_FLOOR, raw_threshold))

        floor_applied = raw_threshold > _HALT_FLOOR
        ceiling_applied = raw_threshold < _HALT_CEILING

        if redis_client:
            redis_client.setex(
                "risk:halt_threshold_pct",
                86400 * 8,  # 8 days — survives a weekend without recalibration
                str(round(threshold, 6)),
            )

        logger.info(
            "halt_threshold_calibrated",
            threshold=round(threshold, 4),
            raw_threshold=round(raw_threshold, 4),
            stddev=round(stddev, 4),
            sessions_used=n,
            closed_trades=closed_trades,
            floor_applied=floor_applied,
            ceiling_applied=ceiling_applied,
        )
        return {
            "calibrated": True,
            "threshold": round(threshold, 4),
            "raw_threshold": round(raw_threshold, 4),
            "stddev": round(stddev, 4),
            "sessions_used": n,
            "closed_trades": closed_trades,
            "floor_applied": floor_applied,
            "ceiling_applied": ceiling_applied,
        }

    except Exception as exc:
        logger.error("halt_threshold_calibration_failed", error=str(exc))
        return {"calibrated": False, "error": str(exc)}
