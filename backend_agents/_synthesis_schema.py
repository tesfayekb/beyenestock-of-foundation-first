"""
Synthesis payload validator — shared schema enforcement for both writers
of `ai:synthesis:latest` (synthesis_agent.py + surprise_detector.py).

Validates `synth["strategy"]` against the production validity set
(`STATIC_SLIPPAGE_BY_STRATEGY` keys in strategy_selector.py — the canonical 10
per AUDIT_DISPOSITION_PLAN.md v1.9 §(m)).

Returns the payload unchanged on valid strategy; returns None (with structured
warning log) on invalid strategy. Both writers MUST call this before writing to
Redis at `ai:synthesis:latest`.
"""
from __future__ import annotations
from typing import Optional

from logger import get_logger
from strategy_selector import STATIC_SLIPPAGE_BY_STRATEGY

logger = get_logger("synthesis_schema")

# Single source of truth for valid strategy strings — derived from production
# validity set used at strategy_selector.py:1021. Do NOT hardcode a list here;
# importing from STATIC_SLIPPAGE_BY_STRATEGY ensures any future canonical-list
# change in strategy_selector propagates automatically.
_VALID_STRATEGIES = frozenset(STATIC_SLIPPAGE_BY_STRATEGY.keys())


def validate_synthesis_payload(synth: dict) -> Optional[dict]:
    """
    Validate a synthesis payload before writing to ai:synthesis:latest.

    Returns the payload unchanged if synth["strategy"] is in the production
    validity set; returns None (with structured warning) otherwise.
    """
    strategy = synth.get("strategy")
    if strategy not in _VALID_STRATEGIES:
        logger.warning(
            "synthesis_payload_invalid_strategy",
            strategy=strategy,
            valid_strategies=sorted(_VALID_STRATEGIES),
        )
        return None
    return synth
