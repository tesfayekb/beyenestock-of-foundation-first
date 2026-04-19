import threading
from datetime import datetime, timezone
from typing import Optional

from config import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
from logger import get_logger

logger = get_logger("db")

_client = None
_client_lock = threading.Lock()

# Belt-and-suspenders: optionally set HTTPX_NO_H2=1 in Railway environment
# variables. Currently a no-op for httpx 0.28 (it does not honour that
# variable), but it costs nothing and protects against a future supabase-py
# / httpx upgrade that re-enables HTTP/2 despite the http2=False flag below.
# The PRIMARY safeguard is the explicit httpx.Client(http2=False, ...) we
# inject below — the env var is purely defensive.


def get_client():
    """
    Lazily build the singleton Supabase client.

    Why this is non-trivial:
      postgrest-py 2.x hard-codes ``http2=True`` when it constructs its own
      httpx.Client (see postgrest/_sync/client.py:102). The h2 HTTP/2 state
      machine maintains internal collections.deque buffers that are NOT
      thread-safe. Our APScheduler uses a ThreadPoolExecutor for sync jobs
      (~10 keepalives every 30s + the trading cycle) AND the asyncio event
      loop runs ``heartbeat_check`` on top of the same client. Concurrent
      access produced three production failure modes — all the same race:

        ERROR 1: "deque mutated during iteration"        (h2 frame buffer)
        ERROR 2: "[Errno 32] Broken pipe" /
                 "ConnectionTerminated error_code:1"     (server GOAWAY)
        ERROR 3: "Received pseudo-header in trailer"     (corrupted frames)

    The fix has two parts:

      1. Inject our own httpx.Client with ``http2=False`` via
         ``ClientOptions.httpx_client``. supabase-py forwards this to
         postgrest, storage, functions, and auth (see
         supabase/_sync/client.py:189). HTTP/1.1 connection pools are
         Lock-guarded and thread-safe by design.

      2. Serialise every DB call site behind ``_client_lock`` (see
         write_health_status / write_audit_log). Defense-in-depth — if a
         future dependency upgrade slips HTTP/2 back in, the lock prevents
         concurrent access to the same connection from corrupting state.

    Lock discipline:
      ``_client_lock`` is a non-reentrant ``threading.Lock``. Callers MUST
      resolve the client *outside* the lock and then hold the lock only
      around the ``.execute()`` call. Doing ``with _client_lock: get_client()``
      would deadlock the same thread on the first call (get_client also
      acquires _client_lock for init). See write_health_status below.

    Imports of supabase / httpx / ClientOptions are deferred to the inner
    block so:
      - the ``patch("supabase.create_client", ...)`` test path keeps working
      - environments that never call get_client() do not pull h2/httpx at
        import time

    Full migration to ``create_async_client`` is a larger refactor (every
    sync ``*_keepalive`` job in main.py would have to become async) and
    is deliberately deferred.
    """
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:  # double-checked locking
                from supabase import ClientOptions, create_client
                import httpx

                # NOTE: import ClientOptions from the top-level ``supabase``
                # namespace — that re-export resolves to ``SyncClientOptions``
                # which carries the ``httpx_client`` field. The base class in
                # ``supabase.lib.client_options`` does NOT accept it.
                #
                # Headers and base_url are intentionally NOT set on the
                # shared session: postgrest passes its own base_url and auth
                # headers per request (see postgrest/_sync/client.py
                # session.request), so a "blank" client is the safest neutral
                # container.
                shared_session = httpx.Client(
                    timeout=httpx.Timeout(10.0, connect=5.0),
                    follow_redirects=True,
                    http2=False,
                    limits=httpx.Limits(
                        max_keepalive_connections=10,
                        max_connections=20,
                        keepalive_expiry=30.0,  # < Cloudflare's idle reaper
                    ),
                )
                options = ClientOptions(
                    postgrest_client_timeout=10,
                    httpx_client=shared_session,
                )
                _client = create_client(
                    SUPABASE_URL,
                    SUPABASE_SERVICE_ROLE_KEY,
                    options=options,
                )
                logger.info(
                    "supabase_client_initialised",
                    http2_enabled=False,
                    keepalive_expiry_s=30,
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
