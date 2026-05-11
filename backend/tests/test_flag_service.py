"""Tests for backend/flag_service.py — two-layer enforcement.

Covers:
- :func:`flag_service.is_enabled` Layer B behavior (read-side blocking)
- :func:`flag_service.can_set_enabled` Layer A behavior (write-side
  blocking)
- Polarity-aware fail-closed semantic on Redis errors (returns
  ``default``, not False — for strategy flags ``default=False`` so the
  strategy disables on outage; for signal/safety-filter flags
  ``default=True`` so the filter stays ON on outage)
- Direct-CLI bypass scenario (operator runs ``redis-cli SET
  strategy:long_straddle:enabled true`` — Layer B must still return
  False)
- BLOCKS_FLAG_FLIP / TASK_REGISTER.md consistency invariant
"""
from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import MagicMock

import flag_service


# ── Layer B (is_enabled) ──────────────────────────────────────────────


def test_blocked_flag_with_redis_true_returns_false():
    """Layer B: catches direct-CLI Redis bypass."""
    mock_redis = MagicMock()
    mock_redis.get.return_value = b"true"
    assert flag_service.is_enabled(
        mock_redis, "strategy:long_straddle:enabled"
    ) is False


def test_blocked_flag_with_redis_false_returns_false():
    """Disabled flag stays disabled even if blocked."""
    mock_redis = MagicMock()
    mock_redis.get.return_value = b"false"
    assert flag_service.is_enabled(
        mock_redis, "strategy:long_straddle:enabled"
    ) is False


def test_non_blocked_flag_with_redis_true_returns_true():
    """Normal happy path: non-blocked flag passes through."""
    mock_redis = MagicMock()
    mock_redis.get.return_value = b"true"
    assert flag_service.is_enabled(
        mock_redis, "strategy:iron_condor:enabled"
    ) is True


def test_non_blocked_flag_with_redis_false_returns_false():
    mock_redis = MagicMock()
    mock_redis.get.return_value = b"false"
    assert flag_service.is_enabled(
        mock_redis, "strategy:iron_condor:enabled"
    ) is False


def test_non_blocked_flag_with_redis_none_returns_default_false():
    """Missing key returns default=False (strategy flag polarity)."""
    mock_redis = MagicMock()
    mock_redis.get.return_value = None
    assert flag_service.is_enabled(
        mock_redis, "strategy:iron_condor:enabled"
    ) is False


def test_signal_flag_absent_key_returns_default_true():
    """Missing key returns default=True (signal flag polarity, default ON)."""
    mock_redis = MagicMock()
    mock_redis.get.return_value = None
    assert flag_service.is_enabled(
        mock_redis,
        "signal:vix_term_filter:enabled",
        default=True,
    ) is True


def test_signal_flag_explicit_false_returns_false():
    """Signal flags: explicit 'false' overrides default=True."""
    mock_redis = MagicMock()
    mock_redis.get.return_value = b"false"
    assert flag_service.is_enabled(
        mock_redis,
        "signal:vix_term_filter:enabled",
        default=True,
    ) is False


def test_redis_error_returns_default_polarity_aware():
    """Fail-closed = polarity-aware: returns ``default`` on Redis error.

    For strategy flags (default=False), outage disables the strategy
    (safe — no trade enabled by accident).
    For signal flags (default=True, safety filters), outage keeps the
    filter ENABLED (safe — safety filter stays on).
    Both are "fail in the safe direction" — the polarity determines
    which way is safe.
    """
    mock_redis = MagicMock()
    mock_redis.get.side_effect = ConnectionError("redis down")

    assert flag_service.is_enabled(
        mock_redis, "strategy:iron_condor:enabled", default=False
    ) is False, "Strategy flag should DISABLE on Redis outage (default=False)"

    assert flag_service.is_enabled(
        mock_redis, "signal:vix_term_filter:enabled", default=True
    ) is True, "Signal safety filter should STAY ENABLED on Redis outage (default=True)"


def test_redis_none_returns_default():
    """``redis_client is None`` returns default (matches existing
    ``StrategySelector._check_feature_flag`` semantic)."""
    assert flag_service.is_enabled(
        None, "strategy:long_straddle:enabled", default=False
    ) is False
    assert flag_service.is_enabled(
        None, "signal:vix_term_filter:enabled", default=True
    ) is True


def test_str_value_handled_alongside_bytes():
    """Some Redis clients return str (decode_responses=True), some
    bytes (decode_responses=False); both must work."""
    mock_redis_bytes = MagicMock()
    mock_redis_bytes.get.return_value = b"true"
    mock_redis_str = MagicMock()
    mock_redis_str.get.return_value = "true"

    assert flag_service.is_enabled(
        mock_redis_bytes, "strategy:iron_condor:enabled"
    ) is True
    assert flag_service.is_enabled(
        mock_redis_str, "strategy:iron_condor:enabled"
    ) is True


