"""
Options flow intelligence agent — Phase 2C.

Reads unusual options activity to detect institutional positioning.
Two sources:
  1. Unusual Whales API (paid) — large unusual trades, dark pool prints
  2. Polygon put/call ratio (already subscribed) — free, directional

Computes a single flow_score: -100 (extreme put flow) to +100 (extreme call flow).
Writes: Redis ai:flow:brief (TTL 8hr).
Refreshes: every 30 min during market hours (lightweight update).

Falls back gracefully — never blocks synthesis.

NOTE: `import config` is at module level (not lazy) so that
`unittest.mock.patch("flow_agent.config")` resolves correctly. This pattern
matches the Phase 2A fix in synthesis_agent.py.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import httpx

import config
from db import get_client
from logger import get_logger

logger = get_logger("flow_agent")

REQUEST_TIMEOUT = 8.0

# Thresholds for classifying flow signals
STRONG_FLOW_THRESHOLD = 60    # |flow_score| > 60 = strong directional signal
MODERATE_FLOW_THRESHOLD = 30  # |flow_score| > 30 = moderate signal


def run_flow_agent(redis_client) -> dict:
    """
    Main entry point. Run at 8:45 AM ET and every 30 min during market hours.
    Returns flow brief dict and writes to Redis (best-effort).
    Never raises.
    """
    try:
        uw_data = (
            _fetch_unusual_whales(config)
            if getattr(config, "UNUSUAL_WHALES_API_KEY", "")
            else {}
        )
        pc_data = (
            _fetch_polygon_put_call(config)
            if getattr(config, "POLYGON_API_KEY", "")
            else {}
        )

        flow_score, flow_signals = _compute_flow_score(uw_data, pc_data)

        if flow_score >= STRONG_FLOW_THRESHOLD:
            flow_direction = "bull"
            flow_confidence = min(0.75, flow_score / 100)
        elif flow_score <= -STRONG_FLOW_THRESHOLD:
            flow_direction = "bear"
            flow_confidence = min(0.75, abs(flow_score) / 100)
        elif flow_score >= MODERATE_FLOW_THRESHOLD:
            flow_direction = "bull"
            flow_confidence = 0.45
        elif flow_score <= -MODERATE_FLOW_THRESHOLD:
            flow_direction = "bear"
            flow_confidence = 0.45
        else:
            flow_direction = "neutral"
            flow_confidence = 0.20

        brief = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "flow_score": flow_score,            # -100 to +100
            "flow_direction": flow_direction,    # bull/bear/neutral
            "flow_confidence": flow_confidence,  # 0.0 to 0.75
            "signals": flow_signals,             # list of contributing signals
            "put_call_ratio": pc_data.get("ratio"),
            "unusual_activity_count": len(uw_data.get("alerts", [])),
        }

        logger.info(
            "flow_agent_complete",
            flow_score=flow_score,
            direction=flow_direction,
            confidence=flow_confidence,
            signals=len(flow_signals),
        )

        # Phase 2C Session 2: per-agent feature flag gates the WRITE only.
        # The brief is always returned to the caller; downstream synthesis
        # consumes whatever is present in Redis, so flag OFF = no influence
        # without losing the in-process brief.
        if redis_client:
            flag_on = False
            try:
                flag = redis_client.get("agents:flow_agent:enabled")
                flag_on = flag in ("true", b"true")
            except Exception:
                flag_on = False  # fail closed — never write on flag-read error

            if flag_on:
                # Redis write — intentionally silent fail-closed path.
                try:
                    redis_client.setex(
                        "ai:flow:brief",
                        28800,  # 8 hours
                        json.dumps(brief),
                    )
                except Exception:
                    pass  # Redis write failure must never block return

                # CSP-fix mirror: dashboard reads via direct supabase-js.
                # C-5: log mirror failures so silent RLS / schema breakage
                # is visible in Railway. Bare except: pass previously
                # masked these from operators.
                try:
                    get_client().table("trading_ai_briefs").upsert(
                        {
                            "brief_kind": "flow",
                            "payload": brief,
                            "generated_at": datetime.now(timezone.utc).isoformat(),
                        },
                        on_conflict="brief_kind",
                    ).execute()
                except Exception as _mirror_exc:
                    logger.warning(
                        "flow_agent_supabase_mirror_failed",
                        error=str(_mirror_exc),
                    )
            else:
                logger.debug(
                    "flow_agent_flag_off_skipping_redis_write",
                    flow_score=flow_score,
                )

        return brief

    except Exception as exc:
        logger.warning("flow_agent_failed", error=str(exc))
        return _empty_brief()


def _fetch_unusual_whales(cfg) -> dict:
    """
    Fetch unusual options activity from Unusual Whales API.
    Returns dict with alerts list. Empty dict on any failure.
    """
    try:
        url = "https://api.unusualwhales.com/api/option-trades/flow-alerts"
        headers = {
            "Authorization": f"Bearer {cfg.UNUSUAL_WHALES_API_KEY}",
            "Content-Type": "application/json",
        }
        params = {"ticker": "SPX", "limit": 20}
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            resp = client.get(url, headers=headers, params=params)

        if resp.status_code != 200:
            # Try SPXW as fallback
            params["ticker"] = "SPXW"
            with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
                resp = client.get(url, headers=headers, params=params)

        if resp.status_code != 200:
            return {}

        data = resp.json()
        alerts = data.get("data", []) or data.get("alerts", [])
        return {"alerts": alerts[:20]}

    except Exception as exc:
        logger.warning("unusual_whales_fetch_failed", error=str(exc))
        return {}


def _fetch_polygon_put_call(cfg) -> dict:
    """
    Fetch SPX put/call ratio from Polygon options snapshot.
    Returns put/call volume breakdown plus ratio. Empty dict on failure.
    """
    try:
        from datetime import date
        today = date.today().isoformat()

        url = (
            f"https://api.polygon.io/v3/snapshot/options/I:SPX"
            f"?expiration_date={today}"
            f"&limit=250"
            f"&apiKey={cfg.POLYGON_API_KEY}"
        )
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            resp = client.get(url)

        if resp.status_code != 200:
            return {}

        data = resp.json()
        results = data.get("results", [])
        if not results:
            return {}

        call_volume = sum(
            r.get("day", {}).get("volume", 0) or 0
            for r in results
            if r.get("details", {}).get("contract_type") == "call"
        )
        put_volume = sum(
            r.get("day", {}).get("volume", 0) or 0
            for r in results
            if r.get("details", {}).get("contract_type") == "put"
        )

        total = call_volume + put_volume
        if total == 0:
            return {}

        ratio = (
            round(put_volume / call_volume, 3)
            if call_volume > 0 else 1.0
        )

        return {
            "put_volume": put_volume,
            "call_volume": call_volume,
            "ratio": ratio,           # < 0.7 bullish, > 1.3 bearish
            "total_volume": total,
        }

    except Exception as exc:
        logger.warning("polygon_put_call_failed", error=str(exc))
        return {}


def _compute_flow_score(uw_data: dict, pc_data: dict) -> tuple[int, list]:
    """
    Compute composite flow score from all sources.
    Returns (score: -100 to +100, signals: list of contributing signals).
    Pure function — no side effects, fully testable.
    """
    score = 0
    signals = []

    # Polygon put/call ratio
    ratio = pc_data.get("ratio")
    if ratio is not None:
        if ratio < 0.5:
            contribution = 40
            signals.append({
                "source": "put_call_ratio", "value": ratio,
                "signal": "strong_bull", "contribution": contribution,
            })
        elif ratio < 0.7:
            contribution = 25
            signals.append({
                "source": "put_call_ratio", "value": ratio,
                "signal": "bull", "contribution": contribution,
            })
        elif ratio > 1.5:
            contribution = -40
            signals.append({
                "source": "put_call_ratio", "value": ratio,
                "signal": "strong_bear", "contribution": contribution,
            })
        elif ratio > 1.2:
            contribution = -25
            signals.append({
                "source": "put_call_ratio", "value": ratio,
                "signal": "bear", "contribution": contribution,
            })
        else:
            contribution = 0
            signals.append({
                "source": "put_call_ratio", "value": ratio,
                "signal": "neutral", "contribution": 0,
            })
        score += contribution

    # Unusual Whales alerts — classify call vs put bias by premium
    alerts = uw_data.get("alerts", [])
    if alerts:
        call_premium = 0.0
        put_premium = 0.0
        for alert in alerts:
            premium = float(
                alert.get("premium", 0)
                or alert.get("cost_basis", 0)
                or 0
            )
            side = str(
                alert.get("put_call", "")
                or alert.get("contract_type", "")
            ).lower()
            if "call" in side:
                call_premium += premium
            elif "put" in side:
                put_premium += premium

        total_premium = call_premium + put_premium
        if total_premium > 0:
            call_bias = (call_premium - put_premium) / total_premium
            uw_contribution = int(call_bias * 50)  # -50 to +50
            signals.append({
                "source": "unusual_whales",
                "call_premium": round(call_premium),
                "put_premium": round(put_premium),
                "bias": round(call_bias, 3),
                "contribution": uw_contribution,
            })
            score += uw_contribution

    # Clamp final score
    score = max(-100, min(100, score))
    return score, signals


def _empty_brief() -> dict:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "flow_score": 0,
        "flow_direction": "neutral",
        "flow_confidence": 0.0,
        "signals": [],
        "put_call_ratio": None,
        "unusual_activity_count": 0,
    }
