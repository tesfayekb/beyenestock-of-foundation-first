from datetime import datetime, timezone
from typing import Optional

from config import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
from logger import get_logger

logger = get_logger("db")

_client = None


def get_client():
    global _client
    if _client is None:
        from supabase import create_client

        _client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    return _client


def write_health_status(service_name: str, status: str, **kwargs) -> bool:
    """
    Upsert a row to trading_system_health.
    Never raises - logs error and returns False on failure.
    """
    try:
        payload = {
            "service_name": service_name,
            "status": status,
            "last_heartbeat_at": datetime.now(timezone.utc).isoformat(),
            **kwargs,
        }
        # Always clear last_error_message when status is healthy — do not persist stale errors
        if status == "healthy" and "last_error_message" not in kwargs:
            payload["last_error_message"] = None
        get_client().table("trading_system_health").upsert(
            payload, on_conflict="service_name"
        ).execute()
        return True
    except Exception as e:
        logger.error("health_write_failed", service=service_name, error=str(e))
        return False


def write_audit_log(
    action: str,
    target_type: str = "trading",
    target_id: Optional[str] = None,
    metadata: Optional[dict] = None,
    correlation_id: Optional[str] = None,
) -> bool:
    """
    Insert a row to audit_logs.
    Never raises - logs error and returns False on failure.
    """
    try:
        payload = {
            "action": action,
            "target_type": target_type,
            "metadata": metadata or {},
        }
        if target_id:
            payload["target_id"] = target_id
        if correlation_id:
            payload["correlation_id"] = correlation_id
        get_client().table("audit_logs").insert(payload).execute()
        return True
    except Exception as e:
        logger.error("audit_write_failed", action=action, error=str(e))
        return False
