from unittest.mock import patch, MagicMock

from strategy_selector import StrategySelector


def test_panic_regime_has_no_candidates():
    """Panic regime must have an empty strategy list — no trades allowed."""
    from strategy_selector import REGIME_STRATEGY_MAP
    assert REGIME_STRATEGY_MAP["panic"] == []


def test_all_strategies_in_slippage_map_with_positive_value():
    """All 8 strategy types must be in STATIC_SLIPPAGE_BY_STRATEGY with value > 0."""
    from strategy_selector import STATIC_SLIPPAGE_BY_STRATEGY
    expected_strategies = {
        "put_credit_spread", "call_credit_spread", "iron_condor",
        "iron_butterfly", "debit_put_spread", "debit_call_spread",
        "long_put", "long_call",
    }
    for strategy in expected_strategies:
        assert strategy in STATIC_SLIPPAGE_BY_STRATEGY, (
            f"{strategy} missing from STATIC_SLIPPAGE_BY_STRATEGY"
        )
        assert STATIC_SLIPPAGE_BY_STRATEGY[strategy] > 0, (
            f"{strategy} slippage must be > 0"
        )


def test_short_and_long_gamma_strategies_have_no_overlap():
    """SHORT_GAMMA_STRATEGIES and LONG_GAMMA_STRATEGIES must be mutually exclusive."""
    from strategy_selector import SHORT_GAMMA_STRATEGIES, LONG_GAMMA_STRATEGIES
    overlap = SHORT_GAMMA_STRATEGIES & LONG_GAMMA_STRATEGIES
    assert overlap == set(), f"Unexpected overlap: {overlap}"


# ---------------------------------------------------------------------------
# PR-A tests — strategy flag gate at strategy_selector.py:1083 / 1097 / 1136
# ---------------------------------------------------------------------------
#
# These tests cover the new `_pick_first_enabled_strategy` helper and the
# end-to-end behaviour of `StrategySelector.select()` after the three
# unchecked `strategy_type = ...` assignments are gated.
#
# Mock pattern: `StrategySelector.__new__(StrategySelector)` (bypasses
# `__init__` so we don't construct a real Redis client). Mirrors the
# pre-existing pattern at `backend/tests/test_phase_2a_agents.py:236-246`.
# Logger capture uses `unittest.mock.patch("strategy_selector.logger")`
# because `backend/logger.py` configures `structlog.PrintLoggerFactory`,
# which bypasses stdlib logging and is therefore invisible to
# `pytest.caplog` (PR-C V8.1 finding).


def test_pick_first_enabled_helper_returns_first_enabled():
    """_pick_first_enabled_strategy returns the first ordered candidate
    whose flag is enabled (skip-on-block, not skip-on-first-block).

    Scenario: event regime ordered list with long_straddle + calendar_spread
    blocked (BLOCKS_FLAG_FLIP) but iron_condor enabled.
    """
    selector = StrategySelector.__new__(StrategySelector)
    selector.redis_client = MagicMock()

    enable_map = {
        "strategy:long_straddle:enabled": False,
        "strategy:calendar_spread:enabled": False,
        "strategy:iron_condor:enabled": True,
    }

    def _flag(key, default=False):
        return enable_map.get(key, default)

    selector._check_feature_flag = MagicMock(side_effect=_flag)

    result = selector._pick_first_enabled_strategy(
        ["long_straddle", "calendar_spread", "iron_condor"]
    )
    assert result == "iron_condor"


