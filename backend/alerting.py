"""
HARD-B: External alerting via Slack webhook and/or Gmail SMTP.

Sends notifications for critical trading events that require human
attention even when the dashboard is not being watched.

CRITICAL DESIGN CONSTRAINT:
  This module NEVER raises. NEVER blocks. NEVER delays trading.
  If a transport fails for any reason, the failure is logged and
  ignored. Trading correctness is always the priority.

T-ACT-063 (2026-05-04): Slack webhook transport added alongside the
existing Gmail SMTP path after the 76-hour silent-watchdog incident
2026-05-01 → 2026-05-04. Railway containers structurally block
outbound SMTP egress (ports 25/465/587 — see Railway docs); every
single watchdog ``send_alert`` call during the outage failed with
``alert_email_failed [Errno 101] Network is unreachable`` and the
operator was never paged. HTTPS:443 egress is always allowed on
Railway, so a webhook-based transport eliminates the egress class
of failure entirely. The two transports are co-equal: each one is
independently try/excepted inside a single daemon thread; one
transport's failure does NOT block the other from firing.

This module is standalone — it does NOT import from any other trading
module at the top level. The only top-level imports are config and
logger (foundational infrastructure modules). All trading-side imports
(db, etc.) happen inside try blocks where they are used to prevent
circular-import risk.

Configuration (Railway env vars — at least ONE transport must be set,
or alerting is silently disabled):

  ALERT_SLACK_WEBHOOK_URL  — Slack Incoming Webhook URL (preferred
                             on Railway; HTTPS, egress always works)

  ALERT_EMAIL              — recipient address (legacy Gmail SMTP)
  ALERT_GMAIL_APP_PASSWORD — Gmail App Password (not account password)
  ALERT_FROM_EMAIL         — sender address (defaults to ALERT_EMAIL)

To set up Slack webhook (T-ACT-063):
  Slack workspace → Apps → "Incoming Webhooks" → Add to channel →
  copy the webhook URL → paste into Railway env var
  ALERT_SLACK_WEBHOOK_URL.

To create a Gmail App Password:
  Google Account → Security → 2-Step Verification → App Passwords
  Name it "MarketMuse Railway" — copy the 16-char password.

Alert levels:
  CRITICAL — immediate action required (halt, backstop, watchdog)
  WARNING  — degraded operation, monitor closely
  INFO     — positive milestone reached (gate passed, threshold met)

All alerts are also written to the system_alerts table in Supabase
for the Phase Activation Dashboard (DASH-A) to display. The DB write
is independent of the external transports — it always fires regardless
of which transports are configured (or whether they succeed).
"""

from __future__ import annotations

import json as _json
import smtplib
import threading
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from urllib.error import URLError
from urllib.request import Request, urlopen

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


def _slack_webhook_configured() -> bool:
    """T-ACT-063: True if the Slack webhook transport is configured."""
    return bool(config.ALERT_SLACK_WEBHOOK_URL)


def _smtp_configured() -> bool:
    """True if the Gmail SMTP transport is configured."""
    return bool(config.ALERT_EMAIL) and bool(
        config.ALERT_GMAIL_APP_PASSWORD
    )


def send_alert(
    level: str,
    event: str,
    detail: str = "",
    *,
    _blocking: bool = False,
) -> None:
    """
    Fire an external alert across all configured transports and write
    to the system_alerts table.

    Never raises. Never blocks trading (runs in a daemon thread by
    default). Silently skips if NO transport is configured.

    Transports are co-equal and independently try/excepted: one
    transport's failure does NOT prevent the other from firing.
    Belt-and-suspenders by design — see T-ACT-063 / HANDOFF A.8.

    Args:
        level:     "critical" | "warning" | "info"
        event:     Short event name, e.g. "daily_halt_triggered"
        detail:    Human-readable explanation of what happened
        _blocking: Internal use only — runs synchronously for tests
    """
    if not _slack_webhook_configured() and not _smtp_configured():
        logger.debug(
            "alert_skipped_not_configured",
            level=level,
            alert_event=event,
        )
        return

    # Write to DB for dashboard (best-effort — never propagate).
    # Independent of external transports: fires even if both webhook
    # and SMTP are unconfigured (well, the early return above guards
    # against that). The dashboard had visibility into the watchdog
    # alerts during the 2026-05-01 outage; only the operator's
    # external notification was missing — that gap is what T-ACT-063
    # closes.
    try:
        _write_alert_to_db(level, event, detail)
    except Exception as exc:
        logger.debug("alert_db_write_failed", error=str(exc))

    # Fan out to all configured transports in a background daemon
    # thread so trading is never blocked. Transports run sequentially
    # inside the thread; each is independently try/excepted.
    if _blocking:
        _send_via_transports(level, event, detail)
    else:
        thread = threading.Thread(
            target=_send_via_transports,
            args=(level, event, detail),
            daemon=True,
            name=f"alert-{event[:20]}",
        )
        thread.start()


def _send_via_transports(level: str, event: str, detail: str) -> None:
    """
    T-ACT-063: Fan out to all configured external alert transports.

    Each transport is independently try/excepted at its own level;
    this orchestrator only coordinates ordering. The webhook fires
    first (preferred on Railway) so even if SMTP later raises, the
    operator has already been paged.
    """
    if _slack_webhook_configured():
        _send_slack_webhook(level, event, detail)
    if _smtp_configured():
        _send_email(level, event, detail)


def _send_slack_webhook(
    level: str,
    event: str,
    detail: str,
) -> None:
    """
    T-ACT-063: HTTP webhook transport. Posts a Slack-formatted
    message to ALERT_SLACK_WEBHOOK_URL via HTTPS:443 (always-allowed
    egress on Railway). Uses stdlib ``urllib.request`` — no new
    dependencies. Catches all exceptions; never raises.
    """
    try:
        prefix = _LEVEL_PREFIX.get(level, level.upper())
        now_utc = datetime.now(timezone.utc).strftime(
            "%Y-%m-%d %H:%M UTC"
        )

        # Slack mrkdwn formatting (asterisks for bold). Plain ASCII
        # only to guarantee transport-safe encoding.
        lines = [
            f"*[MarketMuse] {prefix}: {event}*",
            f"*Time:* {now_utc}",
        ]
        if detail:
            # Truncate aggressively — Slack message limit is ~40k
            # chars but operator notifications should be terse.
            lines.append(f"*Detail:* {detail[:1500]}")
        text = "\n".join(lines)

        payload = _json.dumps({"text": text}).encode("utf-8")
        req = Request(
            config.ALERT_SLACK_WEBHOOK_URL,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urlopen(req, timeout=10) as resp:
            status = getattr(resp, "status", None)
            if status is None:
                # urllib in some environments exposes getcode() instead.
                status = resp.getcode()

        if 200 <= status < 300:
            logger.info(
                "alert_webhook_sent",
                level=level,
                alert_event=event,
                transport="slack",
                status=status,
            )
        else:
            # Slack returns 200 OK on success; non-2xx is a real
            # failure (bad webhook URL, archived channel, etc.).
            logger.error(
                "alert_webhook_non_2xx",
                level=level,
                alert_event=event,
                transport="slack",
                status=status,
            )

    except URLError as url_err:
        logger.error(
            "alert_webhook_failed",
            level=level,
            alert_event=event,
            transport="slack",
            error=str(url_err),
            error_class="URLError",
        )
    except Exception as exc:
        logger.error(
            "alert_webhook_failed",
            level=level,
            alert_event=event,
            transport="slack",
            error=str(exc),
            error_class=type(exc).__name__,
        )


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
