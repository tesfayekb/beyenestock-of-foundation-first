from datetime import date, datetime, timezone
from typing import Optional

from db import get_client, write_audit_log
from logger import get_logger

logger = get_logger("session_manager")


def get_or_create_session(session_date: Optional[date] = None) -> Optional[dict]:
    """
    Get today's session or create it if it does not exist.
    Returns the session row dict or None on failure. Never raises.
    """
    try:
        if session_date is None:
            session_date = date.today()
        date_str = session_date.isoformat()

        result = (
            get_client()
            .table("trading_sessions")
            .select("*")
            .eq("session_date", date_str)
            .maybeSingle()
            .execute()
        )
        if result.data:
            return result.data

        new_session = {
            "session_date": date_str,
            "session_status": "pending",
            "regime": "unknown",
            "day_type": "unknown",
            "capital_preservation_active": False,
            "consecutive_losses_today": 0,
            "consecutive_loss_sessions": 0,
            "virtual_pnl": 0.0,
            "virtual_trades_count": 0,
            "virtual_wins": 0,
            "virtual_losses": 0,
        }
        created = (
            get_client().table("trading_sessions").insert(new_session).execute()
        )
        write_audit_log(
            action="trading.session_created",
            metadata={"session_date": date_str},
        )
        logger.info("session_created", session_date=date_str)
        return created.data[0] if created.data else None

    except Exception as e:
        logger.error("session_create_failed", error=str(e))
        return None


def update_session(session_id: str, **kwargs) -> bool:
    """Update fields on an existing session row. Never raises."""
    try:
        kwargs["updated_at"] = datetime.now(timezone.utc).isoformat()
        get_client().table("trading_sessions").update(kwargs).eq(
            "id", session_id
        ).execute()
        return True
    except Exception as e:
        logger.error("session_update_failed", session_id=session_id, error=str(e))
        return False


def get_today_session() -> Optional[dict]:
    """Get today's session row. Returns None if not found or on error."""
    try:
        result = (
            get_client()
            .table("trading_sessions")
            .select("*")
            .eq("session_date", date.today().isoformat())
            .maybeSingle()
            .execute()
        )
        return result.data
    except Exception as e:
        logger.error("session_fetch_failed", error=str(e))
        return None
