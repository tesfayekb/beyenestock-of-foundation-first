"""
Heartbeat policy tests — service-class-aware staleness gate.

Locks down the fix for the "degraded items in system health" issue
where heartbeat_check applied a single 90-second threshold to every
row in trading_system_health, including services that fire once per
day and are intentionally silent the rest of the time.

Invariants verified here:

  1. A service in _SCHEDULED_SERVICES that has not reported in over an
     hour is NOT marked degraded — heartbeat_check skips it entirely.
  2. A continuous service (prediction_engine, gex_engine, etc.) that
     has not reported in 95 seconds IS marked degraded — the 90 s gate
     for the five always-on services is unchanged.
  3. A scheduled service whose last self-written status is "error" is
     left untouched — heartbeat_check does not overwrite the error
     row with "degraded" between fires.

These tests do NOT exercise scheduling, signal logic, sizing, regime,
or any ROI-critical code path. They only verify the heartbeat policy.
"""
import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)


def _ensure_main_importable():
    """Stub the heavy Railway-only third-party deps that main.py imports
    at module load time so `import main` works in any test environment.

    Mirrors the pattern in test_consolidation_s8.py — fastapi and
    apscheduler are not required to validate the heartbeat policy.
    """
    import types
    if "fastapi" not in sys.modules:
        fastapi = types.ModuleType("fastapi")

        class _StubFastAPI:
            def __init__(self, *_a, **_kw):
                pass

            def add_middleware(self, *_a, **_kw):
                pass

            def _decorator(self, *_a, **_kw):
                def _wrap(fn):
                    return fn
                return _wrap

            on_event = _decorator
            get = _decorator
            post = _decorator
            put = _decorator
            delete = _decorator

        def _passthrough(*_a, **_kw):
            return None

        class _StubHTTPException(Exception):
            def __init__(self, *_a, **_kw):
                super().__init__(_a[0] if _a else "")

        fastapi.FastAPI = _StubFastAPI
        fastapi.Body = _passthrough
        fastapi.Header = _passthrough
        fastapi.HTTPException = _StubHTTPException
        sys.modules["fastapi"] = fastapi

        cors = types.ModuleType("fastapi.middleware.cors")

        class _StubCORS:
            def __init__(self, *_a, **_kw):
                pass

        cors.CORSMiddleware = _StubCORS
        sys.modules["fastapi.middleware"] = types.ModuleType(
            "fastapi.middleware"
        )
        sys.modules["fastapi.middleware.cors"] = cors

    if "apscheduler" not in sys.modules:
        apscheduler = types.ModuleType("apscheduler")
        schedulers = types.ModuleType("apscheduler.schedulers")
        asyncio_mod = types.ModuleType("apscheduler.schedulers.asyncio")

        class _StubAsyncIOScheduler:
            def __init__(self, *_a, **_kw):
                self.jobs = []

            def add_job(self, *_a, **_kw):
                self.jobs.append((_a, _kw))

            def start(self):
                pass

            def shutdown(self, *_a, **_kw):
                pass

        asyncio_mod.AsyncIOScheduler = _StubAsyncIOScheduler
        sys.modules["apscheduler"] = apscheduler
        sys.modules["apscheduler.schedulers"] = schedulers
        sys.modules["apscheduler.schedulers.asyncio"] = asyncio_mod


