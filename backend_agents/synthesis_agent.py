"""
AI synthesis agent — Phase 2A Tier 2 (final step).

Reads: ai:macro:brief + gex signals from Redis
Uses: Configurable AI provider (Anthropic or OpenAI) to synthesize a
      structured trade recommendation. Selected via config.AI_PROVIDER.
Writes: ai:synthesis:latest (TTL 8hr)

CRITICAL DESIGN RULES:
1. Feature flag: agents:ai_synthesis:enabled must be True to write to Redis
2. Default: OFF — only enable after paper trading validates accuracy
3. On ANY failure: return empty dict, never update ai:synthesis:latest
4. The prediction_engine reads ai:synthesis:latest as Priority 0
   but only if the key exists and is fresh (<30 min old)
5. Both providers must be given the IDENTICAL system prompt and must
   return JSON conforming to the same schema. Safety bounds are applied
   centrally in _call_ai_provider().
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional

import config
from db import get_client
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
        provider = (getattr(config, "AI_PROVIDER", "anthropic") or "").lower()
        api_key_present = (
            (provider == "openai" and bool(getattr(config, "OPENAI_API_KEY", "")))
            or (provider != "openai" and bool(config.ANTHROPIC_API_KEY))
        )
        if not api_key_present:
            logger.info(
                "synthesis_agent_skipped",
                reason="no_api_key",
                provider=provider,
            )
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

        # Phase A (Loop 1): read closed-loop feedback brief.
        # Best-effort — synthesis runs without it if missing/malformed.
        feedback = {}
        try:
            feedback_raw = (
                redis_client.get("ai:feedback:brief") if redis_client else None
            )
            if feedback_raw:
                feedback = json.loads(feedback_raw)
        except Exception as exc:
            logger.warning("feedback_brief_read_failed", error=str(exc))
            feedback = {}

        # Stale-brief detection: warn but do NOT suppress the brief.
        # 4-day TTL handles full removal; the warning surfaces unusually
        # long gaps between writes (e.g. agent crashed yesterday).
        generated_at = feedback.get("generated_at", "")
        if generated_at and feedback.get("status") == "ready":
            try:
                age_hours = (
                    datetime.now(timezone.utc)
                    - datetime.fromisoformat(generated_at)
                ).total_seconds() / 3600
                if age_hours > 26:
                    logger.warning(
                        "feedback_brief_stale",
                        age_hours=round(age_hours, 1),
                    )
            except Exception:
                pass

        # Read GEX signals
        gex_context = _read_gex_context(redis_client)

        # Build prompt with all 4 signal sources + feedback brief
        user_message = _build_prompt(
            macro, gex_context, flow, sentiment, confluence_score, feedback
        )

        # Call configured AI provider (Anthropic or OpenAI).
        # Pass redis_client through so per-day token counters can be written.
        synthesis = _call_ai_provider(user_message, redis_client)
        if not synthesis:
            return {}

        # Add metadata
        synthesis["generated_at"] = datetime.now(timezone.utc).isoformat()
        # Keep "claude_synthesis" as the canonical source label for
        # downstream consumers (dashboards, log filters). Provider
        # actually used is recorded separately for auditability.
        synthesis["source"] = "claude_synthesis"
        synthesis["provider"] = provider
        synthesis["model"] = getattr(config, "AI_MODEL", "")
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
                # CSP-fix mirror: dashboard reads via direct supabase-js.
                get_client().table("trading_ai_briefs").upsert(
                    {
                        "brief_kind": "synthesis",
                        "payload": synthesis,
                        "generated_at": datetime.now(timezone.utc).isoformat(),
                    },
                    on_conflict="brief_kind",
                ).execute()
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


def _format_feedback_section(feedback: dict) -> str:
    """
    Render the PERFORMANCE FEEDBACK section for Claude's prompt.

    Returns an empty string in either of these cases:
      1. feedback is missing or malformed
      2. feedback["status"] != "ready" (e.g. "insufficient_history")
    Per Phase A spec, when below MIN_TRADES_FOR_BRIEF the section is
    completely absent — not stubbed, not headed, not even mentioned.

    When the brief is ready, every direction/confidence/regime cell is
    individually checked for cell["sufficient"]. Cells with sufficient=False
    render only as "INSUFFICIENT DATA (n=X)" — no win-rate, no P&L —
    so Claude does not over-rotate on small samples.
    """
    if not feedback or feedback.get("status") != "ready":
        return ""

    n = feedback.get("trade_count", 0)
    by_dir = feedback.get("by_direction", {}) or {}
    by_conf = feedback.get("by_confidence", {}) or {}
    by_regime = feedback.get("by_regime", {}) or {}
    streak = feedback.get("recent_streak", {}) or {}

    def fmt_cell(cell: dict, label: str) -> str:
        if not cell or not cell.get("sufficient", False):
            return f"  {label}: INSUFFICIENT DATA (n={cell.get('n', 0) if cell else 0})"
        wr = cell.get("win_rate", 0)
        ci = cell.get("win_rate_ci", [0, 1]) or [0, 1]
        aw = cell.get("avg_winner", 0)
        al = cell.get("avg_loser", 0)
        np_ = cell.get("net_pnl", 0)
        flag = "profitable" if cell.get("profitable") else "losing money"
        return (
            f"  {label}: {wr:.0%} win rate "
            f"[CI: {ci[0]:.0%}-{ci[1]:.0%}] "
            f"avg winner +${aw:.0f} / avg loser ${al:.0f} "
            f"-> net ${np_:+.0f} {flag}"
        )

    dir_lines = "\n".join(
        fmt_cell(by_dir.get(d, {"n": 0}), d.capitalize())
        for d in ("bull", "bear", "neutral")
    )

    conf_labels = {
        "high":   "High (>70%)",
        "medium": "Medium (55-70%)",
        "low":    "Low (<55%)",
    }
    conf_lines = "\n".join(
        fmt_cell(by_conf.get(b, {"n": 0}), conf_labels[b])
        for b in ("high", "medium", "low")
    )

    if by_regime:
        regime_lines = "\n".join(
            fmt_cell(cell, regime.replace("_", " ").title())
            for regime, cell in by_regime.items()
        )
    else:
        regime_lines = "  (no regime data yet)"

    last_10 = streak.get("last_10", []) or []
    streak_str = " ".join("W" if x else "L" for x in last_10) or "n/a"
    consec = int(streak.get("consecutive_losses", 0) or 0)
    streak_note = (
        f"WARNING: {consec} consecutive losses"
        if consec >= 3 else "No losing-streak concern"
    )

    return f"""
