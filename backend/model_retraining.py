"""
Model retraining — weekly regime model performance + drift detection.
TPLAN-PAPER-004-F: Champion/challenger infrastructure.
Computes directional accuracy from closed positions vs predictions.
Triggers drift alert when accuracy drops below threshold.
"""
from datetime import datetime, timezone, date, timedelta
from typing import Optional
from collections import defaultdict

import config
import httpx

from db import get_client, write_health_status, write_audit_log
from logger import get_logger

logger = get_logger("model_retraining")

DRIFT_THRESHOLD = 0.50    # Below 50% accuracy triggers drift warning
RETRAIN_THRESHOLD = 0.45  # Below 45% triggers critical drift


def label_prediction_outcomes(target_date: Optional[date] = None) -> dict:
    """
    Label yesterday's predictions with realized SPX outcomes.
    For each unlabeled prediction:
      1. Read spx_price at prediction time (already stored on the row)
      2. Fetch SPX price 30 minutes later from Polygon historical API
      3. Compute spx_return_30min, outcome_direction, outcome_correct
      4. Write back to trading_prediction_outputs

    Called daily at ~4:15 PM ET, before criteria evaluation.
    Only labels no_trade_signal=False predictions (actual trade signals).
    Never raises — logs errors and returns summary.

    threshold for direction: ±0.10% (1 SPX point ≈ 0.02%)
    """
    if target_date is None:
        target_date = date.today()

    summary = {"labeled": 0, "skipped": 0, "errors": 0, "total": 0}

    try:
        # Fetch unlabeled trade signals for target_date
        day_start = f"{target_date.isoformat()}T00:00:00+00:00"
        day_end = f"{target_date.isoformat()}T23:59:59+00:00"

        result = (
            get_client()
            .table("trading_prediction_outputs")
            .select("id, predicted_at, direction, spx_price")
            .eq("no_trade_signal", False)
            .gte("predicted_at", day_start)
            .lte("predicted_at", day_end)
            .is_("outcome_correct", "null")
            .execute()
        )
        predictions = result.data or []
        summary["total"] = len(predictions)

        if not predictions:
            logger.info("label_outcomes_no_predictions", date=str(target_date))
            return summary

        api_key = config.POLYGON_API_KEY
        if not api_key:
            logger.warning("label_outcomes_no_polygon_key")
            return summary

        headers = {"Authorization": f"Bearer {api_key}"}

        for pred in predictions:
            try:
                predicted_at_str = pred.get("predicted_at", "")
                spx_at_signal = float(pred.get("spx_price") or 0.0)
                pred_direction = pred.get("direction", "neutral")

                if not predicted_at_str or spx_at_signal <= 0:
                    summary["skipped"] += 1
                    continue

                # Parse predicted_at and compute +30 minute window
                from datetime import timezone as tz
                predicted_at_dt = datetime.fromisoformat(
                    predicted_at_str.replace("Z", "+00:00")
                )
                t30 = predicted_at_dt + timedelta(minutes=30)

                # Polygon expects millisecond timestamps
                t30_ms = int(t30.timestamp() * 1000)
                t31_ms = t30_ms + 60_000  # 1-minute window

                # Fetch SPX 1-minute bar at t+30
                url = f"https://api.polygon.io/v2/aggs/ticker/I:SPX/range/1/minute/{t30_ms}/{t31_ms}"
                with httpx.Client(timeout=10.0) as client:
                    resp = client.get(url, headers=headers)

                if resp.status_code != 200:
                    summary["skipped"] += 1
                    continue

                bars = resp.json().get("results", [])
                if not bars:
                    summary["skipped"] += 1
                    continue

                spx_at_t30 = float(bars[0].get("c", 0.0))  # close of that minute
                if spx_at_t30 <= 0:
                    summary["skipped"] += 1
                    continue

                # Compute return and direction
                spx_return = (spx_at_t30 - spx_at_signal) / spx_at_signal
                DIRECTION_THRESHOLD = 0.001  # ±0.1%

                if spx_return > DIRECTION_THRESHOLD:
                    actual_direction = "bull"
                elif spx_return < -DIRECTION_THRESHOLD:
                    actual_direction = "bear"
                else:
                    actual_direction = "neutral"

                is_correct = pred_direction == actual_direction

                # Write outcome labels back
                get_client().table("trading_prediction_outputs").update({
                    "outcome_direction": actual_direction,
                    "outcome_correct": is_correct,
                    "spx_return_30min": round(spx_return, 6),
                }).eq("id", pred["id"]).execute()

                summary["labeled"] += 1

            except Exception as pred_err:
                logger.error(
                    "label_outcome_single_failed",
                    pred_id=pred.get("id"),
                    error=str(pred_err),
                )
                summary["errors"] += 1

        # Warn if Polygon returned no data for all predictions
        # (likely a plan restriction on I:SPX index data)
        if summary["total"] > 0 and summary["labeled"] == 0 and summary["errors"] == 0:
            logger.warning(
                "label_outcomes_all_skipped",
                total=summary["total"],
                hint="Check Polygon plan covers I:SPX index minute aggregates",
            )
        logger.info("label_prediction_outcomes_complete", **summary)
        write_audit_log(
            action="trading.prediction_outcomes_labeled",
            metadata={**summary, "date": str(target_date)},
        )
        return summary

    except Exception as e:
        logger.error("label_prediction_outcomes_failed", error=str(e))
        return {**summary, "errors": summary["errors"] + 1}


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


