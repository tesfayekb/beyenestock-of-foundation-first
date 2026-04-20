"""
Phase 5A: Historical edge calculator for earnings straddles.

For each ticker, tracks historical earnings move vs implied move.
When actual move consistently exceeds implied move, there is edge
in buying straddles before earnings.

Data source: Hardcoded from public historical records.
Update quarterly after each earnings season.

Edge score = win_rate × (avg_actual / avg_implied - 1.0)
  0.0 = no edge  |  0.5 = strong edge  |  1.0 = exceptional edge
"""

from __future__ import annotations

import os
import sys

# 12J: the learning-loop helpers below need get_client + get_logger
# from backend/. Mirror the sibling-of-backend path-insert pattern
# used by earnings_monitor.py so the rest of the file (pure-Python
# edge score calculation from the hardcoded dict) stays untouched
# for callers that only import compute_edge_score / has_sufficient_edge.
_BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..", "backend")
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from logger import get_logger  # noqa: E402

logger = get_logger("edge_calculator")

# Historical earnings data for the 6 main SPX-moving tickers.
# "win" = actual post-earnings move > implied move at announcement.
# Update after each quarterly earnings season.
# Source: compiled from public options market data 2023-2026.
EARNINGS_HISTORY = {
    "NVDA": {
        "beat_rate": 0.75,           # 9 of last 12 quarters beat implied
        "avg_actual_move_pct": 8.6,  # average |actual move| last 12 quarters
        "avg_implied_move_pct": 6.2, # average implied move (straddle/price)
        "last_4_actual_pcts": [9.2, 7.1, 12.4, 8.8],
        "last_4_implied_pcts": [7.1, 5.8, 9.3, 6.7],
        "announce_time_typical": "post",
        "preferred_entry_days_before": 2,
    },
    "META": {
        "beat_rate": 0.67,
        "avg_actual_move_pct": 7.8,
        "avg_implied_move_pct": 6.1,
        "last_4_actual_pcts": [8.4, 5.9, 11.2, 6.8],
        "last_4_implied_pcts": [6.5, 5.2, 8.9, 5.8],
        "announce_time_typical": "post",
        "preferred_entry_days_before": 2,
    },
    "AAPL": {
        "beat_rate": 0.58,
        "avg_actual_move_pct": 4.2,
        "avg_implied_move_pct": 3.5,
        "last_4_actual_pcts": [3.8, 5.1, 3.2, 4.7],
        "last_4_implied_pcts": [3.2, 4.1, 2.8, 3.9],
        "announce_time_typical": "post",
        "preferred_entry_days_before": 2,
    },
    "TSLA": {
        "beat_rate": 0.67,
        "avg_actual_move_pct": 10.8,
        "avg_implied_move_pct": 9.1,
        "last_4_actual_pcts": [12.1, 7.8, 14.2, 9.8],
        "last_4_implied_pcts": [10.2, 7.1, 11.8, 8.5],
        "announce_time_typical": "post",
        "preferred_entry_days_before": 2,
    },
    "AMZN": {
        "beat_rate": 0.67,
        "avg_actual_move_pct": 7.1,
        "avg_implied_move_pct": 5.8,
        "last_4_actual_pcts": [6.8, 8.9, 5.4, 7.2],
        "last_4_implied_pcts": [5.5, 7.2, 4.8, 5.9],
        "announce_time_typical": "post",
        "preferred_entry_days_before": 2,
    },
    "GOOGL": {
        "beat_rate": 0.58,
        "avg_actual_move_pct": 6.2,
        "avg_implied_move_pct": 5.1,
        "last_4_actual_pcts": [5.8, 7.4, 4.9, 6.7],
        "last_4_implied_pcts": [4.8, 6.2, 4.1, 5.6],
        "announce_time_typical": "post",
        "preferred_entry_days_before": 2,
    },
}

# Minimum edge score to enter a straddle.
EDGE_THRESHOLD = 0.08

# Maximum position size as fraction of account.
MAX_POSITION_PCT = 0.15


def compute_edge_score(ticker: str) -> float:
    """
    Compute edge score for a ticker.
    Score = beat_rate * (avg_actual / avg_implied - 1.0)
    Returns 0.0 if ticker unknown or no edge.
    """
    data = EARNINGS_HISTORY.get(ticker.upper())
    if not data:
        return 0.0

    beat_rate = data.get("beat_rate", 0.5)
    avg_actual = data.get("avg_actual_move_pct", 0.0)
    avg_implied = data.get("avg_implied_move_pct", 1.0)

    if avg_implied <= 0:
        return 0.0

    move_edge = (avg_actual / avg_implied) - 1.0
    score = beat_rate * max(0.0, move_edge)
    return round(score, 4)


