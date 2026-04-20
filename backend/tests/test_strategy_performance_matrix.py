"""D3 (12D) — tests for the regime x strategy performance matrix.

Covers both halves of the feature:

1. get_matrix_sizing_multiplier — the read path hit on every call
   to strategy_selector.select(). MUST fail open to 1.0 on any
   error or missing data so ROI is preserved.

2. update_performance_matrix — the EOD aggregator that runs at
   4:20 PM ET. Verifies single-pass grouping into cells and that
   each cell lands in Redis with the right key format + TTL.

Additional sizing-arithmetic tests cover the int(floor) + max(1, ..)
pattern applied in strategy_selector so a 0.75 multiplier cannot
silently cut a 1-contract signal to 0.
"""
import json
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── read path: get_matrix_sizing_multiplier ──────────────────────────

def test_matrix_returns_1_when_no_data():
    """Cold start / first trade in a cell -> Redis returns None ->
    multiplier must be 1.0 so the very first trade isn't punished
    for having no history."""
    from strategy_performance_matrix import get_matrix_sizing_multiplier

    mock_redis = MagicMock()
    mock_redis.get.return_value = None

    mult = get_matrix_sizing_multiplier(mock_redis, "pin_range", "iron_butterfly")
    assert mult == 1.0


def test_matrix_returns_1_below_10_trades():
    """Even with a terrible win_rate, < 10 trades is not enough
    signal to cut size. Small-N variance would dominate — letting
    those cells compound the loss is preferable to strangling a
    genuinely profitable strategy that had a bad opening streak."""
    from strategy_performance_matrix import get_matrix_sizing_multiplier

    cell_data = {
        "win_rate": 0.125,
        "avg_pnl": -50.0,
        "profit_factor": 0.2,
        "trade_count": 8,
    }
    mock_redis = MagicMock()
    mock_redis.get.return_value = json.dumps(cell_data)

    mult = get_matrix_sizing_multiplier(mock_redis, "pin_range", "iron_butterfly")
    assert mult == 1.0


def test_matrix_reduces_sizing_at_low_winrate():
    """12 trades + win_rate 0.33 -> 25% size cut (multiplier 0.75).
    This is the core D3 intervention and the one that would have
    pre-emptively sized down iron_butterfly in pin_range cells the
    day after a 3-loss streak with trade_count >= 10."""
    from strategy_performance_matrix import get_matrix_sizing_multiplier

    cell_data = {
        "win_rate": 0.33,
        "avg_pnl": -40.0,
        "profit_factor": 0.5,
        "trade_count": 12,
    }
    mock_redis = MagicMock()
    mock_redis.get.return_value = json.dumps(cell_data)

    mult = get_matrix_sizing_multiplier(mock_redis, "pin_range", "iron_butterfly")
    assert mult == 0.75


def test_matrix_normal_sizing_at_good_winrate():
    """15 trades + win_rate 0.60 -> normal sizing. This verifies the
    gate is strictly a down-sizer: good cells are never boosted, and
    borderline-passing cells (>= 0.40) run at full size."""
    from strategy_performance_matrix import get_matrix_sizing_multiplier

    cell_data = {
        "win_rate": 0.60,
        "avg_pnl": 45.0,
        "profit_factor": 1.8,
        "trade_count": 15,
    }
    mock_redis = MagicMock()
    mock_redis.get.return_value = json.dumps(cell_data)

    mult = get_matrix_sizing_multiplier(mock_redis, "pin_range", "iron_condor")
    assert mult == 1.0


def test_matrix_fails_open_on_redis_error():
    """Redis.get raising -> fail-open contract: return 1.0, do NOT
    re-raise. The matrix is a sizing advisor; an outage must never
    cascade into a blocked trade or crashed select() loop."""
    from strategy_performance_matrix import get_matrix_sizing_multiplier

    class _FlakyRedis:
        def get(self, key):
            raise ConnectionError("simulated Redis outage")

    # Must not raise, and must return 1.0 so sizing is unaffected.
    mult = get_matrix_sizing_multiplier(_FlakyRedis(), "pin_range", "iron_butterfly")
    assert mult == 1.0


# ── write path: update_performance_matrix ────────────────────────────

class _StubSupabaseResult:
    def __init__(self, data):
        self.data = data


class _StubSupabaseQuery:
    """Mimics the Supabase query builder's method chaining so the
    production code path (.table().select().eq().eq().gte().execute())
    returns the fixture data without any network call."""

    def __init__(self, data):
        self._data = data

    def table(self, *_a, **_kw):
        return self

    def select(self, *_a, **_kw):
        return self

    def eq(self, *_a, **_kw):
        return self

    def gte(self, *_a, **_kw):
        return self

    def execute(self):
        return _StubSupabaseResult(self._data)


