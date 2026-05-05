"""
T-ACT-063: end-to-end smoke test for the alerting transports.

Sends a single test alert through every transport currently
configured by environment. Exits with code 0 on success.

Usage (Slack webhook only):
    ALERT_SLACK_WEBHOOK_URL=https://hooks.slack.com/services/XXX/YYY/ZZZ \\
        python -m backend.scripts.test_alert "smoke test from MarketMuse"

Usage (Gmail SMTP only — typically only works off-Railway):
    ALERT_EMAIL=you@example.com \\
    ALERT_GMAIL_APP_PASSWORD=xxxxxxxxxxxxxxxx \\
        python -m backend.scripts.test_alert "smoke test from MarketMuse"

Usage (both transports — belt-and-suspenders):
    set both env var groups above; alerts will fire on each.

Notes:
    * The DB write to ``system_alerts`` is intentionally skipped here;
      this script smoke-tests the EXTERNAL transports only.
    * Run with ``_blocking=True`` so the script does not exit before
      the daemon thread completes its HTTP/SMTP work.
"""
from __future__ import annotations

import sys
from unittest.mock import patch


def main() -> int:
    """Send one test alert and return 0 on success, 1 on usage error."""
    detail = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "Default smoke-test detail (no CLI argument supplied)."
    )

    # Ensure backend/ is on sys.path so we can `import alerting`
    # whether the script is invoked via -m or directly.
    import os
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)

    import config
    from alerting import (
        WARNING,
        send_alert,
        _slack_webhook_configured,
        _smtp_configured,
    )

    print("T-ACT-063 alerting smoke test")
    print("-" * 50)
    print(
        f"Slack webhook configured: {_slack_webhook_configured()}"
    )
    print(f"SMTP configured: {_smtp_configured()}")
    if not _slack_webhook_configured() and not _smtp_configured():
        print(
            "ERROR: no transport configured. "
            "Set ALERT_SLACK_WEBHOOK_URL or "
            "ALERT_EMAIL+ALERT_GMAIL_APP_PASSWORD."
        )
        return 1

    # Skip DB write for the smoke test (we only care about transports).
    with patch("alerting._write_alert_to_db"):
        send_alert(
            WARNING,
            "alert_smoke_test",
            detail,
            _blocking=True,
        )

    print("Smoke test dispatched. Check your Slack channel and/or "
          "inbox for delivery.")
    print(
        "If a transport failed, look for "
        "alert_webhook_failed / alert_email_failed in stderr above."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
