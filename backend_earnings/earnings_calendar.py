"""
Phase 5A: Earnings calendar for the earnings volatility system.

Fetches upcoming earnings for the 6 target tickers using Finnhub
(same API key already in use by the economic_calendar agent).
Looks ahead 14 calendar days to find entry opportunities.

Redis output:
  earnings:upcoming_events — JSON list, 24hr TTL
  earnings:last_scan_at    — ISO timestamp
"""

from __future__ import annotations

import json
import os
import sys
from datetime import date, datetime, timedelta, timezone

import httpx

# Path insertion — same pattern as backend_agents (e.g.
# backend/main.py inserts ../backend_agents to import them).
# backend_earnings/ inserts ../backend so it can import shared
# helpers like logger, db, and config without coupling to the
# trading engine modules.
_BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..", "backend")
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from logger import get_logger  # noqa: E402  (path insert above)
from edge_calculator import (  # noqa: E402  (sibling module)
    EARNINGS_HISTORY,
    compute_edge_score,
    get_entry_days_before,
)

logger = get_logger("earnings_calendar")

REQUEST_TIMEOUT = 10.0
SCAN_TTL = 86_400   # 24 hours
LOOKAHEAD_DAYS = 14

# All tickers we track for earnings straddles.
TRACKED_TICKERS = list(EARNINGS_HISTORY.keys())


def scan_upcoming_earnings(redis_client) -> list[dict]:
    """
    Scan Finnhub for upcoming earnings in the next LOOKAHEAD_DAYS.
    Filters to tracked tickers only.
    Writes results to Redis.
    Returns list of upcoming event dicts.
    Never raises.
    """
    try:
        import config
        if not config.FINNHUB_API_KEY:
            logger.warning("earnings_scan_skipped_no_finnhub_key")
            return []

        today = date.today()
        end_date = today + timedelta(days=LOOKAHEAD_DAYS)

        url = (
            f"https://finnhub.io/api/v1/calendar/earnings"
            f"?from={today.isoformat()}&to={end_date.isoformat()}"
            f"&token={config.FINNHUB_API_KEY}"
        )

        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            resp = client.get(url)

        if resp.status_code != 200:
            logger.warning(
                "earnings_scan_http_error",
                status=resp.status_code,
            )
            return []

        all_earnings = resp.json().get("earningsCalendar", [])

        upcoming: list[dict] = []
        for row in all_earnings:
            ticker = (row.get("symbol") or "").upper()
            if ticker not in TRACKED_TICKERS:
                continue

            earnings_date_str = row.get("date")
            if not earnings_date_str:
                continue

            try:
                earnings_date = date.fromisoformat(earnings_date_str)
            except Exception:
                continue

            days_until = (earnings_date - today).days

            entry_days_before = get_entry_days_before(ticker)
            entry_date = _trading_days_before(
                earnings_date, entry_days_before
            )
            days_until_entry = (entry_date - today).days

            edge_score = compute_edge_score(ticker)

            announce_raw = row.get("hour", "unknown")
            if announce_raw == "bmo":
                announce_time = "pre"
            elif announce_raw == "amc":
                announce_time = "post"
            else:
                announce_time = "unknown"

            upcoming.append({
                "ticker": ticker,
                "earnings_date": earnings_date_str,
                "announce_time": announce_time,
                "days_until_earnings": days_until,
                "entry_date": entry_date.isoformat(),
                "days_until_entry": days_until_entry,
                "edge_score": edge_score,
                "should_enter": (
                    edge_score >= 0.08
                    and 0 <= days_until_entry <= 1
                ),
                "fiscal_quarter": row.get("quarter"),
                "estimated_eps": row.get("epsEstimate"),
            })

        upcoming.sort(key=lambda x: x["entry_date"])

        if redis_client:
            try:
                redis_client.setex(
                    "earnings:upcoming_events",
                    SCAN_TTL,
                    json.dumps(upcoming),
                )
                redis_client.setex(
                    "earnings:last_scan_at",
                    SCAN_TTL,
                    datetime.now(timezone.utc).isoformat(),
                )
            except Exception as e:
                logger.warning(
                    "earnings_redis_write_failed", error=str(e)
                )

        logger.info(
            "earnings_scan_complete",
            upcoming_count=len(upcoming),
            should_enter=[
                e["ticker"] for e in upcoming if e["should_enter"]
            ],
        )
        return upcoming

    except Exception as exc:
        logger.error("earnings_scan_failed", error=str(exc))
        return []


def _trading_days_before(target: date, n: int) -> date:
    """Return the date N trading days (Mon-Fri) before target.

    Pure calendar arithmetic — does not consult exchange holiday
    calendars. Good enough for entry-window targeting; the actual
    entry job runs on real market days only.
    """
    d = target
    count = 0
    while count < n:
        d = d - timedelta(days=1)
        if d.weekday() < 5:  # Monday-Friday
            count += 1
    return d


def get_upcoming_events(redis_client) -> list[dict]:
    """Read upcoming events from Redis.

    Returns empty list if stale, missing, or Redis is unreachable.
    Never raises.
    """
    try:
        raw = (
            redis_client.get("earnings:upcoming_events")
            if redis_client else None
        )
        return json.loads(raw) if raw else []
    except Exception:
        return []
