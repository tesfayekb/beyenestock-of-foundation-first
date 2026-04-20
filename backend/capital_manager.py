"""
Capital allocation manager.

Single source of truth for ``deployed_capital`` — the dollar amount
the trading engine should size against on every cycle.

Formula
-------
    deployed_capital = live_equity * deployment_pct * leverage_multiplier

* ``live_equity``        — fetched from Tradier every cycle, Redis-cached
                           for 5 minutes under ``capital:live_equity``.
* ``deployment_pct``     — stored in Redis as ``capital:deployment_pct``,
                           range 0.01 - 2.0 (1% to 200% of account).
                           Default 1.0 (100% deployment).
* ``leverage_multiplier``— stored in Redis as
                           ``capital:leverage_multiplier``, range
                           0.5 - 5.0. Default 1.0 (no leverage).

Hard guards
-----------
* ``deployed_capital >= FLOOR_DEPLOYED`` (Tradier API failure guard)
* ``deployed_capital <= CEILING_DEPLOYED`` (unit conversion bug guard)

Failure semantics
-----------------
On any failure (Tradier down, missing key, response shape unexpected,
floor/ceiling violation) ``get_deployed_capital`` raises
``CapitalError``. Callers (``trading_cycle`` via
``run_prediction_cycle``) MUST catch and skip the cycle — never
substitute a silent fallback. Sizing against a wrong account value
is the worst possible failure mode for risk management.
"""

import httpx

import config
from logger import get_logger

logger = get_logger("capital_manager")

# Redis keys
CAPITAL_CACHE_KEY = "capital:live_equity"
CAPITAL_CACHE_TTL = 300  # seconds (5 minutes)

DEPLOYMENT_PCT_KEY = "capital:deployment_pct"
LEVERAGE_KEY = "capital:leverage_multiplier"

# Defaults
DEFAULT_DEPLOYMENT_PCT = 1.0  # 100% of account
DEFAULT_LEVERAGE = 1.0        # no leverage

# Hard bounds on the FINAL deployed_capital value.
# FLOOR catches Tradier returning 0 / unauthorized / sandbox empty
# accounts. CEILING catches a unit-conversion bug (e.g. cents vs
# dollars) before it sizes us into a margin call.
FLOOR_DEPLOYED = 1_000.0
CEILING_DEPLOYED = 10_000_000.0


class CapitalError(RuntimeError):
    """Raised when deployed capital cannot be determined safely.

    The trading cycle treats this as a halt — no trade is opened
    when this is raised.
    """
    pass


def _get_tradier_base_url() -> str:
    """Return Tradier REST base URL based on TRADIER_SANDBOX flag.

    Mirrors the exact pattern used in ``backend/tradier_feed.py``
    so all Tradier REST calls converge on a single source.
    """
    return (
        "https://sandbox.tradier.com"
        if config.TRADIER_SANDBOX
        else "https://api.tradier.com"
    )


