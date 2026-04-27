"""
Tests for T-ACT-035 databento parser rewrite.

These tests need the real databento SDK installed so that
``isinstance(mock, databento.TradeMsg)`` works via ``MagicMock(spec=...)``.
They will be skipped locally when databento isn't available and should run
in Railway / CI where the SDK is present.
"""
import json
import time
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("databento")
import databento as db  # noqa: E402


@pytest.fixture
def feed():
    """DatabentoFeed with redis + InstrumentMap replaced by MagicMocks."""
    mock_redis = MagicMock()
    # Default: SPX spot present in the cache
    mock_redis.get.return_value = json.dumps(
        {"symbol": "SPX", "last": 5200.0, "ask": 5200.0}
    )
    with patch(
        "databento_feed.redis.Redis.from_url", return_value=mock_redis
    ):
        from databento_feed import DatabentoFeed
        f = DatabentoFeed()
    f._imap = MagicMock()
    return f


def _mk_trade_mock(instrument_id=12345, pretty_price=5.25, size=10,
                   ts_event=None):
    """Build a TradeMsg mock whose isinstance() check returns True."""
    if ts_event is None:
        ts_event = int(
            datetime(2026, 4, 15, tzinfo=timezone.utc).timestamp() * 1e9
        )
    mock = MagicMock(spec=db.TradeMsg)
    mock.instrument_id = instrument_id
    mock.pretty_price = pretty_price
    mock.size = size
    mock.ts_event = ts_event
    return mock


def test_symbol_mapping_msg_feeds_instrument_map(feed):
    """SymbolMappingMsg records are routed into InstrumentMap, not Redis."""
    mock_msg = MagicMock(spec=db.SymbolMappingMsg)

    feed._dispatch_record(mock_msg)

    feed._imap.insert_symbol_mapping_msg.assert_called_once_with(mock_msg)
    feed.redis_client.rpush.assert_not_called()
    assert feed.last_valid_trade_at is None


def test_trade_msg_with_known_id_writes_full_trade(feed):
    """A resolvable TradeMsg yields a fully-populated trade dict in Redis."""
    # OCC: SPXW + 261220 (Dec 20 2026) + P + 05200000 (strike 5200.000)
    feed._imap.resolve.return_value = "SPXW  261220P05200000"

    feed._dispatch_record(_mk_trade_mock())

    feed._imap.insert_symbol_mapping_msg.assert_not_called()
    feed.redis_client.rpush.assert_called_once()

    args, _ = feed.redis_client.rpush.call_args
    assert args[0] == "databento:opra:trades"
    trade = json.loads(args[1])

    assert trade["symbol"] == "SPXW261220P05200000"
    assert trade["price"] == 5.25
    assert trade["strike"] == 5200.0
    assert trade["option_type"] == "P"
    assert trade["volume"] == 10
    assert trade["expiry_date"] == "2026-12-20"
    assert trade["underlying_price"] == 5200.0
    assert feed.last_valid_trade_at is not None


def test_trade_msg_with_unknown_id_skipped(feed):
    """Unresolvable instrument_id drops the trade — no zero-record pollution."""
    feed._imap.resolve.return_value = None  # not yet mapped

    feed._dispatch_record(_mk_trade_mock(instrument_id=99999))

    feed.redis_client.rpush.assert_not_called()
    assert feed.last_valid_trade_at is None


def test_system_and_error_msgs_ignored(feed):
    """SystemMsg and ErrorMsg are silently ignored (not logged as errors)."""
    for cls in (db.SystemMsg, db.ErrorMsg):
        mock_msg = MagicMock(spec=cls)
        feed._dispatch_record(mock_msg)

    feed._imap.insert_symbol_mapping_msg.assert_not_called()
    feed.redis_client.rpush.assert_not_called()
    assert feed.last_valid_trade_at is None


def test_unparseable_occ_symbol_drops_without_raising(feed):
    """A resolved-but-non-OCC symbol is dropped cleanly (no exception)."""
    feed._imap.resolve.return_value = "NOT_OCC_FORMAT"

    # Must not raise, must not push
    feed._dispatch_record(_mk_trade_mock())

    feed.redis_client.rpush.assert_not_called()
    assert feed.last_valid_trade_at is None


def _stateful_redis_list_mock():
    """
    Minimal stateful mock of redis LIST semantics (rpush / ltrim / llen /
    lrange) for the indices this test exercises. Negative-index handling
    matches real Redis: bounds are inclusive and -1 means the last element.

    Scoped to this single test — other tests in this file continue to use
    the existing module-level MagicMock fixture.
    """
    storage = []
    mock = MagicMock()

    def _rpush(_key, value):
        storage.append(value)
        return len(storage)

    def _normalize(idx, n):
        return n + idx if idx < 0 else idx

    def _ltrim(_key, start, stop):
        n = len(storage)
        s = max(0, _normalize(start, n))
        e = min(n - 1, _normalize(stop, n))
        storage[:] = storage[s:e + 1] if s <= e else []

    def _llen(_key):
        return len(storage)

    def _lrange(_key, start, stop):
        n = len(storage)
        s = max(0, _normalize(start, n))
        e = min(n - 1, _normalize(stop, n))
        return list(storage[s:e + 1]) if s <= e else []

    mock.rpush.side_effect = _rpush
    mock.ltrim.side_effect = _ltrim
    mock.llen.side_effect = _llen
    mock.lrange.side_effect = _lrange
    return mock


def test_push_trade_bounds_list_to_10000(feed):
    """
    LTRIM bounds the trades list to 10000 elements; the most-recent push
    is preserved (LTRIM trims from the LEFT). EXPIRE must not be called —
    regression guard against re-introducing the broken per-push TTL reset
    that previously let the list grow unbounded.
    """
    stateful = _stateful_redis_list_mock()
    feed.redis_client = stateful

    for i in range(12000):
        feed._push_trade({"marker": f"trade-{i}", "price": 1.0})

    assert stateful.llen("databento:opra:trades") == 10000

    last = stateful.lrange("databento:opra:trades", -1, -1)
    assert len(last) == 1
    assert json.loads(last[0])["marker"] == "trade-11999"

    # Regression guard: the broken EXPIRE pattern must not coexist with LTRIM.
    stateful.expire.assert_not_called()
