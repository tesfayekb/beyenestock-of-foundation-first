"""
Section 13 Batch 1 — ROI fixes tests.

Covers all five changes shipped in the batch:

  1. `_RISK_PCT` phase ladder distinct + phase 1 unchanged.
  2. Polygon EOD gate moved from 19:00 → 21:00 UTC (VIX + SPX
     kept in lockstep so the IV/RV comparison is close-to-close).
  3. `calendar:earnings_proximity_score` writer — linear decay from
     1.0 (today) to 0.0 (>= 5 days away), fail-open.
  4. `signal_weak` dropped from the 9-feature meta-label vector in
     all three sites (train, champion-challenger, execution_engine).
  5. Redis-authoritative feature-flag kill-switches for the
     counterfactual labeler and the meta-label inference block.

None of these changes reduce ROI: all are fail-open, the phase 1
sizing row (0.005 / 0.0025) is locked by test 2, and the two new
feature-flag defaults preserve today's behaviour.
"""

import ast
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "backend_agents")
    ),
)


# ── Change 1: _RISK_PCT phase ladder ─────────────────────────────────

def test_risk_pct_phase_ladder_distinct():
    """Phases 1, 2, 3 must all use different core/satellite pairs.

    Prior to Section 13 Batch 1 phase 2 was identical to phase 1 and
    phase 4 to phase 3, which made the E1/E2 auto-advance effectively
    a no-op for position sizing. This test locks the three tiers
    apart so a future refactor can't silently collapse them again.
    """
    from risk_engine import _RISK_PCT

    assert _RISK_PCT[1]["core"] != _RISK_PCT[2]["core"], (
        "phase 2 must not equal phase 1"
    )
    assert _RISK_PCT[2]["core"] != _RISK_PCT[3]["core"], (
        "phase 3 must not equal phase 2"
    )
    assert _RISK_PCT[1]["satellite"] != _RISK_PCT[2]["satellite"]
    assert _RISK_PCT[2]["satellite"] != _RISK_PCT[3]["satellite"]


def test_risk_pct_phase1_unchanged():
    """Phase 1 is the active paper-trading tier — must stay at the
    original 0.5% core / 0.25% satellite so Batch 1 is ROI-neutral
    for everyone who hasn't passed the E1 gate yet."""
    from risk_engine import _RISK_PCT

    assert _RISK_PCT[1]["core"] == 0.005
    assert _RISK_PCT[1]["satellite"] == 0.0025


# ── Change 2: EOD gate 19 → 21 UTC ───────────────────────────────────

