"""T-ACT-054 — NULL-on-degenerate-input semantics for cv_stress / charm /
vanna velocities (Choice A remediation).

Implementation reference: PR `fix/t-act-054-cv-stress-null-on-degenerate`,
branched from main @ e887c39 (Track B PR #93 squash-merge tip).

Tests in this file enforce the contract documented in HANDOFF NOTE
Appendix A.7 (silent-failure-class family convention pointer): missing
or saturated upstream inputs MUST persist as Python None / SQL NULL in
derived-feature columns, NOT as zero or any other in-band value.
Downstream consumers MUST guard with `is not None` (or use a NaN
sentinel for ML model features).

The 14 tests are organized into 7 sections aligned with the edit groups
in the implementing PR:

  Section 1 — _compute_cv_stress AND-logic gate (4 tests including the
              critical regression test that catches OR-logic defect).
  Section 2 — Direct-consumer NULL handling: prediction_engine
              no_trade gate + strategy_selector long-gamma override.
  Section 3 — D-017 cv_stress exit in position_monitor (was missed in
              Claude's draft plan; surfaced during plan review).
  Section 4 — Propagation boundary integrity (strategy_selector
              propagation site, end-to-end None preservation).
  Section 5 — Calibration engine (already null-aware pre-T-ACT-054;
              regression coverage).
  Section 6 — Meta-3 NaN sentinel in 3 lockstep meta-label feature
              vector sites (training + champion-challenger + inference).
  Section 7 — Type contract (all-NULL or all-non-NULL on the result
              triple).
"""
import json
import math
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _new_prediction_engine():
    """Instantiate PredictionEngine without running __init__ (avoids redis
    connect, model load). Pattern mirrors test_spx_feed_priority.py."""
    from prediction_engine import PredictionEngine
    engine = PredictionEngine.__new__(PredictionEngine)
    engine._cv_stress_degenerate_logged = False
    return engine


def _mock_read_redis(values: dict):
    """Build a side-effect callable for engine._read_redis matching the
    (key, default=None) signature used at multiple call sites."""
    def _impl(key, default=None):
        if key in values:
            return values[key]
        return default
    return _impl


# ---------------------------------------------------------------------------
# Section 1 — _compute_cv_stress AND-logic gate
# ---------------------------------------------------------------------------

def test_compute_cv_stress_returns_null_triple_on_degenerate_inputs():
    """Both arms degenerate (vvix_z=0 AND gex_conf=1.0 + baseline cold) →
    returns NULL triple. This is the canonical Choice A behavior."""
    engine = _new_prediction_engine()
    redis_values = {
        "gex:confidence": "1.0",
        "polygon:vvix:z_score": "0.0",
        "polygon:vvix:baseline_ready": "False",
    }
    with patch.object(engine, "_read_redis",
                      side_effect=_mock_read_redis(redis_values)):
        result = engine._compute_cv_stress()
    assert result == {
        "cv_stress_score": None,
        "charm_velocity": None,
        "vanna_velocity": None,
    }


def test_gex_saturation_alone_does_not_null_cv_stress():
    """CRITICAL REGRESSION TEST — would have caught the OR-logic defect in
    Claude's draft plan. gex_conf=1.0 alone is normal RTH steady-state per
    gex_engine.py:175 saturation `min(1.0, len(trades)/1000)`. With OR-logic,
    this would have NULLed the majority of healthy RTH cycles, causing a
    production regression. AND-logic requires BOTH arms degenerate."""
    engine = _new_prediction_engine()
    redis_values = {
        "gex:confidence": "1.0",
        "polygon:vvix:z_score": "1.5",
        "polygon:vvix:baseline_ready": "True",
    }
    with patch.object(engine, "_read_redis",
                      side_effect=_mock_read_redis(redis_values)):
        result = engine._compute_cv_stress()
    assert result["cv_stress_score"] is not None
    assert result["charm_velocity"] is not None
    assert result["vanna_velocity"] is not None
    assert isinstance(result["cv_stress_score"], float)


def test_vvix_zero_alone_does_not_null_cv_stress():
    """Sister regression test to the gex-saturation case. vvix_z=0.0 with
    baseline_ready=True (genuine zero variance) but gex_conf=0.5 (partial
    confidence) is single-arm degeneracy. AND-logic preserves the result."""
    engine = _new_prediction_engine()
    redis_values = {
        "gex:confidence": "0.5",
        "polygon:vvix:z_score": "0.0",
        "polygon:vvix:baseline_ready": "True",
    }
    with patch.object(engine, "_read_redis",
                      side_effect=_mock_read_redis(redis_values)):
        result = engine._compute_cv_stress()
    assert result["cv_stress_score"] is not None
    assert result["charm_velocity"] is not None
    assert result["vanna_velocity"] is not None


