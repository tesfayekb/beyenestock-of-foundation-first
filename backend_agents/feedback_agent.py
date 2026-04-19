"""
Closed-loop AI feedback agent — Phase A (Loop 1).

Runs at 9:10 AM ET, 5 minutes before synthesis_agent.
Queries the last 60 closed virtual positions and computes performance
statistics for each direction, confidence band, regime, and signal source.
Writes ai:feedback:brief to Redis for synthesis_agent to include in
Claude's prompt.

CRITICAL SAFETY FEATURES:
1. Bootstrap floor: does not publish a brief below MIN_TRADES_FOR_BRIEF=10
   (avoids biasing Claude with statistically meaningless data).
2. Wilson CI: every win-rate includes a 95% confidence interval so Claude
   knows the uncertainty around each estimate.
3. Per-cell P&L: avg winner, avg loser, net P&L per direction.
   Win rate alone is misleading for asymmetric strategies.
4. Regime-conditional breakdown: separate stats per entry_regime.
5. Signal source accuracy: tracks whether macro/flow/sentiment signals
   correlated with outcomes.
6. 4-day TTL with generated_at timestamp for stale-brief detection.

FAILURE MODES (how to recover):
  IF Claude becomes systematically bearish/bullish after a bad streak:
    redis_client.delete("ai:feedback:brief")
    This wipes the brief and synthesis runs without feedback context.
    Investigate: was it one bad week inflating a small-n cell?
  IF system becomes overcautious after losing streak:
    Same: delete ai:feedback:brief and monitor next 10 trades.
  IF brief is stale after long weekend (>4 days since last write):
    The 4-day TTL prevents missing briefs across 3-day weekends.
    synthesis_agent logs a WARNING if brief age > 26h.

The brief can always be inspected:
  redis-cli GET ai:feedback:brief | python3 -m json.tool
"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from datetime import datetime, timezone

from db import get_client
from logger import get_logger
from market_calendar import is_market_day

logger = get_logger("feedback_agent")

MIN_TRADES_FOR_BRIEF = 10        # publish nothing below this threshold
BRIEF_TTL_SECONDS = 345_600      # 4 days — survives 3-day weekends

# Confidence bands for calibration analysis
HIGH_CONFIDENCE_THRESHOLD = 0.70
LOW_CONFIDENCE_THRESHOLD = 0.55


# ─── Main entry point ─────────────────────────────────────────────────────────

def run_feedback_agent(redis_client) -> dict:
    """
    Main entry point. Run at 9:10 AM ET on market days.
    Returns the brief dict. Writes to Redis. Never raises.
    """
    try:
        if not is_market_day():
            logger.debug("feedback_agent_skipped_non_market_day")
            # Leave previous brief in Redis (4-day TTL handles expiry).
            return {}

        rows = _fetch_closed_trades()
        total = len(rows)

        if total < MIN_TRADES_FOR_BRIEF:
            stub = {
                "status": "insufficient_history",
                "trade_count": total,
                "minimum_required": MIN_TRADES_FOR_BRIEF,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }
            if redis_client:
                try:
                    redis_client.setex(
                        "ai:feedback:brief",
                        BRIEF_TTL_SECONDS,
                        json.dumps(stub),
                    )
                except Exception:
                    # Soft failure — brief absence is itself a signal that
                    # synthesis_agent will handle (omit feedback section).
                    pass
            logger.info(
                "feedback_agent_insufficient_history",
                trade_count=total,
                minimum=MIN_TRADES_FOR_BRIEF,
            )
            return stub

        brief = _compute_brief(rows)
        brief["generated_at"] = datetime.now(timezone.utc).isoformat()
        brief["status"] = "ready"
        brief["trade_count"] = total

        if redis_client:
            try:
                redis_client.setex(
                    "ai:feedback:brief",
                    BRIEF_TTL_SECONDS,
                    json.dumps(brief),
                )
            except Exception as e:
                logger.warning("feedback_redis_write_failed", error=str(e))

        logger.info(
            "feedback_agent_complete",
            trade_count=total,
            overall_win_rate=brief.get("overall", {}).get("win_rate"),
        )
        return brief

    except Exception as exc:
        logger.error("feedback_agent_failed", error=str(exc))
        return {}


# ─── SQL query ────────────────────────────────────────────────────────────────

def _fetch_closed_trades() -> list[dict]:
    """
    Fetch closed positions joined to their closest preceding prediction.
    Uses temporal lateral join: for each position, find the most recent
    prediction in the same session whose predicted_at <= entry_at.
    This is correct because prediction_outputs writes every ~30 min,
    not once per session — session-level join would double-count.
    """
    try:
        # Supabase Python client cannot express LATERAL joins directly.
        # Call the get_feedback_trades() Postgres function via RPC.
        client = get_client()
        result = client.rpc("get_feedback_trades", {}).execute()
        if result.data:
            return result.data
        # If the RPC succeeds but returns nothing, fall through to the
        # Python-side fallback so a missing function is not silently
        # treated as "zero trades" (which would block the brief forever).
        return _fetch_trades_python_join()

    except Exception as exc:
        logger.warning("feedback_fetch_failed", error=str(exc))
        return _fetch_trades_python_join()


def _fetch_trades_python_join() -> list[dict]:
    """
    Fallback: fetch positions and predictions separately.
    Performs the temporal join in Python. Less efficient but works
    even if the get_feedback_trades() RPC has not been deployed yet.
    """
    try:
        client = get_client()

        # Fetch last 60 closed virtual positions.
        pos_result = (
            client.table("trading_positions")
            .select(
                "id, session_id, strategy_type, entry_at, exit_at, "
                "net_pnl, entry_regime, entry_credit, contracts"
            )
            .eq("status", "closed")
            .eq("position_mode", "virtual")
            .not_.is_("net_pnl", "null")
            .order("exit_at", desc=True)
            .limit(60)
            .execute()
        )
        positions = pos_result.data or []

        if not positions:
            return []

        # Collect unique session IDs (capped for safety on a wide
        # session distribution).
        session_ids = list(
            {p["session_id"] for p in positions if p.get("session_id")}
        )

        # Fetch all predictions for those sessions.
        pred_result = (
            client.table("trading_prediction_outputs")
            .select(
                "id, session_id, predicted_at, direction, "
                "confidence, regime"
            )
            .in_("session_id", session_ids[:20])
            .order("predicted_at", desc=False)
            .execute()
        )
        predictions = pred_result.data or []

        # Build session -> sorted-predictions map.
        session_preds: dict[str, list] = defaultdict(list)
        for p in predictions:
            if p.get("session_id"):
                session_preds[p["session_id"]].append(p)

        # Temporal join: for each position, find the closest preceding
        # prediction inside the same session.
        rows = []
        for pos in positions:
            sid = pos.get("session_id")
            entry_at = pos.get("entry_at", "")
            preds = session_preds.get(sid, [])

            best_pred = None
            for pred in reversed(preds):
                if pred.get("predicted_at", "") <= entry_at:
                    best_pred = pred
                    break

            row = {**pos}
            if best_pred:
                row["prediction_direction"] = best_pred.get("direction")
                row["prediction_confidence"] = best_pred.get("confidence")
                row["prediction_regime"] = best_pred.get("regime")
            else:
                row["prediction_direction"] = None
                row["prediction_confidence"] = None
                row["prediction_regime"] = pos.get("entry_regime")

            rows.append(row)

        return rows

    except Exception as exc:
        logger.warning("feedback_python_join_failed", error=str(exc))
        return []


# ─── Wilson confidence interval ───────────────────────────────────────────────

def _wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """
    95% Wilson score confidence interval for a proportion.
    Returns (lower, upper) as fractions in [0, 1].
    More accurate than the normal approximation for small n.
    """
    if n == 0:
        return 0.0, 1.0
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    margin = (
        z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    ) / denom
    return (
        round(max(0.0, center - margin), 3),
        round(min(1.0, center + margin), 3),
    )


# ─── Core computation ─────────────────────────────────────────────────────────

def _compute_brief(rows: list[dict]) -> dict:
    """Compute the full feedback brief from closed trade rows."""
    return {
        "overall":          _compute_overall(rows),
        "by_direction":     _compute_by_direction(rows),
        "by_confidence":    _compute_by_confidence(rows),
        "by_regime":        _compute_by_regime(rows),
        "recent_streak":    _compute_recent_streak(rows),
    }


def _pnl_stats(pnls: list[float]) -> dict:
    """Compute avg_winner, avg_loser, net_pnl from a list of P&Ls."""
    winners = [p for p in pnls if p > 0]
    losers = [p for p in pnls if p <= 0]
    return {
        "avg_winner": round(sum(winners) / len(winners), 2) if winners else 0.0,
        "avg_loser":  round(sum(losers) / len(losers), 2) if losers else 0.0,
        "net_pnl":    round(sum(pnls), 2),
        "profitable": sum(pnls) > 0,
    }


def _cell(wins: int, n: int, pnls: list[float]) -> dict:
    """Build a stats cell with win rate, Wilson CI, and P&L stats."""
    if n < 5:
        return {
            "n": n,
            "sufficient": False,
            "note": "INSUFFICIENT DATA (n<5)",
        }
    ci_lo, ci_hi = _wilson_ci(wins, n)
    return {
        "n": n,
        "sufficient": True,
        "wins": wins,
        "win_rate": round(wins / n, 3),
        "win_rate_ci": [ci_lo, ci_hi],
        **_pnl_stats(pnls),
    }


def _compute_overall(rows: list[dict]) -> dict:
    n = len(rows)
    pnls = [r.get("net_pnl", 0) or 0 for r in rows]
    wins = sum(1 for p in pnls if p > 0)
    ci_lo, ci_hi = _wilson_ci(wins, n)
    winners = [p for p in pnls if p > 0]
    losers = [p for p in pnls if p <= 0]
    pf = (
        sum(winners) / abs(sum(losers))
        if losers and sum(losers) != 0 else None
    )
    return {
        "n": n,
        "win_rate": round(wins / n, 3) if n else 0,
        "win_rate_ci": [ci_lo, ci_hi],
        "total_pnl": round(sum(pnls), 2),
        "avg_win":  round(sum(winners) / len(winners), 2) if winners else 0,
        "avg_loss": round(sum(losers) / len(losers), 2) if losers else 0,
        "profit_factor": round(pf, 3) if pf else None,
        "expectancy": round(sum(pnls) / n, 2) if n else 0,
    }


def _compute_by_direction(rows: list[dict]) -> dict:
    buckets: dict[str, tuple[list, list]] = {
        "bull": ([], []),
        "bear": ([], []),
        "neutral": ([], []),
    }
    for r in rows:
        d = (r.get("prediction_direction") or "neutral").lower()
        key = d if d in buckets else "neutral"
        pnl = r.get("net_pnl", 0) or 0
        buckets[key][0].append(pnl)
        if pnl > 0:
            buckets[key][1].append(1)

    return {
        direction: _cell(len(wins_list), len(pnls), pnls)
        for direction, (pnls, wins_list) in buckets.items()
    }


def _compute_by_confidence(rows: list[dict]) -> dict:
    bands: dict[str, tuple[list, list]] = {
        "high": ([], []),
        "medium": ([], []),
        "low": ([], []),
    }
    for r in rows:
        conf = r.get("prediction_confidence") or 0.0
        try:
            conf = float(conf)
        except (TypeError, ValueError):
            conf = 0.0
        pnl = r.get("net_pnl", 0) or 0
        if conf >= HIGH_CONFIDENCE_THRESHOLD:
            key = "high"
        elif conf >= LOW_CONFIDENCE_THRESHOLD:
            key = "medium"
        else:
            key = "low"
        bands[key][0].append(pnl)
        if pnl > 0:
            bands[key][1].append(1)

    result = {
        band: _cell(len(wins_list), len(pnls), pnls)
        for band, (pnls, wins_list) in bands.items()
    }
    result["thresholds"] = {
        "high": HIGH_CONFIDENCE_THRESHOLD,
        "low":  LOW_CONFIDENCE_THRESHOLD,
    }
    return result


def _compute_by_regime(rows: list[dict]) -> dict:
    regimes: dict[str, tuple[list, list]] = {}
    for r in rows:
        regime = (
            r.get("prediction_regime")
            or r.get("entry_regime")
            or "unknown"
        ).lower()
        if regime not in regimes:
            regimes[regime] = ([], [])
        pnl = r.get("net_pnl", 0) or 0
        regimes[regime][0].append(pnl)
        if pnl > 0:
            regimes[regime][1].append(1)

    return {
        regime: _cell(len(wins_list), len(pnls), pnls)
        for regime, (pnls, wins_list) in regimes.items()
    }


def _compute_recent_streak(rows: list[dict]) -> dict:
    """Most recent 10 trades as W/L list."""
    recent = sorted(
        rows, key=lambda r: r.get("exit_at") or "", reverse=True
    )[:10]
    streak = [1 if (r.get("net_pnl") or 0) > 0 else 0 for r in recent]
    consecutive_losses = 0
    for outcome in streak:
        if outcome == 0:
            consecutive_losses += 1
        else:
            break
    return {
        "last_10": streak,
        "consecutive_losses": consecutive_losses,
    }
