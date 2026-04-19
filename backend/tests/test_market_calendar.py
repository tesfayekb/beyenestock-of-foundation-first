"""Tests for backend/market_calendar.py — holiday/early-close awareness."""
from datetime import date, datetime
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")


def test_weekends_are_not_market_days():
    from market_calendar import is_market_day
    assert is_market_day(date(2026, 4, 18)) is False  # Saturday
    assert is_market_day(date(2026, 4, 19)) is False  # Sunday


def test_holidays_are_not_market_days():
    from market_calendar import is_market_day
    assert is_market_day(date(2026, 1, 1)) is False    # New Year's
    assert is_market_day(date(2026, 12, 25)) is False  # Christmas
    assert is_market_day(date(2026, 4, 3)) is False    # Good Friday


def test_regular_weekday_is_market_day():
    from market_calendar import is_market_day
    assert is_market_day(date(2026, 4, 21)) is True  # Tuesday


def test_normal_day_closes_at_4pm():
    from market_calendar import get_market_close_time
    t = get_market_close_time(date(2026, 4, 21))
    assert t.hour == 16 and t.minute == 0


def test_early_close_day_closes_at_1pm():
    from market_calendar import get_market_close_time
    t = get_market_close_time(date(2026, 7, 2))  # Day before Independence Day
    assert t.hour == 13 and t.minute == 0


def test_market_open_during_hours():
    from market_calendar import is_market_open
    now = datetime(2026, 4, 21, 10, 0, 0, tzinfo=ET)
    assert is_market_open(now) is True


def test_market_closed_before_open():
    from market_calendar import is_market_open
    now = datetime(2026, 4, 21, 9, 0, 0, tzinfo=ET)
    assert is_market_open(now) is False


def test_market_closed_after_close():
    from market_calendar import is_market_open
    now = datetime(2026, 4, 21, 16, 30, 0, tzinfo=ET)
    assert is_market_open(now) is False


def test_market_closed_on_holiday():
    from market_calendar import is_market_open
    now = datetime(2026, 1, 1, 10, 0, 0, tzinfo=ET)
    assert is_market_open(now) is False


def test_345pm_stop_is_1245_on_early_close():
    from market_calendar import get_time_stop_345pm
    t = get_time_stop_345pm(date(2026, 7, 2))
    assert t.hour == 12 and t.minute == 45


def test_345pm_stop_is_345_on_normal_day():
    from market_calendar import get_time_stop_345pm
    t = get_time_stop_345pm(date(2026, 4, 21))
    assert t.hour == 15 and t.minute == 45


def test_230pm_stop_is_1130_on_early_close():
    from market_calendar import get_time_stop_230pm
    t = get_time_stop_230pm(date(2026, 7, 2))
    assert t.hour == 11 and t.minute == 30


def test_230pm_stop_is_230_on_normal_day():
    from market_calendar import get_time_stop_230pm
    t = get_time_stop_230pm(date(2026, 4, 21))
    assert t.hour == 14 and t.minute == 30
