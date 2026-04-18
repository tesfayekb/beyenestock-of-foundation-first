"""Tests for Phase 2C: Flow agent, sentiment agent, synthesis enrichment.

Covers:
  - flow_agent: graceful failure, score signs from put/call ratio
  - sentiment_agent: graceful failure, headline keyword scoring
  - synthesis_agent: confluence math, enriched prompt content
"""
import os
import sys

# Make backend_agents/ importable (sibling directory to backend/)
sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "..", "backend_agents"),
)

from unittest.mock import MagicMock, patch


# --- Flow agent tests ------------------------------------------------------


def test_flow_agent_returns_empty_on_failure():
    """Flow agent never raises — returns a brief dict even when Redis fails."""
    mock_redis = MagicMock()
    mock_redis.get.side_effect = Exception("Redis down")
    with patch("flow_agent.config") as mock_config:
        mock_config.UNUSUAL_WHALES_API_KEY = ""
        mock_config.POLYGON_API_KEY = ""
        from flow_agent import run_flow_agent
        result = run_flow_agent(mock_redis)
    assert isinstance(result, dict)
    assert result.get("flow_score") == 0


def test_flow_score_bullish_low_put_call():
    """Low put/call ratio → positive flow score → bull direction."""
    from flow_agent import _compute_flow_score
    pc_data = {"ratio": 0.45, "call_volume": 10000, "put_volume": 4500}
    score, signals = _compute_flow_score({}, pc_data)
    assert score > 0
    assert any(s["signal"] in ("bull", "strong_bull") for s in signals)


def test_flow_score_bearish_high_put_call():
    """High put/call ratio → negative flow score → bear direction."""
    from flow_agent import _compute_flow_score
    pc_data = {"ratio": 1.8, "call_volume": 5000, "put_volume": 9000}
    score, signals = _compute_flow_score({}, pc_data)
    assert score < 0


def test_flow_score_neutral_balanced():
    """Balanced put/call ratio → near-zero score → neutral region."""
    from flow_agent import _compute_flow_score
    pc_data = {"ratio": 0.95}
    score, _ = _compute_flow_score({}, pc_data)
    assert -30 < score < 30


# --- Sentiment agent tests -------------------------------------------------


def test_sentiment_agent_returns_empty_on_failure():
    """Sentiment agent never raises — returns brief dict on all-source failure."""
    mock_redis = MagicMock()
    mock_redis.get.return_value = None
    with patch("sentiment_agent.config") as mock_config:
        mock_config.NEWSAPI_KEY = ""
        from sentiment_agent import run_sentiment_agent
        result = run_sentiment_agent(mock_redis)
    assert isinstance(result, dict)
    assert result.get("sentiment_score") == 0


def test_bearish_keywords_score_negative():
    """Bearish-keyword headlines produce a negative score."""
    from sentiment_agent import _score_headlines
    headlines = [
        "Markets crash as recession fears grip Wall Street",
        "Stocks plunge on tariff tensions",
    ]
    score = _score_headlines(headlines)
    assert score < 0


def test_bullish_keywords_score_positive():
    """Bullish-keyword headlines produce a positive score."""
    from sentiment_agent import _score_headlines
    headlines = [
        "Markets rally to record high on strong earnings",
        "Economy surges as growth beats expectations",
    ]
    score = _score_headlines(headlines)
    assert score > 0


# --- Confluence + prompt tests --------------------------------------------


def test_confluence_all_agree_bull():
    """All three sources bull (above conf floors) → high confluence."""
    from synthesis_agent import _compute_confluence
    macro = {"direction_bias": "bull", "direction_confidence": 0.6}
    flow = {"flow_direction": "bull", "flow_confidence": 0.5}
    sentiment = {"sentiment_direction": "bull", "sentiment_confidence": 0.5}
    score = _compute_confluence(macro, flow, sentiment)
    assert score >= 0.9, f"Expected >= 0.9, got {score}"


def test_confluence_contradictory_signals():
    """Bull and bear simultaneously → zero confluence (no edge)."""
    from synthesis_agent import _compute_confluence
    macro = {"direction_bias": "bull", "direction_confidence": 0.6}
    flow = {"flow_direction": "bear", "flow_confidence": 0.6}
    sentiment = {"sentiment_direction": "neutral", "sentiment_confidence": 0.0}
    score = _compute_confluence(macro, flow, sentiment)
    assert score == 0.0


def test_confluence_no_signals():
    """No directional signals at all → zero confluence."""
    from synthesis_agent import _compute_confluence
    score = _compute_confluence({}, {}, {})
    assert score == 0.0


def test_build_prompt_includes_flow_and_sentiment():
    """Updated prompt contains flow, sentiment, and confluence sections."""
    from synthesis_agent import _build_prompt
    macro = {
        "date": "2026-04-21", "day_classification": "normal",
        "events": [], "earnings": [], "fed_watch": {},
        "direction_bias": "neutral", "direction_confidence": 0.0,
        "rationale": "test", "expected_move_pct": 0.8,
    }
    flow = {
        "flow_score": 45, "flow_direction": "bull",
        "put_call_ratio": 0.65, "unusual_activity_count": 3,
    }
    sentiment = {
        "sentiment_score": 30, "sentiment_direction": "bull",
        "fear_greed_index": 65, "fear_greed_label": "Greed",
        "overnight_gap_pct": 0.3, "top_headlines": ["Markets rally"],
    }
    gex = {}
    prompt = _build_prompt(macro, gex, flow, sentiment, 0.67)
    assert "OPTIONS FLOW" in prompt
    assert "MARKET SENTIMENT" in prompt
    assert "SIGNAL CONFLUENCE" in prompt
    assert "45" in prompt  # flow_score appears in prompt
