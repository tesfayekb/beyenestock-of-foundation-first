"""Tests for HARD-B alerting module.

Two transport classes are exercised:

* SMTP (legacy / belt-and-suspenders) — tests in this file historically
  patched ``smtplib.SMTP_SSL``; existing fixtures retained as-is, with
  ``ALERT_SLACK_WEBHOOK_URL`` explicitly set to "" so the new webhook
  path does NOT engage and these tests remain pure SMTP-path tests.

* Slack webhook (T-ACT-063, 2026-05-04) — new tests added at the bottom
  of this file. They patch ``alerting.urlopen`` and assert on the JSON
  payload and orchestration semantics.
"""
import json
from unittest.mock import MagicMock, patch


def test_alert_skips_when_not_configured():
    """No transport configured → alert silently skipped, no exception."""
    with patch("alerting.config") as mock_config:
        # Both transports unconfigured.
        mock_config.ALERT_SLACK_WEBHOOK_URL = ""
        mock_config.ALERT_EMAIL = ""
        mock_config.ALERT_GMAIL_APP_PASSWORD = ""
        from alerting import send_alert, CRITICAL
        send_alert(CRITICAL, "test_event", "test detail", _blocking=True)


def test_alert_skips_when_no_password():
    """ALERT_EMAIL set but no password AND no webhook → silently skipped."""
    with patch("alerting.config") as mock_config:
        mock_config.ALERT_SLACK_WEBHOOK_URL = ""
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
        mock_config.ALERT_SLACK_WEBHOOK_URL = ""
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
        mock_config.ALERT_SLACK_WEBHOOK_URL = ""
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
        mock_config.ALERT_SLACK_WEBHOOK_URL = ""
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
        mock_config.ALERT_SLACK_WEBHOOK_URL = ""
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


# ──────────────────────────────────────────────────────────────────
# T-ACT-063: Slack webhook transport tests
# ──────────────────────────────────────────────────────────────────


def _build_urlopen_mock(status: int = 200):
    """
    Build a mock for ``alerting.urlopen`` that mimics the context-manager
    response object stdlib ``urlopen`` returns. Captures the Request
    objects for payload assertions.
    """
    captured_requests = []

    response = MagicMock()
    response.status = status
    response.__enter__ = lambda self: self
    response.__exit__ = lambda self, *a: None

    def fake_urlopen(req, timeout=None):
        captured_requests.append(req)
        return response

    return fake_urlopen, captured_requests


def test_webhook_sends_when_configured_only_webhook():
    """T-ACT-063: webhook URL set, no SMTP → webhook fires once,
    SMTP path is NOT exercised."""
    fake_urlopen, captured = _build_urlopen_mock(status=200)

    with patch("alerting.config") as mock_config:
        mock_config.ALERT_SLACK_WEBHOOK_URL = (
            "https://hooks.slack.com/services/AAA/BBB/CCC"
        )
        mock_config.ALERT_EMAIL = ""
        mock_config.ALERT_GMAIL_APP_PASSWORD = ""
        mock_config.ALERT_FROM_EMAIL = ""
        with patch("alerting._write_alert_to_db"):
            with patch("alerting.urlopen", side_effect=fake_urlopen):
                # Spy on _send_email to assert it is NOT called when
                # SMTP is unconfigured.
                with patch("alerting._send_email") as mock_send_email:
                    from alerting import send_alert, CRITICAL
                    send_alert(
                        CRITICAL,
                        "prediction_watchdog_triggered",
                        "Prediction engine silent for 27.5 minutes.",
                        _blocking=True,
                    )

    assert len(captured) == 1, "Webhook should fire exactly once"
    mock_send_email.assert_not_called()


def test_webhook_payload_shape_and_url():
    """T-ACT-063: webhook payload is JSON with a ``text`` field
    containing level prefix, event name, and detail. Method is POST.
    URL matches configured ALERT_SLACK_WEBHOOK_URL."""
    fake_urlopen, captured = _build_urlopen_mock(status=200)

    webhook_url = "https://hooks.slack.com/services/T123/B456/abc789"
    with patch("alerting.config") as mock_config:
        mock_config.ALERT_SLACK_WEBHOOK_URL = webhook_url
        mock_config.ALERT_EMAIL = ""
        mock_config.ALERT_GMAIL_APP_PASSWORD = ""
        mock_config.ALERT_FROM_EMAIL = ""
        with patch("alerting._write_alert_to_db"):
            with patch("alerting.urlopen", side_effect=fake_urlopen):
                from alerting import send_alert, CRITICAL
                send_alert(
                    CRITICAL,
                    "daily_halt_triggered",
                    "Drawdown -3.0%",
                    _blocking=True,
                )

    assert len(captured) == 1
    req = captured[0]
    assert req.full_url == webhook_url
    assert req.get_method() == "POST"
    assert req.headers.get("Content-type") == "application/json"

    body = json.loads(req.data.decode("utf-8"))
    assert "text" in body
    text = body["text"]
    assert "CRITICAL" in text
    assert "daily_halt_triggered" in text
    assert "Drawdown -3.0%" in text


