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
        fastapi.Depends = _passthrough  # S14 extension
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


# ─────────────────────────────────────────────────────────────────────
# Cache-vs-heartbeat race regression tests
# (the actual bug behind the Health page flicker)
# ─────────────────────────────────────────────────────────────────────

def test_cache_does_not_starve_last_heartbeat_at():
    """
    Regression guard for the S7-5 cache vs heartbeat_check race.

    Original bug: write_health_status short-circuited every same-status
    write, which meant `last_heartbeat_at` only refreshed when status
    actually changed. The 30 s keepalive jobs would fire 3+ times
    silently before heartbeat_check (90 s gate) marked the row
    "degraded". The next keepalive then wrote "healthy" because the
    cached status no longer matched, producing the observed flicker.

    Fix: even on a status match, force a real upsert if the cached
    timestamp is older than _HEALTH_CACHE_REFRESH_SECONDS.

    This test seeds a STALE cache timestamp (older than the threshold)
    and confirms write_health_status reaches the DB anyway.
    """
    import db

    saved_cache = dict(db._health_status_cache)
    saved_ts = dict(db._health_status_cache_ts)

    # Seed status = healthy with a timestamp older than the refresh
    # window, simulating a long quiescent period of identical
    # keepalive writes.
    db._health_status_cache["test_svc_stale"] = "healthy"
    db._health_status_cache_ts["test_svc_stale"] = (
        # time.monotonic() returns increasing seconds; subtracting
        # well past the refresh threshold guarantees cache_age >
        # _HEALTH_CACHE_REFRESH_SECONDS regardless of test scheduling.
        -1e9
    )

    write_calls = []
    try:
        with patch("db.get_client") as mock_client:
            mock_table = MagicMock()
            mock_client.return_value.table.return_value = mock_table

            def capture_upsert(*_a, **_kw):
                write_calls.append(1)
                return MagicMock(execute=MagicMock(return_value=MagicMock()))

            mock_table.upsert.side_effect = capture_upsert
            db.write_health_status("test_svc_stale", "healthy")
    finally:
        db._health_status_cache.clear()
        db._health_status_cache.update(saved_cache)
        db._health_status_cache_ts.clear()
        db._health_status_cache_ts.update(saved_ts)

    assert len(write_calls) == 1, (
        "Stale cache timestamp must force a DB upsert even on identical "
        "status, otherwise heartbeat_check will mark the service "
        "degraded after 90 s and the Health page will flicker."
    )


def test_cache_short_circuits_when_fresh_and_status_unchanged():
    """The performance optimisation must still hold: a fresh cache
    timestamp + identical status + no kwargs MUST skip the upsert.
    Otherwise we pay the 14 400 writes/day/service penalty S7-5
    was designed to avoid."""
    import time
    import db

    saved_cache = dict(db._health_status_cache)
    saved_ts = dict(db._health_status_cache_ts)
    db._health_status_cache["test_svc_fresh"] = "healthy"
    db._health_status_cache_ts["test_svc_fresh"] = time.monotonic()

    try:
        with patch("db.get_client") as mock_client:
            mock_table = MagicMock()
            mock_client.return_value.table.return_value = mock_table
            db.write_health_status("test_svc_fresh", "healthy")
            mock_table.upsert.assert_not_called()
    finally:
        db._health_status_cache.clear()
        db._health_status_cache.update(saved_cache)
        db._health_status_cache_ts.clear()
        db._health_status_cache_ts.update(saved_ts)


def test_cache_refresh_threshold_is_below_heartbeat_gate():
    """The cache refresh window MUST be smaller than the
    heartbeat_check 90 s gate. If the threshold is ever raised
    above 90 s the flicker bug returns."""
    import db
    assert db._HEALTH_CACHE_REFRESH_SECONDS < 90, (
        f"_HEALTH_CACHE_REFRESH_SECONDS={db._HEALTH_CACHE_REFRESH_SECONDS} "
        "must be < 90 (the heartbeat_check staleness gate)"
    )


# ─────────────────────────────────────────────────────────────────────
# data_ingestor keepalive
# ─────────────────────────────────────────────────────────────────────