def fetch_live_equity(redis_client=None) -> float:
    """Fetch ``total_equity`` from Tradier and cache it in Redis.

    Cache key: ``capital:live_equity`` with 5-minute TTL.

    Cache hit  -> returned immediately, no Tradier call.
    Cache miss -> Tradier ``GET /v1/accounts/{id}/balances`` is called
                  synchronously (we run inside APScheduler's thread
                  pool, not the asyncio loop, so a blocking
                  ``httpx.Client`` is appropriate). The result is
                  written back to the Redis cache.

    Raises
    ------
    CapitalError
        * Missing ``TRADIER_API_KEY`` or ``TRADIER_ACCOUNT_ID``.
        * Network failure or non-200 Tradier response.
        * Response missing ``balances.total_equity`` field.
    """
    if redis_client is not None:
        try:
            cached = redis_client.get(CAPITAL_CACHE_KEY)
            if cached:
                equity = float(cached)
                logger.debug(
                    "capital_equity_from_cache",
                    equity=equity,
                )
                return equity
        except Exception:
            pass  # Cache miss / failure -> fall through to API call

    api_key = getattr(config, "TRADIER_API_KEY", None)
    account_id = getattr(config, "TRADIER_ACCOUNT_ID", None)
    if not api_key or not account_id:
        raise CapitalError(
            "Cannot fetch equity: TRADIER_API_KEY or "
            "TRADIER_ACCOUNT_ID not set. Set these in Railway "
            "environment variables."
        )

    base_url = _get_tradier_base_url()
    url = f"{base_url}/v1/accounts/{account_id}/balances"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url, headers=headers)
    except Exception as exc:
        raise CapitalError(
            f"Tradier equity fetch failed: {exc}"
        ) from exc

    if resp.status_code != 200:
        raise CapitalError(
            f"Tradier balances returned {resp.status_code}: "
            f"{resp.text[:200]}"
        )

    data = None
    try:
        data = resp.json()
        # Tradier balances response shape:
        #   {"balances": {"total_equity": 123456.78, ...}}
        equity = float(data["balances"]["total_equity"])
    except (KeyError, TypeError, ValueError) as exc:
        raise CapitalError(
            f"Unexpected Tradier balances response structure: {exc}. "
            f"Response: {str(data)[:200]}"
        ) from exc

    if redis_client is not None:
        try:
            redis_client.setex(
                CAPITAL_CACHE_KEY, CAPITAL_CACHE_TTL, str(equity)
            )
        except Exception:
            pass  # Cache write failure must not abort the cycle

    logger.info(
        "capital_equity_fetched",
        equity=equity,
        account_id=account_id,
        sandbox=config.TRADIER_SANDBOX,
    )
    return equity


def get_deployment_config(redis_client=None) -> tuple:
    """Read ``deployment_pct`` and ``leverage_multiplier`` from Redis.

    Both keys are stored as plain float strings (e.g. ``"0.75"``).
    Absent or out-of-range values silently fall back to the module
    defaults so a malformed config can never crash the cycle —
    range violations are logged at WARN for the operator.

    Returns
    -------
    (deployment_pct, leverage_multiplier) tuple of floats.
    """
    deployment_pct = DEFAULT_DEPLOYMENT_PCT
    leverage = DEFAULT_LEVERAGE

    if redis_client is None:
        return deployment_pct, leverage

    try:
        raw_pct = redis_client.get(DEPLOYMENT_PCT_KEY)
        if raw_pct:
            val = float(raw_pct)
            if 0.01 <= val <= 2.0:
                deployment_pct = val
            else:
                logger.warning(
                    "capital_deployment_pct_out_of_range",
                    value=val,
                    using_default=DEFAULT_DEPLOYMENT_PCT,
                )
    except Exception:
        pass

    try:
        raw_lev = redis_client.get(LEVERAGE_KEY)
        if raw_lev:
            val = float(raw_lev)
            if 0.5 <= val <= 5.0:
                leverage = val
            else:
                logger.warning(
                    "capital_leverage_out_of_range",
                    value=val,
                    using_default=DEFAULT_LEVERAGE,
                )
    except Exception:
        pass

    return deployment_pct, leverage


def get_deployed_capital(redis_client=None) -> float:
    """Compute and return the dollar amount to size against this cycle.

    ``deployed_capital = live_equity * deployment_pct * leverage``

    Raises
    ------
    CapitalError
        * Live equity cannot be fetched (re-raised from
          ``fetch_live_equity``).
        * Computed value falls outside ``[FLOOR_DEPLOYED,
          CEILING_DEPLOYED]``.
    """
    equity = fetch_live_equity(redis_client)
    deployment_pct, leverage = get_deployment_config(redis_client)

    deployed = equity * deployment_pct * leverage

    logger.info(
        "capital_deployed_computed",
        equity=round(equity, 2),
        deployment_pct=deployment_pct,
        leverage=leverage,
        deployed=round(deployed, 2),
    )

    if deployed < FLOOR_DEPLOYED:
        raise CapitalError(
            f"deployed_capital={deployed:.2f} is below "
            f"floor={FLOOR_DEPLOYED}. This usually means Tradier "
            "returned wrong equity (API error, sandbox empty "
            "account, or account not connected). Halting cycle."
        )

    if deployed > CEILING_DEPLOYED:
        raise CapitalError(
            f"deployed_capital={deployed:.2f} exceeds "
            f"ceiling={CEILING_DEPLOYED}. Possible unit conversion "
            "error (cents vs dollars?). Halting cycle."
        )

    return deployed
