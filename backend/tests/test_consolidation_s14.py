"""
Consolidation Session 14 — Security.
T1-14: admin endpoint auth, T1-12: flag POST production block,
T2-12: kill-switch audit, T1-13: RLS migration.

Test strategy note:
    The spec template uses ``fastapi.testclient.TestClient`` + ``from
    main import app``. fastapi is NOT installed in this CI environment
    (the /backend runtime is Railway-only), so TestClient-driven
    integration tests cannot run. We instead follow the same pattern
    proven across S8 / S11 / S12: stub FastAPI with
    ``_ensure_main_importable`` and call ``_require_admin_key``
    DIRECTLY as a plain function — same behavioural coverage as a
    401/200 HTTP round-trip, but no TestClient needed. Structural
    coverage (which endpoints have the dependency wired in, which
    stay public) is provided by source-grep tests.
"""
import os
import sys
import types

import pytest
from unittest.mock import patch

BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

REPO_ROOT = os.path.abspath(os.path.join(BACKEND, ".."))


# ─── Helpers reused from the S8 / S11 pattern ────────────────────────────────

class _S14HTTPException(Exception):
    """HTTPException stub with a ``status_code`` attribute.

    Older test helpers (s8, s11, s12, heartbeat_policy) stub
    fastapi.HTTPException with a barebones ``Exception`` subclass
    that does not expose ``.status_code``. When pytest runs those
    tests first, their stub wins the sys.modules["fastapi"] race
    and our S14 tests cannot assert the 401 / 503 status. Always
    force-upgrade the HTTPException stub so our tests see the
    attribute regardless of collection order.
    """

    def __init__(self, *_a, **kw):
        self.status_code = kw.get("status_code") or (
            _a[0] if _a else 500
        )
        self.detail = kw.get("detail", "")
        super().__init__(self.detail)


def _ensure_main_importable():
    """Stub FastAPI / APScheduler so `import main` succeeds in tests.

    Extended from the S11 helper: we also need ``Depends`` as a stub
    pass-through so the S14 module-import + in-function call both work.
    The HTTPException stub is ALWAYS overwritten (even if another
    test already stubbed fastapi) so status_code is inspectable.
    """
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

        fastapi.FastAPI = _StubFastAPI
        fastapi.Body = _passthrough
        fastapi.Header = _passthrough
        fastapi.Depends = _passthrough
        fastapi.HTTPException = _S14HTTPException
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
    else:
        # Another test already stubbed fastapi — force-upgrade the
        # two symbols we need (HTTPException with status_code,
        # Depends pass-through). Idempotent & safe for other tests.
        fastapi = sys.modules["fastapi"]
        fastapi.HTTPException = _S14HTTPException
        if not hasattr(fastapi, "Depends"):
            def _passthrough(*_a, **_kw):
                return None
            fastapi.Depends = _passthrough

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


