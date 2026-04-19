import threading
from datetime import datetime, timezone
from typing import Optional

from config import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
from logger import get_logger

logger = get_logger("db")

_client = None
_client_lock = threading.Lock()

# S7-5: in-process cache of the last status written per service.
# Keyed on service_name; value is the last status string we upserted.
# The five *_keepalive jobs in main.py each fire every 30s — that's
# ~14,400 health upserts per service per day, virtually all of them
# duplicate "healthy" rows that only refresh last_heartbeat_at.
# Comparing status (alone, not the timestamp) lets us short-circuit
# those identical writes. Cleared on process restart, which is
# intentional — the first write after a restart always goes through
# so monitoring can confirm the new process is alive.
_health_status_cache: dict = {}

# Belt-and-suspenders: optionally set HTTPX_NO_H2=1 in Railway environment
# variables. Currently a no-op for httpx 0.28 (it does not honour that
# variable), but it costs nothing and protects against a future supabase-py
# / httpx upgrade that re-enables HTTP/2 despite the http2=False flag below.
# The PRIMARY safeguard is the explicit httpx.Client(http2=False, ...) we
# inject below — the env var is purely defensive.


def get_client():
    """
    Return the singleton Supabase client.

    Why this is non-trivial:
      postgrest-py hard-codes ``http2=True`` when it constructs its own
      httpx.Client (postgrest/_sync/client.py:~102 in 2.x). The h2 HTTP/2
      state machine maintains internal collections.deque buffers that are
      NOT thread-safe. Our APScheduler ThreadPoolExecutor (~10
      ``*_keepalive`` jobs every 30s + the trading cycle) and the asyncio
      event loop (``heartbeat_check``) both reach into the same shared
      client, producing three production failure modes — all the same race:

        ERROR 1: "deque mutated during iteration"        (h2 frame buffer)
        ERROR 2: "[Errno 32] Broken pipe" /
                 "ConnectionTerminated error_code:1"     (server GOAWAY)
        ERROR 3: "Received pseudo-header in trailer"     (corrupted frames)

    Version-safety note:
      Our previous attempt passed ``httpx_client`` via ``ClientOptions``.
      That field only exists in supabase-py >= 2.16-ish; Railway pins
      ``supabase==2.10.0`` (requirements.txt), where the kwarg is rejected
      with ``SyncClientOptions.__init__() got an unexpected keyword
      argument 'httpx_client'``. Local dev had 2.28.3, so tests passed
      locally and the bug only surfaced after deploy.

      The version-safe approach is to let supabase-py build its own client
      and then *replace* ``postgrest.session`` with our HTTP/1.1
      ``httpx.Client``. ``.session`` is the canonical attribute on
      postgrest-py's sync client across all 2.x releases.

    Layers of defence (in order of effectiveness):

      1. Replace ``postgrest.session`` with ``httpx.Client(http2=False, ...)``
         so the actual wire protocol is HTTP/1.1. HTTP/1.1 connection pools
         are Lock-guarded and thread-safe by design.

      2. Serialise every DB call site behind ``_client_lock`` (see
         ``write_health_status`` / ``write_audit_log``). Defense-in-depth:
         if a future dependency upgrade slips HTTP/2 back in, the lock
         still prevents concurrent access to a single connection from
         corrupting state.

      3. Belt-and-suspenders: optionally set ``HTTPX_NO_H2=1`` in Railway
         env vars. Currently a no-op for httpx 0.27/0.28 (neither honours
         that variable) but reserved for any future version that may.

    Lock discipline:
      ``_client_lock`` is a non-reentrant ``threading.Lock``. Callers MUST
      resolve the client *outside* the lock and then hold the lock only
      around the ``.execute()`` call. Doing ``with _client_lock:
      get_client()`` would deadlock the same thread on the first call
      (get_client also acquires _client_lock for init).

    If the session-replacement patch fails for any reason (e.g. postgrest-py
    refactors the attribute name), the client still works — it just falls
    back to whatever transport supabase-py constructed by default. The
    lock serialisation in (2) keeps the system from corrupting in that
    degraded state. ``supabase_http2_patch_failed`` is logged so the
    failure is visible in Railway.
    """
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:  # double-checked locking
                from supabase import create_client
                import httpx

                _client = create_client(
                    SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
                )

                # Replace the postgrest httpx session with an HTTP/1.1
                # client to eliminate the h2 thread-safety race. We can't
                # pass ``httpx_client=`` to ClientOptions on supabase-py
                # 2.10 (Railway), so we patch after construction instead.
                # ``.session`` is the standard attribute on postgrest-py's
                # sync client across 2.x; storage/functions/auth still use
                # their own clients but those code paths are not currently
                # exercised by our trading hot path.
                try:
                    postgrest = _client.postgrest
                    session = getattr(postgrest, "session", None)
                    if session is not None and isinstance(session, httpx.Client):
                        new_session = httpx.Client(
                            base_url=str(session.base_url),
                            headers=dict(session.headers),
                            timeout=httpx.Timeout(10.0),
                            follow_redirects=True,
                            http2=False,
                            limits=httpx.Limits(
                                max_keepalive_connections=5,
                                max_connections=10,
                                keepalive_expiry=25.0,  # < Cloudflare's 30s reaper
                            ),
                        )
                        postgrest.session = new_session
                        # Best-effort cleanup of the original h2-enabled
                        # client. If close() raises we don't care — the
                        # GC will drop it eventually.
                        try:
                            session.close()
                        except Exception:
                            pass
                        logger.info(
                            "supabase_client_initialised",
                            http2_enabled=False,
                            patch_method="session_replacement",
                        )
                    else:
                        logger.warning(
                            "supabase_client_initialised",
                            http2_enabled="unknown",
                            patch_method="none_session_not_found",
                            session_type=type(session).__name__ if session else "None",
                        )
                except Exception as patch_exc:
                    logger.warning(
                        "supabase_http2_patch_failed",
                        error=str(patch_exc),
                    )

    return _client


