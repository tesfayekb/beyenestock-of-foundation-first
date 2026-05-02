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
        # T2-2: build the day window from ET session boundaries, not
        # UTC midnight. `predicted_at` is written as UTC timestamps by
        # run_cycle, and an ET trading session straddles a UTC date
        # boundary every evening after 8 PM ET (= next UTC day). The
        # previous UTC-midnight-to-midnight filter on the target date
        # missed every evening/overnight prediction that belonged to
        # the just-closed ET session and mis-included pre-midnight
        # UTC predictions from the prior ET session.
        #
        # Window: 4:00 AM ET (pre-market open, well before the 9:30
        # RTH open the S15 T2-4 gate now enforces) through 8:00 PM ET
        # (covers post-market labeling jobs). Both timestamps are
        # timezone-aware so .isoformat() yields the correct UTC
        # offset and PostgREST / Supabase do a proper timestamptz
        # comparison.
        from zoneinfo import ZoneInfo
        ET = ZoneInfo("America/New_York")
        day_start_et = datetime(
            target_date.year, target_date.month, target_date.day,
            4, 0, 0, tzinfo=ET,
        )
        day_end_et = datetime(
            target_date.year, target_date.month, target_date.day,
            20, 0, 0, tzinfo=ET,
        )
        day_start = day_start_et.isoformat()
        day_end = day_end_et.isoformat()

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


def check_prediction_drift(redis_client) -> dict:
    """
    12L (D1): pure-observability drift alert.

    Fires when rolling 10-day directional accuracy drops > 5pp
    below the 30-day baseline. Writes a `model_drift_alert` key
    to Redis (TTL 86400s) that operators / dashboards can poll;
    clears the same key when accuracy recovers.

    ROI contract: NEVER affects trade decisions. No imports from
    execution_engine / strategy_selector / risk_engine /
    trading_cycle (enforced by test_drift_check_does_not_affect_trades).
    Never raises — any exception returns an error payload.

    Gate: both the 10-day and 30-day windows must carry at least
    10 labeled predictions (`outcome_correct IS NOT NULL` on
    real trade signals) before a meaningful ratio can be computed.
    Below that gate we return checked=False without touching Redis.

    Accepts `redis_client` as a parameter (not a module-level
    import) so tests can inject a mock and so a None redis_client
    at the call site surfaces cleanly through the outer try/except
    instead of silently failing.
    """
    try:
        today = date.today()
        day10_cutoff = (today - timedelta(days=10)).isoformat()
        day30_cutoff = (today - timedelta(days=30)).isoformat()

        def _accuracy_for_window(cutoff_iso_date: str):
            result = (
                get_client()
                .table("trading_prediction_outputs")
                .select("outcome_correct")
                .not_.is_("outcome_correct", "null")
                .eq("no_trade_signal", False)
                .gte(
                    "predicted_at",
                    f"{cutoff_iso_date}T00:00:00+00:00",
                )
                .execute()
            )
            rows = result.data or []
            if len(rows) < 10:
                return None, len(rows)
            correct = sum(1 for r in rows if r.get("outcome_correct"))
            return round(correct / len(rows), 4), len(rows)

        acc_10d, count_10d = _accuracy_for_window(day10_cutoff)
        acc_30d, count_30d = _accuracy_for_window(day30_cutoff)

        if acc_10d is None or acc_30d is None:
            logger.info(
                "drift_check_skipped_insufficient_data",
                count_10d=count_10d,
                count_30d=count_30d,
                required=10,
            )
            return {
                "checked": False,
                "reason": "insufficient_data",
                "count_10d": count_10d,
                "count_30d": count_30d,
            }

        # DRIFT_DROP_THRESHOLD is deliberately distinct from the
        # module-level DRIFT_THRESHOLD (0.50 absolute accuracy used
        # by detect_drift). This one is a delta in percentage points
        # between the rolling and baseline windows — a different
        # quantity — and sharing a name would confuse readers of
        # both call sites.
        DRIFT_DROP_THRESHOLD = 0.05
        drop = acc_30d - acc_10d

        if drop > DRIFT_DROP_THRESHOLD:
            redis_client.setex("model_drift_alert", 86400, "1")
            logger.warning(
                "drift_alert_fired",
                acc_10d=acc_10d,
                acc_30d=acc_30d,
                drop=round(drop, 4),
                threshold=DRIFT_DROP_THRESHOLD,
            )
            return {
                "alert": True,
                "acc_10d": acc_10d,
                "acc_30d": acc_30d,
                "drop": round(drop, 4),
                "count_10d": count_10d,
                "count_30d": count_30d,
            }

        # Clear any stale alert — recovery branch.
        try:
            redis_client.delete("model_drift_alert")
        except Exception:
            pass
        logger.info(
            "drift_check_clean",
            acc_10d=acc_10d,
            acc_30d=acc_30d,
            drop=round(drop, 4),
        )
        return {
            "alert": False,
            "acc_10d": acc_10d,
            "acc_30d": acc_30d,
            "drop": round(drop, 4),
            "count_10d": count_10d,
            "count_30d": count_30d,
        }

    except Exception as exc:
        logger.error("drift_check_failed", error=str(exc))
        return {"checked": False, "error": str(exc)}