def _load_backend_main_isolated():
    """Load backend/main.py under a unique slot then alias to "main".

    Same idiom as S8 / S11 / S12 — isolates sys.modules so sibling
    tests (test_fix_group3 etc.) retain their own sentinel main.
    """
    _ensure_main_importable()
    import importlib.util

    saved_main = sys.modules.get("main")

    spec = importlib.util.spec_from_file_location(
        "_s14_backend_main", os.path.join(BACKEND, "main.py")
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["main"] = module
    sys.modules["_s14_backend_main"] = module
    spec.loader.exec_module(module)

    def restore_fn():
        if saved_main is not None:
            sys.modules["main"] = saved_main
        else:
            sys.modules.pop("main", None)
        sys.modules.pop("_s14_backend_main", None)

    return module, restore_fn


# ═════════════════════════════════════════════════════════════════════════════
# T1-14: _require_admin_key dependency — behavioural unit tests (3)
# ═════════════════════════════════════════════════════════════════════════════

def test_require_admin_key_rejects_when_key_set_and_header_wrong():
    """Key set + missing/wrong X-Api-Key -> raises HTTPException(401)."""
    m, restore = _load_backend_main_isolated()
    try:
        from fastapi import HTTPException
        with patch.object(m.config, "RAILWAY_ADMIN_KEY", "real-secret"):
            with pytest.raises(HTTPException) as exc_info:
                m._require_admin_key(x_api_key="")
        assert exc_info.value.status_code == 401, (
            f"expected 401, got {exc_info.value.status_code}"
        )

        # Also reject a wrong-but-present header.
        with patch.object(m.config, "RAILWAY_ADMIN_KEY", "real-secret"):
            with pytest.raises(HTTPException) as exc_info2:
                m._require_admin_key(x_api_key="wrong-key")
        assert exc_info2.value.status_code == 401
    finally:
        restore()


def test_require_admin_key_accepts_correct_header():
    """Correct X-Api-Key -> passes through without raising."""
    m, restore = _load_backend_main_isolated()
    try:
        with patch.object(m.config, "RAILWAY_ADMIN_KEY", "real-secret"):
            # Must NOT raise.
            result = m._require_admin_key(x_api_key="real-secret")
        assert result is None, (
            "_require_admin_key must return None on success"
        )
    finally:
        restore()


def test_require_admin_key_fails_open_when_key_unset():
    """Empty RAILWAY_ADMIN_KEY -> fails open (dev / legacy deploys)."""
    m, restore = _load_backend_main_isolated()
    try:
        with patch.object(m.config, "RAILWAY_ADMIN_KEY", ""):
            # Must NOT raise — preserves legacy behaviour so dev deploys
            # that have not set the secret still work.
            m._require_admin_key(x_api_key="")
            m._require_admin_key(x_api_key="whatever")
    finally:
        restore()


# ═════════════════════════════════════════════════════════════════════════════
# T1-14: Source-grep — 6 endpoints gated, /health public (2 tests)
# ═════════════════════════════════════════════════════════════════════════════

def test_six_admin_get_endpoints_use_require_admin_key():
    """All 6 admin GET endpoints must declare Depends(_require_admin_key)."""
    path = os.path.join(BACKEND, "main.py")
    with open(path, encoding="utf-8") as f:
        src = f.read()

    protected_endpoints = [
        "get_trading_intelligence",
        "get_feature_flags",
        "get_subscription_key_status",
        "get_activation_status",
        "get_ab_status",
        "get_earnings_status",
    ]
    for name in protected_endpoints:
        sig_start = src.find(f"async def {name}(")
        assert sig_start > -1, f"missing endpoint definition: {name}"
        # The dependency must appear in the parameter list — look
        # from the `(` until the matching `)`.
        paren_end = src.find("):", sig_start)
        assert paren_end > -1
        signature = src[sig_start: paren_end + 2]
        assert "Depends(_require_admin_key)" in signature, (
            f"{name} is missing Depends(_require_admin_key) in its signature"
        )

    # Exactly 6 endpoints must reference the dependency (6 endpoints +
    # optionally 1 mention inside the helper definition itself).
    dep_count = src.count("Depends(_require_admin_key)")
    assert dep_count >= 6, (
        f"expected at least 6 Depends(_require_admin_key) usages, got {dep_count}"
    )


def test_depends_imported_and_require_admin_key_defined():
    """main.py must import Depends and define _require_admin_key.

    Structural regression guard: if someone renames the dependency or
    drops the Depends import, all six endpoint decorators break
    silently at runtime with a different FastAPI error than 401.
    """
    path = os.path.join(BACKEND, "main.py")
    with open(path, encoding="utf-8") as f:
        src = f.read()

    # The Depends symbol must be imported from fastapi.
    assert (
        "from fastapi import" in src and "Depends" in src
    ), "Depends must be imported from fastapi"
    # The dependency function itself must be defined.
    assert "def _require_admin_key(" in src, (
        "_require_admin_key dependency function must be defined"
    )
    # The dependency must read RAILWAY_ADMIN_KEY.
    func_start = src.find("def _require_admin_key(")
    func_body = src[func_start: func_start + 1500]
    assert "RAILWAY_ADMIN_KEY" in func_body, (
        "_require_admin_key must consult RAILWAY_ADMIN_KEY"
    )
    assert "HTTPException" in func_body and "401" in func_body, (
        "_require_admin_key must raise HTTPException(401) on bad key"
    )


def test_health_endpoint_remains_public():
    """/health must NOT declare Depends(_require_admin_key).

    Railway's platform probe hits /health every few seconds and cannot
    present a secret. Auth on /health would permanently mark the
    deployment unhealthy and trigger restart loops.
    """
    path = os.path.join(BACKEND, "main.py")
    with open(path, encoding="utf-8") as f:
        src = f.read()

    health_start = src.find("async def get_health(")
    assert health_start > -1, "/health handler get_health() not found"
    paren_end = src.find("):", health_start)
    signature = src[health_start: paren_end + 2]
    assert "Depends(_require_admin_key)" not in signature, (
        "/health must remain public — Railway health probe depends on it"
    )


# ═════════════════════════════════════════════════════════════════════════════
# T1-12: POST flag endpoint returns 503 in production without key (1 test)
# ═════════════════════════════════════════════════════════════════════════════

def test_flag_post_blocks_503_in_production_without_key():
    """ENVIRONMENT=production + no RAILWAY_ADMIN_KEY -> 503."""
    import asyncio

    m, restore = _load_backend_main_isolated()
    try:
        from fastapi import HTTPException
        with patch.object(m.config, "RAILWAY_ADMIN_KEY", ""), \
             patch.object(m.config, "ENVIRONMENT", "production"):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(
                    m.set_feature_flag(
                        payload={
                            "flag_key": "strategy:iron_butterfly:enabled",
                            "enabled": True,
                        },
                        x_api_key="",
                    )
                )
        assert exc_info.value.status_code == 503, (
            f"production + no key must 503, got "
            f"{exc_info.value.status_code}"
        )

        # Sanity check: dev env with no key still passes through
        # (legacy fail-open behaviour preserved).
        with patch.object(m.config, "RAILWAY_ADMIN_KEY", ""), \
             patch.object(m.config, "ENVIRONMENT", "development"), \
             patch.object(m, "redis_client", None):
            # No 503 should be raised; the handler may return
            # an error dict for the unrelated redis_unavailable
            # path, which is fine — we only assert it does NOT
            # raise the production 503.
            try:
                asyncio.run(
                    m.set_feature_flag(
                        payload={
                            "flag_key": "strategy:iron_butterfly:enabled",
                            "enabled": True,
                        },
                        x_api_key="",
                    )
                )
            except HTTPException as he:
                assert he.status_code != 503, (
                    "dev env must not raise 503 when key unset"
                )
    finally:
        restore()


# ═════════════════════════════════════════════════════════════════════════════
# T2-12: Kill switch audit log (2 tests)
# ═════════════════════════════════════════════════════════════════════════════

def test_kill_switch_writes_audit_row():
    """kill-switch Edge Function must insert into audit_logs after halt."""
    path = os.path.join(
        REPO_ROOT, "supabase", "functions", "kill-switch", "index.ts"
    )
    with open(path, encoding="utf-8") as f:
        src = f.read()
    assert "audit_logs" in src, (
        "kill-switch must insert into audit_logs after successful "
        "halt/resume"
    )
    assert "kill_switch_session_halted" in src, (
        "kill-switch must log halt action name "
        "'kill_switch_session_halted'"
    )
    assert "kill_switch_session_resumed" in src, (
        "kill-switch must log resume action name "
        "'kill_switch_session_resumed'"
    )


def test_kill_switch_audit_failure_does_not_block_response():
    """audit_logs insert must be wrapped in try/catch.

    Audit-log failure must never break the kill-switch response —
    halting the book is more important than writing the audit row.
    """
    path = os.path.join(
        REPO_ROOT, "supabase", "functions", "kill-switch", "index.ts"
    )
    with open(path, encoding="utf-8") as f:
        src = f.read()

    audit_pos = src.find("audit_logs")
    assert audit_pos > -1

    # The try { ... } catch { ... } wrapper must surround the audit
    # insert. Window is generous — the insert payload (metadata object)
    # alone is ~400 chars.
    before = src[max(0, audit_pos - 200): audit_pos]
    after = src[audit_pos: audit_pos + 900]
    assert "try" in before, (
        "audit_logs insert must be preceded by `try {` — "
        "failure must not propagate to the kill-switch response"
    )
    assert "catch" in after, (
        "audit_logs insert must be followed by a `catch` block"
    )

    # And the final 200 OK response must still be reachable after
    # the try/catch (not inside it).
    ok_response_pos = src.rfind("{ ok: true")
    assert ok_response_pos > audit_pos, (
        "the final `{ ok: true ... }` response must come AFTER the "
        "audit block, not inside it — otherwise audit failure would "
        "abort the success response"
    )


# ═════════════════════════════════════════════════════════════════════════════
# T1-13: RLS migration file (3 tests)
# ═════════════════════════════════════════════════════════════════════════════

def test_rls_migration_file_exists():
    """Migration file for trading_signals + model_performance must exist."""
    migration_path = os.path.join(
        REPO_ROOT, "supabase", "migrations",
        "20260421_tighten_remaining_rls.sql",
    )
    assert os.path.exists(migration_path), (
        "supabase/migrations/20260421_tighten_remaining_rls.sql "
        "must exist — T1-13 RLS hardening"
    )


def test_rls_migration_covers_both_tables():
    """Migration must cover trading_signals AND trading_model_performance."""
    migration_path = os.path.join(
        REPO_ROOT, "supabase", "migrations",
        "20260421_tighten_remaining_rls.sql",
    )
    with open(migration_path, encoding="utf-8") as f:
        sql = f.read()
    assert "trading_signals" in sql
    assert "trading_model_performance" in sql
    # Must replace old permissive policies with trading.view ones.
    assert "trading_view_read_signals" in sql
    assert "trading_view_read_model_perf" in sql
    # Must drop the old permissive policies.
    assert "authenticated_read_signals" in sql
    assert "authenticated_read_model_perf" in sql


def test_rls_migration_uses_trading_view_not_authenticated():
    """New CREATE POLICY lines must use trading.view, not auth.role()."""
    migration_path = os.path.join(
        REPO_ROOT, "supabase", "migrations",
        "20260421_tighten_remaining_rls.sql",
    )
    with open(migration_path, encoding="utf-8") as f:
        sql = f.read()

    # Every new CREATE POLICY must be of the trading_view_* family.
    # We must NOT create any `authenticated_*` policy in this
    # migration — the DROPs are fine, the CREATEs must use the
    # tightened name.
    for line in sql.split("\n"):
        stripped = line.strip()
        if stripped.startswith("CREATE POLICY"):
            assert "trading_view_read" in stripped, (
                f"CREATE POLICY must use trading_view_read_* name: {stripped}"
            )
            assert "authenticated_read" not in stripped

    # Must reference the trading.view permission key.
    assert "'trading.view'" in sql, (
        "migration must gate reads on the 'trading.view' permission key"
    )
    # EXISTS check against user_roles / role_permissions / permissions
    # must be present (same pattern as 20260420).
    assert "user_roles" in sql
    assert "role_permissions" in sql
    assert "permissions" in sql
