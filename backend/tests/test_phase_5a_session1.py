"""Tests for Phase 5A Session 1: DB foundation + edge + calendar.

backend_earnings/ is a sibling directory of backend/, mirroring
the backend_agents/ pattern. Each test inserts the sibling path
into sys.path so the modules under test can be imported without
modifying any backend/ trading-engine code.
"""
import os
import sys

# Path to the sibling backend_earnings/ package, computed once.
_EARNINGS_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "backend_earnings"
)


def _ensure_earnings_on_path() -> None:
    """Insert backend_earnings/ on sys.path for each test (idempotent)."""
    if _EARNINGS_DIR not in sys.path:
        sys.path.insert(0, _EARNINGS_DIR)


# ── Edge calculator ─────────────────────────────────────────────────────────


def test_nvda_has_strong_edge():
    _ensure_earnings_on_path()
    from edge_calculator import compute_edge_score, has_sufficient_edge
    score = compute_edge_score("NVDA")
    assert score >= 0.10, f"NVDA edge {score} below expected threshold"
    assert has_sufficient_edge("NVDA") is True


def test_unknown_ticker_returns_zero():
    _ensure_earnings_on_path()
    from edge_calculator import compute_edge_score, has_sufficient_edge
    assert compute_edge_score("XYZ") == 0.0
    assert has_sufficient_edge("XYZ") is False


def test_high_current_implied_reduces_edge():
    """If current implied > historical actual, edge disappears."""
    _ensure_earnings_on_path()
    from edge_calculator import has_sufficient_edge
    # Historical NVDA actual ~8.6%. If implied is 10% (higher than
    # historical), the market has already priced in the move.
    assert has_sufficient_edge("NVDA", current_implied_move_pct=10.0) is False


def test_all_6_tickers_have_edge_data():
    _ensure_earnings_on_path()
    from edge_calculator import EARNINGS_HISTORY, compute_edge_score
    for ticker in ["NVDA", "META", "AAPL", "TSLA", "AMZN", "GOOGL"]:
        assert ticker in EARNINGS_HISTORY, (
            f"{ticker} missing from EARNINGS_HISTORY"
        )
        score = compute_edge_score(ticker)
        assert score >= 0, f"{ticker} edge score is negative"


def test_position_size_scales_with_edge():
    _ensure_earnings_on_path()
    from edge_calculator import get_position_size_pct
    nvda_size = get_position_size_pct("NVDA", 200_000)
    aapl_size = get_position_size_pct("AAPL", 200_000)
    # NVDA has higher edge than AAPL → should get larger allocation
    assert nvda_size >= aapl_size
    assert nvda_size <= 0.15  # never exceeds 15%
    assert aapl_size >= 0.05  # always at least 5% if trading


# ── Calendar ─────────────────────────────────────────────────────────────────


def test_trading_days_before():
    _ensure_earnings_on_path()
    from earnings_calendar import _trading_days_before
    from datetime import date
    # Thursday April 23 → 2 trading days before = Tuesday April 21
    result = _trading_days_before(date(2026, 4, 23), 2)
    assert result == date(2026, 4, 21)


def test_trading_days_before_skips_weekend():
    _ensure_earnings_on_path()
    from earnings_calendar import _trading_days_before
    from datetime import date
    # Monday April 27 → 1 trading day before = Friday April 24 (not Sunday)
    result = _trading_days_before(date(2026, 4, 27), 1)
    assert result == date(2026, 4, 24)


def test_get_upcoming_returns_empty_when_no_redis():
    _ensure_earnings_on_path()
    from earnings_calendar import get_upcoming_events
    result = get_upcoming_events(None)
    assert result == []