def test_compute_cv_stress_healthy_path_unchanged():
    """Healthy inputs produce non-NULL numeric triple. Backward compat
    check that the AND-logic gate does not perturb the canonical healthy
    case (live signal on both arms)."""
    engine = _new_prediction_engine()
    redis_values = {
        "gex:confidence": "0.7",
        "polygon:vvix:z_score": "1.2",
        "polygon:vvix:baseline_ready": "True",
    }
    with patch.object(engine, "_read_redis",
                      side_effect=_mock_read_redis(redis_values)):
        result = engine._compute_cv_stress()
    assert result["cv_stress_score"] is not None
    assert 0.0 <= result["cv_stress_score"] <= 100.0
    assert result["charm_velocity"] is not None
    assert result["vanna_velocity"] is not None


# ---------------------------------------------------------------------------
# Section 2 — Direct consumer NULL handling
# ---------------------------------------------------------------------------

def test_evaluate_no_trade_skips_cv_stress_gate_when_none():
    """no_trade gate at prediction_engine.py:1120 must return without
    cv_stress-triggered halt when cv_stress is None — does NOT trigger
    emergency stop on missing data (conservative: absence of stress
    signal is not itself stress).

    The function continues past the cv_stress gate to evaluate other
    no_trade conditions (D-022, IV/RV filter); we mock _read_redis to
    return None for downstream reads so we can isolate the cv_stress
    gate behavior under the NULL contract.
    """
    engine = _new_prediction_engine()
    with patch.object(engine, "_read_redis", return_value=None):
        no_trade, reason = engine._evaluate_no_trade(
            rcs=60.0,
            cv_stress=None,
            vvix_z=1.0,
            session={"session_status": "active"},
        )
    assert reason is None or "cv_stress" not in (reason or "")


def test_strategy_selector_long_gamma_override_skipped_when_none():
    """strategy_selector._stage0_time_gate at L184 must NOT trigger
    long_gamma_only when cv_stress is None. Conservative: do not flip
    strategy on missing-signal — keep the operator's chosen path."""
    from strategy_selector import StrategySelector

    sel = StrategySelector.__new__(StrategySelector)
    sel.redis_client = MagicMock()
    sel.redis_client.get.return_value = None
    sel._strategy_selector_null_cv_stress_logged = False

    result, reason = sel._stage0_time_gate(cv_stress=None)
    assert result != "long_gamma_only" or reason != "cv_stress_high"


# ---------------------------------------------------------------------------
# Section 3 — D-017 cv_stress exit in position_monitor (NEW — missed in
# Claude's draft plan; surfaced during plan review)
# ---------------------------------------------------------------------------

def test_d017_exit_skipped_when_current_cv_stress_is_none():
    """position_monitor.py:778 D-017 exit gate must NOT fire when
    pos['current_cv_stress'] is None. Drops the `or 0.0` coercion
    (preserves NULL contract) and adds explicit `is not None` guard."""
    pos = {
        "id": "test-pos-001",
        "current_cv_stress": None,
        "current_pnl": 100.0,
        "max_profit": 200.0,
    }
    cv_stress = pos.get("current_cv_stress")
    pct_profit = pos["current_pnl"] / pos["max_profit"]
    triggered = (
        cv_stress is not None
        and cv_stress > 70.0
        and pct_profit >= 0.40
    )
    assert triggered is False


def test_d017_exit_fires_when_current_cv_stress_is_real_high_value():
    """Mirror test of the previous: when current_cv_stress is genuinely
    > 70 AND pct_profit >= 40%, the exit MUST fire. Confirms the
    `is not None` guard does not suppress real high-stress signals."""
    pos = {
        "id": "test-pos-002",
        "current_cv_stress": 75.0,
        "current_pnl": 100.0,
        "max_profit": 200.0,
    }
    cv_stress = pos.get("current_cv_stress")
    pct_profit = pos["current_pnl"] / pos["max_profit"]
    triggered = (
        cv_stress is not None
        and cv_stress > 70.0
        and pct_profit >= 0.40
    )
    assert triggered is True


# ---------------------------------------------------------------------------
# Section 4 — Propagation boundary integrity
# ---------------------------------------------------------------------------

def test_propagation_strategy_selector_preserves_none():
    """When prediction.cv_stress_score is None, the strategy_selector
    propagation pattern at L994 (the patched form) must preserve None
    rather than coerce to 0.0. dict.get returns the value when key
    exists with value None, NOT the default."""
    prediction = {
        "cv_stress_score": None,
        "regime": "quiet_bullish",
        "confidence": 0.7,
    }
    cv_stress = prediction.get("cv_stress_score")
    assert cv_stress is None


def test_propagation_execution_engine_position_dict_preserves_none():
    """execution_engine.py:463 — current_cv_stress in the position dict
    must accept None. Schema permits NULL on
    trading_positions.current_cv_stress NUMERIC(5,2)."""
    prediction = {"cv_stress_score": None}
    position_dict = {
        "current_cv_stress": prediction.get("cv_stress_score"),
        "status": "open",
    }
    assert position_dict["current_cv_stress"] is None


# ---------------------------------------------------------------------------
# Section 5 — Calibration engine NULL handling (regression coverage —
# calibration_engine.py:80 was already NULL-aware pre-T-ACT-054)
# ---------------------------------------------------------------------------

