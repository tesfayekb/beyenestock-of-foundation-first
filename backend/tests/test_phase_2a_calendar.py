"""Tests for Phase 2A Session 1: Economic calendar."""
import os
import sys

# Make backend_agents/ importable (sibling directory to backend/)
sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "..", "backend_agents"),
)

import json
from unittest.mock import MagicMock, patch


def test_empty_intel_on_network_error():
    """Network error returns safe empty intel, never raises."""
    with patch("economic_calendar.httpx.Client") as mock_client:
        mock_client.return_value.__enter__.return_value.get.side_effect = (
            Exception("network error")
        )
        from economic_calendar import get_todays_market_intelligence
        result = get_todays_market_intelligence()
    assert result["day_classification"] == "normal"
    assert result["recommended_posture"] == "normal"
    assert result["events"] == []


def test_major_event_classification():
    """Major catalyst sets catalyst_major and straddle posture."""
    from economic_calendar import get_todays_market_intelligence
    from datetime import date
    with patch("economic_calendar._fetch_finnhub_calendar") as mock_cal:
        with patch("economic_calendar._fetch_major_earnings") as mock_earn:
            mock_earn.return_value = []
            mock_cal.return_value = [{
                "event": "Federal Funds Rate",
                "is_major": True,
                "time": "14:00:00",
                "estimate": None, "prev": None, "actual": None,
                "unit": "", "impact": "major", "country": "US",
            }]
            result = get_todays_market_intelligence()
    assert result["day_classification"] == "catalyst_major"
    assert result["recommended_posture"] == "straddle"
    assert result["has_major_catalyst"] is True


def test_minor_event_classification():
    """Minor catalyst sets catalyst_minor and reduced_size posture."""
    from economic_calendar import get_todays_market_intelligence
    with patch("economic_calendar._fetch_finnhub_calendar") as mock_cal:
        with patch("economic_calendar._fetch_major_earnings") as mock_earn:
            mock_earn.return_value = []
            mock_cal.return_value = [{
                "event": "Initial Jobless Claims",
                "is_major": False,
                "time": "08:30:00",
                "estimate": None, "prev": None, "actual": None,
                "unit": "", "impact": "minor", "country": "US",
            }]
            result = get_todays_market_intelligence()
    assert result["day_classification"] == "catalyst_minor"
    assert result["recommended_posture"] == "reduced_size"


def test_earnings_major_classification():
    """Major earnings sets earnings_major classification."""
    from economic_calendar import get_todays_market_intelligence
    with patch("economic_calendar._fetch_finnhub_calendar") as mock_cal:
        with patch("economic_calendar._fetch_major_earnings") as mock_earn:
            mock_cal.return_value = []
            mock_earn.return_value = [{
                "ticker": "NVDA", "name": "NVDA",
                "eps_estimate": 5.5, "eps_actual": None,
                "hour": "amc", "is_major": True,
            }]
            result = get_todays_market_intelligence()
    assert result["day_classification"] == "earnings_major"
    assert result["has_major_earnings"] is True


def test_normal_day_no_events():
    """No events returns normal classification."""
    from economic_calendar import get_todays_market_intelligence
    with patch("economic_calendar._fetch_finnhub_calendar") as mock_cal:
        with patch("economic_calendar._fetch_major_earnings") as mock_earn:
            mock_cal.return_value = []
            mock_earn.return_value = []
            result = get_todays_market_intelligence()
    assert result["day_classification"] == "normal"
    assert result["recommended_posture"] == "normal"


def test_write_intel_to_redis():
    """Intel dict written to Redis with correct TTL."""
    from economic_calendar import write_intel_to_redis, _empty_intel
    from datetime import date
    mock_redis = MagicMock()
    intel = _empty_intel(date.today())
    write_intel_to_redis(mock_redis, intel)
    mock_redis.setex.assert_called_once()
    args = mock_redis.setex.call_args[0]
    assert args[0] == "calendar:today:intel"
    assert args[1] == 86400
    parsed = json.loads(args[2])
    assert "day_classification" in parsed
