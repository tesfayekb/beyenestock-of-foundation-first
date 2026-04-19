"""Tests for Signal-A (VIX term), Signal-B (time gate), Signal-C (GEX bias)."""
from unittest.mock import MagicMock, patch
from datetime import datetime
from zoneinfo import ZoneInfo


def _make_selector(flags: dict):
    """Build a StrategySelector with mocked Redis flag returns.

    Default for any unset key is b"true" (so signal flags read as ON
    unless the test explicitly sets them to "false"). Strings are
    encoded to bytes to match decode_responses=False clients; the
    selector's _check_feature_flag accepts both forms.
    """
    from strategy_selector import StrategySelector
    sel = StrategySelector.__new__(StrategySelector)
    sel.redis_client = MagicMock()
    sel.redis_client.get.side_effect = lambda k: (
        flags.get(k, b"true").encode()
        if isinstance(flags.get(k, b"true"), str)
        else flags.get(k, b"true")
    )
    return sel


# ── Signal-A: VIX term structure ─────────────────────────────────────────────

def test_vix_term_normal_returns_1():
    sel = _make_selector({"signal:vix_term_filter:enabled": "true"})
    mult, status = sel._vix_term_modifier({"vix_term_ratio": 1.05})
    assert mult == 1.0
    assert status == "normal"


def test_vix_term_inverted_soft_reduces_25():
    sel = _make_selector({"signal:vix_term_filter:enabled": "true"})
    mult, status = sel._vix_term_modifier({"vix_term_ratio": 1.15})
    assert mult == 0.75
    assert status == "inverted"


def test_vix_term_inverted_hard_reduces_50():
    sel = _make_selector({"signal:vix_term_filter:enabled": "true"})
    mult, status = sel._vix_term_modifier({"vix_term_ratio": 1.25})
    assert mult == 0.50
    assert status == "strongly_inverted"


def test_vix_term_skip_returns_zero():
    sel = _make_selector({"signal:vix_term_filter:enabled": "true"})
    mult, status = sel._vix_term_modifier({"vix_term_ratio": 1.40})
    assert mult == 0.0
    assert "skip" in status


def test_vix_term_flag_off_returns_1():
    """When flag is off, modifier must return 1.0 regardless of ratio."""
    sel = _make_selector({"signal:vix_term_filter:enabled": "false"})
    mult, status = sel._vix_term_modifier({"vix_term_ratio": 1.50})
    assert mult == 1.0
    assert status == "flag_off"


def test_vix_term_missing_ratio_returns_normal():
    """Missing vix_term_ratio falls back to Redis (mock returns invalid)
    → final fallback is 1.0 = normal."""
    sel = _make_selector({"signal:vix_term_filter:enabled": "true"})
    mult, status = sel._vix_term_modifier({})
    assert mult == 1.0


# ── Signal-C: GEX directional bias ───────────────────────────────────────────

def test_gex_neutral_returns_1():
    sel = _make_selector({"signal:gex_directional_bias:enabled": "true"})
    mult, status = sel._gex_bias_modifier(
        {"gex_net": 100_000_000}, "iron_condor"
    )
    assert mult == 1.0
    assert status == "neutral"


def test_gex_strong_mean_revert_boosts():
    sel = _make_selector({"signal:gex_directional_bias:enabled": "true"})
    mult, status = sel._gex_bias_modifier(
        {"gex_net": 2_000_000_000}, "iron_condor"
    )
    assert mult == 1.10
    assert status == "strong_mean_reversion"


def test_gex_soft_trending_reduces_25():
    sel = _make_selector({"signal:gex_directional_bias:enabled": "true"})
    mult, status = sel._gex_bias_modifier(
        {"gex_net": -700_000_000}, "iron_condor"
    )
    assert mult == 0.75
    assert status == "trending"


def test_gex_hard_trending_reduces_50():
    sel = _make_selector({"signal:gex_directional_bias:enabled": "true"})
    mult, status = sel._gex_bias_modifier(
        {"gex_net": -1_500_000_000}, "iron_condor"
    )
    assert mult == 0.50
    assert status == "strongly_trending"


def test_gex_not_applicable_for_long_strategies():
    """GEX bias must not reduce long straddles — they benefit from trending."""
    sel = _make_selector({"signal:gex_directional_bias:enabled": "true"})
    mult, status = sel._gex_bias_modifier(
        {"gex_net": -2_000_000_000}, "long_straddle"
    )
    assert mult == 1.0
    assert status == "not_applicable"


def test_gex_flag_off_returns_1():
    sel = _make_selector({"signal:gex_directional_bias:enabled": "false"})
    mult, status = sel._gex_bias_modifier(
        {"gex_net": -2_000_000_000}, "iron_condor"
    )
    assert mult == 1.0
    assert status == "flag_off"


# ── Signal-B: time gate floor ────────────────────────────────────────────────

def test_time_gate_blocks_before_945_when_flag_on():
    """9:40 AM should be blocked when signal:entry_time_gate:enabled."""
    sel = _make_selector({"signal:entry_time_gate:enabled": "true"})
    with patch("strategy_selector.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(
            2026, 4, 21, 9, 40,
            tzinfo=ZoneInfo("America/New_York"),
        )
        result, reason = sel._check_time_window(cv_stress=0)
    assert result is False
    assert "940" in reason or "945" in reason or "before" in reason


def test_time_gate_allows_945_when_flag_on():
    """9:45 AM should be allowed when signal:entry_time_gate:enabled."""
    sel = _make_selector({"signal:entry_time_gate:enabled": "true"})
    with patch("strategy_selector.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(
            2026, 4, 21, 9, 45,
            tzinfo=ZoneInfo("America/New_York"),
        )
        result, reason = sel._check_time_window(cv_stress=0)
    assert result is True


def test_time_gate_allows_940_when_flag_off():
    """9:40 AM should be allowed when signal:entry_time_gate:enabled=false
    (falls back to old 9:35 AM floor)."""
    sel = _make_selector({"signal:entry_time_gate:enabled": "false"})
    with patch("strategy_selector.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(
            2026, 4, 21, 9, 40,
            tzinfo=ZoneInfo("America/New_York"),
        )
        result, reason = sel._check_time_window(cv_stress=0)
    assert result is True
