"""
AI synthesis agent — Phase 2A Tier 2 (final step).

Reads: ai:macro:brief + gex signals from Redis
Uses: Claude API (anthropic SDK) to synthesize a structured trade recommendation
Writes: ai:synthesis:latest (TTL 8hr)

CRITICAL DESIGN RULES:
1. Feature flag: agents:ai_synthesis:enabled must be True to write to Redis
2. Default: OFF — only enable after paper trading validates accuracy
3. On ANY failure: return empty dict, never update ai:synthesis:latest
4. The prediction_engine reads ai:synthesis:latest as Priority 0
   but only if the key exists and is fresh (<30 min old)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional

import config
from logger import get_logger

logger = get_logger("synthesis_agent")

SYSTEM_PROMPT = """You are the pre-market trading analyst for an autonomous SPX 0DTE
options trading system. Your job is to synthesize macro, options flow, and technical
signals into a single structured trade recommendation.

Rules:
- You must output ONLY valid JSON matching the schema below. No prose.
- direction: "bull", "bear", or "neutral"
- confidence: 0.0 to 1.0 (be conservative — never above 0.85)
- strategy: "iron_condor", "iron_butterfly", "bull_debit_spread",
  "bear_debit_spread", "long_straddle", or "sit_out"
- rationale: 1-2 sentences maximum
- risk_level: 1 (very low) to 10 (extreme)

Schema:
{
  "direction": "neutral",
  "confidence": 0.55,
  "strategy": "iron_condor",
  "rationale": "Brief explanation.",
  "risk_level": 4,
  "sizing_modifier": 1.0
}

sizing_modifier: 0.25 = quarter size, 0.5 = half, 1.0 = normal, 1.5 = larger
Never recommend sizing_modifier > 1.2 without direction confidence > 0.70."""


def run_synthesis_agent(redis_client) -> dict:
    """
    Main entry point. Run at 9:15 AM ET on trading days.
    Returns synthesis dict. Only writes to Redis if feature flag enabled.
    """
    try:
        if not config.ANTHROPIC_API_KEY:
            logger.info("synthesis_agent_skipped", reason="no_api_key")
            return {}

        # Check feature flag
        flag = redis_client.get("agents:ai_synthesis:enabled") if redis_client else None
        enabled = flag and flag.decode() == "true" if isinstance(flag, bytes) else flag == "true"

        # Read macro brief
        macro_raw = redis_client.get("ai:macro:brief") if redis_client else None
        if not macro_raw:
            return {}

        macro = json.loads(macro_raw)

        # Read GEX signals
        gex_context = _read_gex_context(redis_client)

        # Build prompt
        user_message = _build_prompt(macro, gex_context)

        # Call Claude API
        synthesis = _call_claude(config.ANTHROPIC_API_KEY, user_message)
        if not synthesis:
            return {}

        # Add metadata
        synthesis["generated_at"] = datetime.now(timezone.utc).isoformat()
        synthesis["source"] = "claude_synthesis"
        synthesis["day_classification"] = macro.get("day_classification", "normal")

        logger.info(
            "synthesis_agent_complete",
            direction=synthesis.get("direction"),
            confidence=synthesis.get("confidence"),
            strategy=synthesis.get("strategy"),
            risk_level=synthesis.get("risk_level"),
            enabled=bool(enabled),
        )

        # Only write to Redis if feature flag is ON
        if enabled and redis_client:
            try:
                redis_client.setex(
                    "ai:synthesis:latest",
                    1800,  # 30 min TTL — stale synthesis should not affect trades
                    json.dumps(synthesis),
                )
                logger.info("synthesis_written_to_redis")
            except Exception as e:
                logger.warning("synthesis_redis_write_failed", error=str(e))

        return synthesis

    except Exception as exc:
        logger.warning("synthesis_agent_failed", error=str(exc))
        return {}


def _read_gex_context(redis_client) -> dict:
    """Read GEX signals from Redis for synthesis context."""
    try:
        if not redis_client:
            return {}
        return {
            "gex_net": redis_client.get("gex:net"),
            "gex_confidence": redis_client.get("gex:confidence"),
            "gex_flip_zone": redis_client.get("gex:flip_zone"),
            "vvix_z": redis_client.get("polygon:vvix:z_score"),
            "vix": redis_client.get("polygon:vix:current"),
        }
    except Exception:
        return {}


def _build_prompt(macro: dict, gex: dict) -> str:
    """Build the user message for Claude."""
    events_str = ", ".join(
        e.get("event", "") for e in macro.get("events", [])
    ) or "None scheduled"

    earnings_str = ", ".join(
        e.get("ticker", "") for e in macro.get("earnings", [])
    ) or "None"

    fed_watch = macro.get("fed_watch", {})
    fed_str = (
        f"Hold: {fed_watch.get('hold_pct', 'N/A')}%, "
        f"Cut: {fed_watch.get('cut_pct', 'N/A')}%"
        if fed_watch else "N/A"
    )

    return f"""Today's market context:
Date: {macro.get("date", "unknown")}
Day classification: {macro.get("day_classification", "normal")}
Economic events: {events_str}
Major earnings: {earnings_str}
Fed watch (if FOMC): {fed_str}
Macro direction bias: {macro.get("direction_bias", "neutral")} 
  (confidence: {macro.get("direction_confidence", 0.0):.2f})
Macro rationale: {macro.get("rationale", "N/A")}
Expected SPX move: {macro.get("expected_move_pct", 0.0):.2f}%

GEX signals:
VIX: {gex.get("vix", "N/A")}
VVIX Z-score: {gex.get("vvix_z", "N/A")}
GEX net: {gex.get("gex_net", "N/A")}
GEX confidence: {gex.get("gex_confidence", "N/A")}
Zero-gamma flip zone: {gex.get("gex_flip_zone", "N/A")}

Based on all signals above, provide your structured trade recommendation as JSON."""


def _call_claude(api_key: str, user_message: str) -> Optional[dict]:
    """Call Claude API and parse structured JSON response."""
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        message = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=256,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        response_text = message.content[0].text.strip()

        # Parse JSON
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            response_text = "\n".join(
                l for l in lines if not l.startswith("```")
            )

        result = json.loads(response_text)

        # Validate required fields
        required = {"direction", "confidence", "strategy", "rationale", "risk_level"}
        if not required.issubset(result.keys()):
            logger.warning(
                "synthesis_missing_fields",
                present=list(result.keys()),
            )
            return None

        # Safety bounds
        result["confidence"] = max(0.0, min(0.85, float(result["confidence"])))
        result["risk_level"] = max(1, min(10, int(result["risk_level"])))
        result["sizing_modifier"] = max(
            0.25, min(1.2, float(result.get("sizing_modifier", 1.0)))
        )

        return result

    except Exception as exc:
        logger.warning("claude_api_failed", error=str(exc))
        return None