def has_sufficient_edge(
    ticker: str,
    current_implied_move_pct: float = None,
) -> bool:
    """
    Returns True if there is sufficient historical edge to enter a straddle.

    UNIT CONTRACT (critical — do not change without updating both sides):
      EARNINGS_HISTORY.avg_actual_move_pct  — stored in PERCENT (8.6 = 8.6%)
      current_implied_move_pct              — passed in as FRACTION (0.062 = 6.2%)

    Comparison converts historical percent → fraction before comparing.
    Pre-fix bug: the raw percent (8.6) was compared against fraction
    (0.068), which is always False — the "market priced it in" guard
    never fired and every ticker passed through.
    """
    edge = compute_edge_score(ticker)
    if edge < EDGE_THRESHOLD:
        return False

    if current_implied_move_pct is not None and current_implied_move_pct > 0:
        data = EARNINGS_HISTORY.get(ticker.upper(), {})
        avg_actual_pct = data.get("avg_actual_move_pct", 0.0)
        # Convert stored percent to fraction for comparison with live data
        avg_actual_fraction = avg_actual_pct / 100.0
        # Only enter if historical avg actual > 110% of current implied move
        if avg_actual_fraction < current_implied_move_pct * 1.10:
            return False

    return True


def get_position_size_pct(ticker: str, account_value: float) -> float:
    """
    Return fraction of account to allocate to this earnings straddle.
    Scales with edge score, caps at MAX_POSITION_PCT.

    edge 0.08 → 6% of account, edge 0.20+ → 15% max.
    Floors at 5% if we're trading at all.
    """
    edge = compute_edge_score(ticker)
    if edge <= 0:
        return 0.0

    scaled = min(MAX_POSITION_PCT, edge * 0.75)
    scaled = max(0.05, scaled)
    return round(scaled, 4)


def get_entry_days_before(ticker: str) -> int:
    """Return preferred number of trading days before earnings to enter."""
    data = EARNINGS_HISTORY.get(ticker.upper(), {})
    return data.get("preferred_entry_days_before", 2)


# ────────────────────────────────────────────────────────────────────
# 12J — Phase 5B Earnings Learning Loop Scaffold
#
# label_earnings_outcome()  — fires from trade #1, writes one row to
#                             earnings_trade_outcomes per closed
#                             straddle. No warmup gate.
# train_earnings_model()    — self-gates on total_outcomes >= 50.
#                             Below threshold, compute_edge_score()
#                             keeps using the hardcoded EARNINGS_HISTORY
#                             dict above. Above threshold, per-ticker
#                             weights are published to the Redis key
#                             earnings:ticker_weights for any consumer
#                             that wants to prefer learned weights over
#                             the hardcoded defaults.
#
# Neither function raises. Both fail-open: a labeling failure leaves
# the parent close path unaffected, a training failure leaves the
# previous weights (or the hardcoded defaults) in place.
# ────────────────────────────────────────────────────────────────────

# Minimum outcomes before train_earnings_model writes any weights.
# Chosen to match the activation threshold advertised in the
# TASK_REGISTER and the Counterfactual/matrix learning jobs' pattern
# (scaffold early, activate once samples are meaningful).
MIN_EARNINGS_OUTCOMES_FOR_TRAINING = 50

# Minimum per-ticker trades before that ticker gets a learned weight.
# Below this we leave the ticker out of the weights dict — consumers
# must fall back to EARNINGS_HISTORY for unknown tickers anyway, so
# emitting a noisy 2-sample weight would be a regression.
MIN_PER_TICKER_SAMPLES = 3


def label_earnings_outcome(position: dict, redis_client=None) -> dict:
    """
    Label a closed earnings position with outcome data.

    Called from earnings_monitor immediately after a successful
    close_earnings_position() — passes in a dict synthesized from
    the pre-close `earnings_positions` row plus the freshly computed
    exit_value / net_pnl / actual_move_pct.

    Writes one row to earnings_trade_outcomes. Never raises; a
    labeling failure must not fail the parent close path.

    Expected `position` dict fields (from earnings_positions schema,
    plus close-time additions):
        id                   — earnings_positions.id (FK)
        ticker               — ticker symbol
        entry_at             — entry timestamp (may be absent; falls
                               back to entry_date on the row)
        exit_at              — exit timestamp (may be absent; falls
                               back to exit_date)
        total_debit          — premium paid at entry (positive number)
        net_pnl              — realized $ P&L (positive = win)
        implied_move_pct     — expected move at entry (fraction, e.g.
                               0.062 for 6.2%)
        actual_move_pct      — realized move (fraction)
    """
    try:
        from db import get_client

        ticker = (position.get("ticker") or "").upper()
        net_pnl = float(position.get("net_pnl") or 0)
        total_debit = float(position.get("total_debit") or 0)
        expected_move_pct = (
            float(position["implied_move_pct"])
            if position.get("implied_move_pct") is not None
            else None
        )
        actual_move_pct = (
            float(position["actual_move_pct"])
            if position.get("actual_move_pct") is not None
            else None
        )

        # For straddles the "direction correct" question collapses to
        # "did the realized move exceed implied enough to cover debit
        # + slippage". Positive net_pnl is the cleanest proxy at
        # scaffold stage — the training step (train_earnings_model)
        # will refine the definition once 50+ outcomes exist.
        correct_direction = net_pnl > 0
        # iv_crush_captured is true when we WON in spite of IV compressing
        # into the event. Positive P&L with a non-zero debit basis is
        # our best scaffold-stage proxy; can be sharpened later with
        # entry_iv vs exit_iv when that data is persisted.
        iv_crush_captured = net_pnl > 0 and total_debit > 0

        outcome = {
            "position_id": position.get("id"),
            "ticker": ticker,
            "entry_at": position.get("entry_at") or position.get("entry_date"),
            "exit_at": position.get("exit_at") or position.get("exit_date"),
            "correct_direction": correct_direction,
            # pnl_vs_expected = realized P&L as a fraction of premium
            # paid. A scaffold-stage metric; a stricter "vs expected"
            # metric can be added once expected-return modeling
            # lands alongside train_earnings_model.
            "pnl_vs_expected": (
                round(net_pnl / total_debit, 4) if total_debit > 0 else 0.0
            ),
            "iv_crush_captured": iv_crush_captured,
            "expected_move_pct": expected_move_pct,
            "actual_move_pct": actual_move_pct,
            "net_pnl": round(net_pnl, 2),
        }

        get_client().table("earnings_trade_outcomes").insert(outcome).execute()
        logger.info(
            "earnings_outcome_labeled",
            ticker=ticker,
            net_pnl=net_pnl,
            correct_direction=correct_direction,
        )
        return {"labeled": True, "ticker": ticker}

    except Exception as exc:
        logger.warning("earnings_outcome_label_failed", error=str(exc))
        return {"labeled": False, "error": str(exc)}