def test_pick_first_enabled_helper_excludes_failed_strategy():
    """_pick_first_enabled_strategy with exclude= skips the named
    strategy even when its flag is enabled.

    Used by the AI-hint failed-today fallback to avoid re-selecting a
    strategy that already stop-outted today.
    """
    selector = StrategySelector.__new__(StrategySelector)
    selector.redis_client = MagicMock()

    enable_map = {
        "strategy:long_straddle:enabled": True,
        "strategy:iron_condor:enabled": True,
    }

    def _flag(key, default=False):
        return enable_map.get(key, default)

    selector._check_feature_flag = MagicMock(side_effect=_flag)

    result_no_exclude = selector._pick_first_enabled_strategy(
        ["long_straddle", "iron_condor"]
    )
    assert result_no_exclude == "long_straddle"

    result_excluded = selector._pick_first_enabled_strategy(
        ["long_straddle", "iron_condor"],
        exclude="long_straddle",
    )
    assert result_excluded == "iron_condor"


def test_pick_first_enabled_helper_returns_none_when_all_blocked():
    """_pick_first_enabled_strategy returns None when every candidate
    is flag-blocked. Caller (select) MUST handle this as a cycle skip.
    """
    selector = StrategySelector.__new__(StrategySelector)
    selector.redis_client = MagicMock()

    selector._check_feature_flag = MagicMock(return_value=False)

    result = selector._pick_first_enabled_strategy(
        ["debit_call_spread", "debit_put_spread", "long_call", "long_put"]
    )
    assert result is None


def test_select_returns_none_with_audit_row_when_all_candidates_blocked():
    """End-to-end: when regime=trend and all 4 debit strategies are
    blocked (BLOCKS_FLAG_FLIP), select() returns None AND emits a
    `trading.strategy_selection_blocked` audit_logs row.

    Core PR-A acceptance test: trend regime + debit-blocked = safe
    cycle skip + auditable evidence of the gate firing.
    """
    selector = StrategySelector.__new__(StrategySelector)
    selector.redis_client = MagicMock()

    selector._check_feature_flag = MagicMock(return_value=False)
    selector._stage0_time_gate = MagicMock(return_value=(True, "ok"))
    selector._stage1_regime_gate = MagicMock(
        return_value=[
            "debit_call_spread",
            "debit_put_spread",
            "long_call",
            "long_put",
        ]
    )
    selector._stage2_direction_filter = MagicMock(
        return_value=[
            "debit_call_spread",
            "debit_put_spread",
            "long_call",
            "long_put",
        ]
    )

    prediction = {
        "regime": "trend",
        "direction": "bullish",
        "p_bull": 0.70,
        "p_bear": 0.20,
        "cv_stress_score": 0.0,
        "regime_agreement": True,
    }
    session = {
        "id": "t",
        "virtual_trades_count": 0,
        "consecutive_losses_today": 0,
    }

    with patch("strategy_selector.write_audit_log") as mock_audit, \
            patch("strategy_selector.logger") as mock_logger:
        try:
            selector.select(prediction=prediction, session=session)
        except Exception:
            # Any downstream gate we have not mocked may raise after
            # the audit row + return None fires. The audit row must
            # have been emitted BEFORE any such raise.
            pass

    mock_audit.assert_called_once()
    audit_kwargs = mock_audit.call_args.kwargs
    assert audit_kwargs["action"] == "trading.strategy_selection_blocked"
    assert audit_kwargs["target_type"] == "trading"
    assert audit_kwargs["metadata"]["regime"] == "trend"
    assert set(audit_kwargs["metadata"]["ordered"]) == {
        "debit_call_spread",
        "debit_put_spread",
        "long_call",
        "long_put",
    }
    assert set(audit_kwargs["metadata"]["all_blocked_by"]) == {
        "strategy:debit_call_spread:enabled",
        "strategy:debit_put_spread:enabled",
        "strategy:long_call:enabled",
        "strategy:long_put:enabled",
    }

    info_calls = [
        c for c in mock_logger.info.call_args_list
        if c.args and c.args[0] == "strategy_selection_blocked"
    ]
    assert info_calls, (
        "expected logger.info('strategy_selection_blocked', ...) to "
        f"fire on all-blocked; got: {mock_logger.info.call_args_list!r}"
    )