PERFORMANCE FEEDBACK (last {n} closed trades):
Cells marked INSUFFICIENT DATA have n<5 — do not change strategy based on these.
Win rate alone is misleading. Always check net P&L — a 65% win rate can still lose money.

DIRECTION ACCURACY:
{dir_lines}

CONFIDENCE CALIBRATION:
{conf_lines}

REGIME PERFORMANCE:
{regime_lines}

RECENT TREND: {streak_str} — {streak_note}

INSTRUCTIONS: Do not over-rotate on any bucket. Confidence intervals show true uncertainty.
If net P&L for a direction is negative despite positive win rate, weight that direction down.
If any signal source has been below 50% accuracy across 10+ trades, reduce its weight in reasoning.
"""


def _build_prompt(
    macro: dict,
    gex: dict,
    flow: dict = None,
    sentiment: dict = None,
    confluence_score: float = 0.0,
    feedback: dict = None,
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

    # Phase A: PERFORMANCE FEEDBACK appears between SIGNAL CONFLUENCE and
    # ECONOMIC SIGNALS so Claude reads its own track record before the
    # incoming signals. Empty string when status != "ready".
    feedback_section = _format_feedback_section(feedback or {})

    return f"""Today's complete market context:
Date: {macro.get("date", "unknown")}
Day classification: {macro.get("day_classification", "normal")}

SIGNAL CONFLUENCE: {conf_pct}% of directional signals agree
(Higher confluence = higher conviction sizing recommended)
{feedback_section}
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


def _strip_code_fences(text: str) -> str:
    """Drop triple-backtick fences that some providers wrap JSON in."""
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(l for l in lines if not l.startswith("```"))
    return text


def _validate_and_clamp(result: dict) -> Optional[dict]:
    """
    Shared validation + safety bounds for any provider's response.
    Returns None if the response is malformed (caller logs context).
    """
    required = {"direction", "confidence", "strategy", "rationale", "risk_level"}
    if not required.issubset(result.keys()):
        logger.warning(
            "synthesis_missing_fields",
            present=list(result.keys()),
        )
        return None

    # Safety bounds — never above 0.85 confidence; risk 1-10; sizing 0.25-1.2.
    result["confidence"] = max(0.0, min(0.85, float(result["confidence"])))
    result["risk_level"] = max(1, min(10, int(result["risk_level"])))
    result["sizing_modifier"] = max(
        0.25, min(1.2, float(result.get("sizing_modifier", 1.0)))
    )
    return result


