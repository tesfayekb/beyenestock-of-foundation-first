"""
Market calendar utility — holiday and early-close awareness.

Used by health status writers, time stops, and position monitor to
determine whether the market is currently open and when it closes.

US stock market (NYSE/CBOE) 2026 holidays and early closes. Update
this file annually or when CBOE publishes the next year's schedule.

Standalone — depends on nothing else in the trading system.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")

# 2026 Market Holidays (full close)
MARKET_HOLIDAYS_2026: frozenset[date] = frozenset([
    date(2026, 1, 1),    # New Year's Day
    date(2026, 1, 19),   # Martin Luther King Jr. Day
    date(2026, 2, 16),   # Presidents' Day
    date(2026, 4, 3),    # Good Friday
    date(2026, 5, 25),   # Memorial Day
    date(2026, 6, 19),   # Juneteenth
    date(2026, 7, 3),    # Independence Day (observed)
    date(2026, 9, 7),    # Labor Day
    date(2026, 11, 26),  # Thanksgiving Day
    date(2026, 12, 25),  # Christmas Day
])

# 2026 Early Close Days (market closes at 1:00 PM ET)
EARLY_CLOSE_2026: frozenset[date] = frozenset([
    date(2026, 7, 2),    # Day before Independence Day
    date(2026, 11, 27),  # Day after Thanksgiving (Black Friday)
    date(2026, 12, 24),  # Christmas Eve
])

# Standard market hours
MARKET_OPEN = time(9, 30, 0)
MARKET_CLOSE = time(16, 0, 0)
EARLY_CLOSE = time(13, 0, 0)

# Time stop offsets (close positions before market close)
TIME_STOP_SHORT_GAMMA_OFFSET = timedelta(minutes=90)    # 2:30 PM on normal days
TIME_STOP_ALL_POSITIONS_OFFSET = timedelta(minutes=15)  # 3:45 PM on normal days


def is_market_day(check_date: date | None = None) -> bool:
    """True if the given date is a trading day (not weekend or holiday)."""
    d = check_date or date.today()
    if d.weekday() >= 5:  # Saturday=5, Sunday=6
        return False
    if d in MARKET_HOLIDAYS_2026:
        return False
    return True


def get_market_close_time(check_date: date | None = None) -> time:
    """Return the market close time for the given date (early close aware)."""
    d = check_date or date.today()
    if d in EARLY_CLOSE_2026:
        return EARLY_CLOSE
    return MARKET_CLOSE


def is_market_open(now: datetime | None = None) -> bool:
    """
    True if the US stock market is currently open.

    `now` may be naive (interpreted as ET) or timezone-aware.
    Honors weekends, holidays, and early closes.
    """
    if now is None:
        now = datetime.now(ET)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=ET)

    now_et = now.astimezone(ET)
    today = now_et.date()

    if not is_market_day(today):
        return False

    close = get_market_close_time(today)
    current_time = now_et.time()
    return MARKET_OPEN <= current_time < close


def get_time_stop_230pm(check_date: date | None = None) -> time:
    """
    Short-gamma time stop: 90 minutes before market close.
    Normal days: 2:30 PM ET. Early close: 11:30 AM ET.
    """
    d = check_date or date.today()
    close = get_market_close_time(d)
    close_dt = datetime.combine(d, close, tzinfo=ET)
    stop_dt = close_dt - TIME_STOP_SHORT_GAMMA_OFFSET
    return stop_dt.time()


def get_time_stop_345pm(check_date: date | None = None) -> time:
    """
    All-positions time stop: 15 minutes before market close.
    Normal days: 3:45 PM ET. Early close: 12:45 PM ET.
    """
    d = check_date or date.today()
    close = get_market_close_time(d)
    close_dt = datetime.combine(d, close, tzinfo=ET)
    stop_dt = close_dt - TIME_STOP_ALL_POSITIONS_OFFSET
    return stop_dt.time()
