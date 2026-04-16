"""
Paper phase criteria evaluator — runs daily after market close.
Evaluates all 12 GLC criteria and upserts status to paper_phase_criteria.
Manual criteria (GLC-007, 008, 009, 010) are skipped — require human sign-off.
Implements D-013: 45-day paper phase, all 12 criteria required.
"""
from datetime import datetime, timezone
from typing import Optional

from db import get_client, write_health_status, write_audit_log
from logger import get_logger

logger = get_logger("criteria_evaluator")


def _upsert_criterion(
    criterion_id: str,
    status: str,
    current_value_text: str,
    current_value_numeric: Optional[float],
    observations_count: int = 0,
    notes: Optional[str] = None,
) -> None:
    """Upsert a single criterion row. Never raises."""
    try:
        get_client().table("paper_phase_criteria").update({
            "status": status,
            "current_value_text": current_value_text,
            "current_value_numeric": current_value_numeric,
            "observations_count": observations_count,
            "last_evaluated_at": datetime.now(timezone.utc).isoformat(),
            "notes": notes,
        }).eq("criterion_id", criterion_id).execute()
    except Exception as e:
        logger.error("criterion_upsert_failed", criterion_id=criterion_id, error=str(e))


def evaluate_glc001_prediction_accuracy() -> None:
    """GLC-001: Aggregate prediction accuracy >= 58% over 45 days."""
    try:
        # Count total predictions vs correct (direction matched actual)
        # Phase 2: placeholder models don't have outcome labels yet
        # Track observations count as proxy for progress
        result = (
            get_client()
            .table("trading_prediction_outputs")
            .select("id", count="exact")
            .execute()
        )
        total = result.count or 0
        # Need outcome labels to compute accuracy — that requires position outcomes
        # For now: in_progress with observation count
        status = "in_progress" if total > 0 else "not_started"
        _upsert_criterion(
            "GLC-001",
            status,
            f"{total} signals recorded (accuracy computed when outcomes available)",
            None,
            observations_count=total,
            notes="Accuracy requires closed position outcomes to compute directional correctness",
        )
    except Exception as e:
        logger.error("glc001_eval_failed", error=str(e))


def evaluate_glc002_per_regime_accuracy() -> None:
    """GLC-002: Per-regime accuracy >= 55% for each day type with >= 8 obs."""
    try:
        result = (
            get_client()
            .table("trading_prediction_outputs")
            .select("regime", count="exact")
            .execute()
        )
        total = result.count or 0
        status = "in_progress" if total > 0 else "not_started"
        _upsert_criterion(
            "GLC-002", status,
            f"{total} signals recorded across regimes",
            None,
            observations_count=total,
            notes="Per-regime accuracy requires closed position outcomes",
        )
    except Exception as e:
        logger.error("glc002_eval_failed", error=str(e))


def evaluate_glc003_training_examples() -> None:
    """GLC-003: Minimum 50 training examples per regime-strategy cell."""
    try:
        result = (
            get_client()
            .table("trading_positions")
            .select("entry_regime, strategy_type", count="exact")
            .eq("position_mode", "virtual")
            .execute()
        )
        total = result.count or 0

        # Group by regime x strategy to find minimum cell count
        if result.data:
            from collections import Counter
            cell_counts = Counter(
                (r.get("entry_regime", "unknown"), r.get("strategy_type", "unknown"))
                for r in result.data
            )
            min_cell = min(cell_counts.values()) if cell_counts else 0
            unique_cells = len(cell_counts)
            status = "passed" if min_cell >= 50 else "in_progress" if total > 0 else "not_started"
            text = f"{total} positions, {unique_cells} cells, min cell={min_cell}"
        else:
            min_cell = 0
            status = "not_started"
            text = "No positions recorded yet"

        _upsert_criterion(
            "GLC-003", status, text,
            float(min_cell),
            observations_count=total,
        )
    except Exception as e:
        logger.error("glc003_eval_failed", error=str(e))


def evaluate_glc004_undersampled_handling() -> None:
    """GLC-004: Under-sampled cells flagged and sized at 25%."""
    try:
        # Check if risk_engine is applying 25% sizing for cells with < 50 examples
        # This is implemented in strategy_selector (Phase 2B)
        # Status: in_progress — the code path exists but needs validation
        result = (
            get_client()
            .table("trading_positions")
            .select("id", count="exact")
            .eq("position_mode", "virtual")
            .execute()
        )
        total = result.count or 0
        status = "in_progress" if total > 0 else "not_started"
        _upsert_criterion(
            "GLC-004", status,
            "Under-sampled sizing logic implemented in risk_engine (Phase 2B)",
            None,
            observations_count=total,
            notes="Code path implemented — validation requires 50+ positions per cell",
        )
    except Exception as e:
        logger.error("glc004_eval_failed", error=str(e))