def test_webhook_failure_does_not_raise_and_smtp_still_fires():
    """T-ACT-063 transport-isolation invariant: webhook URLError
    is logged and swallowed; SMTP transport still fires for
    belt-and-suspenders redundancy."""
    from urllib.error import URLError

    smtp_calls = []

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
            smtp_calls.append(msg)

    def failing_urlopen(req, timeout=None):
        raise URLError("Network is unreachable")

    with patch("alerting.config") as mock_config:
        mock_config.ALERT_SLACK_WEBHOOK_URL = (
            "https://hooks.slack.com/services/X/Y/Z"
        )
        mock_config.ALERT_EMAIL = "trader@example.com"
        mock_config.ALERT_GMAIL_APP_PASSWORD = "pw"
        mock_config.ALERT_FROM_EMAIL = "trader@example.com"
        with patch("alerting._write_alert_to_db"):
            with patch("alerting.urlopen", side_effect=failing_urlopen):
                with patch("smtplib.SMTP_SSL", MockSMTP):
                    from alerting import send_alert, CRITICAL
                    # Webhook will raise URLError internally (caught),
                    # SMTP must still fire afterward.
                    send_alert(
                        CRITICAL,
                        "webhook_isolation_test",
                        _blocking=True,
                    )

    assert len(smtp_calls) == 1, (
        "SMTP transport must fire even after webhook URLError — "
        "transport isolation invariant violated"
    )


def test_webhook_non_2xx_logged_but_does_not_raise():
    """T-ACT-063: Slack returns 4xx/5xx → logged at error level
    but no exception propagates."""
    fake_urlopen, captured = _build_urlopen_mock(status=403)

    with patch("alerting.config") as mock_config:
        mock_config.ALERT_SLACK_WEBHOOK_URL = (
            "https://hooks.slack.com/services/bad/url"
        )
        mock_config.ALERT_EMAIL = ""
        mock_config.ALERT_GMAIL_APP_PASSWORD = ""
        mock_config.ALERT_FROM_EMAIL = ""
        with patch("alerting._write_alert_to_db"):
            with patch("alerting.urlopen", side_effect=fake_urlopen):
                from alerting import send_alert, WARNING
                send_alert(
                    WARNING,
                    "test_403",
                    _blocking=True,
                )

    assert len(captured) == 1


def test_webhook_truncates_long_detail():
    """T-ACT-063: detail strings >1500 chars are truncated to keep
    Slack messages terse and within reasonable display limits."""
    fake_urlopen, captured = _build_urlopen_mock(status=200)

    long_detail = "x" * 5000
    with patch("alerting.config") as mock_config:
        mock_config.ALERT_SLACK_WEBHOOK_URL = (
            "https://hooks.slack.com/services/A/B/C"
        )
        mock_config.ALERT_EMAIL = ""
        mock_config.ALERT_GMAIL_APP_PASSWORD = ""
        mock_config.ALERT_FROM_EMAIL = ""
        with patch("alerting._write_alert_to_db"):
            with patch("alerting.urlopen", side_effect=fake_urlopen):
                from alerting import send_alert, CRITICAL
                send_alert(
                    CRITICAL,
                    "long_detail_test",
                    long_detail,
                    _blocking=True,
                )

    body = json.loads(captured[0].data.decode("utf-8"))
    text = body["text"]
    detail_count = text.count("x")
    assert detail_count <= 1500, (
        f"Detail truncation failed: {detail_count} 'x' chars in payload, "
        f"expected <= 1500"
    )


def test_send_alert_is_non_blocking_by_default():
    """T-ACT-063 / preserved invariant: send_alert MUST run in a
    daemon thread by default so trading is never blocked."""
    fake_urlopen, captured = _build_urlopen_mock(status=200)

    with patch("alerting.config") as mock_config:
        mock_config.ALERT_SLACK_WEBHOOK_URL = (
            "https://hooks.slack.com/services/A/B/C"
        )
        mock_config.ALERT_EMAIL = ""
        mock_config.ALERT_GMAIL_APP_PASSWORD = ""
        mock_config.ALERT_FROM_EMAIL = ""
        with patch("alerting._write_alert_to_db"):
            with patch("alerting.urlopen", side_effect=fake_urlopen):
                with patch(
                    "alerting.threading.Thread"
                ) as mock_thread_cls:
                    mock_thread = MagicMock()
                    mock_thread_cls.return_value = mock_thread
                    from alerting import send_alert, INFO
                    send_alert(INFO, "non_blocking_test")

    mock_thread_cls.assert_called_once()
    kwargs = mock_thread_cls.call_args.kwargs
    assert kwargs.get("daemon") is True, (
        "send_alert thread must be daemon to avoid blocking shutdown"
    )
    mock_thread.start.assert_called_once()


def test_webhook_skipped_when_only_smtp_configured():
    """T-ACT-063: SMTP set but no webhook URL → webhook NOT exercised
    (urlopen never called)."""
    smtp_calls = []

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
            smtp_calls.append(msg)

    with patch("alerting.config") as mock_config:
        mock_config.ALERT_SLACK_WEBHOOK_URL = ""
        mock_config.ALERT_EMAIL = "trader@example.com"
        mock_config.ALERT_GMAIL_APP_PASSWORD = "pw"
        mock_config.ALERT_FROM_EMAIL = "trader@example.com"
        with patch("alerting._write_alert_to_db"):
            with patch("alerting.urlopen") as mock_urlopen:
                with patch("smtplib.SMTP_SSL", MockSMTP):
                    from alerting import send_alert, CRITICAL
                    send_alert(
                        CRITICAL,
                        "smtp_only_test",
                        _blocking=True,
                    )

    mock_urlopen.assert_not_called()
    assert len(smtp_calls) == 1
