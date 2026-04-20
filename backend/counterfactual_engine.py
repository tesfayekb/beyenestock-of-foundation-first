"""D4 (12E) — Counterfactual Engine.

Post-session labeler that asks a single question for every no-trade
cycle: "What would the P&L have been if we had opened a position?"
Feeds a weekly summary (top-3 systematic missed opportunities) that
automatically activates once we have 30+ closed sessions of history.

This module is pure observability. It never blocks, modifies, or
informs any live trading decision path. All reads and writes are
fail-open — a Supabase / Polygon outage or a missing schema column
returns an empty summary and logs the failure.

Data flow:
  1. run_counterfactual_job() runs at 4:25 PM ET (mon-fri).
  2. label_counterfactual_outcomes() queries today's
     `trading_prediction_outputs` rows where no_trade_signal=True
     and counterfactual_pnl IS NULL.
  3. For each row: fetch SPX price at t+30min from Polygon (mirrors
     model_retraining.label_prediction_outcomes exactly — same API,
     same window, same fallback behaviour), simulate rough P&L, and
     write counterfactual_pnl / counterfactual_strategy /
     counterfactual_simulated_at back to the row.
  4. generate_weekly_summary() runs Sundays at 6:30 PM ET, gated on
     closed_sessions >= 30, and logs the top-3 reasons by total
     missed P&L.

Simulation model (rough, intentionally):
  Credit spreads (iron_condor / iron_butterfly): win when |exit-entry|
  <= spread_width/2 — collect ~40% of credit. Lose when move exceeds
  the spread — forfeit ~150% of credit.
  Debit strategies (long_straddle / calendar_spread): inverted —
  reward on large moves.
  Generic fallback: 0.5% SPX move threshold.

The model ignores IV changes, theta curve shape, and actual strike
placement. It is sufficient to identify *systematic* missed
opportunities (a `no_trade_reason` that consistently leaves +$ on the
table across 30+ observations), which is the D4 objective. It is
NOT sufficient to backtest absolute dollar accuracy.
"""
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, Optional

import httpx

import config
from logger import get_logger

logger = get_logger("counterfactual_engine")

# Tunable constants. _DEFAULT_SPREAD_WIDTH is the SPX-point width used
# as the win/loss boundary when we don't have an actual strike pair to
# reference. The 5pt width matches the 0DTE iron_butterfly/condor
# widths used elsewhere in the system.
_DEFAULT_SPREAD_WIDTH = 5.0   # SPX points
_WIN_CREDIT_PCT = 0.40        # capture 40% of credit on win
_LOSS_CREDIT_PCT = -1.50      # lose 150% of credit on loss
_TYPICAL_CREDIT = 2.50        # dollars per share of underlying (rough)

_POLYGON_SPX_MINUTE_URL = (
    "https://api.polygon.io/v2/aggs/ticker/I:SPX/range/1/minute/{t0}/{t1}"
)


def _fetch_spx_price_after_signal(
    predicted_at_iso: str,
    minutes: int = 30,
) -> Optional[float]:
    """Fetch SPX price `minutes` after the given signal timestamp.

    Mirrors `model_retraining.label_prediction_outcomes` exactly so
    both labelers see the same realized price and any future polygon
    plan/endpoint change only needs to be coordinated in one place.

    Returns None on any failure — caller must treat None as "skip
    this row, try again tomorrow". Never raises.
    """
    try:
        api_key = config.POLYGON_API_KEY
        if not api_key:
            return None

        predicted_at = datetime.fromisoformat(
            predicted_at_iso.replace("Z", "+00:00")
        )
        target = predicted_at + timedelta(minutes=minutes)
        # Polygon aggregates expect millisecond epoch timestamps and
        # a 1-minute window so we hit exactly one bar.
        t0_ms = int(target.timestamp() * 1000)
        t1_ms = t0_ms + 60_000

        url = _POLYGON_SPX_MINUTE_URL.format(t0=t0_ms, t1=t1_ms)
        headers = {"Authorization": f"Bearer {api_key}"}
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url, headers=headers)
        if resp.status_code != 200:
            return None
        bars = resp.json().get("results", [])
        if not bars:
            return None
        close = float(bars[0].get("c", 0.0))
        return close if close > 0 else None

    except Exception as exc:
        logger.warning("counterfactual_spx_fetch_failed", error=str(exc))
        return None


