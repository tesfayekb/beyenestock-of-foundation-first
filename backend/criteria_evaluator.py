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
        get_client().table("paper_phase_criteria").upsert({
            "criterion_id": criterion_id,
            "status": status,
            "current_value_text": current_value_text,
            "current_value_numeric": current_value_numeric,
            "observations_count": observations_count,
            "last_evaluated_at": datetime.now(timezone.utc).isoformat(),
            "notes": notes,
        }, on_conflict="criterion_id").execute()
    except Exception as e:
        logger.error("criterion_upsert_failed", criterion_id=criterion_id, error=str(e))


def evaluate_glc001_prediction_accuracy() -> None:
    """
    GLC-001: Aggregate directional accuracy >= 58% over 45 days.
    Uses outcome_correct column populated by label_prediction_outcomes().
    Requires >= 50 labeled predictions before computing accuracy.
    Falls back to in_progress with observation count if no labels yet.
    """
    try:
        from datetime import date, timedelta
        cutoff = (date.today() - timedelta(days=45)).isoformat()

        # Count total labeled predictions (outcome_correct IS NOT NULL)
        labeled_result = (
            get_client()
            .table("trading_prediction_outputs")
            .select("id", count="exact")
            .eq("no_trade_signal", False)
            .gte("predicted_at", cutoff)
            .not_.is_("outcome_correct", "null")
            .execute()
        )
        total_labeled = labeled_result.count or 0

        if total_labeled < 50:
            # Not enough labels yet — report progress
            total_result = (
                get_client()
                .table("trading_prediction_outputs")
                .select("id", count="exact")
                .eq("no_trade_signal", False)
                .gte("predicted_at", cutoff)
                .execute()
            )
            total_signals = total_result.count or 0
            _upsert_criterion(
                "GLC-001",
                "in_progress",
                f"{total_labeled} labeled predictions ({total_signals} signals total, need 50)",
                float(total_labeled),
                observations_count=total_labeled,
                notes=f"Need 50 labeled predictions. {total_signals} signals recorded, "
                      f"{total_labeled} have outcome labels from label_prediction_outcomes().",
            )
            return

        # Count correct predictions
        correct_result = (
            get_client()
            .table("trading_prediction_outputs")
            .select("id", count="exact")
            .eq("no_trade_signal", False)
            .eq("outcome_correct", True)
            .gte("predicted_at", cutoff)
            .execute()
        )
        correct = correct_result.count or 0
        accuracy = correct / total_labeled if total_labeled > 0 else 0.0

        TARGET = 0.58
        status = "passed" if accuracy >= TARGET else (
            "failed" if total_labeled >= 100 else "in_progress"
        )

        _upsert_criterion(
            "GLC-001",
            status,
            f"{accuracy:.1%} directional accuracy ({correct}/{total_labeled} correct)",
            round(accuracy, 4),
            observations_count=total_labeled,
            notes=f"Target: {TARGET:.0%}. Based on real SPX direction 30min after signal.",
        )
    except Exception as e:
        logger.error("glc001_eval_failed", error=str(e))


def evaluate_glc002_per_regime_accuracy() -> None:
    """
    GLC-002: Per-regime directional accuracy >= 55% for regimes with >= 8 observations.
    Uses outcome_correct column. Requires >= 8 labeled predictions per regime.
    """
    try:
        from datetime import date, timedelta
        cutoff = (date.today() - timedelta(days=45)).isoformat()

        # Fetch all labeled predictions with regime
        result = (
            get_client()
            .table("trading_prediction_outputs")
            .select("regime, outcome_correct")
            .eq("no_trade_signal", False)
            .gte("predicted_at", cutoff)
            .not_.is_("outcome_correct", "null")
            .execute()
        )
        predictions = result.data or []
        total_labeled = len(predictions)

        if total_labeled < 8:
            _upsert_criterion(
                "GLC-002",
                "in_progress",
                f"{total_labeled} labeled predictions across regimes (need 8 per regime)",
                float(total_labeled),
                observations_count=total_labeled,
                notes="Need >= 8 labeled predictions per regime for per-regime accuracy.",
            )
            return

        # Group by regime
        from collections import defaultdict
        regime_stats: dict = defaultdict(lambda: {"correct": 0, "total": 0})
        for pred in predictions:
            regime = pred.get("regime") or "unknown"
            regime_stats[regime]["total"] += 1
            if pred.get("outcome_correct") is True:
                regime_stats[regime]["correct"] += 1

        TARGET_ACC = 0.55
        TARGET_OBS = 8
        regime_results = {}
        all_pass = True

        for regime, stats in regime_stats.items():
            if stats["total"] < TARGET_OBS:
                regime_results[regime] = {
                    "accuracy": None,
                    "observations": stats["total"],
                    "status": "insufficient_data",
                }
                continue

            acc = stats["correct"] / stats["total"]
            passing = acc >= TARGET_ACC
            if not passing:
                all_pass = False
            regime_results[regime] = {
                "accuracy": round(acc, 4),
                "observations": stats["total"],
                "status": "passed" if passing else "failed",
            }

        # Determine overall status
        regimes_with_data = [r for r in regime_results.values()
                             if r["status"] != "insufficient_data"]
        if not regimes_with_data:
            overall_status = "in_progress"
        elif all(r["status"] == "passed" for r in regimes_with_data):
            overall_status = "passed"
        elif any(r["status"] == "failed" for r in regimes_with_data):
            overall_status = "failed"
        else:
            overall_status = "in_progress"

        passing_regimes = sum(
            1 for r in regimes_with_data if r["status"] == "passed"
        )
        total_regimes = len(regimes_with_data)
        avg_accuracy = (
            sum(r["accuracy"] for r in regimes_with_data if r["accuracy"])
            / total_regimes
        ) if total_regimes > 0 else 0.0

        _upsert_criterion(
            "GLC-002",
            overall_status,
            f"{passing_regimes}/{total_regimes} regimes passing "
            f"(avg accuracy {avg_accuracy:.1%})",
            round(avg_accuracy, 4),
            observations_count=total_labeled,
            notes=str({k: v for k, v in regime_results.items()}),
        )
    except Exception as e:
        logger.error("glc002_eval_failed", error=str(e))


