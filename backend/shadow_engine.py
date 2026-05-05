"""
Phase 3B: Shadow Engine — Portfolio A (rule-based baseline).

Runs the GEX/ZG rule-based prediction logic independently on every
trading cycle and records what the system WOULD do without AI synthesis.

This is Portfolio A in the 90-day A/B validation:
  Portfolio A = rule-based only (this module)
  Portfolio B = full AI system (real paper trading)

Design constraints (enforced by tests):
  - NEVER imports from prediction_engine.py — re-implements the
    rule-based logic independently. The "never-reads-synthesis"
    test in test_shadow_engine.py guards this contract.
  - NEVER reads ai:synthesis:latest, agent flags, or agent briefs.
  - Uses the same VVIX/GEX/VIX thresholds as prediction_engine.py
    rule-based path. If prediction_engine's regime thresholds change,
    update _VVIX_HIGH_Z / _VVIX_MEDIUM_Z / _VVIX_EMERGENCY_Z below.
  - NEVER opens positions — writes one row to shadow_predictions only.
  - Silently skips on any error — never interrupts the real trading
    cycle. trading_cycle.py wraps the call in a bare try/except: pass.
"""

from __future__ import annotations

from typing import Optional

from db import get_client
from logger import get_logger
from polygon_index_helpers import parse_polygon_index_value

logger = get_logger("shadow_engine")

# These thresholds MIRROR prediction_engine.py rule-based logic.
# Confirmed against prediction_engine.py classify_regime() and the
# D-018 emergency check (vvix_z >= 3.0). If prediction_engine changes
# its regime thresholds, update these too.
_VVIX_HIGH_Z       = 2.5    # |vvix_z| > this → volatile_*
_VVIX_MEDIUM_Z     = 1.5    # |vvix_z| > this → quiet_bullish
_VVIX_EMERGENCY_Z  = 3.0    # vvix_z >= this → no_trade (D-018)
_GEX_PIN_RANGE_PCT = 0.3    # SPX within this % of nearest wall = pin
_RCS_HIGH          = 75.0
_RCS_MEDIUM        = 50.0
_RCS_LOW           = 30.0
_CONFIDENCE_THRESHOLD = 0.55   # below this for non-neutral → no_trade


def run_shadow_cycle(redis_client, session_id: str) -> Optional[dict]:
    """
    Run one shadow prediction cycle (rule-based only, no AI synthesis).
    Writes one row to shadow_predictions.
    Returns the shadow prediction dict or None on failure.
    Never raises.
    """
    try:
        prediction = _compute_rule_based_prediction(redis_client)
        if not prediction:
            return None

        row = {
            "session_id":      session_id,
            "direction":       prediction["direction"],
            "confidence":      prediction["confidence"],
            "regime":          prediction["regime"],
            "rcs":             prediction["rcs"],
            "no_trade_signal": prediction["no_trade_signal"],
            "no_trade_reason": prediction.get("no_trade_reason"),
            "vix":             prediction.get("vix"),
            "vvix_z_score":    prediction.get("vvix_z_score"),
            "gex_net":         prediction.get("gex_net"),
            "spx_price":       prediction.get("spx_price"),
        }

        get_client().table("shadow_predictions").insert(row).execute()

        logger.debug(
            "shadow_cycle_complete",
            direction=prediction["direction"],
            regime=prediction["regime"],
            no_trade=prediction["no_trade_signal"],
        )
        return prediction

    except Exception as exc:
        logger.warning("shadow_cycle_failed", error=str(exc))
        return None


def _read(redis_client, key: str, default=None):
    """Safe Redis read — returns default on any failure or missing key."""
    if not redis_client:
        return default
    try:
        val = redis_client.get(key)
        if val is None:
            return default
        # decode_responses=True usually returns str, but tolerate bytes
        if isinstance(val, bytes):
            val = val.decode()
        return val
    except Exception:
        return default