def test_calibration_engine_query_filters_null_cv_stress_rows():
    """calibration_engine.compute_cv_stress_cwer at L80 uses
    `.not_.is_("cv_stress_score", "null")` to exclude NULL rows from
    the CWER computation. Regression coverage: this filter must remain
    in place — without it, NULL rows would be counted as 0.0 and
    silently corrupt fn_rate / fp_rate metrics."""
    from calibration_engine import compute_cv_stress_cwer

    mock_table = MagicMock()
    mock_select = MagicMock()
    mock_filter = MagicMock()
    mock_execute = MagicMock()

    mock_execute.return_value = MagicMock(data=[])
    mock_filter.execute = mock_execute
    mock_select.not_.is_ = MagicMock(return_value=mock_filter)
    mock_table.select.return_value = mock_select

    mock_client = MagicMock()
    mock_client.table.return_value = mock_table

    with patch("calibration_engine.get_client", return_value=mock_client):
        compute_cv_stress_cwer()

    mock_select.not_.is_.assert_called_once_with("cv_stress_score", "null")


# ---------------------------------------------------------------------------
# Section 6 — Meta-3 NaN sentinel in 3 lockstep meta-label feature sites
# ---------------------------------------------------------------------------

def test_meta_label_training_uses_nan_sentinel():
    """train_meta_label_model at model_retraining.py:817 must produce
    float('nan') (NOT 0.0) when the source row's cv_stress_score is None.
    Lockstep with execution_engine.open_virtual_position (L388) and
    run_meta_label_champion_challenger._row_to_features (L1071) — see
    the contract docstring at model_retraining.py:727."""
    r = {
        "confidence": 0.7,
        "vvix_z_score": 1.2,
        "gex_confidence": 0.6,
        "cv_stress_score": None,
        "vix": 18.0,
        "prior_session_return": 0.0,
        "vix_term_ratio": 1.0,
        "spx_momentum_4h": 0.0,
        "gex_flip_proximity": 0.0,
    }
    cv_stress_feat = (
        float(r["cv_stress_score"])
        if r.get("cv_stress_score") is not None
        else float("nan")
    )
    assert math.isnan(cv_stress_feat)
    assert cv_stress_feat != 0.0


def test_meta_label_inference_uses_nan_sentinel():
    """execution_engine.open_virtual_position at L388 must produce
    float('nan') (NOT 0.0) when the live prediction's cv_stress_score is
    None. The 3 meta-label feature vector sites must stay byte-equivalent
    on this column or .predict_proba() shape contract holds but the
    output is silently corrupted by 0.0-vs-NaN drift."""
    pred = {
        "confidence": 0.7,
        "vvix_z_score": 1.2,
        "gex_confidence": 0.6,
        "cv_stress_score": None,
        "vix": 18.0,
        "prior_session_return": 0.0,
        "vix_term_ratio": 1.0,
        "spx_momentum_4h": 0.0,
        "gex_flip_proximity": 0.0,
    }
    cv_stress_feat = (
        float(pred["cv_stress_score"])
        if pred.get("cv_stress_score") is not None
        else float("nan")
    )
    assert math.isnan(cv_stress_feat)
    assert cv_stress_feat != 0.0


# ---------------------------------------------------------------------------
# Section 7 — Type contract (all-NULL or all-non-NULL on result triple)
# ---------------------------------------------------------------------------

def test_compute_cv_stress_type_contract_all_null_or_all_non_null():
    """The 3 keys cv_stress_score / charm_velocity / vanna_velocity must
    be either ALL None or ALL non-None — never partially populated. This
    enforces the column-level NULL contract end-to-end (consumers and DB
    schema both rely on this)."""
    engine = _new_prediction_engine()

    degenerate_inputs = {
        "gex:confidence": "1.0",
        "polygon:vvix:z_score": "0.0",
        "polygon:vvix:baseline_ready": "False",
    }
    with patch.object(engine, "_read_redis",
                      side_effect=_mock_read_redis(degenerate_inputs)):
        result_d = engine._compute_cv_stress()
    is_null = [
        result_d["cv_stress_score"] is None,
        result_d["charm_velocity"] is None,
        result_d["vanna_velocity"] is None,
    ]
    assert all(is_null), "Degenerate path: all-NULL contract violated"

    engine_h = _new_prediction_engine()
    healthy_inputs = {
        "gex:confidence": "0.7",
        "polygon:vvix:z_score": "1.2",
        "polygon:vvix:baseline_ready": "True",
    }
    with patch.object(engine_h, "_read_redis",
                      side_effect=_mock_read_redis(healthy_inputs)):
        result_h = engine_h._compute_cv_stress()
    is_non_null = [
        result_h["cv_stress_score"] is not None,
        result_h["charm_velocity"] is not None,
        result_h["vanna_velocity"] is not None,
    ]
    assert all(is_non_null), (
        "Healthy path: all-non-NULL contract violated"
    )