def evaluate_glc003_training_examples() -> None:
    """GLC-003: Minimum 50 training examples per regime-strategy cell."""
    try:
        # Use Postgres aggregation instead of Python-side Counter
        result = (
            get_client()
            .table("trading_positions")
            .select("entry_regime, strategy_type, id", count="exact")
            .eq("position_mode", "virtual")
            .eq("status", "closed")
            .execute()
        )
        total = result.count or 0

        if not result.data:
            _upsert_criterion(
                "GLC-003", "not_started",
                "No closed positions recorded yet",
                0.0,
                observations_count=0,
            )
            return

        # Group by regime x strategy in Python (Supabase REST doesn't support GROUP BY)
        # but only compute min cell — O(n) is acceptable for criteria evaluation
        from collections import defaultdict
        cell_counts: dict = defaultdict(int)
        for row in result.data:
            regime = row.get("entry_regime") or "unknown"
            strategy = row.get("strategy_type") or "unknown"
            cell_counts[(regime, strategy)] += 1

        min_cell = min(cell_counts.values()) if cell_counts else 0
        unique_cells = len(cell_counts)
        status = (
            "passed" if min_cell >= 50
            else "in_progress" if total > 0
            else "not_started"
        )
        text = f"{total} positions, {unique_cells} cells, min cell={min_cell}"

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
    """
    GLC-006: Zero unhandled exceptions in final 20 paper sessions.
    Uses session_error_snapshot audit entries written at EOD close.
    These snapshots capture the error counts at the moment of session close,
    scoped to each session — not the rolling 1-hour window.
    """
    try:
        from datetime import date, timedelta

        # Count total completed sessions first
        sessions_result = (
            get_client()
            .table("trading_sessions")
            .select("id, session_date")
            .eq("session_status", "closed")
            .order("session_date", desc=True)
            .limit(20)
            .execute()
        )
        sessions = sessions_result.data or []
        session_count = len(sessions)

        if session_count < 20:
            _upsert_criterion(
                "GLC-006",
                "in_progress",
                f"{session_count}/20 sessions completed",
                float(session_count),
                observations_count=session_count,
                notes="Counting completed sessions. Error snapshots recorded at EOD close.",
            )
            return

        # Query error snapshots for the last 20 sessions
        cutoff = (date.today() - timedelta(days=30)).isoformat()
        snapshots_result = (
            get_client()
            .table("audit_logs")
            .select("metadata, created_at")
            .eq("action", "trading.session_error_snapshot")
            .gte("created_at", cutoff)
            .order("created_at", desc=True)
            .limit(20)
            .execute()
        )
        snapshots = snapshots_result.data or []

        if not snapshots:
            # No snapshots yet — fall back to current health table
            errors_result = (
                get_client()
                .table("trading_system_health")
                .select("error_count_1h")
                .gt("error_count_1h", 0)
                .execute()
            )
            total_errors = sum(
                r.get("error_count_1h", 0) or 0
                for r in (errors_result.data or [])
            )
        else:
            total_errors = sum(
                (snap.get("metadata") or {}).get("total_errors", 0) or 0
                for snap in snapshots
            )

        status = "passed" if total_errors == 0 else "failed"
        text = f"{total_errors} errors in last {session_count} sessions"
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

        # Reset error_count_1h at EOD after GLC-006 has read it
        try:
            get_client().table("trading_system_health").update(
                {"error_count_1h": 0}
            ).neq("service_name", "").execute()
        except Exception as e:
            logger.warning("error_count_reset_failed", error=str(e))

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
