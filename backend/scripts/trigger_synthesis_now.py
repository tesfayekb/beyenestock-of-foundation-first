"""Operator-triggered synthesis run for same-day validation.

Use after deploying TTL/schema fixes (T-ACT-040) to verify AI
synthesis end-to-end without waiting for the next 09:15 ET cron.
Cost: 1 LLM call (~$0.05). Idempotent. Safe to run multiple times.

Validation flow post-deploy (on Railway shell or local with .env):
    python backend/scripts/trigger_synthesis_now.py
    # Wait <60s for the next 5-min trading cycle
    # Check Railway logs: grep "prediction_from_ai_synthesis" → expect 1 fire
    # Check supabase: SELECT * FROM trading_prediction_outputs
    #   WHERE predicted_at > NOW() - INTERVAL '5 min'
    #   → expect a row with p_bull ≈ 0.62 (or whatever today's confidence is)
    #     INSTEAD of the 0.35/0.30/0.35 placeholder triplet.

Redis client construction matches the production pattern at
backend/main.py:1274 (decode_responses=True) for parity with how
synthesis_agent.run_synthesis_agent expects the client to behave.
"""
import os
import sys

# Match the path-mangling pattern used by main.py for backend_agents/
_AGENTS_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "backend_agents")
)
if _AGENTS_PATH not in sys.path:
    sys.path.insert(0, _AGENTS_PATH)

# Make backend/ importable so `import config`, `import logger`, etc. work.
_BACKEND_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _BACKEND_PATH not in sys.path:
    sys.path.insert(0, _BACKEND_PATH)

import redis  # noqa: E402

import config  # noqa: E402
from logger import get_logger  # noqa: E402
from synthesis_agent import run_synthesis_agent  # noqa: E402

logger = get_logger("trigger_synthesis_now")


def main() -> int:
    # Construct redis client directly per backend/main.py:1274 pattern.
    # decode_responses=True keeps string returns consistent with how
    # synthesis_agent reads its inputs and writes ai:synthesis:latest.
    try:
        redis_client = redis.Redis.from_url(
            config.REDIS_URL, decode_responses=True
        )
        redis_client.ping()
    except Exception as exc:
        print(f"ERROR: Redis unavailable: {exc}")
        print(f"REDIS_URL = {config.REDIS_URL!r}")
        return 1

    logger.info("manual_synthesis_trigger_start")
    print("Triggering synthesis_agent.run_synthesis_agent(redis_client)...")
    result = run_synthesis_agent(redis_client)

    if not result:
        print(
            "Synthesis returned empty dict. Possible causes: "
            "(a) agents:ai_synthesis:enabled flag is OFF, "
            "(b) one or more sub-agent briefs missing in Redis, "
            "(c) agent raised internally and was caught."
        )
        return 2

    print(
        f"Synthesis complete: direction={result.get('direction')}, "
        f"confidence={result.get('confidence')}, "
        f"strategy={result.get('strategy')}"
    )

    key_exists = redis_client.exists("ai:synthesis:latest")
    ttl = redis_client.ttl("ai:synthesis:latest") if key_exists else -1
    print(f"ai:synthesis:latest exists: {bool(key_exists)}, TTL: {ttl}s")
    print(
        "Expected TTL after T-ACT-040 fix: ~28800 (8hr) on first write, "
        "decreasing thereafter. If TTL ~1800, fix has not deployed."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
