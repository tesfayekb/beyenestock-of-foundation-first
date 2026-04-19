"""Tests for HARD-B alerting module."""
from unittest.mock import patch


def test_alert_skips_when_not_configured():
    """No ALERT_EMAIL set → alert silently skipped, no exception."""
    with patch("alerting.config") as mock_config:
        mock_config.ALERT_EMAIL = ""
        mock_config.ALERT_GMAIL_APP_PASSWORD = ""
        from alerting import send_alert, CRITICAL
        send_alert(CRITICAL, "test_event", "test detail", _blocking=True)


def test_alert_skips_when_no_password():
    """ALERT_EMAIL set but no password → silently skipped."""
    with patch("alerting.config") as mock_config:
        mock_config.ALERT_EMAIL = "test@example.com"
        mock_config.ALERT_GMAIL_APP_PASSWORD = ""
        mock_config.ALERT_FROM_EMAIL = "test@example.com"
        from alerting import send_alert, WARNING
        send_alert(WARNING, "test_event", _blocking=True)


def test_alert_sends_email_when_configured():
    """When configured, _send_email is called with correct subject."""
    sent_messages = []

    class MockSMTP:
        def __init__(self, *a, **kw):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

        def login(self, *a):
            pass

        def sendmail(self, frm, to, msg):
            sent_messages.append({"from": frm, "to": to, "msg": msg})

    with patch("alerting.config") as mock_config:
        mock_config.ALERT_EMAIL = "trader@example.com"
        mock_config.ALERT_GMAIL_APP_PASSWORD = "fake-app-password"
        mock_config.ALERT_FROM_EMAIL = "trader@example.com"
        with patch("alerting._write_alert_to_db"):
            with patch("smtplib.SMTP_SSL", MockSMTP):
                from alerting import send_alert, CRITICAL
                send_alert(
                    CRITICAL,
                    "daily_halt_triggered",
                    "Drawdown -3.0%",
                    _blocking=True,
                )

    assert len(sent_messages) == 1
    assert "daily_halt_triggered" in sent_messages[0]["msg"]
    assert "CRITICAL" in sent_messages[0]["msg"]


def test_alert_survives_smtp_failure():
    """SMTP auth failure → logged but no exception raised."""
    import smtplib

    class FailSMTP:
        def __init__(self, *a, **kw):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

        def login(self, *a):
            raise smtplib.SMTPAuthenticationError(535, b"Bad auth")

    with patch("alerting.config") as mock_config:
        mock_config.ALERT_EMAIL = "trader@example.com"
        mock_config.ALERT_GMAIL_APP_PASSWORD = "wrong-password"
        mock_config.ALERT_FROM_EMAIL = "trader@example.com"
        with patch("alerting._write_alert_to_db"):
            with patch("smtplib.SMTP_SSL", FailSMTP):
                from alerting import send_alert, CRITICAL
                # Must not raise even on SMTP failure
                send_alert(CRITICAL, "test_smtp_failure", _blocking=True)


def test_alert_db_write_failure_does_not_raise():
    """DB write fails → silently ignored, no exception."""
    with patch("alerting.config") as mock_config:
        mock_config.ALERT_EMAIL = "trader@example.com"
        mock_config.ALERT_GMAIL_APP_PASSWORD = "fake-pw"
        mock_config.ALERT_FROM_EMAIL = "trader@example.com"
        with patch(
            "alerting._write_alert_to_db",
            side_effect=Exception("DB down"),
        ):
            with patch("alerting._send_email"):
                from alerting import send_alert, INFO
                # _write_alert_to_db failure must not propagate
                send_alert(INFO, "test_db_failure", _blocking=True)


def test_alert_levels_produce_correct_subjects():
    """Each level produces correct prefix in email subject."""
    subjects = []

    class MockSMTP:
        def __init__(self, *a, **kw):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

        def login(self, *a):
            pass

        def sendmail(self, frm, to, msg):
            subjects.append(msg)

    with patch("alerting.config") as mock_config:
        mock_config.ALERT_EMAIL = "t@e.com"
        mock_config.ALERT_GMAIL_APP_PASSWORD = "pw"
        mock_config.ALERT_FROM_EMAIL = "t@e.com"
        with patch("alerting._write_alert_to_db"):
            with patch("smtplib.SMTP_SSL", MockSMTP):
                from alerting import send_alert, CRITICAL, WARNING, INFO
                send_alert(CRITICAL, "crit_event", _blocking=True)
                send_alert(WARNING, "warn_event", _blocking=True)
                send_alert(INFO, "info_event", _blocking=True)

    assert any("CRITICAL" in s for s in subjects)
    assert any("WARNING" in s for s in subjects)
    assert any("INFO" in s for s in subjects)