def _load_main_isolated():
    """Load backend/main.py under a unique key, then restore sys.modules.

    Same gymnastics as test_consolidation_s8._load_backend_main_isolated:
    `patch("main.get_client")` resolves through sys.modules so we
    temporarily install the freshly-loaded module under "main", but we
    must restore whatever sentinel/main.py or other test had cached
    before we ran.
    """
    _ensure_main_importable()
    import importlib.util

    saved_main = sys.modules.get("main")

    spec = importlib.util.spec_from_file_location(
        "_heartbeat_policy_main", os.path.join(BACKEND, "main.py")
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["main"] = module
    sys.modules["_heartbeat_policy_main"] = module
    spec.loader.exec_module(module)

    def restore():
        if saved_main is not None:
            sys.modules["main"] = saved_main
        else:
            sys.modules.pop("main", None)
        sys.modules.pop("_heartbeat_policy_main", None)

    return module, restore


def _iso(dt: datetime) -> str:
    """Match the trading_system_health column format
    (Postgres timestamptz serialised by supabase-py — ISO 8601 with
    a trailing Z or +00:00). heartbeat_check normalises Z -> +00:00."""
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _run_heartbeat_check(rows):
    """Drive heartbeat_check() once with a stubbed Supabase select that
    returns `rows`, and return the list of (service, status, kwargs)
    tuples that write_health_status was called with.
    """
    m, restore = _load_main_isolated()

    select_chain = MagicMock()
    select_chain.execute.return_value = MagicMock(data=rows)
    table_chain = MagicMock()
    table_chain.select.return_value = select_chain
    db_client = MagicMock()
    db_client.table.return_value = table_chain

    write_calls = []

    def fake_write(service_name, status, **kwargs):
        write_calls.append((service_name, status, kwargs))
        return True

    try:
        with patch.object(m, "get_client", return_value=db_client), \
                patch.object(m, "write_health_status", side_effect=fake_write):
            asyncio.run(m.heartbeat_check())
    finally:
        restore()

    return write_calls


# ─────────────────────────────────────────────────────────────────────
# Test 1 — scheduled service stale 1 hour → NOT marked degraded
# ─────────────────────────────────────────────────────────────────────

def test_scheduled_service_stale_one_hour_is_not_degraded():
    """
    economic_calendar fires once per day at 8:25 AM ET. By 9:25 AM
    ET its row in trading_system_health is 60 minutes stale, but that
    is its NORMAL idle state — not a failure. heartbeat_check must
    skip it; otherwise the Health page shows a false-positive
    "degraded" for 6+ hours every single trading day.

    This is the core regression guard for the fix.
    """
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    rows = [
        {
            "service_name": "economic_calendar",
            "last_heartbeat_at": _iso(one_hour_ago),
        },
    ]

    write_calls = _run_heartbeat_check(rows)

    degraded = [c for c in write_calls if c[1] == "degraded"]
    assert degraded == [], (
        "Scheduled services must NOT be marked degraded between fires. "
        f"Got unexpected write_health_status calls: {write_calls!r}"
    )


def test_all_scheduled_services_are_exempt_from_heartbeat_gate():
    """Verify every name in _SCHEDULED_SERVICES is exempt, not just
    economic_calendar — guards against a partial frozenset that misses
    a service when the registry grows."""
    m, restore = _load_main_isolated()
    try:
        scheduled = sorted(m._SCHEDULED_SERVICES)
    finally:
        restore()

    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    rows = [
        {"service_name": svc, "last_heartbeat_at": _iso(one_hour_ago)}
        for svc in scheduled
    ]

    write_calls = _run_heartbeat_check(rows)

    assert write_calls == [], (
        "No scheduled service should ever be touched by heartbeat_check. "
        f"Spurious writes: {write_calls!r}"
    )


# ─────────────────────────────────────────────────────────────────────
# Test 2 — continuous service stale 95s → IS marked degraded
# ─────────────────────────────────────────────────────────────────────

def test_continuous_service_stale_95s_is_marked_degraded():
    """
    The five always-on services (prediction_engine, gex_engine,
    strategy_selector, risk_engine, execution_engine) and the three
    streaming feeds (tradier_websocket, databento_feed, polygon_feed)
    keep the original 90 s gate. A 95 s gap is a real failure and
    must surface as degraded.
    """
    stale_ts = datetime.now(timezone.utc) - timedelta(seconds=95)
    rows = [
        {
            "service_name": "prediction_engine",
            "last_heartbeat_at": _iso(stale_ts),
        },
    ]

    write_calls = _run_heartbeat_check(rows)

    assert ("prediction_engine", "degraded", {"last_error_message": None}) \
        in write_calls, (
            "Continuous services must still be marked degraded after 90 s. "
            f"write calls were: {write_calls!r}"
        )


def test_continuous_service_fresh_is_not_degraded():
    """A continuous service that reported within the last 30 s must
    NOT be marked degraded — protects against the inverse regression
    (overzealous degradation of healthy services)."""
    fresh_ts = datetime.now(timezone.utc) - timedelta(seconds=30)
    rows = [
        {
            "service_name": "prediction_engine",
            "last_heartbeat_at": _iso(fresh_ts),
        },
    ]

    write_calls = _run_heartbeat_check(rows)

    assert write_calls == [], (
        "Fresh continuous services must not be touched. "
        f"Spurious writes: {write_calls!r}"
    )


# ─────────────────────────────────────────────────────────────────────
# Test 3 — scheduled service that wrote error itself → untouched
# ─────────────────────────────────────────────────────────────────────

def test_scheduled_service_with_real_error_is_not_overwritten():
    """
    If macro_agent fails its 8:30 AM ET run and writes status="error"
    itself, heartbeat_check must not silently downgrade that to
    "degraded" later in the day. Real errors must remain visible on
    the Health page until the agent's next successful run overwrites
    them.

    heartbeat_check only ever WRITES, it does not read status from
    the row, so the guarantee here is purely "scheduled services are
    skipped" — the test asserts no write_health_status call landed
    for macro_agent at all.
    """
    six_hours_ago = datetime.now(timezone.utc) - timedelta(hours=6)
    rows = [
        {
            "service_name": "macro_agent",
            "last_heartbeat_at": _iso(six_hours_ago),
        },
    ]

    write_calls = _run_heartbeat_check(rows)

    macro_writes = [c for c in write_calls if c[0] == "macro_agent"]
    assert macro_writes == [], (
        "Scheduled service with a real error must not be overwritten by "
        f"heartbeat_check. Unexpected writes: {macro_writes!r}"
    )


# ─────────────────────────────────────────────────────────────────────
# Bonus — _SCHEDULED_SERVICES contents and morning idle-marker
# ─────────────────────────────────────────────────────────────────────

def test_scheduled_services_contains_all_known_once_per_day_agents():
    """The frozenset must include every service that fires on a cron
    rather than continuously. Catches accidental removals during
    future refactors."""
    m, restore = _load_main_isolated()
    try:
        scheduled = m._SCHEDULED_SERVICES
    finally:
        restore()

    expected = {
        "economic_calendar",
        "macro_agent",
        "sentiment_agent",
        "synthesis_agent",
        "surprise_detector",
        "flow_agent",
        "earnings_scanner",
        "feedback_agent",
        "prediction_watchdog",
        "emergency_backstop",
        "position_reconciliation",
    }
    missing = expected - set(scheduled)
    assert not missing, f"_SCHEDULED_SERVICES is missing: {missing!r}"


def test_continuous_services_are_not_in_scheduled_set():
    """Belt-and-suspenders — make sure no continuous service slipped
    into the exempt list, which would silently disable degradation
    detection for the engines that actually need it."""
    m, restore = _load_main_isolated()
    try:
        scheduled = m._SCHEDULED_SERVICES
    finally:
        restore()

    must_be_monitored = {
        "prediction_engine",
        "gex_engine",
        "strategy_selector",
        "risk_engine",
        "execution_engine",
        "data_ingestor",
        "tradier_websocket",
        "databento_feed",
        "polygon_feed",
    }
    leaked = must_be_monitored & set(scheduled)
    assert not leaked, (
        f"Continuous services must NOT be exempt from heartbeat_check, "
        f"but these leaked into _SCHEDULED_SERVICES: {leaked!r}"
    )


def test_morning_agents_idle_marker_writes_idle_for_four_agents():
    """The 10:30 AM ET job marks the four pre-market agents as idle
    so the Health page shows a clear status instead of a 6-hour
    silence after their morning run."""
    m, restore = _load_main_isolated()

    write_calls = []

    def fake_write(service_name, status, **kwargs):
        write_calls.append((service_name, status))
        return True

    try:
        with patch.object(m, "write_health_status", side_effect=fake_write):
            m._run_morning_agents_idle_marker()
    finally:
        restore()

    assert set(write_calls) == {
        ("economic_calendar", "idle"),
        ("macro_agent", "idle"),
        ("surprise_detector", "idle"),
        ("earnings_scanner", "idle"),
    }, f"Unexpected idle-marker writes: {write_calls!r}"


def test_morning_idle_marker_job_registered_at_10_30_am_et():
    """Source-grep guard — confirms the cron job survived later
    refactors of on_startup. We deliberately do NOT instantiate the
    scheduler in this test (that path requires real apscheduler) —
    the assertion is a structural fingerprint."""
    with open(os.path.join(BACKEND, "main.py"), encoding="utf-8") as f:
        src = f.read()

    assert "trading_morning_agents_idle_marker" in src, (
        "10:30 AM idle-marker job must be registered in on_startup"
    )
    assert "_run_morning_agents_idle_marker" in src, (
        "Idle-marker job handler must be defined"
    )
    # hour=10 + minute=30 must appear together inside the registration
    # block. We anchor on the job id + hour/minute literals.
    job_block_start = src.find("trading_morning_agents_idle_marker")
    window = src[max(0, job_block_start - 600): job_block_start + 200]
    assert "hour=10" in window and "minute=30" in window, (
        "Idle-marker must fire at 10:30 ET, not some other time"
    )
    assert "day_of_week=\"mon-fri\"" in window, (
        "Idle-marker must only fire on weekdays"
    )