def test_eod_gate_is_21_utc():
    """Both the VIX daily history and SPX daily return appenders must
    fire at 21:00 UTC (after the 16:00 ET cash close), not 19:00
    UTC (mid-afternoon).

    Read the source rather than executing PolygonFeed so the test
    doesn't need a Redis server and catches regressions in either of
    the two coupled sites in one shot.
    """
    src = Path(__file__).resolve().parent.parent / "polygon_feed.py"
    code = src.read_text(encoding="utf-8")

    # Count non-comment instances of each literal pattern. Comments
    # reference the historical 19:00 UTC gate and must not count.
    executable_lines = [
        ln for ln in code.splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    exec_body = "\n".join(executable_lines)

    assert "now.hour >= 19" not in exec_body, (
        "polygon_feed.py still contains an executable `now.hour >= 19` "
        "gate — must be 21:00 UTC to line up with the 16:00 ET close"
    )
    assert exec_body.count("now.hour >= 21") >= 2, (
        "expected at least 2 `now.hour >= 21` gates (VIX + SPX) — "
        f"found {exec_body.count('now.hour >= 21')}"
    )


# ── Change 3: earnings_proximity_score writer ────────────────────────

def _make_intel(upcoming):
    """Minimal intel dict for the score-writer tests."""
    return {
        "date": "2026-04-20",
        "has_major_catalyst": False,
        "has_minor_catalyst": False,
        "has_major_earnings": False,
        "events": [],
        "earnings": [],
        "upcoming_earnings": upcoming,
        "day_classification": "normal",
        "recommended_posture": "normal",
        "consensus_data": {},
    }


def test_earnings_proximity_score_written():
    """A nearest event 2 days out should produce score = 1 - 2/5 = 0.6,
    written to `calendar:earnings_proximity_score` with a 24h TTL."""
    from economic_calendar import write_intel_to_redis

    redis_client = MagicMock()
    intel = _make_intel([
        {"ticker": "NVDA", "days_until": 2, "is_major": True},
        {"ticker": "AAPL", "days_until": 4, "is_major": True},
    ])

    with patch("economic_calendar.get_client") as mock_get_client:
        mock_get_client.return_value.table.return_value.upsert.return_value.execute.return_value = MagicMock()
        write_intel_to_redis(redis_client, intel)

    # Find the setex call that wrote the proximity key.
    proximity_calls = [
        c for c in redis_client.setex.call_args_list
        if c.args and c.args[0] == "calendar:earnings_proximity_score"
    ]
    assert len(proximity_calls) == 1, (
        f"expected exactly one proximity score write; got {proximity_calls}"
    )
    key, ttl, value = proximity_calls[0].args
    assert ttl == 86400, f"TTL must be 24h; got {ttl}"
    assert abs(float(value) - 0.6) < 1e-6, (
        f"score for events 2 days out must be 0.6; got {value}"
    )


def test_earnings_proximity_score_zero_when_no_events():
    """Empty upcoming_earnings → score 0.0 (no catalyst signal)."""
    from economic_calendar import write_intel_to_redis

    redis_client = MagicMock()
    intel = _make_intel([])

    with patch("economic_calendar.get_client") as mock_get_client:
        mock_get_client.return_value.table.return_value.upsert.return_value.execute.return_value = MagicMock()
        write_intel_to_redis(redis_client, intel)

    proximity_calls = [
        c for c in redis_client.setex.call_args_list
        if c.args and c.args[0] == "calendar:earnings_proximity_score"
    ]
    assert len(proximity_calls) == 1
    assert float(proximity_calls[0].args[2]) == 0.0


def test_earnings_proximity_fail_open():
    """A setex that raises inside the score-writer must not propagate —
    the rest of the agent chain must keep running."""
    from economic_calendar import write_intel_to_redis

    redis_client = MagicMock()
    # First setex (calendar:today:intel) succeeds; second
    # (proximity score) raises. Order matters: we assert the
    # second call raised but write_intel_to_redis returns normally.
    redis_client.setex.side_effect = [
        None,
        RuntimeError("simulated redis outage"),
    ]
    intel = _make_intel([
        {"ticker": "NVDA", "days_until": 0, "is_major": True},
    ])

    with patch("economic_calendar.get_client") as mock_get_client:
        mock_get_client.return_value.table.return_value.upsert.return_value.execute.return_value = MagicMock()
        # Must not raise.
        write_intel_to_redis(redis_client, intel)

    assert redis_client.setex.call_count == 2


def test_compute_earnings_proximity_score_gradient():
    """Unit-test the pure score function across the 0..5 day range."""
    from economic_calendar import _compute_earnings_proximity_score

    cases = [
        ([{"days_until": 0}], 1.0),
        ([{"days_until": 1}], 0.8),
        ([{"days_until": 2}], 0.6),
        ([{"days_until": 3}], 0.4),
        ([{"days_until": 4}], 0.2),
        ([{"days_until": 5}], 0.0),
        ([{"days_until": 10}], 0.0),  # clamped
        ([], 0.0),
    ]
    for upcoming, expected in cases:
        score = _compute_earnings_proximity_score(
            {"upcoming_earnings": upcoming}
        )
        assert abs(score - expected) < 1e-6, (
            f"upcoming={upcoming} expected {expected} got {score}"
        )


# ── Change 4: signal_weak dropped from meta-label ────────────────────

def test_signal_weak_not_in_training_select():
    """The SELECT projections and feature-list builders in
    model_retraining.py must not reference `signal_weak`.

    Docstrings/comments that explain the drop are allowed — we only
    fail on executable code. Using AST keeps us from flagging a
    historical rationale written in plain English.
    """
    src = Path(__file__).resolve().parent.parent / "model_retraining.py"
    tree = ast.parse(src.read_text(encoding="utf-8"))

    offending = []

    for node in ast.walk(tree):
        # r.get("signal_weak") / row.get("signal_weak") patterns.
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "get"
        ):
            for arg in node.args:
                if (
                    isinstance(arg, ast.Constant)
                    and arg.value == "signal_weak"
                ):
                    offending.append("r.get('signal_weak')")

        # .select("... signal_weak ...") — literal or f-string arg.
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "select"
        ):
            for arg in node.args:
                if (
                    isinstance(arg, ast.Constant)
                    and isinstance(arg.value, str)
                    and "signal_weak" in arg.value
                ):
                    offending.append(f"select(): {arg.value!r}")
                if isinstance(arg, ast.JoinedStr):
                    for part in arg.values:
                        if (
                            isinstance(part, ast.Constant)
                            and isinstance(part.value, str)
                            and "signal_weak" in part.value
                        ):
                            offending.append(
                                f"select() fstring part: {part.value!r}"
                            )

    # Attribute access (e.g., row.signal_weak) — the project doesn't
    # use this form today but catch it proactively.
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == "signal_weak":
            offending.append("attribute access .signal_weak")

    assert not offending, (
        "model_retraining.py still has executable references to "
        f"signal_weak: {offending}"
    )