def _simulate_pnl(
    entry_spx: float,
    exit_spx: float,
    strategy_type: str,
    confidence: float,
) -> float:
    """Rough 1-contract P&L simulation based on SPX movement.

    `confidence` is accepted for future extensions (e.g. scaling the
    credit by confidence) but intentionally unused today so the
    simulation remains interpretable and auditable.
    """
    if entry_spx <= 0:
        return 0.0

    move = abs(exit_spx - entry_spx)
    credit = _TYPICAL_CREDIT

    # Short-gamma credit spreads: flat pin wins, breakout loses.
    if strategy_type in ("iron_butterfly", "iron_condor"):
        if move <= _DEFAULT_SPREAD_WIDTH / 2:
            return credit * _WIN_CREDIT_PCT * 100
        return credit * _LOSS_CREDIT_PCT * 100

    # Long-gamma debit structures: inverted — breakout wins.
    if strategy_type in ("long_straddle", "calendar_spread"):
        if move >= _DEFAULT_SPREAD_WIDTH:
            return credit * _WIN_CREDIT_PCT * 100
        return credit * _LOSS_CREDIT_PCT * 100

    # Generic (e.g. put_credit_spread without a specific mapping):
    # use a relative 0.5% SPX threshold.
    if move / entry_spx < 0.005:
        return credit * _WIN_CREDIT_PCT * 100
    return credit * _LOSS_CREDIT_PCT * 100


def label_counterfactual_outcomes(
    redis_client=None,
) -> Dict[str, Any]:
    """Label today's unlabeled no-trade rows with counterfactual P&L.

    `redis_client` now also carries the operator kill-switch for this
    whole labeling loop via the `feedback:counterfactual:enabled`
    Redis key (matches the pattern in strategy_selector._check_feature_flag
    and main.set_feature_flag, which write Redis-first and mirror to
    Supabase best-effort).

    Semantics (deliberately fail-open so today's behaviour is preserved
    if the operator has never touched the flag):
      * flag key missing                → ENABLED
      * flag value in {"true"}          → ENABLED
      * flag value in {"false"}         → DISABLED
      * Redis client absent or raises   → ENABLED
    """
    # Feature flag gate — fail-open, Redis-authoritative. Checked
    # before any Supabase query so a DISABLED flag costs nothing.
    if redis_client is not None:
        try:
            raw = redis_client.get("feedback:counterfactual:enabled")
            if raw in ("false", b"false"):
                logger.info("counterfactual_labeling_disabled_by_flag")
                return {"labeled": 0, "skipped": 0, "disabled": True}
        except Exception:
            pass  # fail-open — read error → proceed normally

    summary: Dict[str, Any] = {"labeled": 0, "skipped": 0}
    try:
        from db import get_client
        today = date.today().isoformat()

        # Same "no-trade rows from today that don't have a
        # counterfactual yet" predicate that the partial index on
        # the migration is built for.
        result = (
            get_client()
            .table("trading_prediction_outputs")
            .select(
                "id, predicted_at, spx_price, no_trade_reason, "
                "regime, confidence"
            )
            .eq("no_trade_signal", True)
            .gte("predicted_at", f"{today}T00:00:00+00:00")
            .is_("counterfactual_pnl", "null")
            .execute()
        )
        rows = result.data or []
        if not rows:
            logger.info("counterfactual_no_rows_to_label", date=today)
            return summary

        for row in rows:
            try:
                entry_spx = float(row.get("spx_price") or 0)
                if entry_spx <= 0:
                    summary["skipped"] += 1
                    continue

                exit_spx = _fetch_spx_price_after_signal(
                    row["predicted_at"], minutes=30
                )
                if exit_spx is None:
                    summary["skipped"] += 1
                    continue

                # `strategy_hint` does not exist on this table — use a
                # conservative iron_condor proxy for all rows. The
                # counterfactual_strategy column captures the choice
                # so a future schema change can re-simulate from
                # source data without losing the provenance.
                strategy = "iron_condor"
                confidence = float(row.get("confidence") or 0.5)
                sim_pnl = _simulate_pnl(
                    entry_spx, exit_spx, strategy, confidence
                )

                (
                    get_client()
                    .table("trading_prediction_outputs")
                    .update(
                        {
                            "counterfactual_pnl": round(sim_pnl, 2),
                            "counterfactual_strategy": strategy,
                            "counterfactual_simulated_at": (
                                datetime.now(timezone.utc).isoformat()
                            ),
                        }
                    )
                    .eq("id", row["id"])
                    .execute()
                )
                summary["labeled"] += 1

            except Exception as row_exc:
                # Single-row failure must not poison the batch — the
                # next day's retry will pick up the skipped rows.
                logger.warning(
                    "counterfactual_row_failed",
                    row_id=row.get("id"),
                    error=str(row_exc),
                )
                summary["skipped"] += 1

        logger.info(
            "counterfactual_labeling_complete",
            labeled=summary["labeled"],
            skipped=summary["skipped"],
            date=today,
        )
        return summary

    except Exception as exc:
        logger.error("counterfactual_labeling_failed", error=str(exc))
        return {**summary, "error": str(exc)}