def _compute_rule_based_prediction(redis_client) -> Optional[dict]:
    """
    Compute rule-based regime + direction using ONLY GEX/VIX/VVIX.
    No AI synthesis. No agent flags. No external API calls.
    Mirrors prediction_engine.py's rule-based path.
    """
    try:
        # Read market data from Redis (same keys as prediction_engine).
        # Strategy/agent keys are intentionally absent from this list.
        # T-ACT-062: polygon:vix:current is now a JSON envelope post-
        # PR `feat/t-act-062-vix-vvix-freshness-guard`. Read with the
        # default sentinel ``None`` (instead of "18.0") and parse via
        # the shared backward-compatible helper below; legacy raw-
        # float values still in cache during the rollover window
        # deserialize correctly via the same path.
        raw_vix       = _read(redis_client, "polygon:vix:current", None)
        raw_vvix_z    = _read(redis_client, "polygon:vvix:z_score", "0.0")
        raw_gex_net   = _read(redis_client, "gex:net", "0")
        raw_gex_conf  = _read(redis_client, "gex:confidence", "0.5")
        # 2026-05-01 SPX-real-time-feed fix: read polygon:spx:current first
        # (real-time), fall back to tradier:quotes:SPX (15-min delayed).
        # Mirrors prediction_engine._get_spx_price() priority chain so the
        # shadow harness sees the same SPX value the production path sees.
        raw_spx_polygon = _read(redis_client, "polygon:spx:current", None)
        raw_spx_tradier = _read(redis_client, "tradier:quotes:SPX", None)
        raw_flip_zone = _read(redis_client, "gex:flip_zone", "0")
        raw_wall      = _read(redis_client, "gex:nearest_wall", "0")

        vix          = parse_polygon_index_value(raw_vix, 18.0)
        vvix_z       = float(raw_vvix_z)
        gex_net      = float(raw_gex_net)
        gex_conf     = float(raw_gex_conf)
        # SPX parser: try polygon:spx:current (price field) first; fall
        # back to tradier:quotes:SPX (last/ask/bid). Both are JSON strings.
        # Bug-fix history: tradier:quotes:SPX is a JSON string written by
        # tradier_feed ({"last":..., "bid":..., "ask":..., ...}), not a
        # plain float — previous float(raw_spx) crashed every shadow cycle.
        spx_price = 5200.0
        try:
            import json as _json
            if raw_spx_polygon:
                poly_data = _json.loads(raw_spx_polygon)
                if isinstance(poly_data, dict):
                    candidate = float(poly_data.get("price") or 0)
                    if candidate > 0:
                        spx_price = candidate
            if spx_price == 5200.0 and raw_spx_tradier:
                trad_data = _json.loads(raw_spx_tradier)
                if isinstance(trad_data, dict):
                    spx_price = float(
                        trad_data.get("last")
                        or trad_data.get("ask")
                        or trad_data.get("bid")
                        or 5200.0
                    )
                else:
                    # Defensive fallback: someone wrote a plain numeric
                    # (e.g. legacy cache) — accept it rather than crash.
                    spx_price = float(raw_spx_tradier)
        except (ValueError, TypeError, _json.JSONDecodeError):
            spx_price = 5200.0
        flip_zone    = float(raw_flip_zone)
        nearest_wall = float(raw_wall) if raw_wall else 0.0

        # ── Regime Classification (mirrors prediction_engine.py) ──────
        if nearest_wall > 0:
            pct_from_wall = abs(spx_price - nearest_wall) / spx_price
            if pct_from_wall <= _GEX_PIN_RANGE_PCT / 100:
                regime = "pin_range"
            elif abs(vvix_z) > _VVIX_HIGH_Z:
                regime = (
                    "volatile_bearish" if vvix_z > 0
                    else "volatile_bullish"
                )
            elif vix > 30:
                regime = "crisis"
            elif vix > 20:
                if abs(vvix_z) > _VVIX_MEDIUM_Z:
                    regime = "volatile_bearish"
                else:
                    regime = "range"
            elif gex_net > 500_000_000:
                regime = "pin_range"
            else:
                regime = "quiet_bullish"
        else:
            regime = "quiet_bullish"

        # ── RCS (Regime Confidence Score) ─────────────────────────────
        if abs(vvix_z) <= 0.5 and vix < 20 and gex_conf >= 0.7:
            rcs = _RCS_HIGH + (80 - _RCS_HIGH) * (1 - abs(vvix_z) / 2)
        elif abs(vvix_z) <= 1.5:
            rcs = _RCS_MEDIUM
        elif abs(vvix_z) <= 2.5:
            rcs = _RCS_LOW
        else:
            rcs = 10.0

        rcs = max(0.0, min(100.0, rcs))

        # ── Direction (rule-based: neutral unless strong GEX signal) ──
        # Near flip zone (within 2%) → uncertain
        if flip_zone > 0 and abs(flip_zone - spx_price) / spx_price < 0.02:
            direction = "neutral"
            confidence = 0.45
        elif gex_net > 1_000_000_000 and abs(vvix_z) < 0.5:
            # Strong positive GEX + calm vol → mean-reversion regime
            direction = "neutral"
            confidence = 0.60
        elif gex_net < -500_000_000 and vvix_z > 1.0:
            direction = "bear"
            confidence = 0.52
        else:
            direction = "neutral"
            confidence = 0.48

        # ── No-trade conditions (mirrors D-018 + RCS gate) ────────────
        no_trade = False
        no_trade_reason: Optional[str] = None

        if vvix_z >= _VVIX_EMERGENCY_Z:
            no_trade = True
            no_trade_reason = f"vvix_emergency_z_{vvix_z:.2f}"
        elif rcs < 20:
            no_trade = True
            no_trade_reason = "rcs_danger_zone"
        elif regime == "crisis":
            no_trade = True
            no_trade_reason = "crisis_regime"
        elif (
            confidence < _CONFIDENCE_THRESHOLD
            and direction != "neutral"
        ):
            no_trade = True
            no_trade_reason = "low_confidence"

        return {
            "direction":       direction,
            "confidence":      round(confidence, 4),
            "regime":          regime,
            "rcs":             round(rcs, 2),
            "no_trade_signal": no_trade,
            "no_trade_reason": no_trade_reason,
            "vix":             round(vix, 4),
            "vvix_z_score":    round(vvix_z, 4),
            "gex_net":         round(gex_net, 2),
            "spx_price":       round(spx_price, 4),
        }

    except Exception as exc:
        logger.warning(
            "shadow_prediction_compute_failed", error=str(exc)
        )
        return None


