"""Tests for Phase 2A Session 2: AI agents."""
import os
import sys

# Make backend_agents/ importable (sibling directory to backend/)
sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "..", "backend_agents"),
)

import json
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone


def test_macro_agent_no_calendar_returns_empty():
    """Returns empty brief if no calendar intel in Redis."""
    mock_redis = MagicMock()
    mock_redis.get.return_value = None
    from macro_agent import run_macro_agent
    result = run_macro_agent(mock_redis)
    assert result == {} or result.get("direction_bias") == "neutral"


def test_macro_agent_fallback_on_api_failure():
    """Macro agent never raises even on all failures."""
    mock_redis = MagicMock()
    mock_redis.get.side_effect = Exception("Redis down")
    from macro_agent import run_macro_agent
    result = run_macro_agent(mock_redis)
    assert isinstance(result, dict)


def test_surprise_detector_skips_normal_day():
    """Surprise detector is a no-op on normal days."""
    mock_redis = MagicMock()
    mock_redis.get.return_value = json.dumps(
        {"day_classification": "normal"}
    ).encode()
    from surprise_detector import run_surprise_detector
    result = run_surprise_detector(mock_redis)
    assert result == {}


def test_surprise_detector_detects_cpi_surprise():
    """CPI above consensus = bearish surprise."""
    from surprise_detector import _detect_surprises
    intel = {
        "day_classification": "catalyst_major",
        "consensus_data": {
            "CPI": {"actual": 0.4, "estimate": 0.3, "prev": 0.3}
        }
    }
    surprises = _detect_surprises(intel)
    assert len(surprises) == 1
    assert surprises[0]["direction"] == "bear"
    assert surprises[0]["deviation_pct"] > 0


def test_surprise_detector_cpi_below_consensus_is_bullish():
    """CPI below consensus = bullish surprise."""
    from surprise_detector import _detect_surprises
    intel = {
        "consensus_data": {
            "CPI": {"actual": 0.2, "estimate": 0.3, "prev": 0.3}
        }
    }
    surprises = _detect_surprises(intel)
    assert surprises[0]["direction"] == "bull"


def test_synthesis_agent_skips_without_api_key():
    """Synthesis agent returns empty dict when no API key."""
    mock_redis = MagicMock()
    with patch("synthesis_agent.config") as mock_config:
        mock_config.ANTHROPIC_API_KEY = ""
        from synthesis_agent import run_synthesis_agent
        result = run_synthesis_agent(mock_redis)
    assert result == {}


def test_synthesis_agent_skips_without_feature_flag():
    """Synthesis agent does not write to Redis when flag is OFF."""
    mock_redis = MagicMock()
    mock_redis.get.side_effect = lambda key: (
        b"false" if key == "agents:ai_synthesis:enabled"
        else json.dumps({
            "day_classification": "normal",
            "direction_bias": "neutral",
            "direction_confidence": 0.0,
            "events": [], "earnings": [],
            "fed_watch": {}, "expected_move_pct": 0.0,
            "rationale": "test"
        }).encode()
    )
    with patch("synthesis_agent.config") as mock_config:
        mock_config.ANTHROPIC_API_KEY = "test_key"
        mock_config.OPENAI_API_KEY = ""
        mock_config.AI_PROVIDER = "anthropic"
        mock_config.AI_MODEL = "claude-sonnet-4-5"
        with patch("synthesis_agent._call_ai_provider") as mock_ai:
            mock_ai.return_value = {
                "direction": "bull", "confidence": 0.6,
                "strategy": "bull_debit_spread",
                "rationale": "test", "risk_level": 3,
                "sizing_modifier": 1.0
            }
            from synthesis_agent import run_synthesis_agent
            run_synthesis_agent(mock_redis)
    # setex should NOT have been called (feature flag is OFF)
    setex_calls = [c for c in mock_redis.method_calls
                   if 'setex' in str(c) and 'ai:synthesis:latest' in str(c)]
    assert len(setex_calls) == 0


