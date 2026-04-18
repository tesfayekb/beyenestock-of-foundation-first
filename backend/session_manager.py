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
            .maybe_single()
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
            get_client()
            .table("trading_sessions")
            .upsert(new_session, on_conflict="session_date")
            .execute()
        )
        write_audit_log(
            action="trading.session_created",
            metadata={"session_date": date_str},
        )
        logger.info("session_created", session_date=date_str)
        if not created or not created.data:
            logger.error("session_upsert_empty_response", session_date=date_str)
            return None
        return created.data[0]

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
            .maybe_single()
            .execute()
        )
        return result.data
    except Exception as e:
        logger.error("session_fetch_failed", error=str(e))
        return None


def open_today_session() -> bool:
    """
    Transition today's session from 'pending' to 'active' at market open.
    Called at 9:30 AM ET by scheduler.
    Returns True on success, False on failure. Never raises.
    """
    try:
        session = get_today_session()
        if not session:
            session = get_or_create_session()
        if not session:
            logger.error("open_today_session_no_session")
            return False

        if session.get("session_status") == "halted":
            logger.warning("open_today_session_already_halted")
            return False

        import zoneinfo
        et = zoneinfo.ZoneInfo("America/New_York")
        now_et = datetime.now(et)

        ok = update_session(
            session["id"],
            session_status="active",
            market_open_at=datetime.now(timezone.utc).isoformat(),
            spx_open=None,
            vix_open=None,
        )
        if ok:
            write_audit_log(
                action="trading.session_opened",
                metadata={
                    "session_date": session.get("session_date"),
                    "session_id": session["id"],
                },
            )
            logger.info("session_opened", session_date=session.get("session_date"))
        return ok
    except Exception as e:
        logger.error("open_today_session_failed", error=str(e))
        return False


def close_today_session() -> bool:
    """
    Transition today's session from 'active' to 'closed' at market close.
    Called at 4:30 PM ET by EOD criteria job (after positions are closed).
    Returns True on success, False on failure. Never raises.
    """
    try:
        session = get_today_session()
        if not session:
            logger.warning("close_today_session_no_session")
            return False

        if session.get("session_status") in ("halted", "closed"):
            logger.info(
                "close_today_session_already_terminal",
                status=session.get("session_status"),
            )
            return True  # already in terminal state, not an error

        ok = update_session(
            session["id"],
            session_status="closed",
            market_close_at=datetime.now(timezone.utc).isoformat(),
        )

        # D-022: update consecutive_loss_sessions counter
        if ok:
            try:
                # Read last 3 sessions to compute consecutive losses
                recent = (
                    get_client()
                    .table("trading_sessions")
                    .select("session_date, virtual_pnl")
                    .eq("session_status", "closed")
                    .order("session_date", desc=True)
                    .limit(3)
                    .execute()
                )
                sessions_data = recent.data or []
                consecutive = 0
                for s in sessions_data:
                    if (s.get("virtual_pnl") or 0.0) < 0:
                        consecutive += 1
                    else:
                        break  # streak broken

                update_session(
                    session["id"],
                    consecutive_loss_sessions=consecutive,
                )
                if consecutive >= 3:
                    write_audit_log(
                        action="trading.consecutive_loss_sessions_alert",
                        metadata={
                            "session_date": session.get("session_date"),
                            "consecutive_loss_sessions": consecutive,
                            "d022_active": True,
                        },
                    )
                    logger.warning(
                        "d022_consecutive_loss_sessions",
                        consecutive=consecutive,
                        session_date=session.get("session_date"),
                    )
            except Exception as e:
                logger.error("d022_session_tracking_failed", error=str(e))

        # Snapshot error counts for GLC-006 before EOD reset
        if ok:
            try:
                health_result = (
                    get_client()
                    .table("trading_system_health")
                    .select("service_name, error_count_1h")
                    .execute()
                )
                total_errors = sum(
                    (r.get("error_count_1h") or 0)
                    for r in (health_result.data or [])
                )
                write_audit_log(
                    action="trading.session_error_snapshot",
                    metadata={
                        "session_date": session.get("session_date"),
                        "session_id": session["id"],
                        "total_errors": total_errors,
                        "services": [
                            {"service": r.get("service_name"),
                             "errors": r.get("error_count_1h") or 0}
                            for r in (health_result.data or [])
                            if (r.get("error_count_1h") or 0) > 0
                        ],
                    },
                )
            except Exception as snap_err:
                logger.warning(
                    "session_error_snapshot_failed", error=str(snap_err)
                )

        if ok:
            write_audit_log(
                action="trading.session_closed",
                metadata={
                    "session_date": session.get("session_date"),
                    "session_id": session["id"],
                    "virtual_pnl": session.get("virtual_pnl"),
                    "virtual_trades": session.get("virtual_trades_count"),
                },
            )
            logger.info(
                "session_closed",
                session_date=session.get("session_date"),
                virtual_pnl=session.get("virtual_pnl"),
            )
        return ok
    except Exception as e:
        logger.error("close_today_session_failed", error=str(e))
        return False
