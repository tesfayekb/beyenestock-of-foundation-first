"""
Model retraining — weekly regime model performance + drift detection.
TPLAN-PAPER-004-F: Champion/challenger infrastructure.
Computes directional accuracy from closed positions vs predictions.
Triggers drift alert when accuracy drops below threshold.
"""
from datetime import datetime, timezone, date, timedelta
from typing import Optional
from collections import defaultdict

from db import get_client, write_health_status, write_audit_log
from logger import get_logger

logger = get_logger("model_retraining")

DRIFT_THRESHOLD = 0.50    # Below 50% accuracy triggers drift warning
RETRAIN_THRESHOLD = 0.45  # Below 45% triggers critical drift


def compute_directional_accuracy(days: int = 20) -> dict:
    """
    Compute directional prediction accuracy over the last N days.
    Accuracy = % of predictions where direction matched position outcome.
    Proxy: bull prediction + win = correct; bear prediction + win = correct.
    Phase 4B: uses virtual position P&L as outcome proxy.
    """
    try:
        cutoff = (date.today() - timedelta(days=days)).isoformat()
        result = (
            get_client()
            .table("trading_prediction_outputs")
            .select("direction, no_trade_signal, predicted_at, session_id")
            .gte("predicted_at", cutoff)
            .eq("no_trade_signal", False)
            .execute()
        )
        predictions = result.data or []
        n = len(predictions)

        if n < 5:
            return {
                "accuracy": None,
                "observations": n,
                "days": days,
                "sufficient_data": False,
            }

        # Get closed positions in same period
        pos_result = (
            get_client()
            .table("trading_positions")
            .select("net_pnl, entry_regime, strategy_type")
            .gte("entry_at", cutoff)
            .eq("status", "closed")
            .eq("position_mode", "virtual")
            .execute()
        )
        positions = pos_result.data or []
        p = len(positions)

        if p < 3:
            return {
                "accuracy": None,
                "observations": n,
                "positions": p,
                "days": days,
                "sufficient_data": False,
            }

        # Simple proxy: win rate as accuracy proxy
        wins = sum(1 for pos in positions if (pos.get("net_pnl") or 0) > 0)
        win_rate = wins / p if p > 0 else 0

        return {
            "accuracy": round(win_rate, 4),
            "observations": p,
            "days": days,
            "sufficient_data": True,
        }
    except Exception as e:
        logger.error("accuracy_compute_failed", days=days, error=str(e))
        return {
            "accuracy": None,
            "observations": 0,
            "days": days,
            "sufficient_data": False,
        }


def compute_per_regime_accuracy() -> dict:
    """
    Compute accuracy broken down by regime.
    Returns dict mapping regime -> {accuracy, count}.
    Needed for GLC-002.
    """
    try:
        result = (
            get_client()
            .table("trading_positions")
            .select("entry_regime, net_pnl")
            .eq("status", "closed")
            .eq("position_mode", "virtual")
            .execute()
        )
        positions = result.data or []

        regime_stats = defaultdict(lambda: {"wins": 0, "total": 0})
        for pos in positions:
            regime = pos.get("entry_regime") or "unknown"
            regime_stats[regime]["total"] += 1
            if (pos.get("net_pnl") or 0) > 0:
                regime_stats[regime]["wins"] += 1

        regime_accuracy = {}
        for regime, stats in regime_stats.items():
            if stats["total"] >= 3:
                regime_accuracy[regime] = {
                    "accuracy": round(stats["wins"] / stats["total"], 4),
                    "observations": stats["total"],
                    "meets_glc002": (
                        stats["total"] >= 8
                        and (stats["wins"] / stats["total"]) >= 0.55
                    ),
                }

        return regime_accuracy
    except Exception as e:
        logger.error("regime_accuracy_failed", error=str(e))
        return {}


def detect_drift(
    accuracy_5d: Optional[float], accuracy_20d: Optional[float]
) -> dict:
    """
    Detect model drift by comparing short vs long window accuracy.
    D-016: drift alert when 5d accuracy drops > 8pp below 20d baseline.
    """
    if accuracy_5d is None or accuracy_20d is None:
        return {"drift_status": "unknown", "drift_z_score": None}

    gap = accuracy_20d - accuracy_5d
    # Normalize to a simple z-score proxy (gap / 0.05 as stddev estimate)
    z_score = round(gap / 0.05, 2) if gap > 0 else 0.0

    if accuracy_5d < RETRAIN_THRESHOLD:
        status = "critical"
    elif accuracy_5d < DRIFT_THRESHOLD or gap > 0.08:
        status = "warning"
    else:
        status = "ok"

    if status != "ok":
        write_audit_log(
            action="trading.model_drift_detected",
            metadata={
                "drift_status": status,
                "accuracy_5d": accuracy_5d,
                "accuracy_20d": accuracy_20d,
                "gap": round(gap, 4),
                "drift_z_score": z_score,
            },
        )
        logger.warning(
            "model_drift_detected",
            status=status,
            accuracy_5d=accuracy_5d,
            accuracy_20d=accuracy_20d,
        )

    return {"drift_status": status, "drift_z_score": z_score}


