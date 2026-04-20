"""
Section 13 UI-2 — /admin/trading/learning-stats endpoint tests.

Test strategy
    FastAPI is not installed in the CI backend environment (Railway-
    only runtime). Rather than add a TestClient dependency just for
    this file, we reuse the S14 idiom (`_ensure_main_importable` +
    `_load_backend_main_isolated`) and call get_learning_stats()
    directly as a plain async function. Authentication is exercised
    by calling _require_admin_key() directly with
    config.RAILWAY_ADMIN_KEY patched — same behavioural coverage as a
    401 / 200 round-trip.

Nine pins, one per documented contract:
    1. shape: response carries every top-level key the UI expects
    2. iv_rv_ratio: computed from VIX / RV when both present
    3. iv_rv_ratio: null when RV absent (UI shows "warming up")
    4. butterfly_gates: all six reason keys present (contract match)
    5. model_drift_alert: True when `model_drift_alert = "1"`
    6. model_drift_alert: False when key absent
    7. sizing_phase: default 1 when key absent
    8. fail-open: redis raising on every .get() returns a 200-shaped
       dict with null/default fields — no exception escapes
    9. auth: _require_admin_key rejects wrong header when the env
       secret is set
"""
import asyncio
import os
import sys
import types
from unittest.mock import patch

import pytest


BACKEND = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)


# ── Stub FastAPI / APScheduler so `import main` succeeds ────────────


class _LearningStatsHTTPException(Exception):
    """HTTPException stub that surfaces status_code — mirror of the
    S14 helper. Required so the auth test can inspect the 401."""

    def __init__(self, *_a, **kw):
        self.status_code = kw.get("status_code") or (
            _a[0] if _a else 500
        )
        self.detail = kw.get("detail", "")
        super().__init__(self.detail)


def _ensure_main_importable():
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
        fastapi.HTTPException = _LearningStatsHTTPException
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
        # Force-upgrade HTTPException + ensure Depends is a
        # pass-through. Idempotent with S14's helper.
        fastapi = sys.modules["fastapi"]
        fastapi.HTTPException = _LearningStatsHTTPException
        if not hasattr(fastapi, "Depends"):
            def _passthrough(*_a, **_kw):
                return None
            fastapi.Depends = _passthrough

    if "apscheduler" not in sys.modules:
        apscheduler = types.ModuleType("apscheduler")
        schedulers = types.ModuleType("apscheduler.schedulers")
        asyncio_mod = types.ModuleType("apscheduler.schedulers.asyncio")

        class _StubScheduler:
            def __init__(self, *_a, **_kw):
                self.jobs = []

            def add_job(self, *_a, **_kw):
                self.jobs.append((_a, _kw))

            def start(self):
                pass

            def shutdown(self, *_a, **_kw):
                pass

        asyncio_mod.AsyncIOScheduler = _StubScheduler
        sys.modules["apscheduler"] = apscheduler
        sys.modules["apscheduler.schedulers"] = schedulers
        sys.modules["apscheduler.schedulers.asyncio"] = asyncio_mod


