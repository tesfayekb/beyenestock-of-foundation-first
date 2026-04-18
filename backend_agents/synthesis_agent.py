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

        # Phase 2C: read flow brief (best-effort, may be missing)
        flow_raw = (
            redis_client.get("ai:flow:brief") if redis_client else None
        )
        flow = json.loads(flow_raw) if flow_raw else {}

        # Phase 2C: read sentiment brief (best-effort, may be missing)
        sentiment_raw = (
            redis_client.get("ai:sentiment:brief") if redis_client else None
        )
        sentiment = json.loads(sentiment_raw) if sentiment_raw else {}

        # Phase 2C: confluence across macro + flow + sentiment directions
        confluence_score = _compute_confluence(macro, flow, sentiment)

        # Read GEX signals
        gex_context = _read_gex_context(redis_client)

        # Build prompt with all 4 signal sources
        user_message = _build_prompt(
            macro, gex_context, flow, sentiment, confluence_score
        )

        # Call Claude API
        synthesis = _call_claude(config.ANTHROPIC_API_KEY, user_message)
        if not synthesis:
            return {}

        # Add metadata
        synthesis["generated_at"] = datetime.now(timezone.utc).isoformat()
        synthesis["source"] = "claude_synthesis"
        synthesis["day_classification"] = macro.get("day_classification", "normal")
        synthesis["confluence_score"] = confluence_score
        synthesis["flow_direction"] = flow.get("flow_direction", "neutral")
        synthesis["sentiment_direction"] = sentiment.get(
            "sentiment_direction", "neutral"
        )

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


def _compute_confluence(macro: dict, flow: dict, sentiment: dict) -> float:
    """
    How strongly do macro, flow, and sentiment agree on direction?

    Only signals above their per-source confidence floor are counted:
      - macro    : direction_confidence    >= 0.4
      - flow     : flow_confidence         >= 0.3
      - sentiment: sentiment_confidence    >= 0.3

    Returns 0.0 — 1.0:
      - all sources agree                              → count / 3 (up to 1.0)
      - bull AND bear simultaneously                   → 0.0 (contradictory)
      - majority but not unanimous (no contradiction)  → partial credit
    Pure function, fully testable.
    """
    directions = []

    macro_dir = macro.get("direction_bias", "neutral")
    macro_conf = float(macro.get("direction_confidence", 0.0) or 0.0)
    if macro_dir != "neutral" and macro_conf >= 0.4:
        directions.append(macro_dir)

    flow_dir = flow.get("flow_direction", "neutral")
    flow_conf = float(flow.get("flow_confidence", 0.0) or 0.0)
    if flow_dir != "neutral" and flow_conf >= 0.3:
        directions.append(flow_dir)

    sentiment_dir = sentiment.get("sentiment_direction", "neutral")
    sentiment_conf = float(sentiment.get("sentiment_confidence", 0.0) or 0.0)
    if sentiment_dir != "neutral" and sentiment_conf >= 0.3:
        directions.append(sentiment_dir)

    if not directions:
        return 0.0

    bull_count = directions.count("bull")
    bear_count = directions.count("bear")
    total = len(directions)

    if bull_count == total or bear_count == total:
        return round(total / 3.0, 2)  # 1/3, 2/3, or 3/3
    elif bull_count > 0 and bear_count > 0:
        return 0.0  # contradictory signals — no edge
    else:
        return round(max(bull_count, bear_count) / total / 2, 2)


def _build_prompt(
    macro: dict,
    gex: dict,
    flow: dict = None,
    sentiment: dict = None,
    confluence_score: float = 0.0,
) -> str:
    """Build the enriched user message for Claude with all 4 signal sources."""
    flow = flow or {}
    sentiment = sentiment or {}

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

    flow_score = flow.get("flow_score", "N/A")
    flow_dir = flow.get("flow_direction", "no data")
    pc_ratio = flow.get("put_call_ratio", "N/A")
    uw_count = flow.get("unusual_activity_count", 0)

    sent_score = sentiment.get("sentiment_score", "N/A")
    sent_dir = sentiment.get("sentiment_direction", "no data")
    fg = sentiment.get("fear_greed_index", "N/A")
    fg_label = sentiment.get("fear_greed_label", "")
    overnight = sentiment.get("overnight_gap_pct", 0.0)
    headlines = sentiment.get("top_headlines", [])
    headlines_str = " | ".join(headlines[:2]) if headlines else "No headlines"

    conf_pct = int(confluence_score * 100)

    return f"""Today's complete market context:
Date: {macro.get("date", "unknown")}
Day classification: {macro.get("day_classification", "normal")}

SIGNAL CONFLUENCE: {conf_pct}% of directional signals agree
(Higher confluence = higher conviction sizing recommended)

ECONOMIC SIGNALS:
  Events today: {events_str}
  Major earnings: {earnings_str}
  Fed watch: {fed_str}
  Macro direction: {macro.get("direction_bias", "neutral")} (conf: {macro.get("direction_confidence", 0.0):.2f})
  Macro rationale: {macro.get("rationale", "N/A")}
  Expected SPX move: {macro.get("expected_move_pct", 0.0):.2f}%

OPTIONS FLOW:
  Flow score: {flow_score} (-100=extreme puts, +100=extreme calls)
  Flow direction: {flow_dir}
  Put/call ratio: {pc_ratio} (<0.7=bullish, >1.3=bearish)
  Unusual alerts: {uw_count} large trades detected

MARKET SENTIMENT:
  Sentiment score: {sent_score} (-100=extreme fear, +100=extreme greed)
  Sentiment direction: {sent_dir}
  Fear & Greed: {fg}/100 ({fg_label})
  Overnight gap: {overnight:+.2f}%
  Top headlines: {headlines_str}

GEX / TECHNICAL:
  VIX: {gex.get("vix", "N/A")}
  VVIX Z-score: {gex.get("vvix_z", "N/A")}
  GEX net: {gex.get("gex_net", "N/A")}
  GEX confidence: {gex.get("gex_confidence", "N/A")}
  Zero-gamma flip zone: {gex.get("gex_flip_zone", "N/A")}

Synthesize all signals above. Weight high-confluence setups more aggressively.
Provide your structured trade recommendation as JSON."""


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