def compute_sharpe_ratio(days: int = 20) -> Optional[float]:
    """
    Compute annualized Sharpe ratio from virtual session P&L.
    Target: >= 1.5 (GLC-005).
    """
    try:
        cutoff = (date.today() - timedelta(days=days)).isoformat()
        result = (
            get_client()
            .table("trading_sessions")
            .select("virtual_pnl, session_date")
            .gte("session_date", cutoff)
            .not_.is_("virtual_pnl", "null")
            .order("session_date")
            .execute()
        )
        sessions = result.data or []
        pnls = [
            s["virtual_pnl"]
            for s in sessions
            if s.get("virtual_pnl") is not None
        ]

        if len(pnls) < 5:
            return None

        import statistics
        mean_pnl = statistics.mean(pnls)
        std_pnl = statistics.stdev(pnls) if len(pnls) > 1 else 0.0001
        if std_pnl == 0:
            return None

        # Annualize: ~252 trading days
        sharpe = (mean_pnl / std_pnl) * (252 ** 0.5)
        return round(sharpe, 3)
    except Exception as e:
        logger.error("sharpe_compute_failed", error=str(e))
        return None


def compute_profit_factor(days: int = 20) -> Optional[float]:
    """Gross profit / gross loss from closed positions."""
    try:
        cutoff = (date.today() - timedelta(days=days)).isoformat()
        result = (
            get_client()
            .table("trading_positions")
            .select("gross_pnl")
            .gte("entry_at", cutoff)
            .eq("status", "closed")
            .eq("position_mode", "virtual")
            .execute()
        )
        positions = result.data or []
        if len(positions) < 3:
            return None

        gross_profit = sum(
            p["gross_pnl"]
            for p in positions
            if (p.get("gross_pnl") or 0) > 0
        )
        gross_loss = abs(sum(
            p["gross_pnl"]
            for p in positions
            if (p.get("gross_pnl") or 0) < 0
        ))

        if gross_loss == 0:
            return None
        return round(gross_profit / gross_loss, 3)
    except Exception as e:
        logger.error("profit_factor_failed", error=str(e))
        return None


def count_preservation_triggers_this_week() -> int:
    """Count capital preservation audit events this week."""
    try:
        week_start = (
            date.today() - timedelta(days=date.today().weekday())
        ).isoformat()
        result = (
            get_client()
            .table("audit_logs")
            .select("id", count="exact")
            .eq("action", "trading.capital_preservation_triggered")
            .gte("created_at", week_start)
            .execute()
        )
        return result.count or 0
    except Exception:
        return 0


def run_weekly_model_performance() -> dict:
    """
    Run full weekly model performance computation.
    Updates trading_model_performance with accuracy, drift, Sharpe,
    profit factor. Never raises.
    """
    try:
        logger.info("weekly_model_performance_started")

        acc_5d = compute_directional_accuracy(days=5)
        acc_20d = compute_directional_accuracy(days=20)
        acc_60d = compute_directional_accuracy(days=60)
        regime_acc = compute_per_regime_accuracy()
        drift = detect_drift(acc_5d.get("accuracy"), acc_20d.get("accuracy"))
        sharpe = compute_sharpe_ratio(days=20)
        profit_factor = compute_profit_factor(days=20)
        preservation_count = count_preservation_triggers_this_week()

        def regime_acc_val(regime_key):
            data = regime_acc.get(regime_key, {})
            return (
                data.get("accuracy")
                if data.get("observations", 0) >= 8
                else None
            )

        payload = {
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "accuracy_5d": acc_5d.get("accuracy"),
            "accuracy_20d": acc_20d.get("accuracy"),
            "accuracy_60d": acc_60d.get("accuracy"),
            "accuracy_range_day": (
                regime_acc_val("pin_range") or regime_acc_val("range")
            ),
            "accuracy_trend_day": regime_acc_val("trend"),
            "accuracy_reversal_day": regime_acc_val("volatile_bearish"),
            "accuracy_event_day": regime_acc_val("event"),
            "drift_status": drift["drift_status"],
            "drift_z_score": drift["drift_z_score"],
            "sharpe_20d": sharpe,
            "profit_factor_20d": profit_factor,
            "preservation_triggers_this_week": preservation_count,
            "samples_since_retrain": acc_20d.get("observations", 0),
            "challenger_active": False,  # Phase 4B: no challenger yet
        }

        get_client().table("trading_model_performance").insert(payload).execute()

        summary = {
            "accuracy_5d": acc_5d.get("accuracy"),
            "accuracy_20d": acc_20d.get("accuracy"),
            "drift_status": drift["drift_status"],
            "sharpe_20d": sharpe,
            "profit_factor_20d": profit_factor,
        }

        write_audit_log(
            action="trading.weekly_model_performance_complete",
            metadata=summary,
        )
        logger.info("weekly_model_performance_complete", **summary)
        write_health_status("prediction_engine", "healthy")
        return summary

    except Exception as e:
        logger.error(
            "weekly_model_performance_failed", error=str(e), exc_info=True
        )
        return {"error": str(e)}