def test_arbitrary_non_true_string_returns_false():
    """Strict tuple-membership semantic: only exact ``"true"`` /
    ``b"true"`` is enabled. ``"True"``, ``"1"``, ``"yes"`` etc. all
    return False (matches the prior in-line semantic at
    ``StrategySelector._check_feature_flag``)."""
    mock_redis = MagicMock()
    for raw in (b"yes", b"1", b"on", b"True", b"TRUE", b" true", b"random"):
        mock_redis.get.return_value = raw
        assert flag_service.is_enabled(
            mock_redis, "strategy:iron_condor:enabled"
        ) is False, f"Non-exact raw={raw!r} must return False"


# ── Layer A (can_set_enabled) ──────────────────────────────────────────


def test_can_set_enabled_blocked_flag_refused():
    allowed, reason = flag_service.can_set_enabled(
        "strategy:long_straddle:enabled", True
    )
    assert allowed is False
    assert "long_straddle" in reason
    assert "TASK_REGISTER" in reason


def test_can_set_enabled_non_blocked_flag_allowed():
    allowed, reason = flag_service.can_set_enabled(
        "strategy:iron_condor:enabled", True
    )
    assert allowed is True
    assert reason is None


def test_can_set_disabled_blocked_flag_allowed():
    """Operator must be able to disable a strategy even if it is
    on the blocks list (halt-on-demand)."""
    allowed, reason = flag_service.can_set_enabled(
        "strategy:long_straddle:enabled", False
    )
    assert allowed is True
    assert reason is None


def test_can_set_disabled_non_blocked_flag_allowed():
    allowed, reason = flag_service.can_set_enabled(
        "strategy:iron_condor:enabled", False
    )
    assert allowed is True
    assert reason is None


def test_all_six_blocked_flags_refuse_enable():
    """Every flag in BLOCKS_FLAG_FLIP must be refused on enable."""
    expected_flags = {
        "strategy:long_straddle:enabled",
        "strategy:calendar_spread:enabled",
        "strategy:long_call:enabled",
        "strategy:long_put:enabled",
        "strategy:debit_call_spread:enabled",
        "strategy:debit_put_spread:enabled",
    }
    assert expected_flags == set(flag_service.BLOCKS_FLAG_FLIP), (
        "BLOCKS_FLAG_FLIP membership has drifted from the 6 long_straddle "
        "remediation flags. If this is intentional, update the test AND "
        "TASK_REGISTER.md AND constitution.md T-Rule 11."
    )
    for flag in expected_flags:
        allowed, reason = flag_service.can_set_enabled(flag, True)
        assert allowed is False, f"{flag} should be blocked"
        assert reason is not None and flag in reason


# ── Direct-CLI bypass scenario ─────────────────────────────────────────


def test_direct_redis_set_does_not_enable_blocked_flag():
    """Canonical scenario the operator exercised on 2026-05-11 morning.

    Simulates ``redis-cli SET strategy:long_straddle:enabled true`` —
    bypassing the admin endpoint (Layer A is not exercised). Layer B
    must still catch the bypass at read time.
    """
    mock_redis = MagicMock()
    mock_redis.get.return_value = b"true"

    assert flag_service.is_enabled(
        mock_redis, "strategy:long_straddle:enabled"
    ) is False, (
        "Direct-CLI Redis bypass must be caught by Layer B (read-side "
        "enforcement)"
    )


# ── Code/docs invariant ────────────────────────────────────────────────


def test_blocks_list_matches_task_register_annotations():
    """Every flag in BLOCKS_FLAG_FLIP must appear in TASK_REGISTER.md
    as a ``Blocks-flag-flip:`` annotation. Every Blocks-flag-flip
    annotation in TASK_REGISTER.md must appear in BLOCKS_FLAG_FLIP.

    This is the critical regression coverage: if anyone adds to
    BLOCKS_FLAG_FLIP without updating the markdown (or vice versa),
    this test fails.
    """
    task_register_path = (
        Path(__file__).resolve().parents[2]
        / "trading-docs"
        / "08-planning"
        / "TASK_REGISTER.md"
    )
    assert task_register_path.exists(), (
        f"TASK_REGISTER.md not found at {task_register_path!s}"
    )
    content = task_register_path.read_text(encoding="utf-8")

    # Match the canonical annotation format used in T-ACT-088 through
    # T-ACT-093: ``**Blocks-flag-flip:** strategy:X:enabled``. Tolerant
    # to case in the keyword and to ``-`` / ``_`` between words.
    pattern = r"[Bb]locks[-_]flag[-_]flip:\*?\*?\s*(\S+)"
    register_flags = {
        m.strip("`*_ \t")
        for m in re.findall(pattern, content)
    }
    # Filter out any non-flag artefacts (e.g. test code paths that
    # mention the keyword without a real flag string).
    register_flags = {f for f in register_flags if f.startswith("strategy:")}

    missing_in_register = set(flag_service.BLOCKS_FLAG_FLIP) - register_flags
    extra_in_register = register_flags - set(flag_service.BLOCKS_FLAG_FLIP)

    assert not missing_in_register, (
        f"Flags in BLOCKS_FLAG_FLIP missing from TASK_REGISTER.md: "
        f"{sorted(missing_in_register)}"
    )
    assert not extra_in_register, (
        f"Flags annotated Blocks-flag-flip in TASK_REGISTER.md but "
        f"missing from BLOCKS_FLAG_FLIP: {sorted(extra_in_register)}"
    )
