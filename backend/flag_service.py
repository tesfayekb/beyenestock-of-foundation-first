"""Flag service — two-layer enforcement of strategy feature flag changes.

Background: three prior instances (IC/IB 2026-04-25 commit 77af9aa;
PCS/CCS 2026-04-28 commit fc6b077; long_straddle 2026-05-11) of the same
target_credit defect class shipped to production. In each case, the prior
commit deferred adjacent fixes, the deferral was captured in markdown
only (no runtime enforcement), and the operator subsequently flipped
the deferred-strategy flag, producing contaminated trades.

This module closes the governance loop:

- Layer A (write-side): the admin endpoint ``set_feature_flag`` at
  ``backend/main.py`` calls :func:`can_set_enabled` before
  ``redis_client.set()``. Refuses to set "true" for any flag listed in
  :data:`BLOCKS_FLAG_FLIP`.

- Layer B (read-side): every strategy_selector / execution_engine site
  reading a strategy flag calls :func:`is_enabled` (directly or via
  ``StrategySelector._check_feature_flag``). If the flag is in
  :data:`BLOCKS_FLAG_FLIP` AND Redis says "true", returns False
  regardless of the Redis value — catches direct-CLI Redis bypass.

:data:`BLOCKS_FLAG_FLIP` is the canonical Python representation of the
``Blocks-flag-flip`` annotations in
``trading-docs/08-planning/TASK_REGISTER.md``. The markdown is the
source of intent. The Python is the enforcement. Both must agree;
``test_flag_service.test_blocks_list_matches_task_register_annotations``
asserts consistency.

Fail-closed semantic (polarity-aware): on Redis errors or when
``redis_client`` is None, :func:`is_enabled` returns ``default`` rather
than a hard-coded False. This preserves the safety direction for both
polarities:

- Strategy flags (``default=False``): outage disables the strategy
  (safe — no trade enabled by accident).
- Signal flags (safety filters, ``default=True``): outage keeps the
  filter ENABLED (safe — safety filter stays on). Returning False
  unconditionally would disable signal-flag safety filters during a
  Redis outage — that is fail-open for safety, the opposite of what
  "fail-closed" is meant to deliver.
"""
from __future__ import annotations

from typing import Optional, Tuple

from logger import get_logger

logger = get_logger("flag_service")


# Flags blocked from being enabled until their corresponding T-ACT-XXX
# entry in ``trading-docs/08-planning/TASK_REGISTER.md`` is closed.
# Synced manually by the operator + reviewer when each PR in the
# long_straddle remediation sequence lands.
#
# Adding entries to this set:
#   1. Add T-ACT-XXX entry to TASK_REGISTER.md with
#      ``**Blocks-flag-flip:** <flag>`` annotation.
#   2. Add the flag name to this set.
#   3. Both must agree (enforced by
#      ``test_flag_service.test_blocks_list_matches_task_register_annotations``).
#
# Removing entries from this set (when a PR closes the corresponding fix):
#   1. Mark T-ACT-XXX as ``Status: [x] DONE`` in TASK_REGISTER.md and
#      remove its ``Blocks-flag-flip`` annotation (or strike-through it).
#   2. Remove the flag from this set.
#   3. Both must agree (same test).
BLOCKS_FLAG_FLIP: frozenset = frozenset({
    "strategy:long_straddle:enabled",
    "strategy:calendar_spread:enabled",
    "strategy:long_call:enabled",
    "strategy:long_put:enabled",
    "strategy:debit_call_spread:enabled",
    "strategy:debit_put_spread:enabled",
})


def is_enabled(
    redis_client,
    flag_key: str,
    default: bool = False,
) -> bool:
    """Check if a feature flag is enabled, with blocks-list enforcement.

    Polarity-aware: the ``default`` parameter mirrors the existing
    ``StrategySelector._check_feature_flag`` contract.

    - ``default=False`` (strategy/agent flags): absent key returns False;
      explicit ``"true"`` returns True (unless blocked).
    - ``default=True`` (signal flags, default-ON polarity): absent key
      returns True; explicit ``"false"`` returns False.

    Blocking suppresses explicit enabling; it does NOT invert default
    polarity. If a flag with ``default=True`` is in
    :data:`BLOCKS_FLAG_FLIP` and Redis has no value, the read returns
    True (default behavior unchanged). Blocking applies only when an
    explicit "true" value is read from Redis. This is intentional —
    blocking is for preventing admin / CLI "enable" actions, not for
    overriding flag polarity. No flag with ``default=True`` is currently
    in :data:`BLOCKS_FLAG_FLIP`; if one ever is, this semantic should
    be re-evaluated.

    Fail-closed semantic (polarity-aware): on Redis errors or when
    ``redis_client`` is falsy, returns ``default``. For strategy flags
    (``default=False``), this disables the strategy on outage. For
    signal flags (``default=True``), this keeps the filter ENABLED on
    outage. Both are "fail in the safe direction" — the polarity
    determines which way is safe.

    Args:
        redis_client: a ``redis.Redis`` (or compatible) client whose
            ``.get()`` returns ``bytes`` / ``str`` / ``None``. May be
            ``None`` / falsy; the function handles that path safely.
        flag_key: the flag name (e.g. ``"strategy:long_straddle:enabled"``).
        default: the value to return when the Redis key is absent OR
            when Redis is unreachable. See polarity rules above.

    Returns:
        True if the flag is enabled in Redis AND not blocked.
        False if the flag is explicitly disabled OR blocked.
        ``default`` if the key is absent OR Redis is unreachable.
    """
    if not redis_client:
        return default

    try:
        raw = redis_client.get(flag_key)
    except Exception as exc:
        logger.warning(
            "flag_service_read_error",
            flag_key=flag_key,
            error=str(exc),
        )
        return default

    if raw is None:
        return default

    # Strict tuple-membership check mirrors the prior in-line
    # implementation at StrategySelector._check_feature_flag verbatim
    # (``val in ("true", b"true")``). Any other value — including
    # mixed-case ``"True"``, whitespace-padded ``" true "``, ``"1"``,
    # ``"yes"`` — is treated as False. Preserving this strict semantic
    # avoids silent broadening of what counts as "enabled" across the
    # ~16 call sites that previously relied on it.
    raw_enabled = raw in ("true", b"true")

    if flag_key in BLOCKS_FLAG_FLIP and raw_enabled:
        logger.warning(
            "flag_read_blocked",
            flag_key=flag_key,
            raw_value=str(raw),
            reason="flag_in_blocks_flag_flip_list",
        )
        return False

    return raw_enabled


def can_set_enabled(
    flag_key: str,
    new_value: bool,
) -> Tuple[bool, Optional[str]]:
    """Check if an admin endpoint is allowed to set a flag to a value.

    Layer A: write-side enforcement.

    Disabling a flag (``new_value=False``) is always allowed (operator
    must be able to halt a strategy even if it is on the blocks list).
    Enabling a flag (``new_value=True``) is refused if the flag is in
    :data:`BLOCKS_FLAG_FLIP`.

    Args:
        flag_key: the flag name.
        new_value: the target boolean value (True = enable; False =
            disable).

    Returns:
        ``(True, None)`` if the set is allowed.
        ``(False, reason_string)`` if the set is refused.
    """
    if not new_value:
        return (True, None)

    if flag_key in BLOCKS_FLAG_FLIP:
        return (
            False,
            (
                f"flag_key={flag_key} is in BLOCKS_FLAG_FLIP; see "
                "trading-docs/08-planning/TASK_REGISTER.md for the "
                "corresponding T-ACT entry. Resolve the deferred fix "
                "before enabling."
            ),
        )

    return (True, None)
