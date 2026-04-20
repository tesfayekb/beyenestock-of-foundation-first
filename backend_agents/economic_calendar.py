"""
Economic calendar intelligence — Phase 2A Tier 1.

Three data sources, in priority order:
1. Finnhub economic calendar (paid, already subscribed) — best data
2. FRED release dates (free fallback) — dates only, no consensus
3. Hardcoded known dates (last resort)

Output: Redis key calendar:today:intel (TTL 24hr)
Format: JSON list of event dicts

Every function has try/except. Never blocks trading.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from typing import Optional

import httpx

from db import get_client
from logger import get_logger

logger = get_logger("economic_calendar")

# ─── Constants ───────────────────────────────────────────────────────────────

# Tier 1: Major catalysts — sit out or buy straddle
MAJOR_EVENTS: set[str] = {
    "Federal Funds Rate",            # FOMC rate decision
    "FOMC Meeting Minutes",          # Fed minutes
    "CPI",                           # Consumer Price Index
    "Core CPI",
    "PCE Price Index",               # Fed's preferred inflation measure
    "Core PCE Price Index",
    "Nonfarm Payrolls",              # NFP
    "Unemployment Rate",
    "GDP",
    "GDP Growth Rate",
    "Fed Chair Powell Speech",
    "Fed Chair Speech",
}

# Tier 2: Significant — reduce size
MINOR_EVENTS: set[str] = {
    "PPI",
    "Core PPI",
    "Retail Sales",
    "ADP Nonfarm Employment Change",
    "ISM Manufacturing PMI",
    "ISM Services PMI",
    "Initial Jobless Claims",
    "JOLTS Job Openings",
    "Consumer Confidence",
    "Durable Goods Orders",
}

# High-impact earnings tickers that move SPX significantly
MAJOR_EARNINGS_TICKERS: set[str] = {
    "NVDA", "AAPL", "MSFT", "META", "AMZN", "GOOGL", "GOOG",
    "TSLA", "NFLX", "AMD", "AVGO",
}

REQUEST_TIMEOUT = 6.0


# ─── Main entry point ─────────────────────────────────────────────────────────

def get_todays_market_intelligence(
    check_date: Optional[date] = None,
) -> dict:
    """
    Returns complete market intelligence for today.

    {
        "date": "2026-04-21",
        "has_major_catalyst": bool,
        "has_minor_catalyst": bool,
        "has_major_earnings": bool,
        "events": [list of event dicts],
        "earnings": [list of earnings dicts],
        "day_classification": "catalyst_major"|"catalyst_minor"|"earnings_major"|"normal",
        "recommended_posture": "sit_out"|"straddle"|"reduced_size"|"normal",
        "consensus_data": dict,   # actual vs expected where available
    }
    """
    target = check_date or date.today()

    try:
        events = _fetch_finnhub_calendar(target)
        # upcoming_earnings spans the next 5 trading days (per
        # _fetch_major_earnings). `earnings` is the legacy today-only
        # slice preserved for the dashboard brief consumer and for
        # day_classification, which has always been a same-day signal.
        upcoming_earnings = _fetch_major_earnings(target)
        earnings = [
            e for e in upcoming_earnings if e.get("days_until") == 0
        ]

        major_events = [e for e in events if e.get("is_major")]
        minor_events = [e for e in events if not e.get("is_major")]

        has_major = len(major_events) > 0
        has_minor = len(minor_events) > 0
        has_major_earnings = len(earnings) > 0

        # Classification
        if has_major:
            day_classification = "catalyst_major"
            recommended_posture = "straddle"  # buy direction, not sell premium
        elif has_major_earnings:
            day_classification = "earnings_major"
            recommended_posture = "reduced_size"
        elif has_minor:
            day_classification = "catalyst_minor"
            recommended_posture = "reduced_size"
        else:
            day_classification = "normal"
            recommended_posture = "normal"

        intel = {
            "date": target.isoformat(),
            "has_major_catalyst": has_major,
            "has_minor_catalyst": has_minor,
            "has_major_earnings": has_major_earnings,
            "events": events,
            "earnings": earnings,
            "upcoming_earnings": upcoming_earnings,
            "day_classification": day_classification,
            "recommended_posture": recommended_posture,
            "consensus_data": _extract_consensus_data(events),
        }

        logger.info(
            "market_intelligence_ready",
            date=target.isoformat(),
            classification=day_classification,
            posture=recommended_posture,
            major_count=len(major_events),
            earnings_count=len(earnings),
        )
        return intel

    except Exception as exc:
        logger.warning("market_intelligence_failed", error=str(exc))
        return _empty_intel(target)


# ─── Finnhub calendar ─────────────────────────────────────────────────────────

def _fetch_finnhub_calendar(target: date) -> list[dict]:
    """Fetch economic events from Finnhub (paid subscription)."""
    try:
        import config
        if not config.FINNHUB_API_KEY:
            return _fetch_fred_fallback(target)

        # S7-6: token moved out of the URL into the X-Finnhub-Token
        # header (Finnhub's documented auth header). Keys in URLs leak
        # into Railway log streams, httpx exception messages, and any
        # upstream proxy access logs.
        url = (
            f"https://finnhub.io/api/v1/calendar/economic"
            f"?from={target.isoformat()}&to={target.isoformat()}"
        )
        headers = {"X-Finnhub-Token": config.FINNHUB_API_KEY}
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            resp = client.get(url, headers=headers)

        if resp.status_code != 200:
            return _fetch_fred_fallback(target)

        data = resp.json()
        raw_events = data.get("economicCalendar", [])

        events = []
        for ev in raw_events:
            event_name = ev.get("event", "")
            is_major = any(m.lower() in event_name.lower() for m in MAJOR_EVENTS)
            is_minor = (
                not is_major
                and any(m.lower() in event_name.lower() for m in MINOR_EVENTS)
            )
            if not is_major and not is_minor:
                continue  # skip low-impact events

            events.append({
                "event": event_name,
                "time": ev.get("time", ""),
                "country": ev.get("country", "US"),
                "is_major": is_major,
                "estimate": ev.get("estimate"),  # consensus forecast
                "prev": ev.get("prev"),           # previous reading
                "actual": ev.get("actual"),       # None until released
                "unit": ev.get("unit", ""),
                "impact": "major" if is_major else "minor",
            })

        return events

    except Exception as exc:
        logger.warning("finnhub_calendar_failed", error=str(exc))
        return _fetch_fred_fallback(target)


def _fetch_fred_fallback(target: date) -> list[dict]:
    """
    Fallback: FRED release dates (no consensus data, dates only).
    Only used when Finnhub is unavailable.
    """
    try:
        FRED_RELEASES = {
            10: ("Federal Funds Rate", True),
            21: ("CPI", True),
            50: ("PCE Price Index", True),
            11: ("Nonfarm Payrolls", True),
            54: ("GDP", True),
            46: ("PPI", False),
            33: ("Retail Sales", False),
        }

        events = []
        start = (target - timedelta(days=1)).isoformat()
        end = (target + timedelta(days=1)).isoformat()

        for release_id, (name, is_major) in FRED_RELEASES.items():
            try:
                url = (
                    f"https://api.stlouisfed.org/fred/release/dates"
                    f"?release_id={release_id}"
                    f"&realtime_start={start}&realtime_end={end}"
                    f"&file_type=json"
                )
                with httpx.Client(timeout=4.0) as client:
                    resp = client.get(url)
                if resp.status_code != 200:
                    continue
                dates = resp.json().get("release_dates", [])
                if any(d.get("date") == target.isoformat() for d in dates):
                    events.append({
                        "event": name,
                        "time": "08:30:00",
                        "country": "US",
                        "is_major": is_major,
                        "estimate": None,
                        "prev": None,
                        "actual": None,
                        "unit": "",
                        "impact": "major" if is_major else "minor",
                    })
            except Exception:
                continue

        return events

    except Exception as exc:
        logger.warning("fred_fallback_failed", error=str(exc))
        return []


# Look-ahead horizon for the earnings proximity score. Kept as a
# module-level constant because it's shared by _fetch_major_earnings
# (window bound) and write_intel_to_redis (gradient denominator).
EARNINGS_PROXIMITY_HORIZON_DAYS = 5


def _fetch_major_earnings(target: date) -> list[dict]:
    """
    Fetch earnings for major SPX-moving tickers via Finnhub across a
    5-trading-day window (today → today+5) so the prediction engine
    can score "days until next major earnings" as a gradient feature
    instead of the binary "is today an earnings day?".

    Each returned dict includes:
      ticker, name, eps_estimate, eps_actual, hour, is_major,
      date (ISO "YYYY-MM-DD"), days_until (int, 0 = today).

    Events are sorted by date ascending so `upcoming[0]` is always
    the nearest event — callers that only want today's earnings can
    filter on `days_until == 0`.
    """
    try:
        import config
        if not config.FINNHUB_API_KEY:
            return []

        window_end = target + timedelta(days=EARNINGS_PROXIMITY_HORIZON_DAYS)
        # S7-6: token in X-Finnhub-Token header (same fix as the
        # economic calendar above — keeps the key out of every log path).
        url = (
            f"https://finnhub.io/api/v1/calendar/earnings"
            f"?from={target.isoformat()}&to={window_end.isoformat()}"
        )
        headers = {"X-Finnhub-Token": config.FINNHUB_API_KEY}
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            resp = client.get(url, headers=headers)

        if resp.status_code != 200:
            return []

        data = resp.json()
        all_earnings = data.get("earningsCalendar", [])

        out: list[dict] = []
        for e in all_earnings:
            symbol = e.get("symbol")
            if symbol not in MAJOR_EARNINGS_TICKERS:
                continue
            event_date_str = e.get("date") or target.isoformat()
            try:
                event_date = date.fromisoformat(event_date_str)
            except Exception:
                # Malformed date from upstream — skip rather than
                # poison downstream proximity math with a bogus event.
                continue
            days_until = (event_date - target).days
            # Clamp into the requested window; Finnhub has occasionally
            # returned dates one day outside the asked range on
            # timezone boundaries.
            if days_until < 0 or days_until > EARNINGS_PROXIMITY_HORIZON_DAYS:
                continue
            out.append({
                "ticker": symbol,
                "name": symbol,
                "eps_estimate": e.get("epsEstimate"),
                "eps_actual": e.get("epsActual"),
                "hour": e.get("hour", "amc"),  # bmo/amc/dmh
                "is_major": True,
                "date": event_date.isoformat(),
                "days_until": days_until,
            })

        out.sort(key=lambda x: x["days_until"])
        return out

    except Exception as exc:
        logger.warning("earnings_calendar_failed", error=str(exc))
        return []


def _extract_consensus_data(events: list[dict]) -> dict:
    """Extract consensus vs estimate data for use by AI agents."""
    consensus = {}
    for ev in events:
        if ev.get("estimate") is not None or ev.get("actual") is not None:
            consensus[ev["event"]] = {
                "estimate": ev.get("estimate"),
                "prev": ev.get("prev"),
                "actual": ev.get("actual"),
                "has_surprise": (
                    ev.get("actual") is not None
                    and ev.get("estimate") is not None
                ),
            }
    return consensus


def _empty_intel(target: date) -> dict:
    return {
        "date": target.isoformat(),
        "has_major_catalyst": False,
        "has_minor_catalyst": False,
        "has_major_earnings": False,
        "events": [],
        "earnings": [],
        "upcoming_earnings": [],
        "day_classification": "normal",
        "recommended_posture": "normal",
        "consensus_data": {},
    }


def _compute_earnings_proximity_score(intel: dict) -> float:
    """
    Compute the earnings proximity score consumed by
    prediction_engine._compute_phase_a_features().

    Score is a linear decay from 1.0 (earnings today) to 0.0 (5+ days
    away or no earnings). Using the nearest event (min days_until) is
    deliberate: the model cares about the closest known catalyst, not
    the density of events in the window.

    Separated from the writer so it is independently unit-testable
    and can be reused by other consumers without an I/O dependency.
    """
    upcoming = intel.get("upcoming_earnings") or []
    if not upcoming:
        return 0.0
    min_days = min(
        (e.get("days_until", EARNINGS_PROXIMITY_HORIZON_DAYS + 1) for e in upcoming),
        default=EARNINGS_PROXIMITY_HORIZON_DAYS + 1,
    )
    score = 1.0 - (min_days / EARNINGS_PROXIMITY_HORIZON_DAYS)
    return round(max(0.0, min(1.0, score)), 4)


def write_intel_to_redis(redis_client, intel: dict) -> None:
    """Write market intelligence to Redis for all agents to read."""
    try:
        redis_client.setex(
            "calendar:today:intel",
            86400,  # expires midnight
            json.dumps(intel),
        )
        # CSP-fix mirror: dashboard reads via direct supabase-js.
        get_client().table("trading_ai_briefs").upsert(
            {
                "brief_kind": "calendar",
                "payload": intel,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
            on_conflict="brief_kind",
        ).execute()
    except Exception as exc:
        logger.warning("calendar_redis_write_failed", error=str(exc))

    # 12H follow-up: write earnings_proximity_score for the
    # prediction engine's Phase-A feature vector. Independent
    # try/except so a Supabase or intel-write failure can't leave
    # LightGBM reading a stale score, and vice versa. Fail-open:
    # any error is logged and the Redis key is left at whatever the
    # previous run wrote (TTL 24h) — never blocks trading.
    try:
        score = _compute_earnings_proximity_score(intel)
        redis_client.setex(
            "calendar:earnings_proximity_score",
            86400,
            str(score),
        )
        logger.info("earnings_proximity_score_written", score=score)
    except Exception as exc:
        logger.warning(
            "earnings_proximity_score_write_failed",
            error=str(exc),
        )