def test_data_ingestor_keepalive_writes_healthy():
    """data_ingestor was previously written exactly once at startup
    and then never again — guaranteeing it stuck at degraded after
    90 s. The new keepalive must write healthy on each fire."""
    m, restore = _load_main_isolated()

    write_calls = []

    def fake_write(service_name, status, **kwargs):
        write_calls.append((service_name, status))
        return True

    try:
        with patch.object(m, "write_health_status", side_effect=fake_write):
            m.data_ingestor_keepalive()
    finally:
        restore()

    assert ("data_ingestor", "healthy") in write_calls, (
        f"data_ingestor_keepalive must write healthy. Got: {write_calls!r}"
    )


def test_data_ingestor_keepalive_registered_at_30s():
    """Source-grep guard — confirms the 30 s interval job is wired
    in on_startup at the same cadence as the engine keepalives."""
    with open(os.path.join(BACKEND, "main.py"), encoding="utf-8") as f:
        src = f.read()

    assert "data_ingestor_keepalive" in src, (
        "data_ingestor_keepalive function must exist"
    )
    job_block_start = src.find('id="data_ingestor_keepalive"')
    assert job_block_start > 0, (
        "data_ingestor_keepalive must be registered as a scheduler job"
    )
    window = src[max(0, job_block_start - 200): job_block_start + 100]
    assert "seconds=30" in window, (
        "data_ingestor_keepalive must fire every 30 s "
        "(matches the other engine keepalives)"
    )
    assert 'trigger="interval"' in window, (
        "data_ingestor_keepalive must use an interval trigger"
    )


# ─────────────────────────────────────────────────────────────────────
# Startup flush of stale degraded rows (cleans up rows written by the
# pre-abaf8db heartbeat_check)
# ─────────────────────────────────────────────────────────────────────

def _run_flush_with_rows(rows):
    """Drive _flush_stale_scheduled_service_status() once with a stubbed
    Supabase select that returns `rows`. Returns the list of
    (service, status) tuples that write_health_status was called with."""
    m, restore = _load_main_isolated()

    select_chain = MagicMock()
    select_chain.execute.return_value = MagicMock(data=rows)
    eq_chain = MagicMock()
    eq_chain.execute.return_value = MagicMock(data=rows)
    in_chain = MagicMock()
    in_chain.eq.return_value = eq_chain
    select_table = MagicMock()
    select_table.in_.return_value = in_chain
    table_chain = MagicMock()
    table_chain.select.return_value = select_table
    db_client = MagicMock()
    db_client.table.return_value = table_chain

    write_calls = []

    def fake_write(service_name, status, **kwargs):
        write_calls.append((service_name, status))
        return True

    try:
        with patch.object(m, "get_client", return_value=db_client), \
                patch.object(m, "write_health_status", side_effect=fake_write):
            m._flush_stale_scheduled_service_status()
    finally:
        restore()

    return write_calls


def test_flush_flips_degraded_scheduled_rows_to_idle():
    """The startup flush must reset stale degraded rows on scheduled
    services so the Health page shows a clean state without waiting
    for the next agent fire (which can be 12+ hours away for
    prediction_watchdog outside market hours)."""
    rows = [
        {"service_name": "flow_agent", "status": "degraded"},
        {"service_name": "prediction_watchdog", "status": "degraded"},
    ]
    write_calls = _run_flush_with_rows(rows)

    assert ("flow_agent", "idle") in write_calls
    assert ("prediction_watchdog", "idle") in write_calls
    assert all(status == "idle" for _, status in write_calls), (
        f"Flush must only ever write 'idle'. Got: {write_calls!r}"
    )


def test_flush_no_op_when_no_stale_rows():
    """If the DB has no stale degraded rows on scheduled services,
    the flush must not write anything."""
    write_calls = _run_flush_with_rows([])
    assert write_calls == [], (
        f"Flush must be a no-op on a clean DB. Got: {write_calls!r}"
    )


def test_flush_function_is_called_at_startup():
    """Source-grep guard — the flush must run inside on_startup so
    the cleanup happens on every Railway restart, not just one
    deploy. Anchors on the call site comment."""
    with open(os.path.join(BACKEND, "main.py"), encoding="utf-8") as f:
        src = f.read()

    assert "_flush_stale_scheduled_service_status()" in src, (
        "Startup flush must be called from on_startup"
    )
    on_startup_idx = src.find("async def on_startup")
    assert on_startup_idx > 0, "on_startup not found in main.py"
    flush_call_idx = src.find(
        "_flush_stale_scheduled_service_status()", on_startup_idx
    )
    assert flush_call_idx > on_startup_idx, (
        "Flush call must appear inside on_startup, not just defined "
        "as a function"
    )