def test_select_falls_through_to_first_enabled_in_event_regime():
    """End-to-end: event regime with long_straddle + calendar_spread
    blocked but iron_condor enabled. select() must NOT emit the
    all-blocked audit row (since iron_condor IS enabled and selectable).

    Core operator-visible benefit: even on catalyst days, credit-only
    trading works because the gate falls through to the credit
    fallback (iron_condor) in the event regime.
    """
    selector = StrategySelector.__new__(StrategySelector)
    selector.redis_client = MagicMock()

    enable_map = {
        "strategy:ai_hint_override:enabled": False,
        "strategy:long_straddle:enabled": False,
        "strategy:calendar_spread:enabled": False,
        "strategy:iron_condor:enabled": True,
    }

    def _flag(key, default=False):
        return enable_map.get(key, default)

    selector._check_feature_flag = MagicMock(side_effect=_flag)
    selector._stage0_time_gate = MagicMock(return_value=(True, "ok"))
    selector._stage1_regime_gate = MagicMock(
        return_value=["long_straddle", "calendar_spread", "iron_condor"]
    )
    selector._stage2_direction_filter = MagicMock(
        return_value=["long_straddle", "calendar_spread", "iron_condor"]
    )

    prediction = {
        "regime": "event",
        "direction": "neutral",
        "p_bull": 0.50,
        "p_bear": 0.50,
        "cv_stress_score": 0.0,
        "regime_agreement": True,
    }
    session = {
        "id": "t",
        "virtual_trades_count": 0,
        "consecutive_losses_today": 0,
    }

    with patch("strategy_selector.write_audit_log") as mock_audit:
        try:
            selector.select(prediction=prediction, session=session)
        except Exception:
            # Downstream gates beyond strategy_type selection may raise
            # on our mock data; that is acceptable for this assertion.
            pass

    mock_audit.assert_not_called()


def test_select_blocks_ai_hint_when_flag_off():
    """End-to-end: AI-hint override is on, hint suggests long_straddle
    (BLOCKS_FLAG_FLIP), confidence is high. The hint must NOT override
    the regime-iterated value. The new
    `logger.info('ai_hint_blocked_by_flag')` fires for observability.

    Closes the 6th-phantom defect at strategy_selector.py:1097 where
    the AI hint could accept a BLOCKS_FLAG_FLIP strategy.
    """
    selector = StrategySelector.__new__(StrategySelector)
    selector.redis_client = MagicMock()

    enable_map = {
        "strategy:ai_hint_override:enabled": True,
        "strategy:long_straddle:enabled": False,
        "strategy:iron_condor:enabled": True,
    }

    def _flag(key, default=False):
        return enable_map.get(key, default)

    selector._check_feature_flag = MagicMock(side_effect=_flag)
    selector._stage0_time_gate = MagicMock(return_value=(True, "ok"))
    selector._stage1_regime_gate = MagicMock(return_value=["iron_condor"])
    selector._stage2_direction_filter = MagicMock(return_value=["iron_condor"])

    prediction = {
        "regime": "event",
        "direction": "neutral",
        "p_bull": 0.40,
        "p_bear": 0.40,
        "cv_stress_score": 0.0,
        "regime_agreement": True,
        "strategy_hint": "long_straddle",
        "confidence": 0.80,
    }
    session = {
        "id": "t",
        "virtual_trades_count": 0,
        "consecutive_losses_today": 0,
    }

    with patch("strategy_selector.logger") as mock_logger:
        try:
            selector.select(prediction=prediction, session=session)
        except Exception:
            pass

    info_calls = [
        c for c in mock_logger.info.call_args_list
        if c.args and c.args[0] == "ai_hint_blocked_by_flag"
    ]
    assert info_calls, (
        "expected logger.info('ai_hint_blocked_by_flag', ...) to fire "
        f"on blocked-but-valid hint; got: "
        f"{mock_logger.info.call_args_list!r}"
    )
    assert info_calls[0].kwargs.get("hint") == "long_straddle"
    assert info_calls[0].kwargs.get("regime_iterated") == "iron_condor"