def train_earnings_model(redis_client=None) -> dict:
    """
    Train per-ticker edge score weights from labeled outcome history.

    Auto-gates on total_outcomes >= MIN_EARNINGS_OUTCOMES_FOR_TRAINING
    (50). Below that threshold, returns trained=False and does NOT
    touch Redis — compute_edge_score() keeps using the hardcoded
    EARNINGS_HISTORY dict.

    Output: writes a JSON dict of per-ticker stats to the Redis key
    earnings:ticker_weights with an 8-day TTL (covers a full weekly
    calibration gap with 1 day of slack). Only tickers with >=
    MIN_PER_TICKER_SAMPLES (3) trades are included — low-sample
    noise would regress signal quality vs. the hardcoded defaults.

    Never raises. A training failure leaves the previous weights
    (or the hardcoded defaults) in place.
    """
    try:
        from db import get_client

        count_result = (
            get_client()
            .table("earnings_trade_outcomes")
            .select("id", count="exact")
            .execute()
        )
        total = count_result.count or 0

        if total < MIN_EARNINGS_OUTCOMES_FOR_TRAINING:
            logger.info(
                "earnings_model_training_skipped",
                total_outcomes=total,
                required=MIN_EARNINGS_OUTCOMES_FOR_TRAINING,
            )
            return {
                "trained": False,
                "total_outcomes": total,
                "required": MIN_EARNINGS_OUTCOMES_FOR_TRAINING,
            }

        result = (
            get_client()
            .table("earnings_trade_outcomes")
            .select("ticker, correct_direction, net_pnl, iv_crush_captured")
            .execute()
        )
        rows = result.data or []

        by_ticker: dict = {}
        for r in rows:
            t = (r.get("ticker") or "").upper()
            if not t:
                continue
            bucket = by_ticker.setdefault(
                t, {"wins": 0, "count": 0, "total_pnl": 0.0}
            )
            bucket["count"] += 1
            bucket["total_pnl"] += float(r.get("net_pnl") or 0)
            if r.get("correct_direction"):
                bucket["wins"] += 1

        import json

        weights: dict = {}
        for ticker, stats in by_ticker.items():
            if stats["count"] >= MIN_PER_TICKER_SAMPLES:
                win_rate = stats["wins"] / stats["count"]
                avg_pnl = stats["total_pnl"] / stats["count"]
                # edge_score blends win-rate (60%) with a normalized
                # avg-$P&L contribution (40%, capped at $200 per trade
                # for the scaffold). Rescale later once the empirical
                # P&L distribution is known from real data.
                avg_pnl_norm = min(1.0, max(0.0, avg_pnl / 200.0))
                weights[ticker] = {
                    "win_rate": round(win_rate, 3),
                    "avg_pnl": round(avg_pnl, 2),
                    "sample_count": stats["count"],
                    "edge_score": round(
                        win_rate * 0.6 + avg_pnl_norm * 0.4, 3
                    ),
                }

        if redis_client and weights:
            try:
                redis_client.setex(
                    "earnings:ticker_weights",
                    86400 * 8,
                    json.dumps(weights),
                )
            except Exception as redis_exc:
                logger.warning(
                    "earnings_weights_redis_write_failed",
                    error=str(redis_exc),
                )

        logger.info(
            "earnings_model_trained",
            tickers=len(weights),
            total_outcomes=total,
        )
        return {
            "trained": True,
            "tickers_calibrated": len(weights),
            "total_outcomes": total,
        }

    except Exception as exc:
        logger.error("earnings_model_training_failed", error=str(exc))
        return {"trained": False, "error": str(exc)}
