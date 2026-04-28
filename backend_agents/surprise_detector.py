"""
Post-event surprise detector — Phase 2A Tier 3.

Runs at 8:45 AM ET on catalyst days (15 min after major releases).
Reads Finnhub actual vs consensus and classifies the surprise.
Updates ai:synthesis:latest with surprise-informed direction.

Why this matters: the market reaction is driven by SURPRISE vs consensus,
not the absolute value. A 0.3% CPI print = bullish if consensus was 0.4%.
Same print = bearish if consensus was 0.2%.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional

import httpx

from _synthesis_schema import validate_synthesis_payload
from db import get_client
from logger import get_logger

logger = get_logger("surprise_detector")

REQUEST_TIMEOUT = 6.0

# Surprise thresholds
LARGE_SURPRISE_THRESHOLD = 0.15  # 15% deviation from consensus = large surprise
SMALL_SURPRISE_THRESHOLD = 0.05  # 5% = small surprise


def _classify_direction(event_name: str, deviation: float) -> str:
    """T1-10: classify the directional surprise for a macro event.

    Pure function — event family matching plus deviation-bucket logic.
    Extracted from _detect_surprises so the NFP polarity fix is
    independently testable.

    NFP polarity was previously broken: only three branches existed
    (<5% = bull, >10% = bear, else = bear). The `else` swept in the
    5-10% positive-deviation band ("mild jobs beat") and classified
    it as bearish "too cold" — the opposite of the actual market
    reaction. NFP prints in that band are Goldilocks: strong enough
    to confirm growth, weak enough to keep the Fed benign.

    Polarity now:
      * > +10%  bear (too hot — Fed tightening risk)
      * +5% to +10%  bull (mild beat — Goldilocks)
      * -5% to +5%  bull (inline — slight positive bias)
      * -10% to -5%  bull (mild miss — Fed less hawkish)
      * < -10%  bear (recession fear)
    """
    if any(x in event_name for x in ["CPI", "PCE", "PPI"]):
        # Higher inflation = bearish for SPX
        return "bear" if deviation > 0 else "bull"

    if any(x in event_name for x in ["Nonfarm", "Employment", "NFP", "ADP"]):
        # T1-10: explicit branches — see docstring for the polarity map.
        # Do NOT collapse the "mild beat" and "inline" branches into a
        # single `abs(deviation) < 0.05` — the inline zone extends only
        # to -5% on the miss side (anything beyond is a mild miss which
        # still returns bull, but via a different semantic branch).
        if deviation > 0.10:
            return "bear"   # Too hot — Fed tightening risk
        if deviation >= 0.05:
            return "bull"   # Mild beat — Goldilocks
        if deviation > -0.05:
            return "bull"   # Inline — slight positive bias
        if deviation >= -0.10:
            return "bull"   # Mild miss — Fed less hawkish
        return "bear"       # Too cold — recession fear

    if "Federal Funds" in event_name:
        return "neutral"  # Rate decisions require more context

    # Generic: a beat on anything else we have no special polarity for
    # is treated as growth-positive (bull), a miss as bearish.
    return "bull" if deviation < 0 else "bear"


def run_surprise_detector(redis_client) -> dict:
    """
    Main entry point. Run at 8:45 AM ET on catalyst days.
    Returns surprise analysis and updates ai:synthesis:latest.
    """
    try:
        # Only run on catalyst days
        intel_raw = redis_client.get("calendar:today:intel") if redis_client else None
        if not intel_raw:
            return {}

        intel = json.loads(intel_raw)
        if intel.get("day_classification") not in (
            "catalyst_major", "catalyst_minor"
        ):
            return {}  # Not a catalyst day — skip

        # Get latest consensus data from Finnhub (post-release)
        surprises = _detect_surprises(intel)

        if not surprises:
            return {}

        # Classify overall surprise
        overall = _classify_overall_surprise(surprises)

        logger.info(
            "surprise_detected",
            surprises=len(surprises),
            direction=overall.get("direction"),
            magnitude=overall.get("magnitude"),
        )

        # Update synthesis in Redis if surprises detected
        _update_synthesis(redis_client, overall, surprises)

        return overall

    except Exception as exc:
        logger.warning("surprise_detector_failed", error=str(exc))
        return {}


def _detect_surprises(intel: dict) -> list[dict]:
    """
    Check each event's actual vs consensus.
    Returns list of surprise dicts.
    """
    surprises = []
    consensus_data = intel.get("consensus_data", {})

    for event_name, data in consensus_data.items():
        actual = data.get("actual")
        estimate = data.get("estimate")

        if actual is None or estimate is None:
            continue

        if estimate == 0:
            continue

        deviation = (actual - estimate) / abs(estimate)

        # T1-10: direction classification extracted to a pure module-level
        # helper so it is independently testable without a live Finnhub
        # payload. Same behaviour as before for CPI/PCE/PPI/Fed/generic,
        # but fixes the NFP fall-through bug — see _classify_direction.
        direction = _classify_direction(event_name, deviation)

        magnitude = (
            "large" if abs(deviation) > LARGE_SURPRISE_THRESHOLD
            else "small" if abs(deviation) > SMALL_SURPRISE_THRESHOLD
            else "inline"
        )

        surprises.append({
            "event": event_name,
            "actual": actual,
            "estimate": estimate,
            "deviation_pct": round(deviation * 100, 2),
            "direction": direction,
            "magnitude": magnitude,
        })

    return surprises


def _classify_overall_surprise(surprises: list[dict]) -> dict:
    """Aggregate multiple surprises into single direction + magnitude."""
    if not surprises:
        return {"direction": "neutral", "magnitude": "none", "confidence": 0.0}

    # Weight large surprises more heavily
    bull_score = 0.0
    bear_score = 0.0

    for s in surprises:
        weight = 2.0 if s["magnitude"] == "large" else 0.5
        if s["direction"] == "bull":
            bull_score += weight
        elif s["direction"] == "bear":
            bear_score += weight

    total = bull_score + bear_score
    if total == 0:
        return {"direction": "neutral", "magnitude": "none", "confidence": 0.0}

    if bull_score > bear_score * 1.5:
        direction = "bull"
        confidence = min(0.75, bull_score / total)
    elif bear_score > bull_score * 1.5:
        direction = "bear"
        confidence = min(0.75, bear_score / total)
    else:
        direction = "neutral"
        confidence = 0.30

    max_magnitude = (
        "large" if any(s["magnitude"] == "large" for s in surprises)
        else "small"
    )

    return {
        "direction": direction,
        "magnitude": max_magnitude,
        "confidence": round(confidence, 3),
        "surprises": surprises,
    }


def _update_synthesis(redis_client, overall: dict, surprises: list) -> None:
    """Update ai:synthesis:latest with surprise-informed direction."""
    try:
        if not redis_client or overall.get("direction") == "neutral":
            return

        # Read existing synthesis
        existing_raw = redis_client.get("ai:synthesis:latest")
        existing = json.loads(existing_raw) if existing_raw else {}

        # Update with surprise data
        existing.update({
            "direction": overall["direction"],
            "confidence": overall["confidence"],
            "surprise_detected": True,
            "surprise_magnitude": overall["magnitude"],
            "surprise_detail": surprises,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })

        # Update strategy based on surprise
        if overall["magnitude"] == "large" and overall["confidence"] > 0.60:
            if overall["direction"] == "bull":
                existing["strategy"] = "debit_call_spread"
            elif overall["direction"] == "bear":
                existing["strategy"] = "debit_put_spread"

        # Validator gate: refuse to write payloads with invalid strategy
        # strings (closes Action 1 / Phase 2 silent-drift writer path).
        validated = validate_synthesis_payload(existing)
        if validated is None:
            return

        redis_client.setex(
            "ai:synthesis:latest",
            1800,  # 30 min
            json.dumps(validated),
        )
        # CSP-fix mirror: dashboard reads via direct supabase-js.
        get_client().table("trading_ai_briefs").upsert(
            {
                "brief_kind": "synthesis",
                "payload": validated,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
            on_conflict="brief_kind",
        ).execute()
        logger.info(
            "synthesis_updated_with_surprise",
            direction=overall["direction"],
            magnitude=overall["magnitude"],
        )

    except Exception as exc:
        logger.warning("surprise_synthesis_update_failed", error=str(exc))
