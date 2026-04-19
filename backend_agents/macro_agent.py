"""
Macro agent — Phase 2A Tier 2.

Reads today's economic intelligence and enriches it with:
1. CME FedWatch probabilities (free, no auth)
2. Pre-event direction bias from consensus vs history
3. Options-implied expected move from the chain

Writes: Redis key ai:macro:brief (TTL 8hr)
Falls back gracefully — never blocks trading.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional

import httpx

from db import get_client
from logger import get_logger

logger = get_logger("macro_agent")

REQUEST_TIMEOUT = 8.0


def run_macro_agent(redis_client) -> dict:
    """
    Main entry point. Run at 8:30 AM ET on trading days.
    Returns macro brief dict and writes to Redis.
    """
    try:
        # Read today's calendar intel
        intel_raw = redis_client.get("calendar:today:intel") if redis_client else None
        if not intel_raw:
            return _empty_brief("no_calendar_intel")

        intel = json.loads(intel_raw)
        classification = intel.get("day_classification", "normal")

        # Build macro brief
        brief = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "day_classification": classification,
            "events": intel.get("events", []),
            "earnings": intel.get("earnings", []),
            "fed_watch": {},
            "direction_bias": "neutral",
            "direction_confidence": 0.0,
            "expected_move_pct": 0.0,
            "rationale": "",
        }

        # Fed watch probabilities on FOMC days
        if any(
            "Federal Funds" in e.get("event", "") or "FOMC" in e.get("event", "")
            for e in intel.get("events", [])
        ):
            brief["fed_watch"] = _fetch_fed_watch()

        # Direction bias from consensus data
        consensus = intel.get("consensus_data", {})
        bias, conf, rationale = _compute_direction_bias(
            classification, consensus, intel.get("events", [])
        )
        brief["direction_bias"] = bias
        brief["direction_confidence"] = conf
        brief["rationale"] = rationale

        # Expected move from options implied vol
        brief["expected_move_pct"] = _estimate_expected_move(redis_client)

        logger.info(
            "macro_agent_complete",
            classification=classification,
            direction_bias=bias,
            confidence=conf,
            expected_move=brief["expected_move_pct"],
        )

        # Write to Redis (silent: intentional fail-closed path)
        if redis_client:
            try:
                redis_client.setex(
                    "ai:macro:brief",
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
                        "brief_kind": "macro",
                        "payload": brief,
                        "generated_at": datetime.now(timezone.utc).isoformat(),
                    },
                    on_conflict="brief_kind",
                ).execute()
            except Exception as _mirror_exc:
                logger.warning(
                    "macro_agent_supabase_mirror_failed",
                    error=str(_mirror_exc),
                )

        return brief

    except Exception as exc:
        logger.warning("macro_agent_failed", error=str(exc))
        return _empty_brief(str(exc))


def _fetch_fed_watch() -> dict:
    """
    Fetch CME FedWatch probabilities (free public endpoint).
    Returns probability of hold/cut/hike for next FOMC.
    """
    try:
        # CME FedWatch public data
        url = "https://www.cmegroup.com/CmeWS/mvc/ProductCalendar/V2/FedWatch"
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            resp = client.get(url, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code != 200:
            return {}
        data = resp.json()
        # Extract next meeting probabilities
        meetings = data.get("fedFundList", [])
        if not meetings:
            return {}
        next_meeting = meetings[0]
        return {
            "hold_pct": next_meeting.get("noChange", 0),
            "cut_pct": next_meeting.get("decrease", 0),
            "hike_pct": next_meeting.get("increase", 0),
            "meeting_date": next_meeting.get("lastUpdate", ""),
        }
    except Exception:
        return {}


def _compute_direction_bias(
    classification: str,
    consensus: dict,
    events: list,
) -> tuple[str, float, str]:
    """
    Compute pre-event direction bias from consensus data.
    Returns (direction, confidence, rationale).
    """
    if classification == "normal":
        return "neutral", 0.0, "No catalyst today"

    # Look for CPI/PCE data with consensus
    for event_name, data in consensus.items():
        if data.get("estimate") is None:
            continue

        estimate = data["estimate"]
        prev = data.get("prev")

        # CPI/PCE: higher than previous = bearish for equities
        if any(x in event_name for x in ["CPI", "PCE", "PPI"]):
            if prev is not None and estimate > prev:
                return (
                    "bear",
                    0.55,
                    f"{event_name} consensus ({estimate}) above prior ({prev}). "
                    f"Inflationary signal = bearish for SPX.",
                )
            elif prev is not None and estimate < prev:
                return (
                    "bull",
                    0.55,
                    f"{event_name} consensus ({estimate}) below prior ({prev}). "
                    f"Cooling inflation = bullish for SPX.",
                )

        # NFP: higher than previous = neutral to bullish
        if "Nonfarm Payroll" in event_name or "NFP" in event_name:
            if prev is not None and estimate > prev * 1.1:
                return (
                    "bull",
                    0.50,
                    f"Strong NFP consensus ({estimate}k) suggests healthy economy.",
                )

    # FOMC with no rate change expected = mildly bullish
    has_fomc = any("Federal Funds" in e.get("event", "") for e in events)
    if has_fomc:
        return (
            "neutral",
            0.45,
            "FOMC day. Market awaits decision. Size reduced. Straddle recommended.",
        )

    return "neutral", 0.30, f"Catalyst day ({classification}). Monitoring."


def _estimate_expected_move(redis_client) -> float:
    """
    Estimate today's expected SPX move from ATM IV.
    Uses iv_atm from options chain if available.
    Falls back to VIX proxy.
    """
    try:
        # Try to get ATM IV from recent Databento data (via GEX engine)
        iv_raw = redis_client.get("gex:atm_iv") if redis_client else None
        if iv_raw:
            iv_atm = float(iv_raw)
            import math
            return round(iv_atm * math.sqrt(1 / 252) * 100, 2)

        # Fallback: VIX proxy (VIX ≈ annualized vol, divide for daily)
        vix_raw = redis_client.get("polygon:vix:current") if redis_client else None
        if vix_raw:
            vix = float(vix_raw)
            import math
            return round((vix / 100) * math.sqrt(1 / 252) * 100, 2)

        return 0.0
    except Exception:
        return 0.0


def _empty_brief(reason: str = "") -> dict:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "day_classification": "normal",
        "events": [],
        "earnings": [],
        "fed_watch": {},
        "direction_bias": "neutral",
        "direction_confidence": 0.0,
        "expected_move_pct": 0.0,
        "rationale": reason,
    }