def test_feature_vectors_are_9_features():
    """Statically verify that all three lockstep feature-vector sites
    build 9-element lists. Uses AST so commented-out signal_weak
    lines or string mentions cannot satisfy the check by accident.

    Sites:
      backend/model_retraining.py     — train_meta_label_model
      backend/model_retraining.py     — _row_to_features (champion-challenger)
      backend/execution_engine.py     — meta-label inference _feat builder
    """
    backend = Path(__file__).resolve().parent.parent

    def _count_feat_elements(path: Path, token: str) -> list:
        """Walk the AST looking for feature-vector list literals that
        contain `token`. Skips pure matrix wrappers (a 1-element list
        whose single element is itself a list), because ast.walk
        recurses into them and we'd double-count the inner row.
        """
        tree = ast.parse(path.read_text(encoding="utf-8"))
        counts = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.List):
                continue
            # Skip outer `[[...]]` matrix wrappers — ast.walk will
            # visit the inner row separately.
            if (
                len(node.elts) == 1
                and isinstance(node.elts[0], ast.List)
            ):
                continue
            has_token = any(
                token in ast.unparse(e) for e in node.elts
            )
            if has_token:
                counts.append(len(node.elts))
        return counts

    # Identify the meta-label feature vectors by the presence of
    # "gex_flip_proximity" — unique to this feature set across the
    # whole codebase.
    train_counts = _count_feat_elements(
        backend / "model_retraining.py", "gex_flip_proximity"
    )
    exec_counts = _count_feat_elements(
        backend / "execution_engine.py", "gex_flip_proximity"
    )

    # Expect 2 sites in model_retraining (train + champion-challenger),
    # 1 site in execution_engine. All must be length 9.
    assert len(train_counts) == 2, (
        f"expected 2 feature-vector sites in model_retraining.py, "
        f"found {len(train_counts)}"
    )
    assert len(exec_counts) == 1, (
        f"expected 1 feature-vector site in execution_engine.py, "
        f"found {len(exec_counts)}"
    )
    for n in train_counts + exec_counts:
        assert n == 9, (
            f"meta-label feature vector must be 9 elements; got {n}"
        )


# ── Change 5: feature flags (counterfactual + meta-label) ────────────

def test_counterfactual_flag_disabled():
    """Redis flag = 'false' → labeler returns disabled payload and
    never hits Supabase."""
    from counterfactual_engine import label_counterfactual_outcomes

    redis_client = MagicMock()
    redis_client.get.return_value = "false"

    with patch("db.get_client") as mock_get_client:
        result = label_counterfactual_outcomes(redis_client)

    assert result == {"labeled": 0, "skipped": 0, "disabled": True}
    mock_get_client.assert_not_called(), (
        "a DISABLED flag must short-circuit BEFORE any Supabase query"
    )