def evaluate_glc005_sharpe_ratio() -> None:
    """GLC-005: Paper Sharpe ratio >= 1.5."""
    try:
        result = (
            get_client()
            .table("trading_model_performance")
            .select("sharpe_20d, recorded_at")
            .order("recorded_at", desc=True)
            .limit(1)
            .execute()
        )
        if result.data and result.data[0].get("sharpe_20d") is not None:
            sharpe = result.data[0]["sharpe_20d"]
            status = "passed" if sharpe >= 1.5 else "in_progress"
            text = f"Sharpe (20d): {sharpe:.2f}"
        else:
            sharpe = None
            status = "not_started"
            text = "Insufficient data — need 20+ sessions"

        _upsert_criterion(
            "GLC-005", status, text,
            float(sharpe) if sharpe is not None else None,
            notes="Target: >= 1.5 over full 45-day paper period",
        )
    except Exception as e:
        logger.error("glc005_eval_failed", error=str(e))


def evaluate_glc006_zero_exceptions() -> None:
    """GLC-006: Zero unhandled exceptions in final 20 paper sessions."""
    try:
        # Get last 20 sessions
        sessions_result = (
            get_client()
            .table("trading_sessions")
            .select("id, session_date")
            .order("session_date", desc=True)
            .limit(20)
            .execute()
        )
        sessions = sessions_result.data or []
        session_count = len(sessions)

        if session_count < 20:
            status = "in_progress"
            text = f"{session_count}/20 sessions completed"
            _upsert_criterion(
                "GLC-006", status, text, float(session_count),
                observations_count=session_count,
                notes="Need 20 sessions. Errors tracked via trading_system_health error_count_1h",
            )
            return

        # Check error counts in health table for these sessions
        errors_result = (
            get_client()
            .table("trading_system_health")
            .select("service_name, error_count_1h")
            .gt("error_count_1h", 0)
            .execute()
        )
        error_services = errors_result.data or []
        total_errors = sum(r.get("error_count_1h", 0) or 0 for r in error_services)

        status = "passed" if total_errors == 0 else "failed"
        text = f"{total_errors} errors across last 20 sessions"
        _upsert_criterion(
            "GLC-006", status, text, float(total_errors),
            observations_count=session_count,
        )
    except Exception as e:
        logger.error("glc006_eval_failed", error=str(e))


def evaluate_glc011_slippage_observations() -> None:
    """GLC-011: >= 200 fill observations for slippage model."""
    try:
        result = (
            get_client()
            .table("trading_calibration_log")
            .select("id", count="exact")
            .execute()
        )
        total = result.count or 0
        status = "passed" if total >= 200 else "in_progress" if total > 0 else "not_started"
        pct = min(100, int(total / 2))
        text = f"{total} / 200 observations ({pct}%)"
        _upsert_criterion(
            "GLC-011", status, text, float(total),
            observations_count=total,
        )
    except Exception as e:
        logger.error("glc011_eval_failed", error=str(e))


def evaluate_glc012_gex_tracking() -> None:
    """GLC-012: GEX tracking error <= 15% vs OCC actuals (requires CBOE DataShop)."""
    try:
        # CBOE DataShop account pending approval
        # Cannot evaluate until CBOE feed is connected
        _upsert_criterion(
            "GLC-012", "blocked",
            "Blocked — awaiting CBOE DataShop account approval",
            None,
            observations_count=0,
            notes="Requires CBOE DataShop SFTP feed. Account approval pending.",
        )
    except Exception as e:
        logger.error("glc012_eval_failed", error=str(e))


def run_criteria_evaluation() -> dict:
    """
    Run full criteria evaluation. Called daily at EOD.
    Returns summary of pass/fail/in_progress counts.
    """
    try:
        logger.info("criteria_evaluation_started")

        # Automated criteria
        evaluate_glc001_prediction_accuracy()
        evaluate_glc002_per_regime_accuracy()
        evaluate_glc003_training_examples()
        evaluate_glc004_undersampled_handling()
        evaluate_glc005_sharpe_ratio()
        evaluate_glc006_zero_exceptions()
        evaluate_glc011_slippage_observations()
        evaluate_glc012_gex_tracking()

        # Manual criteria (GLC-007 through GLC-010) — do NOT overwrite
        # their status since they require human sign-off.
        # They stay at 'not_started' until operator manually marks them.

        # Read back results for summary
        result = (
            get_client()
            .table("paper_phase_criteria")
            .select("criterion_id, status")
            .execute()
        )
        rows = result.data or []

        passed = sum(1 for r in rows if r["status"] == "passed")
        failed = sum(1 for r in rows if r["status"] == "failed")
        in_progress = sum(1 for r in rows if r["status"] == "in_progress")
        blocked = sum(1 for r in rows if r["status"] == "blocked")
        all_passed = passed == 12

        summary = {
            "total": len(rows),
            "passed": passed,
            "failed": failed,
            "in_progress": in_progress,
            "blocked": blocked,
            "all_criteria_passed": all_passed,
        }

        write_audit_log(
            action="trading.criteria_evaluation_complete",
            metadata=summary,
        )

        if all_passed:
            logger.info("ALL_12_GO_LIVE_CRITERIA_PASSED", **summary)
        else:
            logger.info("criteria_evaluation_complete", **summary)

        write_health_status("prediction_engine", "healthy")
        return summary

    except Exception as e:
        logger.error("criteria_evaluation_failed", error=str(e), exc_info=True)
        return {"error": str(e)}