def compute_eod_comparison(
    session_date: str, redis_client
) -> Optional[dict]:
    """
    Compute end-of-day A/B comparison for a given session date.
    Called at 4:30 PM ET after market close.

    Fetches:
      - Portfolio A: best shadow prediction of the day (highest confidence)
      - Portfolio B: actual session P&L from trading_sessions
      - Actual market: SPX open and close from Redis/Polygon

    Computes Portfolio A synthetic P&L using a simplified iron-condor model:
      - no_trade_signal=True → P&L = 0 (correctly sat out)
      - traded + |move| < 0.5% → P&L = +$120 (typical condor profit)
      - traded + 0.5% <= |move| < 1.0% → P&L = -$50 (partial loss)
      - traded + |move| >= 1.0% → P&L = -$300 (condor blowout)
    Rough by design — adequate for 90-day A/B comparison.
    Upserts on session_date so the job is idempotent.
    """
    try:
        client = get_client()

        session_result = (
            client.table("trading_sessions")
            .select("id, virtual_pnl, virtual_trades_count")
            .eq("session_date", session_date)
            .maybe_single()
            .execute()
        )
        session = session_result.data
        if not session:
            return None

        session_id = session["id"]
        b_pnl = float(session.get("virtual_pnl") or 0)
        b_trades = int(session.get("virtual_trades_count") or 0)
        b_no_trade = b_trades == 0

        shadow_result = (
            client.table("shadow_predictions")
            .select("*")
            .eq("session_id", session_id)
            .order("confidence", desc=True)
            .limit(1)
            .execute()
        )
        shadow_rows = shadow_result.data or []
        if not shadow_rows:
            return None

        shadow = shadow_rows[0]
        a_no_trade = shadow.get("no_trade_signal", True)
        a_direction = shadow.get("direction", "neutral")
        a_confidence = float(shadow.get("confidence") or 0)
        a_regime = shadow.get("regime", "unknown")

        spx_open = float(_read(redis_client, "polygon:spx:open", "0") or 0)
        spx_close = float(
            _read(redis_client, "polygon:spx:close", "0") or 0
        )

        move_pct = 0.0
        if spx_open > 0 and spx_close > 0:
            move_pct = abs((spx_close - spx_open) / spx_open)

        a_would_trade = not a_no_trade
        if not a_would_trade:
            a_synthetic_pnl = 0.0
        elif move_pct < 0.005:
            a_synthetic_pnl = 120.0
        elif move_pct < 0.010:
            a_synthetic_pnl = -50.0
        else:
            a_synthetic_pnl = -300.0

        row = {
            "session_date":        session_date,
            "a_no_trade":          a_no_trade,
            "a_direction":         a_direction,
            "a_confidence":        round(a_confidence, 4),
            "a_regime":            a_regime,
            "a_synthetic_pnl":     a_synthetic_pnl,
            "a_would_have_traded": a_would_trade,
            "b_session_pnl":       b_pnl,
            "b_trades_count":      b_trades,
            "b_no_trade":          b_no_trade,
            "spx_open":            round(spx_open, 4) if spx_open else None,
            "spx_close":           round(spx_close, 4) if spx_close else None,
            "move_pct":            round(move_pct, 6),
        }

        client.table("ab_session_comparison").upsert(
            row, on_conflict="session_date"
        ).execute()

        logger.info(
            "ab_eod_comparison_computed",
            session_date=session_date,
            a_pnl=a_synthetic_pnl,
            b_pnl=b_pnl,
            move_pct=round(move_pct * 100, 2),
        )
        return row

    except Exception as exc:
        logger.warning(
            "ab_eod_comparison_failed",
            error=str(exc),
            date=session_date,
        )
        return None