def generate_weekly_summary(
    redis_client=None,
) -> Optional[Dict[str, Any]]:
    """Produce a weekly missed-opportunity summary, or None if we
    have fewer than 30 closed sessions of history.

    30 sessions was chosen so the ranked `no_trade_reason` list has
    a large enough denominator that spurious per-reason spikes from a
    single strange day don't dominate the podium.
    """
    try:
        from db import get_client

        sessions_result = (
            get_client()
            .table("trading_sessions")
            .select("id", count="exact")
            .eq("session_status", "closed")
            .execute()
        )
        closed_sessions = sessions_result.count or 0

        if closed_sessions < 30:
            logger.info(
                "counterfactual_summary_skipped_insufficient_data",
                closed_sessions=closed_sessions,
                required=30,
            )
            return None

        cutoff = (date.today() - timedelta(days=7)).isoformat()
        result = (
            get_client()
            .table("trading_prediction_outputs")
            .select(
                "no_trade_reason, counterfactual_pnl, "
                "counterfactual_strategy, regime"
            )
            .eq("no_trade_signal", True)
            .not_.is_("counterfactual_pnl", "null")
            .gte("predicted_at", f"{cutoff}T00:00:00+00:00")
            .execute()
        )
        rows = result.data or []

        if not rows:
            return {
                "message": "no counterfactual data this week",
                "top_opportunities": [],
            }

        by_reason: Dict[str, Dict[str, float]] = {}
        for row in rows:
            reason = row.get("no_trade_reason") or "unknown"
            pnl = float(row.get("counterfactual_pnl") or 0)
            cell = by_reason.setdefault(
                reason, {"total_pnl": 0.0, "count": 0}
            )
            cell["total_pnl"] += pnl
            cell["count"] += 1

        # Sort DESC so the most-positive total_missed_pnl is top:
        # this is the highest-leverage no_trade_reason to loosen.
        opportunities = sorted(
            (
                {
                    "reason": r,
                    "count": int(v["count"]),
                    "avg_missed_pnl": round(
                        v["total_pnl"] / v["count"], 2
                    ) if v["count"] else 0.0,
                    "total_missed_pnl": round(v["total_pnl"], 2),
                }
                for r, v in by_reason.items()
            ),
            key=lambda x: x["total_missed_pnl"],
            reverse=True,
        )[:3]

        summary = {
            "week_ending": date.today().isoformat(),
            "total_no_trade_rows": len(rows),
            "top_opportunities": opportunities,
        }

        # Log the structured summary so it flows into the same
        # observability pipeline as every other weekly job.
        import json
        logger.info(
            "counterfactual_weekly_summary",
            week_ending=summary["week_ending"],
            total_no_trade_rows=summary["total_no_trade_rows"],
            top_3=json.dumps(opportunities),
        )
        return summary

    except Exception as exc:
        logger.error("counterfactual_weekly_summary_failed", error=str(exc))
        return None


def run_counterfactual_job(redis_client=None) -> Dict[str, Any]:
    """
    Entry point invoked by the daily 4:25 PM ET scheduled job.

    Writes `trading_system_health` so the Engine Health admin page
    reflects the last run. Status is `idle` on success (the engine is
    a batch job, not a heartbeat service — `idle` is the correct label
    between runs) and `error` on exception. Per-run stats land in the
    `details` JSONB column rather than as top-level kwargs, because
    `trading_system_health` has no `labeled`/`skipped` columns — passing
    them directly to `write_health_status` would silently fail the
    upsert. Health writes are wrapped in their own try/except so any
    observability failure never masks the real job result.
    """
    try:
        result = label_counterfactual_outcomes(redis_client)
        try:
            from db import write_health_status
            write_health_status(
                "counterfactual_engine",
                "idle",
                details={
                    "labeled": result.get("labeled", 0),
                    "skipped": result.get("skipped", 0),
                },
            )
        except Exception:
            pass  # observability must never mask the real result
        return result
    except Exception as exc:
        try:
            from db import write_health_status
            write_health_status(
                "counterfactual_engine",
                "error",
                last_error_message=str(exc),
            )
        except Exception:
            pass
        logger.error("run_counterfactual_job_failed", error=str(exc))
        return {"labeled": 0, "skipped": 0, "error": str(exc)}
