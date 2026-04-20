"""
Consolidation Session 11 — Capital Allocation.

Locks the contract for the new capital_manager module:

    deployed_capital = live_equity * deployment_pct * leverage_multiplier

Bug families covered:
  * Formula correctness (3 tests)
  * Floor / ceiling guards (3 tests — zero-equity, tiny, huge)
  * Cache hit / cache write (2 tests)
  * Deployment config defaults + custom values + range guard
    + no-redis fallback (4 tests)
  * Error propagation: missing API key + Tradier non-200 (2 tests)
  * Cycle integration: run_prediction_cycle skips on CapitalError
    (1 test using the S8 main-import helper)

Total: 15 tests, 0 failures expected.
"""
import os
import sys
import types

import pytest
from unittest.mock import MagicMock, patch

BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)


# ─── Helpers reused from the S8 pattern ──────────────────────────────────────

def _ensure_main_importable():
    """Stub heavy Railway-only deps so `import main` succeeds in tests.

    Same pattern proven in test_consolidation_s8.py — only stubs the
    minimum surface (FastAPI, CORSMiddleware, AsyncIOScheduler) needed
    for main.py to load. Real trading code paths exercised by these
    tests do NOT touch the stubs at runtime.
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


def _load_backend_main_isolated():
    """Load backend/main.py under a unique slot then alias to "main".

    Same idiom as test_consolidation_s8 — keeps sys.modules["main"]
    clean for sibling tests (e.g. sentinel/main.py in test_fix_group3)
    but still allows ``patch("main.X")`` to resolve correctly during
    this test's lifetime.
    """
    _ensure_main_importable()
    import importlib.util

    saved_main = sys.modules.get("main")

    spec = importlib.util.spec_from_file_location(
        "_s11_backend_main", os.path.join(BACKEND, "main.py")
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["main"] = module
    sys.modules["_s11_backend_main"] = module
    spec.loader.exec_module(module)

    def restore_fn():
        if saved_main is not None:
            sys.modules["main"] = saved_main
        else:
            sys.modules.pop("main", None)
        sys.modules.pop("_s11_backend_main", None)

    return module, restore_fn


# ═════════════════════════════════════════════════════════════════════════════
# Core formula
# ═════════════════════════════════════════════════════════════════════════════

def test_deployed_capital_formula():
    """deployed_capital = equity * deployment_pct * leverage."""
    with patch(
        "capital_manager.fetch_live_equity", return_value=200_000.0
    ), patch(
        "capital_manager.get_deployment_config",
        return_value=(0.75, 1.0),
    ):
        from capital_manager import get_deployed_capital
        result = get_deployed_capital()
    assert abs(result - 150_000.0) < 0.01, (
        f"200k * 0.75 * 1.0 must equal 150_000, got {result}"
    )


def test_leverage_multiplier_applied():
    """200% leverage doubles deployed capital."""
    with patch(
        "capital_manager.fetch_live_equity", return_value=100_000.0
    ), patch(
        "capital_manager.get_deployment_config",
        return_value=(1.0, 2.0),
    ):
        from capital_manager import get_deployed_capital
        result = get_deployed_capital()
    assert abs(result - 200_000.0) < 0.01, (
        f"100k * 1.0 * 2.0 must equal 200_000, got {result}"
    )


def test_both_at_default_returns_full_equity():
    """Both at 1.0 -> deployed_capital == live_equity (no scaling)."""
    with patch(
        "capital_manager.fetch_live_equity", return_value=157_432.50
    ), patch(
        "capital_manager.get_deployment_config",
        return_value=(1.0, 1.0),
    ):
        from capital_manager import get_deployed_capital
        result = get_deployed_capital()
    assert abs(result - 157_432.50) < 0.01


# ═════════════════════════════════════════════════════════════════════════════
# Floor / ceiling guards
# ═════════════════════════════════════════════════════════════════════════════

def test_floor_guard_raises_on_tiny_equity():
    """deployed_capital below $1,000 raises CapitalError (Tradier failure)."""
    from capital_manager import CapitalError, get_deployed_capital
    with patch(
        "capital_manager.fetch_live_equity", return_value=50.0
    ), patch(
        "capital_manager.get_deployment_config",
        return_value=(1.0, 1.0),
    ):
        with pytest.raises(CapitalError, match="below floor"):
            get_deployed_capital()


def test_floor_guard_raises_on_zero_equity():
    """Tradier returning $0 (sandbox empty account) must halt cycle.

    Without this, a sandbox -> production env mix-up could size every
    trade against 0 contracts forever — silent failure.
    """
    from capital_manager import CapitalError, get_deployed_capital
    with patch(
        "capital_manager.fetch_live_equity", return_value=0.0
    ), patch(
        "capital_manager.get_deployment_config",
        return_value=(1.0, 1.0),
    ):
        with pytest.raises(CapitalError, match="below floor"):
            get_deployed_capital()


def test_ceiling_guard_raises_on_huge_value():
    """deployed_capital above $10M raises CapitalError (unit conv bug)."""
    from capital_manager import CapitalError, get_deployed_capital
    with patch(
        "capital_manager.fetch_live_equity", return_value=50_000_000.0
    ), patch(
        "capital_manager.get_deployment_config",
        return_value=(1.0, 1.0),
    ):
        with pytest.raises(CapitalError, match="exceeds ceiling"):
            get_deployed_capital()


# ═════════════════════════════════════════════════════════════════════════════
# Cache behaviour
# ═════════════════════════════════════════════════════════════════════════════

def test_equity_served_from_cache():
    """Second call within TTL reads from Redis, not Tradier."""
    from capital_manager import fetch_live_equity

    redis = MagicMock()
    redis.get.return_value = "185000.0"  # cache hit

    with patch("capital_manager.httpx") as mock_httpx:
        equity = fetch_live_equity(redis)

    assert abs(equity - 185_000.0) < 0.01
    mock_httpx.Client.assert_not_called()  # No Tradier call when cached


def test_equity_cached_after_api_call():
    """After fetching from Tradier, result is written to Redis with 5-min TTL."""
    from capital_manager import fetch_live_equity

    redis = MagicMock()
    redis.get.return_value = None  # cache miss

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "balances": {"total_equity": 95_000.0}
    }

    with patch("capital_manager.httpx.Client") as mock_client, \
         patch("capital_manager.config") as mc:
        mc.TRADIER_API_KEY = "test-key"
        mc.TRADIER_ACCOUNT_ID = "12345"
        mc.TRADIER_SANDBOX = True
        mock_client.return_value.__enter__.return_value.get.return_value = (
            mock_resp
        )
        equity = fetch_live_equity(redis)

    assert abs(equity - 95_000.0) < 0.01
    redis.setex.assert_called_once()
    cache_args = redis.setex.call_args[0]
    assert cache_args[0] == "capital:live_equity"
    assert cache_args[1] == 300  # 5-minute TTL


# ═════════════════════════════════════════════════════════════════════════════
# Deployment config
# ═════════════════════════════════════════════════════════════════════════════

def test_deployment_config_defaults_when_keys_absent():
    """Absent Redis keys -> defaults (1.0, 1.0)."""
    from capital_manager import get_deployment_config

    redis = MagicMock()
    redis.get.return_value = None

    pct, lev = get_deployment_config(redis)
    assert pct == 1.0
    assert lev == 1.0


def test_deployment_config_defaults_when_no_redis():
    """No Redis client -> defaults (1.0, 1.0) with no exceptions."""
    from capital_manager import get_deployment_config

    pct, lev = get_deployment_config(None)
    assert pct == 1.0
    assert lev == 1.0


def test_deployment_config_reads_custom_values():
    """Custom Redis values within range are applied."""
    from capital_manager import get_deployment_config

    redis = MagicMock()

    def mock_get(key):
        if key == "capital:deployment_pct":
            return "0.75"
        if key == "capital:leverage_multiplier":
            return "1.5"
        return None

    redis.get.side_effect = mock_get

    pct, lev = get_deployment_config(redis)
    assert abs(pct - 0.75) < 0.001
    assert abs(lev - 1.5) < 0.001


def test_deployment_pct_out_of_range_uses_default():
    """deployment_pct outside 0.01-2.0 falls back to default (1.0)."""
    from capital_manager import get_deployment_config

    redis = MagicMock()
    redis.get.side_effect = lambda k: "99.0" if "pct" in k else None

    pct, _ = get_deployment_config(redis)
    assert pct == 1.0, (
        f"99.0 is outside [0.01, 2.0] — must fall back to default. Got {pct}"
    )


# ═════════════════════════════════════════════════════════════════════════════
# Error propagation
# ═════════════════════════════════════════════════════════════════════════════

def test_capital_error_raised_when_no_api_key():
    """Missing TRADIER_API_KEY raises CapitalError."""
    from capital_manager import CapitalError, fetch_live_equity

    redis = MagicMock()
    redis.get.return_value = None

    with patch("capital_manager.config") as mc:
        mc.TRADIER_API_KEY = None
        mc.TRADIER_ACCOUNT_ID = "12345"
        mc.TRADIER_SANDBOX = True
        with pytest.raises(CapitalError, match="TRADIER_API_KEY"):
            fetch_live_equity(redis)


def test_capital_error_raised_on_tradier_error():
    """Non-200 Tradier response raises CapitalError with the status code."""
    from capital_manager import CapitalError, fetch_live_equity

    redis = MagicMock()
    redis.get.return_value = None

    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.text = "Unauthorized"

    with patch("capital_manager.httpx.Client") as mock_client, \
         patch("capital_manager.config") as mc:
        mc.TRADIER_API_KEY = "bad-key"
        mc.TRADIER_ACCOUNT_ID = "12345"
        mc.TRADIER_SANDBOX = True
        mock_client.return_value.__enter__.return_value.get.return_value = (
            mock_resp
        )
        with pytest.raises(CapitalError, match="401"):
            fetch_live_equity(redis)


# ═════════════════════════════════════════════════════════════════════════════
# Startup defaults seeding (S11 main.py change 2)
# ═════════════════════════════════════════════════════════════════════════════

def test_capital_keys_registered_in_trading_flag_keys():
    """Both capital keys must be in _TRADING_FLAG_KEYS for audit trail.

    Source-grep guard — does not import main.py. Adding either key to
    _TRADING_FLAG_KEYS makes it appear in /trading/flags and triggers
    the audit mirror in _backfill_feature_flags_to_supabase.
    """
    main_path = os.path.join(BACKEND, "main.py")
    with open(main_path, encoding="utf-8") as f:
        src = f.read()

    # Locate the _TRADING_FLAG_KEYS block
    block_start = src.find("_TRADING_FLAG_KEYS = [")
    assert block_start > -1, "_TRADING_FLAG_KEYS list not found in main.py"
    block_end = src.find("]", block_start)
    block = src[block_start:block_end]

    assert '"capital:deployment_pct"' in block, (
        "capital:deployment_pct must be registered in _TRADING_FLAG_KEYS"
    )
    assert '"capital:leverage_multiplier"' in block, (
        "capital:leverage_multiplier must be registered in "
        "_TRADING_FLAG_KEYS"
    )


# ═════════════════════════════════════════════════════════════════════════════
# Cycle integration
# ═════════════════════════════════════════════════════════════════════════════

def test_run_prediction_cycle_skips_on_capital_error():
    """run_prediction_cycle must NOT call run_trading_cycle when
    CapitalError is raised — sizing on the wrong number is the worst
    failure mode for risk management.
    """
    from capital_manager import CapitalError

    m, restore = _load_backend_main_isolated()
    try:
        with patch.object(
            m, "get_deployed_capital",
            side_effect=CapitalError("Tradier unreachable"),
        ), patch.object(m, "run_trading_cycle") as mock_cycle:
            m.run_prediction_cycle()
            mock_cycle.assert_not_called()
    finally:
        restore()