def _load_backend_main_isolated():
    """Load backend/main.py under a unique slot then alias to "main"
    so sibling tests with their own sentinel main are unaffected."""
    _ensure_main_importable()
    import importlib.util

    saved_main = sys.modules.get("main")

    spec = importlib.util.spec_from_file_location(
        "_learning_stats_backend_main",
        os.path.join(BACKEND, "main.py"),
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["main"] = module
    sys.modules["_learning_stats_backend_main"] = module
    spec.loader.exec_module(module)

    def restore_fn():
        if saved_main is not None:
            sys.modules["main"] = saved_main
        else:
            sys.modules.pop("main", None)
        sys.modules.pop("_learning_stats_backend_main", None)

    return module, restore_fn


# ── Redis mock — single source of truth for every test ──────────────


class _FakeRedis:
    """Minimal redis.Redis stand-in. Backed by a plain dict so tests
    can assert on what was read without mocking per-call. `decode`
    path matches the real decode_responses=True client: we return
    the raw str and the endpoint's isinstance(val, bytes) branch is
    inert. Setting `fail=True` makes every .get / .keys raise to
    exercise the fail-open path."""

    def __init__(self, data=None, fail=False):
        self._data = dict(data or {})
        self._fail = fail

    def get(self, key):
        if self._fail:
            raise RuntimeError("redis down")
        return self._data.get(key)

    def keys(self, pattern):
        if self._fail:
            raise RuntimeError("redis down")
        if not pattern.endswith("*"):
            return [pattern] if pattern in self._data else []
        prefix = pattern[:-1]
        return [k for k in self._data if k.startswith(prefix)]


def _run(coro):
    """Execute an async endpoint handler from a sync test."""
    return asyncio.get_event_loop().run_until_complete(coro) \
        if sys.version_info < (3, 10) else asyncio.run(coro)


# ═════════════════════════════════════════════════════════════════════
# 1) shape — every top-level key the UI contracts on is present
# ═════════════════════════════════════════════════════════════════════


def test_learning_stats_returns_200():
    """Happy-path call with an empty Redis must still return a dict
    carrying every documented top-level key. The UI relies on the
    shape being stable; missing keys would render as undefined."""
    m, restore = _load_backend_main_isolated()
    try:
        with patch.object(m, "redis_client", _FakeRedis({})):
            result = _run(m.get_learning_stats(_auth=None))

        expected_keys = {
            "realized_vol_20d",
            "vix_current",
            "iv_rv_ratio",
            "realized_vol_last_date",
            "butterfly_gates",
            "butterfly_allowed_today",
            "strategy_matrix",
            "halt_threshold_pct",
            "halt_threshold_source",
            "butterfly_thresholds",
            "model_drift_alert",
            "sizing_phase",
            "sizing_phase_advanced_at",
        }
        missing = expected_keys - set(result.keys())
        assert not missing, f"missing keys in response: {missing}"
    finally:
        restore()


# ═════════════════════════════════════════════════════════════════════
# 2) iv_rv_ratio — computed when both inputs present
# ═════════════════════════════════════════════════════════════════════


def test_learning_stats_realized_vol_present():
    """VIX=19.0, RV=16.5 → iv_rv_ratio = round(19/16.5, 3) = 1.152.
    Also asserts the underlying floats round-trip intact."""
    m, restore = _load_backend_main_isolated()
    try:
        redis = _FakeRedis({
            "polygon:spx:realized_vol_20d": "16.5",
            "polygon:vix:current": "19.0",
        })
        with patch.object(m, "redis_client", redis):
            result = _run(m.get_learning_stats(_auth=None))

        assert result["realized_vol_20d"] == 16.5
        assert result["vix_current"] == 19.0
        assert result["iv_rv_ratio"] == 1.152
    finally:
        restore()


# ═════════════════════════════════════════════════════════════════════
# 3) iv_rv_ratio — null when the divisor is absent
# ═════════════════════════════════════════════════════════════════════


def test_learning_stats_iv_rv_ratio_null_when_rv_missing():
    """Only VIX present → iv_rv_ratio must be None (UI shows "warming
    up (N/20 daily sessions)"). Division-by-zero would both break the
    math AND teach the UI a garbage ratio; explicit null is the clean
    contract."""
    m, restore = _load_backend_main_isolated()
    try:
        redis = _FakeRedis({"polygon:vix:current": "19.0"})
        with patch.object(m, "redis_client", redis):
            result = _run(m.get_learning_stats(_auth=None))

        assert result["realized_vol_20d"] is None
        assert result["vix_current"] == 19.0
        assert result["iv_rv_ratio"] is None
    finally:
        restore()


# ═════════════════════════════════════════════════════════════════════
# 4) butterfly_gates — all six reason keys present, default to 0
# ═════════════════════════════════════════════════════════════════════


def test_learning_stats_butterfly_gates_all_present():
    """The UI renders a 6-bar chart. If any reason is missing from
    the response dict the chart falls over. All six keys must be
    present and default to 0 when Redis has no counter for today.
    Regime_mismatch is populated here to prove the look-up actually
    reads Redis, not just returns all-zero."""
    from datetime import date
    today = date.today().isoformat()

    m, restore = _load_backend_main_isolated()
    try:
        redis = _FakeRedis({
            f"butterfly:blocked:regime_mismatch:{today}": "3",
            f"butterfly:allowed:{today}": "5",
        })
        with patch.object(m, "redis_client", redis):
            result = _run(m.get_learning_stats(_auth=None))

        gates = result["butterfly_gates"]
        assert set(gates.keys()) == {
            "regime_mismatch",
            "time_gate",
            "failed_today",
            "low_concentration",
            "wall_unstable",
            "drawdown_block",
        }
        assert gates["regime_mismatch"] == 3
        assert gates["time_gate"] == 0
        assert gates["drawdown_block"] == 0  # writer not wired yet
        assert result["butterfly_allowed_today"] == 5
    finally:
        restore()


# ═════════════════════════════════════════════════════════════════════
# 5) model_drift_alert — True when flag is "1"
# ═════════════════════════════════════════════════════════════════════


def test_learning_stats_drift_alert_true():
    """Redis `model_drift_alert` = "1" → endpoint returns True so the
    UI banner activates. Any other value (including bytes b"1") would
    need to be handled by the fake-redis decode path — here we pin
    the primary string case."""
    m, restore = _load_backend_main_isolated()
    try:
        redis = _FakeRedis({"model_drift_alert": "1"})
        with patch.object(m, "redis_client", redis):
            result = _run(m.get_learning_stats(_auth=None))

        assert result["model_drift_alert"] is True
    finally:
        restore()


# ═════════════════════════════════════════════════════════════════════
# 6) model_drift_alert — False when key absent
# ═════════════════════════════════════════════════════════════════════


def test_learning_stats_drift_alert_false():
    """Absent key → False. The UI treats False as "no banner", which
    is the normal steady state. Pinned separately from the True case
    because the comparison (`== "1"`) could silently flip if someone
    refactors to raw bool coercion of the stored string."""
    m, restore = _load_backend_main_isolated()
    try:
        redis = _FakeRedis({})
        with patch.object(m, "redis_client", redis):
            result = _run(m.get_learning_stats(_auth=None))

        assert result["model_drift_alert"] is False
    finally:
        restore()


# ═════════════════════════════════════════════════════════════════════
# 7) sizing_phase — default 1 when key absent
# ═════════════════════════════════════════════════════════════════════


def test_learning_stats_sizing_phase_default():
    """No capital:sizing_phase key → endpoint reports 1 so the UI
    ribbon stays silent and risk_engine's existing fallback aligns.
    Also asserts sizing_phase_advanced_at is null (no advance yet)."""
    m, restore = _load_backend_main_isolated()
    try:
        redis = _FakeRedis({})
        with patch.object(m, "redis_client", redis):
            result = _run(m.get_learning_stats(_auth=None))

        assert result["sizing_phase"] == 1
        assert result["sizing_phase_advanced_at"] is None
    finally:
        restore()


# ═════════════════════════════════════════════════════════════════════
# 8) fail-open — Redis raising on every .get() still returns 200 shape
# ═════════════════════════════════════════════════════════════════════


def test_learning_stats_fail_open_on_redis_error():
    """Every Redis .get / .keys raises → endpoint contract says 200
    with null/default fields, NEVER 500. Each per-key helper catches
    individually, so the response shape stays intact even when the
    Redis client is completely broken. UI treats every field as
    "warming up" and shows empty state."""
    m, restore = _load_backend_main_isolated()
    try:
        redis = _FakeRedis({}, fail=True)
        with patch.object(m, "redis_client", redis):
            result = _run(m.get_learning_stats(_auth=None))

        assert result["realized_vol_20d"] is None
        assert result["vix_current"] is None
        assert result["iv_rv_ratio"] is None
        assert result["model_drift_alert"] is False
        assert result["sizing_phase"] == 1
        # butterfly_gates is always a 6-key dict even when every
        # .get() raises — individual exceptions collapse to 0.
        assert set(result["butterfly_gates"].keys()) == {
            "regime_mismatch",
            "time_gate",
            "failed_today",
            "low_concentration",
            "wall_unstable",
            "drawdown_block",
        }
        for v in result["butterfly_gates"].values():
            assert v == 0
        assert result["strategy_matrix"] == []
        # No "error" key unless the *outer* wrapper caught — the
        # per-key helpers absorb everything, so error should NOT
        # appear here. If this assertion ever flips it means the
        # fail-open granularity regressed.
        assert "error" not in result
    finally:
        restore()


# ═════════════════════════════════════════════════════════════════════
# 9) auth — admin secret enforced when env var is set
# ═════════════════════════════════════════════════════════════════════


def test_learning_stats_requires_admin_auth():
    """The new endpoint reuses `_require_admin_key` just like the
    other six admin GETs. When RAILWAY_ADMIN_KEY is set, calling the
    dependency without the correct X-Api-Key must raise 401. We
    exercise the dep directly — FastAPI is not installed in CI, but
    behaviourally this IS the auth gate for every request."""
    m, restore = _load_backend_main_isolated()
    try:
        from fastapi import HTTPException

        with patch.object(m.config, "RAILWAY_ADMIN_KEY", "real-secret"):
            with pytest.raises(HTTPException) as exc_info:
                m._require_admin_key(x_api_key="")
            assert exc_info.value.status_code == 401

            with pytest.raises(HTTPException) as exc_info2:
                m._require_admin_key(x_api_key="wrong-key")
            assert exc_info2.value.status_code == 401

        # Sanity: correct key must NOT raise.
        with patch.object(m.config, "RAILWAY_ADMIN_KEY", "real-secret"):
            m._require_admin_key(x_api_key="real-secret")

        # Structural pin: the endpoint signature itself carries the
        # dependency. Without this, a future edit could drop the
        # Depends(...) and the behavioural test above would pass while
        # the real route went unprotected.
        path = os.path.join(BACKEND, "main.py")
        with open(path, encoding="utf-8") as fh:
            src = fh.read()
        sig_start = src.find("async def get_learning_stats(")
        assert sig_start > -1, "get_learning_stats not found"
        paren_end = src.find("):", sig_start)
        signature = src[sig_start: paren_end + 2]
        assert "Depends(_require_admin_key)" in signature, (
            "get_learning_stats is missing Depends(_require_admin_key)"
        )
    finally:
        restore()
