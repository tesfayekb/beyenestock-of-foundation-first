"""Consolidation Sprint — Session 7 regression tests.

Locks down the reliability cleanup fixes from this session:

  S7-1  on_shutdown guards each feed.stop() with a None check so a
        partial startup doesn't mask the real error with
        AttributeError on None.
  S7-2  trading_flow_refresh interval job carries max_instances=1 +
        coalesce=True so a slow flow_agent run can't stack up.
  S7-3  heartbeat_check moves its sync DB read into asyncio.to_thread()
        so the event loop is never blocked on a Supabase round-trip.
  S7-4  logger.get_logger() configures structlog exactly once per
        process via the _configured sentinel.
  S7-5  write_health_status compares the new status against an
        in-process cache and skips the upsert when nothing changed
        and no diagnostic kwargs are present. Errors and status
        changes always write through.
  S7-6  Finnhub (economic + earnings calendars) and the Polygon flow
        agent move their API keys out of the URL and into headers.
"""
import os
import sys
from unittest.mock import MagicMock, patch

# Ensure backend/ and backend_agents/ are importable regardless of
# pytest's current working directory.
_BACKEND_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)
_AGENTS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "backend_agents")
)
for _p in (_BACKEND_DIR, _AGENTS_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)


# ── S7-1: on_shutdown None guards ─────────────────────────────────────

def _read_on_shutdown_body():
    """Return the source body of on_shutdown() for inspection.

    We can't always import main in a unit-test process — apscheduler
    is a Railway-only dependency in some local environments — so we
    grep the function out of the source file instead. Same pattern
    used for the heartbeat_check assertion below.
    """
    path = os.path.join(_BACKEND_DIR, "main.py")
    with open(path, encoding="utf-8") as f:
        src = f.read()
    idx = src.find("async def on_shutdown")
    assert idx != -1, "on_shutdown not found in main.py"
    # Body extends until the next top-level decorator or def.
    next_marker = min(
        x for x in (
            src.find('@app.', idx + 1),
            src.find('\nasync def ', idx + 1),
            src.find('\ndef ', idx + 1),
            len(src),
        ) if x != -1
    )
    return src[idx:next_marker]


def test_shutdown_guards_tradier_feed():
    """on_shutdown must None-check tradier_feed before await .stop()."""
    body = _read_on_shutdown_body()
    assert "if tradier_feed is not None" in body, (
        "on_shutdown must guard tradier_feed.stop() with a None check "
        "— partial startup leaves the global as None and "
        "AttributeError on None masks the real startup error"
    )


def test_shutdown_guards_polygon_and_databento_feeds():
    """All three feeds must be None-guarded — not just tradier."""
    body = _read_on_shutdown_body()
    assert "if polygon_feed is not None" in body, (
        "on_shutdown must guard polygon_feed.stop() with a None check"
    )
    assert "if databento_feed is not None" in body, (
        "on_shutdown must guard databento_feed.stop() with a None check"
    )
    # Existing redis guard must still be present (regression check).
    assert "if redis_client is not None" in body, (
        "Existing redis_client guard removed — must stay"
    )


# ── S7-2: flow agent interval job guards ─────────────────────────────

def test_flow_agent_interval_has_max_instances_and_coalesce():
    """trading_flow_refresh registration must carry both guards."""
    path = os.path.join(_BACKEND_DIR, "main.py")
    with open(path, encoding="utf-8") as f:
        src = f.read()
    # Pull just the trading_flow_refresh add_job block.
    idx = src.find('id="trading_flow_refresh"')
    assert idx != -1, "trading_flow_refresh registration not found"
    # Look at a generous window around the add_job kwargs block —
    # the comment block we add for S7-2 pushes max_instances/coalesce
    # well past the id= line.
    block = src[max(0, idx - 200): idx + 1200]
    assert "max_instances=1" in block, (
        "trading_flow_refresh missing max_instances=1 — "
        "concurrent runs can stack up on slow flow_agent fetches"
    )
    assert "coalesce=True" in block, (
        "trading_flow_refresh missing coalesce=True — "
        "missed fires queue back-to-back"
    )


# ── S7-3: heartbeat_check off the event loop ─────────────────────────

def test_heartbeat_check_uses_to_thread():
    """heartbeat_check body must run the DB read via asyncio.to_thread."""
    path = os.path.join(_BACKEND_DIR, "main.py")
    with open(path, encoding="utf-8") as f:
        src = f.read()
    idx = src.find("async def heartbeat_check")
    assert idx != -1, "heartbeat_check not found"
    # Inspect the function body up to the next top-level `async def`
    # or `@app.on_event`.
    next_def = src.find("async def ", idx + 1)
    body = src[idx:next_def] if next_def != -1 else src[idx:]
    assert "asyncio.to_thread" in body, (
        "heartbeat_check must wrap the sync DB read in asyncio.to_thread "
        "to avoid blocking the event loop"
    )


# ── S7-4: structlog configure guard ──────────────────────────────────