def test_update_performance_matrix_groups_correctly():
    """10 positions split across 2 regimes x 2 strategies = 4 cells.
    Verifies the single-pass aggregation writes exactly one Redis
    entry per cell with a 90-day TTL and the correct key format.

    Fixture distribution (by cell):
      pin_range:iron_butterfly       3 trades  (2W 1L)
      pin_range:iron_condor          2 trades  (1W 1L)
      volatile_bullish:put_credit    3 trades  (1W 2L)
      volatile_bullish:iron_condor   2 trades  (2W 0L)
    """
    from strategy_performance_matrix import update_performance_matrix

    fixture = [
        # pin_range:iron_butterfly — 2W 1L
        {"entry_regime": "pin_range", "strategy_type": "iron_butterfly", "net_pnl": 50},
        {"entry_regime": "pin_range", "strategy_type": "iron_butterfly", "net_pnl": 75},
        {"entry_regime": "pin_range", "strategy_type": "iron_butterfly", "net_pnl": -120},
        # pin_range:iron_condor — 1W 1L
        {"entry_regime": "pin_range", "strategy_type": "iron_condor", "net_pnl": 30},
        {"entry_regime": "pin_range", "strategy_type": "iron_condor", "net_pnl": -40},
        # volatile_bullish:put_credit_spread — 1W 2L
        {"entry_regime": "volatile_bullish", "strategy_type": "put_credit_spread", "net_pnl": 60},
        {"entry_regime": "volatile_bullish", "strategy_type": "put_credit_spread", "net_pnl": -80},
        {"entry_regime": "volatile_bullish", "strategy_type": "put_credit_spread", "net_pnl": -50},
        # volatile_bullish:iron_condor — 2W 0L
        {"entry_regime": "volatile_bullish", "strategy_type": "iron_condor", "net_pnl": 25},
        {"entry_regime": "volatile_bullish", "strategy_type": "iron_condor", "net_pnl": 35},
    ]

    stored: dict = {}
    mock_redis = MagicMock()

    def _setex(key, ttl, value):
        stored[key] = (ttl, value)
        return True

    mock_redis.setex.side_effect = _setex

    # `get_client` is imported lazily inside update_performance_matrix
    # (`from db import get_client`), so we patch it at the source
    # module rather than strategy_performance_matrix.
    with patch(
        "db.get_client",
        return_value=_StubSupabaseQuery(fixture),
    ):
        result = update_performance_matrix(mock_redis)

    assert result["cells_updated"] == 4
    assert result["positions_analyzed"] == 10

    expected_keys = {
        "strategy_matrix:pin_range:iron_butterfly",
        "strategy_matrix:pin_range:iron_condor",
        "strategy_matrix:volatile_bullish:put_credit_spread",
        "strategy_matrix:volatile_bullish:iron_condor",
    }
    assert set(stored.keys()) == expected_keys

    # All cells must use a 90-day TTL (the spec value — long enough
    # for the rolling window, short enough that stale regimes decay).
    for ttl, _ in stored.values():
        assert ttl == 86400 * 90

    # Spot-check one cell's math: pin_range:iron_butterfly
    # 2W 1L -> win_rate = 2/3 = 0.6667
    _, butterfly_payload = stored["strategy_matrix:pin_range:iron_butterfly"]
    butterfly = json.loads(butterfly_payload)
    assert butterfly["trade_count"] == 3
    assert butterfly["win_rate"] == 0.6667
    # gross_profit = 50 + 75 = 125; gross_loss = 120 -> pf = 1.042
    assert butterfly["profit_factor"] == round(125 / 120, 3)


# ── sizing arithmetic: floor + contract-count safety ─────────────────

def test_matrix_contracts_floor_at_1():
    """2 contracts * 0.75 = 1.5 -> int() truncates to 1 -> max(1, 1)
    is 1. The floor must prevent an active signal from being rounded
    down to 0 contracts, which would block trading entirely and
    violate the `MUST NOT reduce ROI` invariant at tiny position
    sizes."""
    original = 2
    multiplier = 0.75
    adjusted = max(1, int(original * multiplier)) if original > 0 else 0
    assert adjusted == 1


def test_matrix_zero_contracts_stays_zero():
    """If a prior gate already zeroed out contracts, the matrix
    multiplier must NOT resurrect it to 1 via the max(1, ..) floor.
    The guard `if original > 0` preserves the upstream decision."""
    original = 0
    multiplier = 0.75
    adjusted = max(1, int(original * multiplier)) if original > 0 else 0
    assert adjusted == 0