def _write_token_counters(
    redis_client, tokens_in: int, tokens_out: int
) -> None:
    """
    Per-day token counter for cost tracking.
    Keys: ai:tokens:in:YYYY-MM-DD, ai:tokens:out:YYYY-MM-DD (90-day TTL).
    Soft failure — never raises.
    """
    if not redis_client or (not tokens_in and not tokens_out):
        return
    try:
        from datetime import date
        day = date.today().isoformat()
        in_key = f"ai:tokens:in:{day}"
        out_key = f"ai:tokens:out:{day}"
        if tokens_in:
            redis_client.incrby(in_key, int(tokens_in))
            redis_client.expire(in_key, 90 * 86400)
        if tokens_out:
            redis_client.incrby(out_key, int(tokens_out))
            redis_client.expire(out_key, 90 * 86400)
    except Exception as exc:
        logger.warning("token_counter_write_failed", error=str(exc))


def _call_ai_provider(
    user_message: str, redis_client=None
) -> Optional[dict]:
    """
    Dispatch to the configured AI provider and return a validated
    synthesis dict, or None on any failure.

    Provider is selected via config.AI_PROVIDER ("anthropic" | "openai")
    and the model via config.AI_MODEL. Both providers receive the
    identical SYSTEM_PROMPT and are expected to return JSON matching
    the same schema. All safety bounds are applied centrally.

    Phase A: when redis_client is provided, per-day token usage counters
    are written to Redis (ai:tokens:in/out:YYYY-MM-DD, 90-day TTL).

    Provider functions return either a dict {text, tokens_in, tokens_out}
    in production, or a bare string in legacy/test paths. Both shapes
    are handled here to preserve backward compatibility with existing
    mocks in test_phase_2a_agents.py.
    """
    provider = (getattr(config, "AI_PROVIDER", "anthropic") or "").lower()
    model = getattr(config, "AI_MODEL", "claude-sonnet-4-5")
    try:
        if provider == "openai":
            raw = _call_openai(
                config.OPENAI_API_KEY, model, user_message,
            )
        else:
            raw = _call_claude(
                config.ANTHROPIC_API_KEY, model, user_message,
            )
        if not raw:
            return None

        # Normalize: tolerate both dict (new contract) and str (legacy/test).
        if isinstance(raw, dict):
            response_text = raw.get("text") or ""
            tokens_in = int(raw.get("tokens_in", 0) or 0)
            tokens_out = int(raw.get("tokens_out", 0) or 0)
            _write_token_counters(redis_client, tokens_in, tokens_out)
        else:
            response_text = str(raw)

        if not response_text:
            return None

        result = json.loads(_strip_code_fences(response_text.strip()))
        return _validate_and_clamp(result)
    except Exception as exc:
        logger.warning(
            "ai_provider_failed",
            provider=provider,
            model=model,
            error=str(exc),
        )
        return None


def _call_claude(
    api_key: str, model: str, user_message: str
) -> Optional[dict]:
    """
    Anthropic backend — returns {"text": ..., "tokens_in": int,
    "tokens_out": int} or None on failure.
    """
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=model,
            max_tokens=256,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        usage = getattr(message, "usage", None)
        return {
            "text": message.content[0].text,
            "tokens_in": getattr(usage, "input_tokens", 0) if usage else 0,
            "tokens_out": getattr(usage, "output_tokens", 0) if usage else 0,
        }
    except Exception as exc:
        logger.warning("claude_api_failed", error=str(exc), model=model)
        return None


def _call_openai(
    api_key: str, model: str, user_message: str
) -> Optional[dict]:
    """
    OpenAI backend — returns {"text": ..., "tokens_in": int,
    "tokens_out": int} or None on failure. Requires openai>=1.0.0.
    """
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        completion = client.chat.completions.create(
            model=model,
            max_tokens=256,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
        )
        usage = getattr(completion, "usage", None)
        return {
            "text": completion.choices[0].message.content,
            "tokens_in": getattr(usage, "prompt_tokens", 0) if usage else 0,
            "tokens_out": (
                getattr(usage, "completion_tokens", 0) if usage else 0
            ),
        }
    except Exception as exc:
        logger.warning("openai_api_failed", error=str(exc), model=model)
        return None