def test_call_ai_provider_dispatches_to_claude_by_default():
    """Default config.AI_PROVIDER should route through _call_claude."""
    from synthesis_agent import _call_ai_provider
    fake_response = json.dumps({
        "direction": "neutral", "confidence": 0.5,
        "strategy": "iron_condor", "rationale": "ok",
        "risk_level": 4, "sizing_modifier": 1.0,
    })
    with patch("synthesis_agent.config") as mock_config:
        mock_config.AI_PROVIDER = "anthropic"
        mock_config.AI_MODEL = "claude-sonnet-4-5"
        mock_config.ANTHROPIC_API_KEY = "key"
        mock_config.OPENAI_API_KEY = ""
        with patch("synthesis_agent._call_claude") as mock_claude, \
             patch("synthesis_agent._call_openai") as mock_openai:
            mock_claude.return_value = fake_response
            result = _call_ai_provider("test prompt")
    assert mock_claude.called
    assert not mock_openai.called
    assert result["direction"] == "neutral"


def test_call_ai_provider_dispatches_to_openai_when_configured():
    """AI_PROVIDER=openai should route through _call_openai, not Claude."""
    from synthesis_agent import _call_ai_provider
    fake_response = json.dumps({
        "direction": "bull", "confidence": 0.65,
        "strategy": "bull_debit_spread", "rationale": "ok",
        "risk_level": 5, "sizing_modifier": 1.0,
    })
    with patch("synthesis_agent.config") as mock_config:
        mock_config.AI_PROVIDER = "openai"
        mock_config.AI_MODEL = "gpt-4o"
        mock_config.ANTHROPIC_API_KEY = ""
        mock_config.OPENAI_API_KEY = "key"
        with patch("synthesis_agent._call_claude") as mock_claude, \
             patch("synthesis_agent._call_openai") as mock_openai:
            mock_openai.return_value = fake_response
            result = _call_ai_provider("test prompt")
    assert mock_openai.called
    assert not mock_claude.called
    assert result["direction"] == "bull"


def test_call_ai_provider_applies_safety_bounds_for_both_providers():
    """confidence > 0.85, risk_level > 10, and sizing > 1.2 must clamp,
    regardless of which provider returned them."""
    from synthesis_agent import _call_ai_provider
    over_limits = json.dumps({
        "direction": "bull", "confidence": 0.99,
        "strategy": "iron_condor", "rationale": "x",
        "risk_level": 99, "sizing_modifier": 5.0,
    })
    for provider, mock_target in [
        ("anthropic", "synthesis_agent._call_claude"),
        ("openai", "synthesis_agent._call_openai"),
    ]:
        with patch("synthesis_agent.config") as mock_config:
            mock_config.AI_PROVIDER = provider
            mock_config.AI_MODEL = "x"
            mock_config.ANTHROPIC_API_KEY = "k"
            mock_config.OPENAI_API_KEY = "k"
            with patch(mock_target) as mock_call:
                mock_call.return_value = over_limits
                result = _call_ai_provider("p")
        assert result["confidence"] == 0.85, provider
        assert result["risk_level"] == 10, provider
        assert result["sizing_modifier"] == 1.2, provider


def test_run_synthesis_agent_skips_when_openai_provider_has_no_key():
    """If AI_PROVIDER=openai but OPENAI_API_KEY missing, skip silently."""
    from synthesis_agent import run_synthesis_agent
    mock_redis = MagicMock()
    with patch("synthesis_agent.config") as mock_config:
        mock_config.AI_PROVIDER = "openai"
        mock_config.AI_MODEL = "gpt-4o"
        mock_config.OPENAI_API_KEY = ""
        mock_config.ANTHROPIC_API_KEY = "set-but-irrelevant"
        with patch("synthesis_agent._call_ai_provider") as mock_ai:
            result = run_synthesis_agent(mock_redis)
    assert result == {}
    assert not mock_ai.called