def get_ab_gate_status() -> dict:
    """
    Compute current A/B gate status.
    Gate requires: ≥90 calendar days + ≥100 closed trades + Portfolio B
    annualized return ≥ Portfolio A annualized return + 8%.
    Always returns a dict — never raises.
    """
    try:
        client = get_client()

        result = (
            client.table("ab_session_comparison")
            .select("session_date, a_synthetic_pnl, b_session_pnl")
            .order("session_date", desc=False)
            .execute()
        )
        rows = result.data or []

        if not rows:
            return {
                "built":                True,
                "days_elapsed":         0,
                "days_required":        90,
                "trades_count":         0,
                "trades_required":      100,
                "portfolio_b_lead_pct": None,
                "gate_passed":          False,
            }

        from datetime import date
        first_date = date.fromisoformat(rows[0]["session_date"])
        days_elapsed = (date.today() - first_date).days

        a_total = sum(
            float(r.get("a_synthetic_pnl") or 0) for r in rows
        )
        b_total = sum(
            float(r.get("b_session_pnl") or 0) for r in rows
        )

        tc_result = (
            client.table("trading_positions")
            .select("id", count="exact")
            .eq("status", "closed")
            .eq("position_mode", "virtual")
            .execute()
        )
        closed_trades = tc_result.count or 0

        # S11: annualize using LIVE deployed capital instead of the old
        # hardcoded $100k. shadow_engine runs post-market when Tradier
        # may be closed (cached value still works); on any failure we
        # fall back to 100_000.0 because shadow analytics must never
        # block — it's a research surface, not a trading decision.
        try:
            from capital_manager import get_deployed_capital
            account = get_deployed_capital(
                getattr(self, "redis_client", None)
            )
        except Exception:
            account = 100_000.0  # graceful fallback for shadow analytics
        trading_days = len(rows)
        if trading_days > 0:
            a_annualized = (a_total / account) / trading_days * 252 * 100
            b_annualized = (b_total / account) / trading_days * 252 * 100
            b_lead = b_annualized - a_annualized
        else:
            a_annualized = b_annualized = b_lead = 0.0

        gate_passed = (
            days_elapsed >= 90
            and closed_trades >= 100
            and b_lead >= 8.0
        )

        return {
            "built":                True,
            "days_elapsed":         days_elapsed,
            "days_required":        90,
            "trades_count":         closed_trades,
            "trades_required":      100,
            "a_total_pnl":          round(a_total, 2),
            "b_total_pnl":          round(b_total, 2),
            "a_annualized_pct":     round(a_annualized, 2),
            "b_annualized_pct":     round(b_annualized, 2),
            "portfolio_b_lead_pct": round(b_lead, 2),
            "gate_passed":          gate_passed,
        }

    except Exception as exc:
        logger.warning("ab_gate_status_failed", error=str(exc))
        return {
            "built":                True,
            "days_elapsed":         0,
            "days_required":        90,
            "gate_passed":          False,
            "portfolio_b_lead_pct": None,
        }
