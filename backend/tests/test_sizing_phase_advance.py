"""
12N — Sizing phase auto-advance (Phase E1/E2) tests.

Two surfaces:
  * calibration_engine.evaluate_sizing_phase — the Sunday job that
    writes capital:sizing_phase to Redis when the Sharpe gates
    pass. Conservative by design: only advances, never retreats,
    and fails open with phase=1 in the return payload while
    leaving the Redis key untouched on any error so a previous
    successful advance is preserved across Supabase / Redis hiccups.
  * main._read_sizing_phase_from_redis — the per-cycle read that
    feeds sizing_phase into run_trading_cycle and downstream into
    risk_engine.compute_position_size. Fallback to 1 on any error
    is the ROI-safe default.

The eight tests pin, in order:
  1) below-gate live-days → no write
  2) positive gate → write "2" with 1-year TTL
  3) positive days but Sharpe too low → no write
  4) E2 gate (phase 2 → 3) → write "3"
  5) already at max phase → no write
  6) Supabase raises → fail-open to phase=1, no write
  7) Redis raises → fail-open, no setex called
  8) risk_engine consumer path: main's Redis reader returns the
     right int, or falls back to 1 on any error
"""
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..")
)


# ── Fluent Supabase mock ─────────────────────────────────────────────


class _FluentTable:
    """Chainable PostgREST builder stand-in. `.order()` is recorded
    so tests can verify chronological ordering when that becomes
    the right invariant to pin, but is not asserted here — the
    Sharpe gates are the primary correctness surface for 12N."""

    def __init__(self, rows=None):
        self._rows = rows or []

    def select(self, *args, **kwargs):
        return self

    def eq(self, *args):
        return self

    @property
    def not_(self):
        return self

    def is_(self, *args):
        return self

    def order(self, *args, **kwargs):
        return self

    def execute(self):
        result = MagicMock()
        result.data = self._rows
        return result


class _FluentClient:
    def __init__(self, rows=None):
        self._rows = rows or []

    def table(self, _name):
        return _FluentTable(rows=self._rows)


def _sessions(pnls: list) -> list:
    """Build a list of trading_sessions rows with the given per-day
    P&L stream. session_date values are synthetic — only the count
    and virtual_pnl values matter for the gate math."""
    return [
        {"session_date": f"2026-01-{(i % 28) + 1:02d}", "virtual_pnl": p}
        for i, p in enumerate(pnls)
    ]


def _alternating(n: int, hi: float, lo: float) -> list:
    """Alternating high/low returns — controls mean and stddev.

    With n even, hi=1100, lo=-900:
      mean = 100, stddev = 1000
      mean/stddev = 0.1, annualised Sharpe ≈ 0.1 * sqrt(252) ≈ 1.587
    That lands above the E1 (1.2) and E2 (1.5) gates with margin,
    so the same construction can drive both advances."""
    return [hi if i % 2 == 0 else lo for i in range(n)]


# ─────────────────────────────────────────────────────────────────────
# 1) below 45-day floor → phase 1 stays phase 1
# ─────────────────────────────────────────────────────────────────────


def test_sizing_stays_phase1_below_45_days():
    """30 sessions → E1_MIN_LIVE_DAYS gate (45) fails. Function
    must return advanced=False with a reason, and MUST NOT call
    redis.setex — writing a phase change below the day floor
    would violate the conservative ROI contract."""
    from calibration_engine import evaluate_sizing_phase

    redis_mock = MagicMock()
    redis_mock.get.return_value = None  # no previous phase → default to 1
    client = _FluentClient(rows=_sessions(_alternating(30, 1100, -900)))

    with patch(
        "calibration_engine.get_client", return_value=client
    ):
        result = evaluate_sizing_phase(redis_mock)

    assert result["phase"] == 1
    assert result["advanced"] is False
    assert result["reason"] == "live_days_below_gate"
    assert result["live_days"] == 30
    redis_mock.setex.assert_not_called()


# ─────────────────────────────────────────────────────────────────────
# 2) E1 gate passes → write "2" with 1-year TTL
# ─────────────────────────────────────────────────────────────────────