def write_health_status(service_name: str, status: str, **kwargs) -> bool:
    """
    Upsert a row to trading_system_health.
    Never raises - logs error and returns False on failure.

    All Supabase calls in this function are serialised behind
    ``_client_lock`` — see get_client() docstring for the rationale.
    The client is resolved BEFORE acquiring the lock to avoid the
    same-thread deadlock that re-entry into get_client() would cause.
    """
    try:
        client = get_client()
        payload = {
            "service_name": service_name,
            "status": status,
            "last_heartbeat_at": datetime.now(timezone.utc).isoformat(),
            **kwargs,
        }
        # Always clear last_error_message when status is healthy — do not persist stale errors
        if status == "healthy" and "last_error_message" not in kwargs:
            payload["last_error_message"] = None

        # S7-5: skip the upsert when the cached status matches the new
        # status AND the call carries no extra data. This eliminates
        # ~95% of the keepalive write volume (steady-state "healthy"
        # heartbeats). Always write through when:
        #   * status changed (the cache miss path),
        #   * status is "error" or "degraded" (operational signal that
        #     must reach the dashboard immediately, even if we already
        #     wrote an error a moment ago — last_heartbeat_at refresh
        #     proves the writer itself is still alive),
        #   * any kwargs are present (latency_ms, last_error_message,
        #     databento_connected, etc. — those carry diagnostic data
        #     that downstream consumers depend on).
        cached_status = _health_status_cache.get(service_name)
        if (
            cached_status == status
            and status not in ("error", "degraded")
            and not kwargs
        ):
            return True
        _health_status_cache[service_name] = status

        # Increment error_count_1h when writing an error status (GLC-006)
        if status == "error":
            try:
                with _client_lock:
                    current = (
                        client
                        .table("trading_system_health")
                        .select("error_count_1h")
                        .eq("service_name", service_name)
                        .maybe_single()
                        .execute()
                    )
                current_count = 0
                if current.data and current.data.get("error_count_1h"):
                    current_count = int(current.data["error_count_1h"])
                payload["error_count_1h"] = current_count + 1
            except Exception:
                payload["error_count_1h"] = 1
        with _client_lock:
            client.table("trading_system_health").upsert(
                payload, on_conflict="service_name"
            ).execute()
        return True
    except Exception as e:
        logger.error("health_write_failed", service=service_name, error=str(e))
        return False


def write_audit_log(
    action: str,
    target_type: str = "trading",
    target_id: Optional[str] = None,
    metadata: Optional[dict] = None,
    correlation_id: Optional[str] = None,
) -> bool:
    """
    Insert a row to audit_logs.
    Never raises - logs error and returns False on failure.

    Insert is serialised behind ``_client_lock`` for the same reason as
    write_health_status — see get_client() docstring. Client is resolved
    BEFORE the lock for the same reason.
    """
    try:
        client = get_client()
        payload = {
            "action": action,
            "target_type": target_type,
            "metadata": metadata or {},
        }
        if target_id:
            payload["target_id"] = target_id
        if correlation_id:
            payload["correlation_id"] = correlation_id
        with _client_lock:
            client.table("audit_logs").insert(payload).execute()
        return True
    except Exception as e:
        logger.error("audit_write_failed", action=action, error=str(e))
        return False
