"""
Phase 5A: Historical edge calculator for earnings straddles.

For each ticker, tracks historical earnings move vs implied move.
When actual move consistently exceeds implied move, there is edge
in buying straddles before earnings.

Data source: Hardcoded from public historical records.
Update quarterly after each earnings season.

Edge score = win_rate × (avg_actual / avg_implied - 1.0)
  0.0 = no edge  |  0.5 = strong edge  |  1.0 = exceptional edge
"""

from __future__ import annotations

# Historical earnings data for the 6 main SPX-moving tickers.
# "win" = actual post-earnings move > implied move at announcement.
# Update after each quarterly earnings season.
# Source: compiled from public options market data 2023-2026.
EARNINGS_HISTORY = {
    "NVDA": {
        "beat_rate": 0.75,           # 9 of last 12 quarters beat implied
        "avg_actual_move_pct": 8.6,  # average |actual move| last 12 quarters
        "avg_implied_move_pct": 6.2, # average implied move (straddle/price)
        "last_4_actual_pcts": [9.2, 7.1, 12.4, 8.8],
        "last_4_implied_pcts": [7.1, 5.8, 9.3, 6.7],
        "announce_time_typical": "post",
        "preferred_entry_days_before": 2,
    },
    "META": {
        "beat_rate": 0.67,
        "avg_actual_move_pct": 7.8,
        "avg_implied_move_pct": 6.1,
        "last_4_actual_pcts": [8.4, 5.9, 11.2, 6.8],
        "last_4_implied_pcts": [6.5, 5.2, 8.9, 5.8],
        "announce_time_typical": "post",
        "preferred_entry_days_before": 2,
    },
    "AAPL": {
        "beat_rate": 0.58,
        "avg_actual_move_pct": 4.2,
        "avg_implied_move_pct": 3.5,
        "last_4_actual_pcts": [3.8, 5.1, 3.2, 4.7],
        "last_4_implied_pcts": [3.2, 4.1, 2.8, 3.9],
        "announce_time_typical": "post",
        "preferred_entry_days_before": 2,
    },
    "TSLA": {
        "beat_rate": 0.67,
        "avg_actual_move_pct": 10.8,
        "avg_implied_move_pct": 9.1,
        "last_4_actual_pcts": [12.1, 7.8, 14.2, 9.8],
        "last_4_implied_pcts": [10.2, 7.1, 11.8, 8.5],
        "announce_time_typical": "post",
        "preferred_entry_days_before": 2,
    },
    "AMZN": {
        "beat_rate": 0.67,
        "avg_actual_move_pct": 7.1,
        "avg_implied_move_pct": 5.8,
        "last_4_actual_pcts": [6.8, 8.9, 5.4, 7.2],
        "last_4_implied_pcts": [5.5, 7.2, 4.8, 5.9],
        "announce_time_typical": "post",
        "preferred_entry_days_before": 2,
    },
    "GOOGL": {
        "beat_rate": 0.58,
        "avg_actual_move_pct": 6.2,
        "avg_implied_move_pct": 5.1,
        "last_4_actual_pcts": [5.8, 7.4, 4.9, 6.7],
        "last_4_implied_pcts": [4.8, 6.2, 4.1, 5.6],
        "announce_time_typical": "post",
        "preferred_entry_days_before": 2,
    },
}

# Minimum edge score to enter a straddle.
EDGE_THRESHOLD = 0.08

# Maximum position size as fraction of account.
MAX_POSITION_PCT = 0.15


def compute_edge_score(ticker: str) -> float:
    """
    Compute edge score for a ticker.
    Score = beat_rate * (avg_actual / avg_implied - 1.0)
    Returns 0.0 if ticker unknown or no edge.
    """
    data = EARNINGS_HISTORY.get(ticker.upper())
    if not data:
        return 0.0

    beat_rate = data.get("beat_rate", 0.5)
    avg_actual = data.get("avg_actual_move_pct", 0.0)
    avg_implied = data.get("avg_implied_move_pct", 1.0)

    if avg_implied <= 0:
        return 0.0

    move_edge = (avg_actual / avg_implied) - 1.0
    score = beat_rate * max(0.0, move_edge)
    return round(score, 4)


def has_sufficient_edge(
    ticker: str,
    current_implied_move_pct: float = None,
) -> bool:
    """
    Returns True if there is sufficient historical edge to enter a straddle.

    UNIT CONTRACT (critical — do not change without updating both sides):
      EARNINGS_HISTORY.avg_actual_move_pct  — stored in PERCENT (8.6 = 8.6%)
      current_implied_move_pct              — passed in as FRACTION (0.062 = 6.2%)

    Comparison converts historical percent → fraction before comparing.
    Pre-fix bug: the raw percent (8.6) was compared against fraction
    (0.068), which is always False — the "market priced it in" guard
    never fired and every ticker passed through.
    """
    edge = compute_edge_score(ticker)
    if edge < EDGE_THRESHOLD:
        return False

    if current_implied_move_pct is not None and current_implied_move_pct > 0:
        data = EARNINGS_HISTORY.get(ticker.upper(), {})
        avg_actual_pct = data.get("avg_actual_move_pct", 0.0)
        # Convert stored percent to fraction for comparison with live data
        avg_actual_fraction = avg_actual_pct / 100.0
        # Only enter if historical avg actual > 110% of current implied move
        if avg_actual_fraction < current_implied_move_pct * 1.10:
            return False

    return True


def get_position_size_pct(ticker: str, account_value: float) -> float:
    """
    Return fraction of account to allocate to this earnings straddle.
    Scales with edge score, caps at MAX_POSITION_PCT.

    edge 0.08 → 6% of account, edge 0.20+ → 15% max.
    Floors at 5% if we're trading at all.
    """
    edge = compute_edge_score(ticker)
    if edge <= 0:
        return 0.0

    scaled = min(MAX_POSITION_PCT, edge * 0.75)
    scaled = max(0.05, scaled)
    return round(scaled, 4)


def get_entry_days_before(ticker: str) -> int:
    """Return preferred number of trading days before earnings to enter."""
    data = EARNINGS_HISTORY.get(ticker.upper(), {})
    return data.get("preferred_entry_days_before", 2)