def test_sizing_advances_to_phase2():
    """50 sessions of alternating 1100/-900 P&L → mean=100,
    stddev=1000, annualised Sharpe ≈ 1.587 ≥ 1.2. Function must
    write "2" to the Redis key with the 1-year TTL
    (86400 * 365 = 31_536_000s) so a Redis restart that loses
    volatile keys will replay the advance on the very next Sunday
    rather than silently demoting the sizing."""
    from calibration_engine import (
        evaluate_sizing_phase,
        SIZING_PHASE_REDIS_KEY,
        SIZING_PHASE_TTL_SECONDS,
    )

    redis_mock = MagicMock()
    redis_mock.get.return_value = None  # current phase = 1
    client = _FluentClient(rows=_sessions(_alternating(50, 1100, -900)))

    with patch(
        "calibration_engine.get_client", return_value=client
    ):
        result = evaluate_sizing_phase(redis_mock)

    assert result["phase"] == 2
    assert result["advanced"] is True
    assert result["reason"] == "E1_gate_passed"
    assert result["live_days"] == 50
    assert result["sharpe"] >= 1.2

    redis_mock.setex.assert_called_once_with(
        SIZING_PHASE_REDIS_KEY,
        SIZING_PHASE_TTL_SECONDS,
        "2",
    )
    assert SIZING_PHASE_TTL_SECONDS == 86400 * 365


# ─────────────────────────────────────────────────────────────────────
# 3) days-gate passes but Sharpe too low → no write
# ─────────────────────────────────────────────────────────────────────


def test_sizing_stays_phase1_when_sharpe_too_low():
    """50 sessions with high variance relative to mean
    (alternating 2000/-1900 → mean=50, stddev=1950, Sharpe≈0.41)
    → E1 Sharpe gate (1.2) fails. Days gate alone must not be
    enough to advance — both conditions must hold."""
    from calibration_engine import evaluate_sizing_phase

    redis_mock = MagicMock()
    redis_mock.get.return_value = None
    client = _FluentClient(rows=_sessions(_alternating(50, 2000, -1900)))

    with patch(
        "calibration_engine.get_client", return_value=client
    ):
        result = evaluate_sizing_phase(redis_mock)

    assert result["phase"] == 1
    assert result["advanced"] is False
    assert result["reason"] == "E1_sharpe_below_gate"
    assert result["sharpe"] is not None
    assert result["sharpe"] < 1.2
    redis_mock.setex.assert_not_called()


# ─────────────────────────────────────────────────────────────────────
# 4) current_phase=2 + E2 gate passes → write "3"
# ─────────────────────────────────────────────────────────────────────


def test_sizing_advances_to_phase3():
    """Current phase "2" read from Redis, 96 sessions of the
    high-Sharpe stream (alternating 1100/-900 → Sharpe≈1.587 on
    the last 60). E2 Sharpe gate (1.5) passes → function must
    write "3" (not replace with the read "2" or some cast error).
    Assertion includes the exact written value to catch
    off-by-one bugs between current_phase and new_phase."""
    from calibration_engine import (
        evaluate_sizing_phase,
        SIZING_PHASE_REDIS_KEY,
        SIZING_PHASE_TTL_SECONDS,
    )

    redis_mock = MagicMock()
    redis_mock.get.return_value = "2"
    client = _FluentClient(rows=_sessions(_alternating(96, 1100, -900)))

    with patch(
        "calibration_engine.get_client", return_value=client
    ):
        result = evaluate_sizing_phase(redis_mock)

    assert result["phase"] == 3
    assert result["advanced"] is True
    assert result["reason"] == "E2_gate_passed"
    assert result["live_days"] == 96
    assert result["sharpe"] >= 1.5

    redis_mock.setex.assert_called_once_with(
        SIZING_PHASE_REDIS_KEY,
        SIZING_PHASE_TTL_SECONDS,
        "3",
    )


# ─────────────────────────────────────────────────────────────────────
# 5) already at max phase → no-op
# ─────────────────────────────────────────────────────────────────────


def test_sizing_never_retreats():
    """Current phase is already 3 (the max). The function must
    return without touching Redis — there is no phase 4 in the
    risk table, and any write here would be a future-compat
    footgun. Must also not query Supabase: short-circuit at the
    top of the function to keep the operation cheap."""
    from calibration_engine import evaluate_sizing_phase

    redis_mock = MagicMock()
    redis_mock.get.return_value = "3"

    with patch("calibration_engine.get_client") as mock_get_client:
        result = evaluate_sizing_phase(redis_mock)

    assert result["phase"] == 3
    assert result["advanced"] is False
    assert result["reason"] == "already_at_max_phase"
    redis_mock.setex.assert_not_called()
    mock_get_client.assert_not_called()


