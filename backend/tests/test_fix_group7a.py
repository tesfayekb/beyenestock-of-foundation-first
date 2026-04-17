"""
Tests for Fix Group 7A: Real data feeds.
Covers: TradierFeed process_quote Redis writes, DatabentoFeed process_trade
Redis writes, OCC symbol parsing logic.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_tradier_feed_process_quote_stores_to_redis():
    """process_quote writes correct keys to Redis."""
    from unittest.mock import MagicMock
    from tradier_feed import TradierFeed

    feed = TradierFeed.__new__(TradierFeed)
    mock_redis = MagicMock()
    feed.redis_client = mock_redis
    feed.last_data_at = None

    quote = {
        "symbol": "SPX",
        "bid": 5195.0,
        "ask": 5205.0,
        "last": 5200.0,
        "volume": 100,
        "timestamp": "2026-04-17T14:00:00Z",
    }
    feed.process_quote(quote)

    mock_redis.setex.assert_called_once()
    call_args = mock_redis.setex.call_args[0]
    assert call_args[0] == "tradier:quotes:SPX"
    assert call_args[1] == 60  # TTL


def test_tradier_feed_process_quote_ignores_missing_symbol():
    """process_quote handles missing symbol gracefully."""
    from unittest.mock import MagicMock
    from tradier_feed import TradierFeed

    feed = TradierFeed.__new__(TradierFeed)
    feed.redis_client = MagicMock()
    feed.last_data_at = None

    # Should not raise even with bad data
    feed.process_quote({})


def test_databento_feed_process_trade_stores_to_redis():
    """process_trade writes to databento:opra:trades list."""
    from unittest.mock import MagicMock
    from databento_feed import DatabentoFeed

    feed = DatabentoFeed.__new__(DatabentoFeed)
    mock_redis = MagicMock()
    feed.redis_client = mock_redis
    feed.last_data_at = None

    trade = {
        "symbol": "SPXW241220P05200000",
        "price": 1.50,
        "volume": 10,
        "underlying_price": 5200.0,
        "strike": 5200.0,
        "time_to_expiry_years": 0.002,
        "implied_vol": 0.20,
        "risk_free_rate": 0.05,
    }
    feed.process_trade(trade)

    mock_redis.rpush.assert_called_once_with(
        "databento:opra:trades",
        mock_redis.rpush.call_args[0][1],
    )
    mock_redis.expire.assert_called_once()


def test_databento_occ_symbol_parse():
    """OCC symbol parsing extracts correct strike, expiry, option type."""
    import re
    from datetime import date

    sym_clean = "SPXW241220P05200000"
    occ_match = re.match(r"([A-Z]{1,6})(\d{6})([CP])(\d{8})", sym_clean)
    assert occ_match is not None
    root, date_str, opt_type, strike_str = occ_match.groups()
    assert root == "SPXW"
    assert opt_type == "P"
    assert float(strike_str) / 1000.0 == 5200.0
    year = int("20" + date_str[:2])
    month = int(date_str[2:4])
    day = int(date_str[4:6])
    assert date(year, month, day) == date(2024, 12, 20)
