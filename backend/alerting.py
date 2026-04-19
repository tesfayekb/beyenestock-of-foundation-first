"""
HARD-B: External alerting via Gmail.

Sends email notifications for critical trading events that require
human attention even when the dashboard is not being watched.

CRITICAL DESIGN CONSTRAINT:
  This module NEVER raises. NEVER blocks. NEVER delays trading.
  If email fails for any reason, the failure is logged and ignored.
  Trading correctness is always the priority.

This module is standalone — it does NOT import from any other trading
module at the top level. The only top-level imports are config and
logger (foundational infrastructure modules). All trading-side imports
(db, etc.) happen inside try blocks where they are used to prevent
circular-import risk.

Configuration (Railway env vars):
  ALERT_EMAIL              — recipient address
  ALERT_GMAIL_APP_PASSWORD — Gmail App Password (not account password)
  ALERT_FROM_EMAIL         — sender address (defaults to ALERT_EMAIL)

To create a Gmail App Password:
  Google Account → Security → 2-Step Verification → App Passwords
  Name it "MarketMuse Railway" — copy the 16-char password.

Alert levels:
  CRITICAL — immediate action required (halt, backstop, watchdog)
  WARNING  — degraded operation, monitor closely
  INFO     — positive milestone reached (gate passed, threshold met)

All alerts are also written to the system_alerts table in Supabase
for the Phase Activation Dashboard (DASH-A) to display.
"""

from __future__ import annotations

import smtplib
import threading
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import config
from logger import get_logger

logger = get_logger("alerting")

# Alert level definitions
CRITICAL = "critical"
WARNING = "warning"
INFO = "info"

# Subject-line prefix per level for quick scanning in email client.
# ASCII-only to guarantee SMTP-safe encoding across mail providers.
_LEVEL_PREFIX = {
    CRITICAL: "CRITICAL",
    WARNING: "WARNING",
    INFO: "INFO",
}


def send_alert(
    level: str,
    event: str,
    detail: str = "",
    *,
    _blocking: bool = False,
) -> None:
    """
    Send an external alert email and write to system_alerts table.

    Never raises. Never blocks trading (runs in a daemon thread).
    Silently skips if ALERT_EMAIL or ALERT_GMAIL_APP_PASSWORD is not set.

    Args:
        level:     "critical" | "warning" | "info"
        event:     Short event name, e.g. "daily_halt_triggered"
        detail:    Human-readable explanation of what happened
        _blocking: Internal use only — runs synchronously for tests
    """
    if not config.ALERT_EMAIL or not config.ALERT_GMAIL_APP_PASSWORD:
        logger.debug(
            "alert_skipped_not_configured",
            level=level,
            alert_event=event,
        )
        return

    # Write to DB for dashboard (best-effort — never propagate)
    try:
        _write_alert_to_db(level, event, detail)
    except Exception as exc:
        logger.debug("alert_db_write_failed", error=str(exc))

    # Send email in background thread so trading is never blocked
    if _blocking:
        _send_email(level, event, detail)
    else:
        thread = threading.Thread(
            target=_send_email,
            args=(level, event, detail),
            daemon=True,
            name=f"alert-{event[:20]}",
        )
        thread.start()


def _send_email(level: str, event: str, detail: str) -> None:
    """Internal: build and send the email. Catches all exceptions."""
    try:
        prefix = _LEVEL_PREFIX.get(level, level.upper())
        subject = f"[MarketMuse] {prefix}: {event}"

        now_et = datetime.now(timezone.utc).strftime(
            "%Y-%m-%d %H:%M UTC"
        )

        body_text = (
            f"MarketMuse Trading Alert\n"
            f"{'=' * 50}\n"
            f"Level:  {prefix}\n"
            f"Event:  {event}\n"
            f"Time:   {now_et}\n\n"
            f"{detail if detail else 'No additional detail provided.'}\n\n"
            f"{'=' * 50}\n"
            f"View dashboard: check /trading/health for current "
            f"system status.\n"
            f"To silence: set ALERT_EMAIL= in Railway environment "
            f"variables.\n"
        )

        # Color cue per level for the HTML view
        level_color = (
            "#dc2626" if level == CRITICAL
            else "#d97706" if level == WARNING
            else "#2563eb"
        )
        detail_row = (
            f'<tr><td style="padding: 4px 8px; font-weight: bold;">'
            f'Detail</td>'
            f'<td style="padding: 4px 8px;">{detail}</td></tr>'
        ) if detail else ""

        body_html = (
            f'<html><body style="font-family: Arial, sans-serif; '
            f'max-width: 600px;">'
            f'<h2 style="color: {level_color}">{prefix}: {event}</h2>'
            f'<table style="border-collapse: collapse; width: 100%;">'
            f'<tr><td style="padding: 4px 8px; font-weight: bold;">'
            f'Time</td><td style="padding: 4px 8px;">{now_et}</td></tr>'
            f'<tr><td style="padding: 4px 8px; font-weight: bold;">'
            f'Event</td><td style="padding: 4px 8px;">{event}</td></tr>'
            f'{detail_row}'
            f'</table>'
            f'<p style="margin-top: 16px; color: #6b7280; '
            f'font-size: 12px;">MarketMuse | View: /trading/health</p>'
            f'</body></html>'
        )

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = config.ALERT_FROM_EMAIL
        msg["To"] = config.ALERT_EMAIL
        msg.attach(MIMEText(body_text, "plain"))
        msg.attach(MIMEText(body_html, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as srv:
            srv.login(
                config.ALERT_FROM_EMAIL,
                config.ALERT_GMAIL_APP_PASSWORD,
            )
            srv.sendmail(
                config.ALERT_FROM_EMAIL,
                config.ALERT_EMAIL,
                msg.as_string(),
            )

        logger.info("alert_email_sent", level=level, alert_event=event)

    except smtplib.SMTPAuthenticationError:
        logger.error(
            "alert_email_auth_failed",
            hint=(
                "Check ALERT_GMAIL_APP_PASSWORD in Railway env vars. "
                "Must be a Gmail App Password, not your account password."
            ),
        )
    except Exception as exc:
        logger.error(
            "alert_email_failed",
            level=level,
            alert_event=event,
            error=str(exc),
        )


def _write_alert_to_db(level: str, event: str, detail: str) -> None:
    """
    Write alert to system_alerts table for DASH-A dashboard display.
    Best-effort — silently ignored if table does not exist yet (pre-DASH-A).
    Imports db lazily inside the function to keep this module
    free of trading-side imports at the top level.
    """
    try:
        # Lazy import — kept inside the try block to avoid circular
        # imports and to keep alerting.py importable in isolation.
        from db import get_client
        get_client().table("system_alerts").insert({
            "level": level,
            "event": event,
            "detail": detail[:1000] if detail else "",
            "fired_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
    except Exception:
        # Table may not exist until DASH-A is built — that is fine.
        pass