# ─────────────────────────────────────────────────────────────────────
# 6) Supabase raises → fail-open, no write
# ─────────────────────────────────────────────────────────────────────


def test_sizing_fail_open_on_supabase_error():
    """Supabase .table() raises → outer try/except returns a
    fail-open dict. Contract: phase=1 is reported for
    observability, but redis.setex is NOT called — so a previous
    legitimate advance written to Redis is preserved across the
    transient Supabase outage. The next Sunday job picks up where
    it left off once Supabase recovers."""
    from calibration_engine import evaluate_sizing_phase

    redis_mock = MagicMock()
    redis_mock.get.return_value = "2"
    raising_client = MagicMock()
    raising_client.table.side_effect = RuntimeError(
        "supabase unreachable"
    )

    with patch(
        "calibration_engine.get_client",
        return_value=raising_client,
    ):
        result = evaluate_sizing_phase(redis_mock)

    assert result["phase"] == 1
    assert result["advanced"] is False
    assert "error" in result
    assert "supabase unreachable" in result["error"]
    redis_mock.setex.assert_not_called()


# ─────────────────────────────────────────────────────────────────────
# 7) Redis raises → fail-open, no write
# ─────────────────────────────────────────────────────────────────────


def test_sizing_fail_open_on_redis_error():
    """redis.get() raises on the very first line of the function
    → outer except catches it and returns phase=1. Critically,
    redis.setex must NOT be called (the client is already broken;
    calling setex would just raise again). Guarantees the weekly
    calibration job keeps moving through its remaining blocks
    rather than aborting on a Redis hiccup."""
    from calibration_engine import evaluate_sizing_phase

    redis_mock = MagicMock()
    redis_mock.get.side_effect = RuntimeError("redis timeout")

    result = evaluate_sizing_phase(redis_mock)

    assert result["phase"] == 1
    assert result["advanced"] is False
    assert "error" in result
    assert "redis timeout" in result["error"]
    redis_mock.setex.assert_not_called()


# ─────────────────────────────────────────────────────────────────────
# 8) risk_engine consumer: main._read_sizing_phase_from_redis
# ─────────────────────────────────────────────────────────────────────


def test_risk_engine_reads_phase_from_redis():
    """The per-cycle reader that feeds sizing_phase into
    run_trading_cycle must:
      * return the int parsed from Redis when the key is present,
      * default to 1 when the key is absent,
      * default to 1 when the client is None,
      * default to 1 when Redis raises,
      * use the SAME Redis key as evaluate_sizing_phase writes.
    Pinning all five shapes here is the cheapest way to
    guarantee the live trading cycle never propagates a None /
    string / exception into risk_engine.compute_position_size
    and blows up sizing on a trivial cache miss, AND that the
    reader and writer never drift onto different key names."""
    from calibration_engine import (
        read_sizing_phase,
        SIZING_PHASE_REDIS_KEY,
    )

    assert SIZING_PHASE_REDIS_KEY == "capital:sizing_phase"

    # a) present, numeric string
    client = MagicMock()
    client.get.return_value = "2"
    assert read_sizing_phase(client) == 2
    client.get.assert_called_with(SIZING_PHASE_REDIS_KEY)

    # b) absent key
    client = MagicMock()
    client.get.return_value = None
    assert read_sizing_phase(client) == 1

    # c) client is None (Redis init failed at startup)
    assert read_sizing_phase(None) == 1

    # d) client raises
    client = MagicMock()
    client.get.side_effect = RuntimeError("redis down")
    assert read_sizing_phase(client) == 1

    # e) main.py call site imports and uses the same helper —
    #    guards against a future refactor that forks the reader
    #    back into main.py without updating the shared key.
    import pathlib
    main_src = (
        pathlib.Path(__file__).parent.parent / "main.py"
    ).read_text(encoding="utf-8")
    assert "from calibration_engine import read_sizing_phase" in main_src
    assert "read_sizing_phase(redis_client)" in main_src
