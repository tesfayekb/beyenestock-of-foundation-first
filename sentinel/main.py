"""
MarketMuse Sentinel — Independent watchdog on GCP Cloud Run.
Monitors Railway backend heartbeat. Closes all positions if heartbeat lost.
GLC-009: Must be independently operational on GCP.

ISOLATION PRINCIPLE: This process has NO shared state with Railway.
It reads Supabase directly and calls Tradier independently.
If Railway is completely down, this process still runs.
"""
import asyncio
import os
import threading
import time
import logging
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler

import httpx
from supabase import create_client

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"sentinel ok")

    def log_message(self, format, *args):
        pass  # suppress HTTP access logs


def start_health_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info(f"sentinel_health_server_started port={port}")


# -----------------------------------------------------------------------
# Config — all from environment variables
# -----------------------------------------------------------------------
RAILWAY_HEALTH_URL = os.environ["RAILWAY_HEALTH_URL"]  # https://diplomatic-mercy-production-7e61.up.railway.app/health
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_ROLE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
TRADIER_API_KEY = os.environ["TRADIER_API_KEY"]
TRADIER_ACCOUNT_ID = os.environ["TRADIER_ACCOUNT_ID"]
TRADIER_SANDBOX = os.environ.get("TRADIER_SANDBOX", "true").lower() == "true"
HEARTBEAT_INTERVAL_SECONDS = int(
    os.environ.get("HEARTBEAT_INTERVAL_SECONDS", "30")
)
STALE_THRESHOLD_SECONDS = int(
    os.environ.get("STALE_THRESHOLD_SECONDS", "120")
)

TRADIER_BASE = (
    "https://sandbox.tradier.com"
    if TRADIER_SANDBOX
    else "https://api.tradier.com"
)

# -----------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("sentinel")

# -----------------------------------------------------------------------
# State
# -----------------------------------------------------------------------
last_healthy_at: float = time.time()
emergency_triggered: bool = False


def get_supabase():
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


def write_sentinel_health(status: str, message: str = "") -> None:
    """Write sentinel status to trading_system_health."""
    try:
        get_supabase().table("trading_system_health").upsert(
            {
                "service_name": "sentinel",
                "status": status,
                "last_heartbeat_at": datetime.now(timezone.utc).isoformat(),
                "last_error_message": message if message else None,
            },
            on_conflict="service_name",
        ).execute()
    except Exception as e:
        logger.error(f"sentinel_health_write_failed: {e}")