def test_counterfactual_flag_missing_enables():
    """Redis returns None (key absent) → labeler proceeds normally
    (fail-open preserves today's behaviour)."""
    from counterfactual_engine import label_counterfactual_outcomes

    redis_client = MagicMock()
    redis_client.get.return_value = None  # key missing

    with patch("counterfactual_engine.date") as mock_date:
        mock_date.today.return_value.isoformat.return_value = "2026-04-20"
        with patch("db.get_client") as mock_get_client:
            mock_table = (
                mock_get_client.return_value
                .table.return_value
                .select.return_value
                .eq.return_value
                .gte.return_value
                .is_.return_value
            )
            mock_table.execute.return_value.data = []
            result = label_counterfactual_outcomes(redis_client)

    assert result.get("disabled") is not True, (
        "missing flag must NOT disable the labeler"
    )
    mock_get_client.assert_called(), (
        "labeler must reach Supabase when the flag is absent"
    )


def test_counterfactual_flag_error_enables():
    """Redis raises on .get() → labeler proceeds normally (fail-open)."""
    from counterfactual_engine import label_counterfactual_outcomes

    redis_client = MagicMock()
    redis_client.get.side_effect = RuntimeError("redis down")

    with patch("counterfactual_engine.date") as mock_date:
        mock_date.today.return_value.isoformat.return_value = "2026-04-20"
        with patch("db.get_client") as mock_get_client:
            mock_table = (
                mock_get_client.return_value
                .table.return_value
                .select.return_value
                .eq.return_value
                .gte.return_value
                .is_.return_value
            )
            mock_table.execute.return_value.data = []
            result = label_counterfactual_outcomes(redis_client)

    assert result.get("disabled") is not True
    mock_get_client.assert_called()


def test_meta_label_flag_disabled_skips_inference():
    """When Redis says meta_label:enabled=false AND a pkl exists, the
    inference block must NOT call .predict_proba — the trade proceeds
    with its original contracts count.

    Static check: read the execution_engine source and verify the
    flag-read block is syntactically upstream of the `_model_path.exists()`
    guard, and that `_model_path.exists()` is conjoined with
    `_meta_label_enabled`. This captures the semantic we care about
    without spinning up a full ExecutionEngine + LightGBM model.
    """
    src = Path(__file__).resolve().parent.parent / "execution_engine.py"
    code = src.read_text(encoding="utf-8")

    # The flag-read declaration must appear before the _model_path
    # construction line. String.find gives the earliest match which
    # is fine — both phrases are unique in the file.
    flag_decl = code.find('_meta_label_enabled = True')
    model_path = code.find('/ "meta_label_v1.pkl"')
    assert flag_decl != -1, "meta-label flag gate is missing"
    assert model_path != -1, "meta-label inference block is missing"
    assert flag_decl < model_path, (
        "flag gate must be evaluated BEFORE the pkl existence check"
    )

    # The existence check must be conjoined with the flag — a bare
    # `if _model_path.exists():` would run inference even when the
    # flag is false.
    assert "_meta_label_enabled and _model_path.exists()" in code, (
        "inference must be gated on both the flag and the pkl file"
    )


def test_meta_label_flag_missing_enables():
    """Redis key absent → `_meta_label_enabled` stays True so a pkl
    that exists runs the inference. Verified by source inspection:
    the gate's default value must be True, and the only assignment
    to False must be inside the `raw in (...false...)` branch."""
    src = Path(__file__).resolve().parent.parent / "execution_engine.py"
    code = src.read_text(encoding="utf-8")

    # Default is True.
    assert "_meta_label_enabled = True" in code

    # No unconditional `_meta_label_enabled = False` — must only be
    # set false inside the flag-read try block.
    false_assignments = [
        ln for ln in code.splitlines()
        if ln.strip() == "_meta_label_enabled = False"
    ]
    assert len(false_assignments) == 1, (
        f"expected exactly one conditional False assignment; "
        f"found {len(false_assignments)}: {false_assignments}"
    )
