"""
News sentiment agent — Phase 2C.

Combines three sentiment signals into a single composite score:
  1. NewsAPI headlines (paid key in Railway)
  2. Fear & Greed Index (CNN, free)
  3. SPX overnight gap (already in Redis from Polygon feed)

Computes: sentiment_score -100 (extreme fear/bearish) to +100 (extreme greed/bullish).
Writes: Redis ai:sentiment:brief (TTL 8hr).

Falls back gracefully — never blocks synthesis.

NOTE: `import config` is at module level (not lazy) so that
`unittest.mock.patch("sentiment_agent.config")` resolves correctly. This
matches the Phase 2A fix in synthesis_agent.py.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import httpx

import config
from db import get_client
from logger import get_logger

logger = get_logger("sentiment_agent")

REQUEST_TIMEOUT = 8.0

# Headline sentiment scoring keywords (English, financial-domain)
BULLISH_KEYWORDS = [
    "rally", "surge", "gains", "record high", "beat", "exceeds",
    "strong", "growth", "optimism", "rebound", "recovery", "upgrade",
]
BEARISH_KEYWORDS = [
    "crash", "plunge", "falls", "decline", "miss", "disappoints",
    "weak", "recession", "fear", "sell-off", "downgrade", "warns",
    "tariff", "tension", "crisis", "default",
]


def run_sentiment_agent(redis_client) -> dict:
    """
    Main entry point. Run at 8:30 AM ET (same time as macro agent).
    Returns sentiment brief dict and writes to Redis (best-effort).
    Never raises.
    """
    try:
        news_data = (
            _fetch_newsapi(config)
            if getattr(config, "NEWSAPI_KEY", "")
            else {}
        )
        fg_data = _fetch_fear_greed()
        gap_data = _read_overnight_gap(redis_client)

        sentiment_score, components = _compute_sentiment_score(
            news_data, fg_data, gap_data
        )

        if sentiment_score >= 50:
            sentiment_direction = "bull"
            sentiment_confidence = min(0.70, sentiment_score / 100)
        elif sentiment_score <= -50:
            sentiment_direction = "bear"
            sentiment_confidence = min(0.70, abs(sentiment_score) / 100)
        elif sentiment_score >= 20:
            sentiment_direction = "bull"
            sentiment_confidence = 0.40
        elif sentiment_score <= -20:
            sentiment_direction = "bear"
            sentiment_confidence = 0.40
        else:
            sentiment_direction = "neutral"
            sentiment_confidence = 0.20

        brief = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "sentiment_score": sentiment_score,           # -100 to +100
            "sentiment_direction": sentiment_direction,
            "sentiment_confidence": sentiment_confidence,
            "fear_greed_index": fg_data.get("value"),
            "fear_greed_label": fg_data.get("label", ""),
            "overnight_gap_pct": gap_data.get("gap_pct", 0.0),
            "headline_score": components.get("news_score", 0),
            "top_headlines": news_data.get("headlines", [])[:3],
            "components": components,
        }

        logger.info(
            "sentiment_agent_complete",
            sentiment_score=sentiment_score,
            direction=sentiment_direction,
            confidence=sentiment_confidence,
            fear_greed=fg_data.get("value"),
            overnight_gap=gap_data.get("gap_pct", 0.0),
        )

        # Phase 2C Session 2: per-agent feature flag gates the WRITE only.
        # The brief is always returned to the caller; downstream synthesis
        # consumes whatever is present in Redis, so flag OFF = no influence
        # without losing the in-process brief.
        if redis_client:
            flag_on = False
            try:
                flag = redis_client.get("agents:sentiment_agent:enabled")
                flag_on = flag in ("true", b"true")
            except Exception:
                flag_on = False  # fail closed — never write on flag-read error

            if flag_on:
                try:
                    redis_client.setex(
                        "ai:sentiment:brief",
                        28800,  # 8 hours
                        json.dumps(brief),
                    )
                    # CSP-fix mirror: dashboard reads via direct supabase-js.
                    get_client().table("trading_ai_briefs").upsert(
                        {
                            "brief_kind": "sentiment",
                            "payload": brief,
                            "generated_at": datetime.now(timezone.utc).isoformat(),
                        },
                        on_conflict="brief_kind",
                    ).execute()
                except Exception:
                    pass  # Redis write failure must never block return
            else:
                logger.debug(
                    "sentiment_agent_flag_off_skipping_redis_write",
                    sentiment_score=sentiment_score,
                )

        return brief

    except Exception as exc:
        logger.warning("sentiment_agent_failed", error=str(exc))
        return _empty_brief()


def _fetch_newsapi(cfg) -> dict:
    """Fetch top US business headlines from NewsAPI. Empty dict on failure."""
    try:
        url = "https://newsapi.org/v2/top-headlines"
        params = {
            "category": "business",
            "country": "us",
            "pageSize": 10,
            "apiKey": cfg.NEWSAPI_KEY,
        }
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            resp = client.get(url, params=params)

        if resp.status_code != 200:
            return {}

        data = resp.json()
        articles = data.get("articles", [])
        headlines = [a.get("title", "") for a in articles if a.get("title")]
        headline_score = _score_headlines(headlines)

        return {
            "headlines": headlines,
            "headline_score": headline_score,
            "article_count": len(articles),
        }

    except Exception as exc:
        logger.warning("newsapi_fetch_failed", error=str(exc))
        return {}


def _fetch_fear_greed() -> dict:
    """
    Fetch CNN Fear & Greed Index (free public endpoint).
    Returns {value: 0-100, label: str}. Empty dict on failure.
    """
    try:
        url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            resp = client.get(
                url,
                headers={"User-Agent": "Mozilla/5.0"},
            )

        if resp.status_code != 200:
            return {}

        data = resp.json()
        fg = data.get("fear_and_greed", {})
        value = fg.get("score", None)
        label = fg.get("rating", "")

        if value is None:
            return {}

        return {
            "value": round(float(value), 1),
            "label": label,
        }

    except Exception as exc:
        logger.warning("fear_greed_fetch_failed", error=str(exc))
        return {}


def _read_overnight_gap(redis_client) -> dict:
    """Read SPX overnight gap from Redis (set by Polygon feed)."""
    try:
        if not redis_client:
            return {}
        raw = redis_client.get("polygon:spx:overnight_gap")
        if raw:
            gap_pct = float(raw) * 100  # convert decimal to percent
            return {"gap_pct": round(gap_pct, 3)}
    except Exception:
        pass
    return {}


def _score_headlines(headlines: list) -> int:
    """
    Score headlines -50 to +50 based on bullish/bearish keyword hits.
    5 points per keyword match, clamped to [-50, +50].
    Pure function — fully testable.
    """
    score = 0
    for headline in headlines:
        h_lower = headline.lower()
        bull_hits = sum(1 for kw in BULLISH_KEYWORDS if kw in h_lower)
        bear_hits = sum(1 for kw in BEARISH_KEYWORDS if kw in h_lower)
        score += (bull_hits - bear_hits) * 5

    return max(-50, min(50, score))


def _compute_sentiment_score(
    news_data: dict, fg_data: dict, gap_data: dict
) -> tuple[int, dict]:
    """
    Composite sentiment score from all sources.
    Weights: Fear/Greed 40%, News 35%, Overnight gap 25%.
    Each weight is only applied if the corresponding source has data.
    """
    components = {}
    weighted_sum = 0.0
    weight_total = 0.0

    # Fear & Greed Index (0-100 → -100 to +100, centered at 50)
    fg_value = fg_data.get("value")
    if fg_value is not None:
        fg_contribution = int((float(fg_value) - 50) * 2)
        fg_contribution = max(-100, min(100, fg_contribution))
        components["fear_greed_contribution"] = fg_contribution
        weighted_sum += fg_contribution * 0.40
        weight_total += 0.40

    # News headlines (-50/+50 → -100/+100)
    news_score = news_data.get("headline_score", 0)
    if news_data:  # source present even if score=0
        news_contribution = news_score * 2
        components["news_score"] = news_score
        components["news_contribution"] = news_contribution
        weighted_sum += news_contribution * 0.35
        weight_total += 0.35

    # Overnight gap (±1% gap → ±50 contribution)
    gap_pct = gap_data.get("gap_pct", 0.0)
    if gap_pct != 0.0:
        gap_contribution = int(gap_pct * 50)
        gap_contribution = max(-100, min(100, gap_contribution))
        components["gap_pct"] = gap_pct
        components["gap_contribution"] = gap_contribution
        weighted_sum += gap_contribution * 0.25
        weight_total += 0.25

    if weight_total == 0:
        return 0, components

    final_score = int(weighted_sum / weight_total)
    final_score = max(-100, min(100, final_score))
    return final_score, components


def _empty_brief() -> dict:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sentiment_score": 0,
        "sentiment_direction": "neutral",
        "sentiment_confidence": 0.0,
        "fear_greed_index": None,
        "fear_greed_label": "",
        "overnight_gap_pct": 0.0,
        "headline_score": 0,
        "top_headlines": [],
        "components": {},
    }
