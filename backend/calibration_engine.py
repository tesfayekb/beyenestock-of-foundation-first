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
        result = (
            get_client()
            .table("trading_calibration_log")
            .select("predicted_slippage, actual_slippage")
            .not_.is_("predicted_slippage", "null")
            .not_.is_("actual_slippage", "null")
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
                .maybeSingle()
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