def test_structlog_configure_called_once():
    """get_logger() must call structlog.configure() exactly once."""
    import logger as log_module

    saved = log_module._configured
    log_module._configured = False

    calls = []
    real_configure = log_module.structlog.configure

    def counting_configure(*a, **kw):
        calls.append(1)
        return real_configure(*a, **kw)

    try:
        with patch.object(
            log_module.structlog,
            "configure",
            side_effect=counting_configure,
        ):
            log_module.get_logger("test_a")
            log_module.get_logger("test_b")
            log_module.get_logger("test_c")
        assert len(calls) == 1, (
            f"structlog.configure called {len(calls)} times across 3 "
            "get_logger() calls; expected exactly 1"
        )
    finally:
        log_module._configured = saved


# ── S7-5: write_health_status compare-then-write cache ───────────────

def test_write_health_status_skips_duplicate_healthy():
    """Same-status 'healthy' write with no kwargs and a fresh
    cache timestamp must skip the upsert.

    Post-flicker-fix: the cache short-circuit is now also gated
    on `_health_status_cache_ts` being newer than
    `_HEALTH_CACHE_REFRESH_SECONDS`, so the test must seed both
    caches to exercise the skip path (the original behaviour
    before the time-aware bound was added).
    """
    import time
    import db

    saved_cache = dict(db._health_status_cache)
    saved_ts = dict(db._health_status_cache_ts)
    db._health_status_cache["test_service_skip"] = "healthy"
    db._health_status_cache_ts["test_service_skip"] = time.monotonic()

    try:
        with patch("db.get_client") as mock_get_client:
            mock_table = MagicMock()
            mock_get_client.return_value.table.return_value = mock_table
            result = db.write_health_status("test_service_skip", "healthy")
        assert result is True
        mock_table.upsert.assert_not_called()
    finally:
        db._health_status_cache.clear()
        db._health_status_cache.update(saved_cache)
        db._health_status_cache_ts.clear()
        db._health_status_cache_ts.update(saved_ts)


def test_write_health_status_writes_on_status_change():
    """A status change (healthy → error) must always reach the DB."""
    import db

    saved_cache = dict(db._health_status_cache)
    db._health_status_cache["test_service_change"] = "healthy"

    try:
        with patch("db.get_client") as mock_get_client:
            mock_table = MagicMock()
            mock_get_client.return_value.table.return_value = mock_table
            db.write_health_status("test_service_change", "error")
        mock_table.upsert.assert_called_once()
    finally:
        db._health_status_cache.clear()
        db._health_status_cache.update(saved_cache)


def test_write_health_status_always_writes_error():
    """Error status must always upsert, even when cache already shows error.

    Two error writes in a row still need to reach the DB so the
    last_heartbeat_at refresh proves the writer is alive and
    error_count_1h keeps incrementing.
    """
    import db

    saved_cache = dict(db._health_status_cache)
    db._health_status_cache["test_service_err"] = "error"

    try:
        with patch("db.get_client") as mock_get_client:
            mock_table = MagicMock()
            mock_get_client.return_value.table.return_value = mock_table
            db.write_health_status("test_service_err", "error")
        mock_table.upsert.assert_called_once()
    finally:
        db._health_status_cache.clear()
        db._health_status_cache.update(saved_cache)


def test_write_health_status_writes_when_kwargs_present():
    """Same-status write that carries diagnostic kwargs must NOT be cached
    away — kwargs (latency_ms, last_error_message, ...) are real data."""
    import db

    saved_cache = dict(db._health_status_cache)
    db._health_status_cache["test_service_kw"] = "healthy"

    try:
        with patch("db.get_client") as mock_get_client:
            mock_table = MagicMock()
            mock_get_client.return_value.table.return_value = mock_table
            db.write_health_status(
                "test_service_kw", "healthy", latency_ms=42
            )
        mock_table.upsert.assert_called_once()
    finally:
        db._health_status_cache.clear()
        db._health_status_cache.update(saved_cache)


# ── S7-6: API keys in headers, not URLs ──────────────────────────────

def test_finnhub_token_not_in_calendar_urls():
    """Finnhub token must not appear in URL strings in economic_calendar.py."""
    path = os.path.join(_AGENTS_DIR, "economic_calendar.py")
    with open(path, encoding="utf-8") as f:
        src = f.read()
    assert "token=" not in src, (
        "token= still in a Finnhub URL — must use X-Finnhub-Token header"
    )
    assert "X-Finnhub-Token" in src, (
        "economic_calendar.py must send X-Finnhub-Token header"
    )


def test_polygon_apikey_not_in_flow_agent_url():
    """Polygon apiKey must not appear in URL string in flow_agent.py."""
    path = os.path.join(_AGENTS_DIR, "flow_agent.py")
    with open(path, encoding="utf-8") as f:
        src = f.read()
    assert "apiKey=" not in src, (
        "apiKey= still in flow_agent URL — must use Authorization header"
    )
    assert "Authorization" in src and "Bearer" in src, (
        "flow_agent.py must send Authorization: Bearer header"
    )
