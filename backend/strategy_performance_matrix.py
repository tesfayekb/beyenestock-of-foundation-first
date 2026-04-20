"""D3 — Regime x Strategy Performance Matrix.

Tracks win_rate, avg_pnl, profit_factor per (regime, strategy_type)
cell. Updates daily from closed virtual positions over a 90-day
rolling window. Influences sizing in strategy_selector.select() when
a cell has >= 10 trades AND win_rate < 0.40 (25% size reduction).

Auto-activates from trade 1 — no warmup gate on the collection side.
Sizing influence self-gates on trade_count < 10 (returns 1.0).

Fail-open invariant: every read/write path must return 1.0 (normal
sizing) or an empty summary on ANY error. This observability layer
must never block a trade or crash the EOD job.
"""
from datetime import date, timedelta
from typing import Any, Dict

from logger import get_logger

logger = get_logger("strategy_performance_matrix")


def update_performance_matrix(redis_client) -> Dict[str, Any]:
    """Query last 90 days of closed virtual positions, compute per-cell
    stats in a single pass, persist each cell to Redis.

    Returns summary dict with cells_updated + positions_analyzed for
    the EOD log line. `error` key is populated on failure.
    """
    try:
        from db import get_client

        cutoff = (date.today() - timedelta(days=90)).isoformat()

        result = (
            get_client()
            .table("trading_positions")
            .select("strategy_type, entry_regime, net_pnl, status")
            .eq("status", "closed")
            .eq("position_mode", "virtual")
            .gte("entry_at", cutoff)
            .execute()
        )
        positions = result.data or []

        if not positions:
            logger.info("strategy_matrix_no_data")
            return {"cells_updated": 0, "positions_analyzed": 0}

        # Single-pass aggregation per (regime, strategy) cell.
        # Accumulating gross_profit / gross_loss here avoids the
        # spec's O(N*K) nested-loop profit_factor computation.
        cells: Dict[str, Dict[str, float]] = {}
        for p in positions:
            regime = p.get("entry_regime") or "unknown"
            strategy = p.get("strategy_type") or "unknown"
            pnl = float(p.get("net_pnl") or 0)
            key = f"{regime}:{strategy}"
            cell = cells.setdefault(
                key,
                {
                    "wins": 0,
                    "losses": 0,
                    "total_pnl": 0.0,
                    "gross_profit": 0.0,
                    "gross_loss": 0.0,
                    "count": 0,
                },
            )
            cell["count"] += 1
            cell["total_pnl"] += pnl
            if pnl > 0:
                cell["wins"] += 1
                cell["gross_profit"] += pnl
            else:
                # Breakeven (pnl == 0) counted as a loss — conservative
                # for the sizing gate, matches spec semantics.
                cell["losses"] += 1
                cell["gross_loss"] += abs(pnl)

        cells_updated = 0
        import json
        for cell_key, stats in cells.items():
            count = int(stats["count"])
            wins = int(stats["wins"])
            total_pnl = stats["total_pnl"]
            gross_profit = stats["gross_profit"]
            gross_loss = stats["gross_loss"]

            win_rate = wins / count if count > 0 else 0.0
            avg_pnl = total_pnl / count if count > 0 else 0.0
            # profit_factor = 0.0 when there are no losses — treat
            # "all wins" as a flag value (not inf) so the Redis JSON
            # stays clean. Downstream only gates on win_rate anyway.
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0

            cell_data = {
                "win_rate": round(win_rate, 4),
                "avg_pnl": round(avg_pnl, 2),
                "profit_factor": round(profit_factor, 3),
                "trade_count": count,
            }
            redis_client.setex(
                f"strategy_matrix:{cell_key}",
                86400 * 90,
                json.dumps(cell_data),
            )
            cells_updated += 1

        logger.info(
            "strategy_matrix_updated",
            cells_updated=cells_updated,
            positions_analyzed=len(positions),
        )
        return {
            "cells_updated": cells_updated,
            "positions_analyzed": len(positions),
        }

    except Exception as exc:
        # Observability only — must never crash the EOD job.
        logger.error("strategy_matrix_update_failed", error=str(exc))
        return {
            "cells_updated": 0,
            "positions_analyzed": 0,
            "error": str(exc),
        }


def get_matrix_sizing_multiplier(
    redis_client,
    regime: str,
    strategy_type: str,
) -> float:
    """Return sizing multiplier for a (regime, strategy) cell.

    Rules:
      * No cell data in Redis    -> 1.0 (cold start, first trade in
        cell — never punish unknown states).
      * trade_count < 10         -> 1.0 (insufficient sample, reduces
        variance noise from masquerading as real edge loss).
      * win_rate < 0.40          -> 0.75 (25% cut on proven losers).
      * win_rate >= 0.40         -> 1.0 (normal sizing).

    Fail-open: any Redis/JSON error returns 1.0 so a bad Redis read
    never blocks a trade or crashes select().
    """
    try:
        if redis_client is None:
            return 1.0

        import json
        cell_key = f"{regime}:{strategy_type}"
        raw = redis_client.get(f"strategy_matrix:{cell_key}")
        if not raw:
            return 1.0

        cell_data = json.loads(raw)
        trade_count = int(cell_data.get("trade_count", 0))
        # Default 1.0 on missing key so a malformed cell never
        # accidentally crosses the 0.40 threshold.
        win_rate = float(cell_data.get("win_rate", 1.0))

        if trade_count < 10:
            return 1.0

        if win_rate < 0.40:
            logger.info(
                "strategy_matrix_sizing_reduced",
                regime=regime,
                strategy=strategy_type,
                win_rate=win_rate,
                trade_count=trade_count,
                multiplier=0.75,
            )
            return 0.75

        return 1.0

    except Exception:
        # Fail-open — never let an observability read block a trade.
        return 1.0


def run_matrix_update(redis_client) -> Dict[str, Any]:
    """
    Entry point invoked by the scheduled EOD job in main.py.

    Writes `trading_system_health` so the Engine Health admin page
    reflects the last run. Per-run stats land in the `details` JSONB
    column — `trading_system_health` has no `cells_updated` /
    `positions_analyzed` columns, so passing them directly would
    silently fail the upsert. Health writes are wrapped in their own
    try/except so an observability failure can never mask the real
    result of the matrix update.
    """
    try:
        result = update_performance_matrix(redis_client)
        try:
            from db import write_health_status
            write_health_status(
                "strategy_matrix",
                "idle",
                details={
                    "cells_updated": result.get("cells_updated", 0),
                    "positions_analyzed": result.get(
                        "positions_analyzed", 0
                    ),
                },
            )
        except Exception:
            pass  # observability must never mask the real result
        return result
    except Exception as exc:
        try:
            from db import write_health_status
            write_health_status(
                "strategy_matrix",
                "error",
                last_error_message=str(exc),
            )
        except Exception:
            pass
        logger.error("run_matrix_update_failed", error=str(exc))
        return {
            "cells_updated": 0,
            "positions_analyzed": 0,
            "error": str(exc),
        }