def write_audit_log(action: str, metadata: dict) -> None:
    """Write audit log entry."""
    try:
        get_supabase().table("audit_logs").insert(
            {
                "action": action,
                "actor_type": "system",
                "metadata": metadata,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        ).execute()
    except Exception as e:
        logger.error(f"audit_log_write_failed: {e}")


async def check_railway_heartbeat() -> bool:
    """
    Ping Railway backend /health endpoint.
    Returns True if healthy, False if unreachable or unhealthy.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(RAILWAY_HEALTH_URL)
            if resp.status_code == 200:
                return True
            logger.warning(
                f"railway_health_non_200: status={resp.status_code}"
            )
            return False
    except Exception as e:
        logger.warning(f"railway_health_check_failed: {e}")
        return False


async def get_open_positions() -> list:
    """Get all open virtual positions from Supabase."""
    try:
        result = (
            get_supabase()
            .table("trading_positions")
            .select(
                "id, instrument, strategy_type, contracts, position_mode"
            )
            .eq("status", "open")
            .execute()
        )
        return result.data or []
    except Exception as e:
        logger.error(f"get_open_positions_failed: {e}")
        return []


async def close_all_positions_tradier() -> dict:
    """
    Close all open positions via Tradier API.
    Phase 2: virtual positions — marks them closed in Supabase.
    Phase 5: real orders sent to Tradier.
    Returns dict with closed count and any errors.
    """
    positions = await get_open_positions()
    if not positions:
        logger.info("sentinel_close_all: no open positions found")
        return {"closed": 0, "errors": 0}

    closed = 0
    errors = 0

    for pos in positions:
        try:
            get_supabase().table("trading_positions").update(
                {
                    "status": "closed",
                    "exit_at": datetime.now(timezone.utc).isoformat(),
                    "exit_reason": "sentinel_emergency_close",
                    "last_updated_at": datetime.now(timezone.utc).isoformat(),
                }
            ).eq("id", pos["id"]).execute()
            closed += 1
            logger.info(
                f"sentinel_closed_position: "
                f"id={pos['id']} "
                f"strategy={pos.get('strategy_type')}"
            )
        except Exception as e:
            errors += 1
            logger.error(
                f"sentinel_close_position_failed: "
                f"id={pos['id']} error={e}"
            )

    # Also halt today's session
    try:
        from datetime import date
        get_supabase().table("trading_sessions").update(
            {
                "session_status": "halted",
                "halt_reason": "sentinel_emergency_halt",
            }
        ).eq("session_date", date.today().isoformat()).execute()
        logger.critical("sentinel_halted_session")
    except Exception as e:
        logger.error(f"sentinel_halt_session_failed: {e}")

    return {"closed": closed, "errors": errors}


async def trigger_emergency_close(reason: str) -> None:
    """
    Trigger emergency close. Called when heartbeat lost > STALE_THRESHOLD.
    Idempotent — will not fire twice in the same sentinel process lifecycle.
    """
    global emergency_triggered

    if emergency_triggered:
        logger.warning("sentinel_emergency_already_triggered_skipping")
        return

    emergency_triggered = True
    logger.critical(f"SENTINEL_EMERGENCY_TRIGGERED: {reason}")

    write_audit_log(
        action="trading.sentinel_emergency_triggered",
        metadata={
            "reason": reason,
            "railway_url": RAILWAY_HEALTH_URL,
            "triggered_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    write_sentinel_health("error", f"EMERGENCY: {reason}")

    result = await close_all_positions_tradier()
    logger.critical(f"SENTINEL_EMERGENCY_CLOSE_RESULT: {result}")

    write_audit_log(
        action="trading.sentinel_emergency_close_complete",
        metadata=result,
    )
    write_sentinel_health(
        "degraded",
        f"Emergency close complete: {result['closed']} positions closed, "
        f"{result['errors']} errors",
    )


async def run_sentinel_loop() -> None:
    """
    Main sentinel loop. Runs forever.
    Checks Railway heartbeat every HEARTBEAT_INTERVAL_SECONDS.
    """
    start_health_server()
    global last_healthy_at

    logger.info(
        f"sentinel_started: "
        f"railway_url={RAILWAY_HEALTH_URL} "
        f"interval={HEARTBEAT_INTERVAL_SECONDS}s "
        f"stale_threshold={STALE_THRESHOLD_SECONDS}s "
        f"sandbox={TRADIER_SANDBOX}"
    )
    write_sentinel_health("healthy", "sentinel_started")

    while True:
        try:
            is_healthy = await check_railway_heartbeat()

            if is_healthy:
                last_healthy_at = time.time()
                global emergency_triggered
                # Reset emergency flag if system recovers
                if emergency_triggered:
                    emergency_triggered = False
                    logger.info("sentinel_railway_recovered")
                write_sentinel_health("healthy")
                logger.info("sentinel_heartbeat_ok")
            else:
                stale_seconds = time.time() - last_healthy_at
                logger.warning(
                    f"sentinel_heartbeat_missed: "
                    f"stale_for={stale_seconds:.0f}s "
                    f"threshold={STALE_THRESHOLD_SECONDS}s"
                )
                write_sentinel_health(
                    "degraded",
                    f"heartbeat_missed_{stale_seconds:.0f}s",
                )

                if stale_seconds > STALE_THRESHOLD_SECONDS:
                    await trigger_emergency_close(
                        f"railway_heartbeat_lost_{stale_seconds:.0f}s"
                    )

        except Exception as e:
            logger.error(f"sentinel_loop_error: {e}")
            write_sentinel_health("error", str(e))

        await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)


if __name__ == "__main__":
    asyncio.run(run_sentinel_loop())