def get_kelly_multiplier_from_db(days: int = 20) -> float:
    """
    Compute Kelly position size multiplier from recent closed positions.

    Queries last N days of closed virtual positions to get:
    - win_rate: % of trades with net_pnl > 0
    - avg_win: mean net_pnl of winning trades (dollars)
    - avg_loss: mean abs(net_pnl) of losing trades (dollars)

    Enforces minimum 20 closed trades (B4 caller contract).
    Returns 1.0 (no adjustment) when insufficient data.
    Never raises.
    """
    try:
        from risk_engine import compute_kelly_multiplier

        cutoff = (date.today() - timedelta(days=days)).isoformat()
        result = (
            get_client()
            .table("trading_positions")
            .select("net_pnl")
            .gte("entry_at", cutoff)
            .eq("status", "closed")
            .eq("position_mode", "virtual")
            .execute()
        )
        positions = result.data or []
        n = len(positions)

        # B4 caller contract: minimum 20 closed trades
        if n < 20:
            logger.info(
                "kelly_multiplier_skipped_insufficient_trades",
                trades=n,
                required=20,
            )
            return 1.0

        pnls = [float(p.get("net_pnl") or 0.0) for p in positions]
        wins = [p for p in pnls if p > 0]
        losses = [abs(p) for p in pnls if p <= 0]

        win_rate = len(wins) / n
        avg_win = sum(wins) / len(wins) if wins else 0.0
        avg_loss = sum(losses) / len(losses) if losses else 0.0

        multiplier = compute_kelly_multiplier(
            recent_win_rate=win_rate,
            avg_win_dollars=avg_win,
            avg_loss_dollars=avg_loss,
        )

        logger.info(
            "kelly_multiplier_computed",
            trades=n,
            win_rate=round(win_rate, 3),
            avg_win=round(avg_win, 2),
            avg_loss=round(avg_loss, 2),
            multiplier=multiplier,
        )
        return multiplier

    except Exception as e:
        logger.error("kelly_multiplier_db_failed", error=str(e))
        return 1.0


def compute_per_regime_accuracy() -> dict:
    """
    Compute accuracy broken down by regime.
    Returns dict mapping regime -> {accuracy, count}.
    Needed for GLC-002.
    """
    try:
        cutoff = (date.today() - timedelta(days=60)).isoformat()
        result = (
            get_client()
            .table("trading_positions")
            .select("entry_regime, net_pnl")
            .eq("status", "closed")
            .eq("position_mode", "virtual")
            .gte("entry_at", cutoff)
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
    Uses percentage daily returns (pnl / account_value) not raw dollars.
    Target: >= 1.5 (GLC-005). Account value assumed 100,000 (Phase 1 sizing).
    """
    try:
        ACCOUNT_VALUE = 100_000.0
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

        # Convert to daily percentage returns
        daily_returns = [p / ACCOUNT_VALUE for p in pnls]

        import statistics
        mean_return = statistics.mean(daily_returns)
        std_return = (
            statistics.stdev(daily_returns) if len(daily_returns) > 1 else 0.0001
        )
        if std_return == 0:
            return None

        # Annualize: sqrt(252) trading days
        sharpe = (mean_return / std_return) * (252 ** 0.5)
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