def compute_directional_accuracy(days: int = 20) -> dict:
    """
    Compute directional prediction accuracy over the last N days.

    T2-1: now reads outcome_correct directly from
    trading_prediction_outputs. That column is populated by
    label_prediction_outcomes(), which compares the predicted direction
    against the actual SPX +30-minute move — the definition of
    directional accuracy.

    Previous implementation (Phase 4B) used virtual-position P&L win
    rate as a proxy. That measures execution quality, not model
    calibration. A bearish prediction that made money on a credit
    spread was counted as "correct" even if SPX rallied, and drift
    detection / champion-challenger responded to P&L luck instead of
    calibration. The proxy had no reference to `direction` at all.
    """
    try:
        cutoff = (date.today() - timedelta(days=days)).isoformat()

        result = (
            get_client()
            .table("trading_prediction_outputs")
            .select("outcome_correct")
            .gte("predicted_at", cutoff)
            .eq("no_trade_signal", False)
            .not_.is_("outcome_correct", "null")
            .execute()
        )
        rows = result.data or []
        n = len(rows)

        if n < 5:
            return {
                "accuracy": None,
                "observations": n,
                "days": days,
                "sufficient_data": False,
                "method": "outcome_correct",
            }

        correct = sum(1 for r in rows if r.get("outcome_correct") is True)
        accuracy = correct / n

        return {
            "accuracy": round(accuracy, 4),
            "observations": n,
            "correct": correct,
            "days": days,
            "sufficient_data": True,
            "method": "outcome_correct",
        }

    except Exception as e:
        logger.error("accuracy_compute_failed", days=days, error=str(e))
        return {
            "accuracy": None,
            "observations": 0,
            "days": days,
            "sufficient_data": False,
            "method": "outcome_correct",
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
        # S11: Sharpe denominator now uses LIVE deployed capital instead
        # of the old hardcoded 100_000. Falls back to 100_000.0 only if
        # capital_manager cannot determine equity (Tradier unreachable
        # during weekly batch run) — Sharpe is a research metric, not a
        # trading decision, so a graceful fallback is appropriate.
        try:
            from capital_manager import get_deployed_capital
            ACCOUNT_VALUE = get_deployed_capital(None)
        except Exception:
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


# ── 12K: Loop 2 meta-label model scaffold ────────────────────────────
#
# Purpose: learn which SPECIFIC trade setups actually win, not just
# which regimes win. Feature set mirrors the columns persisted by
# prediction_engine.run_cycle (Phase A scaffold from 12H), so training
# can proceed the moment we have 100+ labeled prediction rows.
#
# ROI contract:
#   * Gates on closed_trades >= 100. Below that → no file written.
#   * Trained model only affects live trading via the scoring block
#     in execution_engine.open_virtual_position(). That block is
#     itself pkl-gated, so before this function has ever produced a
#     file the entire path is a pure pass-through.
#   * Never raises: a failure here must never abort the weekly
#     calibration chain.

MIN_CLOSED_TRADES_FOR_META_LABEL = 100
MIN_LABELED_ROWS_FOR_META_LABEL = 100


def train_meta_label_model(redis_client=None) -> dict:
    """
    Loop 2: train a meta-label model to predict whether a specific
    trade setup will win — not just which regime wins.

    Features (9, must stay in lockstep with
    execution_engine.open_virtual_position and
    run_meta_label_champion_challenger._row_to_features):
      confidence, vvix_z_score, gex_confidence, cv_stress_score, vix,
      prior_session_return, vix_term_ratio, spx_momentum_4h,
      gex_flip_proximity.

    NULL-handling contract (T-ACT-054 Meta-3, ratified in
    `fix/t-act-054-cv-stress-null-on-degenerate`):
      cv_stress_score may be persisted as NULL in the database when
      _compute_cv_stress detected degenerate inputs (Choice A). All
      three feature-vector sites — this trainer, the champion-
      challenger _row_to_features (L1071), and the live inference
      path at execution_engine.open_virtual_position (L388) — convert
      NULL → float("nan") via the pattern:
        (float(r["cv_stress_score"]) if r.get("cv_stress_score") is not None
         else float("nan"))
      LightGBM handles NaN natively as a missing value (zero_as_missing
      defaults to False; missing values traverse a learned default
      direction at each split). DO NOT replace this with `or 0.0` —
      that pattern silently coerces NULL to a real 0.0 reading and
      defeats the explicit semantic distinction Choice A creates. All
      three sites MUST stay byte-equivalent on this column or the
      .predict_proba() shape contract holds but the model output is
      corrupted; tests in test_t_act_054_cv_stress_null_semantics.py
      enforce lockstep.

    `signal_weak` was dropped in Section 13 Batch 1 because its
    training distribution is a constant 0 (no_trade_signal=True when
    signal_weak=True, and the training set filters to
    no_trade_signal=False), so LightGBM learned nothing from it and
    the column inflated the feature count without contributing
    information.

    Target: outcome_correct (labeled by label_prediction_outcomes).

    Auto-gates on closed_trades >= 100 AND labeled_rows >= 100.
    Output: backend/models/meta_label_v1.pkl
    Falls back gracefully when lightgbm not installed. Never raises.
    """
    try:
        from pathlib import Path

        # Gate 1: need 100+ closed labeled trades before a meta-label
        # model is even worth training.
        count_result = (
            get_client()
            .table("trading_positions")
            .select("id", count="exact")
            .eq("status", "closed")
            .eq("position_mode", "virtual")
            .execute()
        )
        closed_trades = count_result.count or 0

        if closed_trades < MIN_CLOSED_TRADES_FOR_META_LABEL:
            logger.info(
                "meta_label_training_skipped",
                closed_trades=closed_trades,
                required=MIN_CLOSED_TRADES_FOR_META_LABEL,
            )
            return {
                "trained": False,
                "closed_trades": closed_trades,
                "required": MIN_CLOSED_TRADES_FOR_META_LABEL,
            }

        # Gate 2: fetch labeled predictions. `.order("predicted_at")`
        # is load-bearing — the 80/20 split below is explicitly
        # walk-forward ("train on earliest 80%, validate on most
        # recent 20%"), so the rows MUST come back in chronological
        # order. Without ordering, PostgREST returns insertion-order
        # at best and arbitrary planner-order at worst, which leaks
        # future information into training and makes val_accuracy /
        # val_auc meaningless.
        result = (
            get_client()
            .table("trading_prediction_outputs")
            .select(
                "outcome_correct, confidence, vvix_z_score, gex_confidence, "
                "cv_stress_score, vix, prior_session_return, "
                "vix_term_ratio, spx_momentum_4h, gex_flip_proximity, "
                "predicted_at"
            )
            .not_.is_("outcome_correct", "null")
            .eq("no_trade_signal", False)
            .order("predicted_at")
            .execute()
        )
        rows = result.data or []

        if len(rows) < MIN_LABELED_ROWS_FOR_META_LABEL:
            return {
                "trained": False,
                "labeled_rows": len(rows),
                "required": MIN_LABELED_ROWS_FOR_META_LABEL,
                "reason": "insufficient_labeled_rows",
            }

        # Build feature matrix. Defaults mirror the inference-side
        # fallbacks in execution_engine so the model sees the same
        # domain values at train time and at predict time.
        features = []
        labels = []
        for r in rows:
            try:
                feat = [
                    float(r.get("confidence") or 0),
                    float(r.get("vvix_z_score") or 0),
                    float(r.get("gex_confidence") or 0),
                    # T-ACT-054 Meta-3: NaN sentinel preserves NULL-on-
                    # degenerate-input semantics through the meta-label
                    # training feature contract. LightGBM natively
                    # handles NaN as missing; the model learns to split
                    # on "is cv_stress observed?" as a feature. Lockstep
                    # with run_meta_label_champion_challenger._row_to_features
                    # (L1071) and execution_engine.open_virtual_position (L388).
                    (
                        float(r["cv_stress_score"])
                        if r.get("cv_stress_score") is not None
                        else float("nan")
                    ),
                    float(r.get("vix") or 18.0),
                    float(r.get("prior_session_return") or 0),
                    float(r.get("vix_term_ratio") or 1.0),
                    float(r.get("spx_momentum_4h") or 0),
                    float(r.get("gex_flip_proximity") or 0),
                ]
                features.append(feat)
                labels.append(1 if r.get("outcome_correct") else 0)
            except Exception:
                continue

        if len(features) < MIN_LABELED_ROWS_FOR_META_LABEL:
            return {
                "trained": False,
                "valid_rows": len(features),
                "reason": "insufficient_valid_rows",
            }

        try:
            import lightgbm as lgb
            import numpy as np
            import pickle

            X = np.array(features)
            y = np.array(labels)

            # Walk-forward split — honest only because the upstream
            # query is now .order("predicted_at").
            split = int(len(X) * 0.8)
            X_train, X_val = X[:split], X[split:]
            y_train, y_val = y[:split], y[split:]

            model = lgb.LGBMClassifier(
                n_estimators=100,
                learning_rate=0.05,
                max_depth=4,
                random_state=42,
                verbose=-1,
            )
            model.fit(X_train, y_train)

            val_preds = model.predict(X_val)
            val_acc = float(np.mean(val_preds == y_val))

            # Log AUC alongside accuracy. AUC is strictly more
            # informative for a binary classifier that drives a
            # probability-threshold gate (0.55 / 0.75 in the
            # execution-side scoring block) — accuracy collapses
            # calibration information that the thresholds are
            # sensitive to. Treated as observability only; training
            # still succeeds even when AUC cannot be computed (e.g.
            # single-class holdout fold).
            val_auc = None
            try:
                if len(set(y_val.tolist())) > 1:
                    from sklearn.metrics import roc_auc_score
                    val_proba = model.predict_proba(X_val)[:, 1]
                    val_auc = float(round(roc_auc_score(y_val, val_proba), 3))
            except Exception as auc_exc:
                logger.info(
                    "meta_label_auc_skipped",
                    reason=str(auc_exc),
                )

            model_path = Path(__file__).parent / "models" / "meta_label_v1.pkl"
            model_path.parent.mkdir(exist_ok=True)
            with open(model_path, "wb") as f:
                pickle.dump(model, f)

            logger.info(
                "meta_label_model_trained",
                val_accuracy=round(val_acc, 3),
                val_auc=val_auc,
                training_rows=len(X_train),
                val_rows=len(X_val),
                model_path=str(model_path),
            )
            return {
                "trained": True,
                "val_accuracy": round(val_acc, 3),
                "val_auc": val_auc,
                "training_rows": len(X_train),
                "val_rows": len(X_val),
                "closed_trades": closed_trades,
            }

        except ImportError:
            logger.warning("meta_label_lightgbm_not_installed")
            return {"trained": False, "reason": "lightgbm_not_installed"}

    except Exception as exc:
        logger.error("meta_label_training_failed", error=str(exc))
        return {"trained": False, "error": str(exc)}


# ─────────────────────────────────────────────────────────────────────
# 12M — D2 champion/challenger retrain scaffold
# ─────────────────────────────────────────────────────────────────────
#
# DEVIATION FROM THE ORIGINAL 12M SPEC (documented in TASK_REGISTER):
# the spec framed this as a champion/challenger for the directional
# LightGBM model `lgbm_direction_v1.pkl` with the Phase-A live-
# inference set and an `outcome_correct` target. Reading the actual
# code surfaces three blockers against that literal framing:
#   1) the real directional file is `direction_lgbm_v1.pkl`
#      (token order) — the spec would gate on a path that can never
#      exist in production;
#   2) the directional model's feature space is the 25-column
#      bar-engineered FEATURE_COLS list in
#      backend/scripts/train_direction_model.py, not the live
#      features from trading_prediction_outputs — calling
#      .predict() on the mismatched shape crashes, and if it silently
#      padded would produce meaningless accuracy numbers;
#   3) the directional model predicts "bull"/"bear" string labels,
#      not 1/0 outcome_correct — so a naive equality comparison
#      would always score the champion at 0 and swap on the first
#      weekly run.
#
# Option A (confirmed by operator 2026-04-20): target the 12K
# meta-label model instead, which DOES live in the
# trading_prediction_outputs / 9-feature / {0,1} space this
# scaffold's code is actually correct for (9 features as of
# Section 13 Batch 1 — signal_weak dropped as always-zero). Pre-requisite
# `meta_label_v1.pkl` is produced by train_meta_label_model()
# (self-gated on 100 closed trades + 100 labeled rows), so until
# that file exists this function is a complete pass-through — the
# ROI contract of the task is preserved by construction.
#
# Walk-forward split matches the 12K pattern: .order("predicted_at")
# is load-bearing — without it, PostgREST returns rows in
# insertion-order at best and arbitrary planner-order at worst,
# which contaminates the train/holdout split with future data and
# makes the improvement metric meaningless.

MIN_CHAMPION_CHALLENGER_ROWS = 50
MIN_CHAMPION_CHALLENGER_TRAIN_ROWS = 30
MIN_CHAMPION_CHALLENGER_HOLDOUT_ROWS = 10
CHAMPION_CHALLENGER_SWAP_THRESHOLD = 0.01  # 1 percentage point


def run_meta_label_champion_challenger(redis_client=None) -> dict:
    """
    12M (D2): weekly champion/challenger retrain for the 12K
    meta-label model.

    Loads champion `backend/models/meta_label_v1.pkl`, retrains
    a challenger on the rolling 90-day labeled window from
    trading_prediction_outputs, compares both on a 30-day
    walk-forward holdout, and swaps ONLY if the challenger
    improves holdout accuracy by >= 1 percentage point. On swap,
    the prior champion is copied to `meta_label_v0.pkl` as an
    emergency fallback and the new challenger is written to
    `meta_label_v1.pkl` atomically from the caller's view (pickle
    write is not torn-read-safe but the file system rename the OS
    performs on close is; the dashboard / execution_engine read
    either the old blob or the new one, never a half-written file).

    Auto-gates:
      * champion pkl absent → skip cleanly (pre-12K state).
      * lightgbm / numpy / pickle import fails → skip.
      * < 50 labeled rows in the 90d window → skip.
      * train or holdout legs below their minimum counts → skip.

    Never raises. All exceptions return an error payload so the
    weekly calibration chain is never broken by a retrain failure.

    Feature set MUST stay identical to train_meta_label_model() —
    the champion was produced by that function, so any drift
    between the two feature matrices corrupts the comparison.
    """
    try:
        from pathlib import Path

        model_dir = Path(__file__).parent / "models"
        champion_path = model_dir / "meta_label_v1.pkl"
        fallback_path = model_dir / "meta_label_v0.pkl"

        if not champion_path.exists():
            logger.info(
                "champion_challenger_skipped_no_model",
                expected_path=str(champion_path),
            )
            return {"swapped": False, "reason": "no_champion_model"}

        try:
            import lightgbm as lgb
            import numpy as np
            import pickle
            import shutil
        except ImportError as import_exc:
            logger.warning(
                "champion_challenger_import_failed",
                error=str(import_exc),
            )
            return {
                "swapped": False,
                "reason": f"import_failed: {import_exc}",
            }

        cutoff_90 = (date.today() - timedelta(days=90)).isoformat()
        cutoff_30 = (date.today() - timedelta(days=30)).isoformat()
        holdout_boundary = f"{cutoff_30}T00:00:00+00:00"

        result = (
            get_client()
            .table("trading_prediction_outputs")
            .select(
                "outcome_correct, confidence, vvix_z_score, "
                "gex_confidence, cv_stress_score, vix, "
                "prior_session_return, vix_term_ratio, "
                "spx_momentum_4h, gex_flip_proximity, predicted_at"
            )
            .not_.is_("outcome_correct", "null")
            .eq("no_trade_signal", False)
            .gte("predicted_at", f"{cutoff_90}T00:00:00+00:00")
            .order("predicted_at")
            .execute()
        )
        rows = result.data or []

        if len(rows) < MIN_CHAMPION_CHALLENGER_ROWS:
            logger.info(
                "champion_challenger_skipped_insufficient_data",
                rows=len(rows),
                required=MIN_CHAMPION_CHALLENGER_ROWS,
            )
            return {
                "swapped": False,
                "reason": "insufficient_data",
                "rows": len(rows),
            }

        def _row_to_features(r: dict) -> list:
            # 9-feature vector. Defaults mirror train_meta_label_model's
            # fallbacks so the two code paths materialise the same
            # feature vector for the same row. ANY divergence here
            # silently corrupts every comparison this scaffold ever
            # produces — and the execution_engine inference side must
            # match, or .predict_proba() raises on a shape mismatch.
            #
            # T-ACT-054 Meta-3: cv_stress_score uses NaN sentinel (NOT
            # 0.0) when the source row had degenerate inputs at compute
            # time. Must stay in lockstep with
            # train_meta_label_model (L817) and
            # execution_engine.open_virtual_position (L388).
            return [
                float(r.get("confidence") or 0),
                float(r.get("vvix_z_score") or 0),
                float(r.get("gex_confidence") or 0),
                (
                    float(r["cv_stress_score"])
                    if r.get("cv_stress_score") is not None
                    else float("nan")
                ),
                float(r.get("vix") or 18.0),
                float(r.get("prior_session_return") or 0),
                float(r.get("vix_term_ratio") or 1.0),
                float(r.get("spx_momentum_4h") or 0),
                float(r.get("gex_flip_proximity") or 0),
            ]

        train_rows = [
            r for r in rows
            if r.get("predicted_at", "") < holdout_boundary
        ]
        holdout_rows = [
            r for r in rows
            if r.get("predicted_at", "") >= holdout_boundary
        ]

        if (
            len(train_rows) < MIN_CHAMPION_CHALLENGER_TRAIN_ROWS
            or len(holdout_rows) < MIN_CHAMPION_CHALLENGER_HOLDOUT_ROWS
        ):
            logger.info(
                "champion_challenger_skipped_bad_split",
                train=len(train_rows),
                holdout=len(holdout_rows),
                train_required=MIN_CHAMPION_CHALLENGER_TRAIN_ROWS,
                holdout_required=MIN_CHAMPION_CHALLENGER_HOLDOUT_ROWS,
            )
            return {
                "swapped": False,
                "reason": "insufficient_split",
                "train": len(train_rows),
                "holdout": len(holdout_rows),
            }

        X_train = np.array(
            [_row_to_features(r) for r in train_rows]
        )
        y_train = np.array(
            [1 if r.get("outcome_correct") else 0 for r in train_rows]
        )
        X_hold = np.array(
            [_row_to_features(r) for r in holdout_rows]
        )
        y_hold = np.array(
            [1 if r.get("outcome_correct") else 0 for r in holdout_rows]
        )

        with open(champion_path, "rb") as f:
            champion = pickle.load(f)
        champion_preds = np.asarray(champion.predict(X_hold))
        champion_acc = float(np.mean(champion_preds == y_hold))

        # Hyperparameters intentionally match
        # train_meta_label_model's LGBMClassifier config so the
        # only difference between champion and challenger at
        # comparison time is the training data window — never the
        # model architecture.
        challenger = lgb.LGBMClassifier(
            n_estimators=100,
            learning_rate=0.05,
            max_depth=4,
            random_state=42,
            verbose=-1,
        )
        challenger.fit(X_train, y_train)
        challenger_preds = np.asarray(challenger.predict(X_hold))
        challenger_acc = float(np.mean(challenger_preds == y_hold))

        improvement = challenger_acc - champion_acc

        if improvement >= CHAMPION_CHALLENGER_SWAP_THRESHOLD:
            # Back up the outgoing champion to v0 BEFORE overwriting
            # v1. On the rare failure path where shutil.copy succeeds
            # and the pickle.dump that follows crashes, the operator
            # can restore v0 manually — losing the copy first would
            # leave us with no fallback at all.
            shutil.copy(champion_path, fallback_path)
            with open(champion_path, "wb") as f:
                pickle.dump(challenger, f)
            logger.info(
                "model_swapped",
                challenger_acc=round(challenger_acc, 3),
                champion_acc=round(champion_acc, 3),
                improvement=round(improvement, 3),
                training_rows=len(train_rows),
                holdout_rows=len(holdout_rows),
                threshold=CHAMPION_CHALLENGER_SWAP_THRESHOLD,
            )
            return {
                "swapped": True,
                "challenger_acc": round(challenger_acc, 3),
                "champion_acc": round(champion_acc, 3),
                "improvement": round(improvement, 3),
                "training_rows": len(train_rows),
                "holdout_rows": len(holdout_rows),
            }

        logger.info(
            "model_retained",
            challenger_acc=round(challenger_acc, 3),
            champion_acc=round(champion_acc, 3),
            improvement=round(improvement, 3),
            threshold=CHAMPION_CHALLENGER_SWAP_THRESHOLD,
        )
        return {
            "swapped": False,
            "challenger_acc": round(challenger_acc, 3),
            "champion_acc": round(champion_acc, 3),
            "improvement": round(improvement, 3),
            "training_rows": len(train_rows),
            "holdout_rows": len(holdout_rows),
        }

    except Exception as exc:
        logger.error("champion_challenger_failed", error=str(exc))
        return {"swapped": False, "error": str(exc)}
