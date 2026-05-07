# HANDOFF NOTE — T-ACT-082 Feature Pipeline Completion (Path Alpha + B.1.iii)

**Date:** 2026-05-07
**Branch / PR:** `fix/t-act-082-feature-pipeline-completion`
**Predecessor:** T-ACT-076 (binary labeler fix — F-068-I dissolution; merged 2026-05-07 morning)
**Successors (queued):** T-ACT-084 (daily-aligned VIX series), T-ACT-085 (SPX OHLC fetch + day-boundary state), T-ACT-086 (`polygon:spx:open` writer — 8th A.7-family subclass)
**Owner:** Cursor (implementation), Operator (decision authority + verification gate)
**Status:** SHIPPED to PR. Pending operator review/merge + post-deploy verification window.

---

## §1 — Why this T-ACT exists

### 1.1 The presenting problem

After T-ACT-076 shipped (2026-05-07 morning), operator-data showed the structural collapse driven by F-068-I (binary-trained model + ternary labeler) was dissolved. But the post-T-ACT-076 production accuracy on labeled rows did not recover toward the 52.92% LightGBM training holdout floor — it remained materially below, in the 30-35% band. The 2026-05-07 model-quality investigation set out to identify the second structural driver.

### 1.2 The root cause

Audit of `prediction_engine.py:1085-1110` (the LightGBM inference site) cross-referenced against `polygon_feed.py` (the producer side) revealed **six unwritten Redis keys** — features that LightGBM reads at inference time but no producer ever writes:

| Feature | Training importance rank | Status before T-ACT-082 |
|---|---|---|
| `polygon:spx:vwap_distance` | #1 | UNWRITTEN — pinned 0.0 |
| `polygon:spx:realized_vol_20d` (semantic) | #2 | WRITTEN as `sqrt(252)` daily basis (12A); training expects `sqrt(252*78)` 5-min basis |
| `polygon:spx:macd_signal` | #6 | UNWRITTEN — pinned 0.0 |
| `polygon:spx:morning_range` | #7 | UNWRITTEN — pinned 0.0 |
| `polygon:vix:5d_change` | #10 | UNWRITTEN — pinned 0.0 |
| `polygon:spx:bb_pct_b` | (mid-pack) | UNWRITTEN — pinned 0.0 |
| `polygon:spx:overnight_gap` | (top-quartile) | UNWRITTEN — pinned 0.0 |

LightGBM was effectively running on ~15 of 25 features. The model's tree-splits encoded in those six unwritten / semantically-mismatched dimensions never fire under any input regime. Net effect: the inference-time feature distribution materially differs from the training-time distribution, in exactly the dimensions the model relies on most.

This is a sixth A.7-family subclass instance: **feature-pipeline incompleteness — consumer reads from a key that no producer writes.** Compare to T-ACT-076 (class-space mismatch) and T-ACT-067 (schema-CHECK constraint mismatch) — same family, different surface.

---

## §2 — Critique-first phase (Q1-Q14)

Operator imposed CRITIQUE-FIRST per the standing post-T-ACT-072 discipline. Cursor's Phase 1 review surfaced **three STOP-class issues** that invalidated the original "populate all 6 keys" framing:

### 2.1 Q1 (STOP) — cache-class insufficiency for OHLC features

`self.spx_history` is `List[float]` of spot CLOSES (capped at 60). Three of the six unwritten features require data the live pipeline does not maintain:

- **`vwap_distance`** needs `(high + low + close) / 3` (typical price) per bar + day-boundary anchor for the expanding-day mean.
- **`morning_range`** needs `high` / `low` per bar + first-30-minutes day-boundary state + `day_open`.
- **`overnight_gap`** needs `prev_session_close` (separate from the existing `spx_prev_session_close`) + `first_5m_open` of the current session, gated on `hour == 9`.

**Verdict:** Cannot populate these three keys without introducing an entirely new data class (`spx_5m_bars: List[dict]` with OHLC fields) plus day-boundary state (`day_open`, `morning_high`, `morning_low`, `prev_session_close_for_overnight`). Estimated ~200 LOC just for the producer-side infrastructure, before any feature math.

**Operator independent verification:** "spx_history is List[float] of spot prices, capped at 60 — confirmed at L21, L240, L247. No OHLC. The comment at L1241 even says 'self.spx_history is a 5-minute intraday' buffer." VERIFIED.

### 2.2 Q2 (STOP) — `rv_20d` 5-min-basis buffer feasibility

The training formula (`train_direction_model.py:292-298`) computes `rolling(20*78).std() * sqrt(252*78) * 100` over the **5-min returns series**, not daily returns. To replicate this in the live pipeline byte-for-byte, we need 1560 5-min returns in a buffer. `spx_history` holds only 60. The two options are:

- (a) Wait ~21 trading days (1560 / 78 ≈ 20 sessions) for organic accumulation post-deploy
- (b) Add a startup backfill that fetches 1560 5-min closes from Polygon's `/v2/aggs/ticker/I:SPX/range/5/minute/...` endpoint

Path (a) is operationally a 3-week regression — `rv_20d` would fall back to the `prediction_engine` default 15.0 the entire time, and the iv_rv_ratio gate at `prediction_engine.py:1264-1290` would behave as if `rv_20d` is constant. The B.1.iii startup backfill (Path b) costs ~110 LOC including tests but eliminates the cold-start window.

**Verdict:** Cannot ship Scope B without B.1.iii backfill OR explicit operator acknowledgment of the 21-day cold-start.

### 2.3 Q7 (STOP) — anti-Scope-B test file

`backend/tests/test_spx_daily_rv.py` (~210 LOC) explicitly locks in the 12A daily-basis formula. The docstring at L186 reads:

> "Catches accidental re-introduction of intraday annualization factors (sqrt(252 * 78) etc.)"

— exactly the formula Scope B re-introduces, by training-pipeline alignment. The test file is anti-Scope-B by design. We cannot keep it; we must replace its invariants with 5-min-basis equivalents.

**Verdict:** Cannot ship Scope B without ~150 LOC test churn rewriting the file.

**Operator independent verification:** "The 12A test is exactly what Cursor described. The docstring literally says it's there to 'catch accidental re-introduction of intraday annualization factors (sqrt(252 * 78) etc.)' — the exact formula Scope B reintroduces. Test purpose is anti-Scope-B by design." VERIFIED.

### 2.4 M1 — new A.7-family instance surfaced (T-ACT-086)

While grepping for unwritten Redis keys to compose Q1's answer, Cursor found `shadow_engine.py:318` reads `polygon:spx:open` but no producer writes it. This is a NEW silent feature gap, not in any prior T-ACT scope. The 8th A.7-family subclass instance counted in the past 7 days.

**Operator independent verification:** "polygon:spx:open is read at shadow_engine.py:318 and never written anywhere in the codebase. Cursor's M1 finding (an additional A.7-class instance, possibly the 8th this week)." VERIFIED.

### 2.5 Operator decision

Operator authorized **Path Alpha** (subset to byte-for-byte-alignable features + B.1.iii backfill) over Path Beta (bundle OHLC fetch, ~570 LOC) and Path Gamma (close-only approximations, REJECTED per workflow rule #11 — feeding the model approximated distributions when trained on true ones may be worse than constants).

---

## §3 — Path Alpha shipped scope

### 3.1 Code changes (`backend/polygon_feed.py`)

1. **`__init__` block (~50 LOC):** new state — `_spx_5m_returns_history: List[float]` (cap 1560), `_spx_5m_history_max = 1560`, `_spx_5m_backfill_done: bool`. Updated commentary supersedes the 12A daily-basis backstory.

2. **`start()` (~10 LOC):** wire `_backfill_spx_5m_history()` alongside `_backfill_vix_history()`, fail-open on Polygon errors.

3. **`_backfill_spx_5m_history()` (~110 LOC, new method):** fetches 35-calendar-day window (~1950 5-min bars) from `/v2/aggs/ticker/I:SPX/range/5/minute/...`, computes 1560 returns via successive pct_change, seeds buffer + last 60 closes into `spx_history` for warm-start of EMA recurrence and `safe_return(48)`.

4. **`_compute_spx_features()` (~60 LOC added):** new live writers for `polygon:spx:bb_pct_b` (training L242-244 byte-aligned), `polygon:spx:macd_signal` (training L237-240 byte-aligned, MACD histogram = MACD line minus 9-bar EMA-of-MACD-line), and `polygon:spx:realized_vol_20d` 5-min basis (training L292-298 byte-aligned).

5. **`_store_vix_baseline()` (~20 LOC added):** `polygon:vix:5d_change` writer (training L274-276 byte-aligned), 7200s TTL matching sibling daily VIX keys.

6. **`_append_spx_daily_return_if_due()` (gutted realized_vol write, ~25 LOC removed):** deprecated daily-basis writer removed; date-guard infrastructure retained for future daily-basis sibling.

7. **`_ewm_adjust_false()` (~25 LOC, new static helper):** replicates `pandas.Series.ewm(span=N, adjust=False).mean()` recursive contract; locked numerically by test against pandas to <1e-9 noise.

### 3.2 Test changes

- **NEW: `tests/test_spx_5m_basis_rv.py` (8 tests, ~280 LOC)** — supersedes `test_spx_daily_rv.py`. Locks in 1560-bar warmth threshold, 5-min-basis annualization math (`sqrt(252*78)` with hard regression guard against `sqrt(252)` re-introduction), FIFO buffer cap, backfill population + `spx_history` seed side effect, regression guard that `_append_spx_daily_return_if_due` no longer writes the realized-vol key, date-guard preservation.
- **NEW: `tests/test_t_act_082_feature_writers.py` (10 tests, ~270 LOC)** — byte-for-byte alignment for `bb_pct_b` / `macd_signal` / `vix_5d_change` against closed-form training formulas, warmth-threshold regression guards (no premature writes), TTL contracts, and `_ewm_adjust_false` ↔ pandas equivalence.
- **DELETED: `tests/test_spx_daily_rv.py` (7 tests, ~210 LOC)** — anti-Scope-B by design (Q7 STOP issue).
- **COMMENT ONLY: `tests/test_iron_butterfly_safety_gates.py:235-241`** — updated docstring to reflect post-T-ACT-082 semantics; no behavioural change.

### 3.3 Comment hygiene

Updated 4 outdated narrative blocks that referred to superseded behavior:
- `polygon_feed.py:43-58` (12A backstory — superseded by T-ACT-082 §B note)
- `polygon_feed.py:316-324` (`polygon:spx:realized_vol_20d` write location — moved from EOD to per-cycle)
- `polygon_feed.py:519-524` (21:00 UTC EOD gate description)
- `prediction_engine.py:1264-1275` (IV/RV filter "garbage values 1.05-1.29" rationale — superseded; warmth guard retained as defensive sanity check)

### 3.4 Total scope

- **~370 LOC code** added/modified in `polygon_feed.py`, ~10 LOC modified in `prediction_engine.py`, comment-only in `tests/test_iron_butterfly_safety_gates.py`.
- **~150 LOC test churn** (`test_spx_daily_rv.py` deleted; `test_spx_5m_basis_rv.py` written).
- **~270 LOC new tests** (`test_t_act_082_feature_writers.py`).
- **0 dependency additions.**

Reviewable in one sitting per Phase 1 critique sizing.

---

## §4 — What this T-ACT does NOT do (deferred work)

### 4.1 T-ACT-084 — daily-aligned VIX series (~150 LOC, MEDIUM severity)

`vix_close` / `vvix_close` features are written as live `polygon:vix:current` / `polygon:vvix:current` (real-time intraday). Training uses EOD daily aggregates. Same key NAME, different statistical distribution. Fix: add separate `polygon:vix:close_eod` / `polygon:vvix:close_eod` keys updated only at the 21:00 UTC EOD gate; reader-site change in `prediction_engine.py:1085-1110`.

### 4.2 T-ACT-085 — SPX OHLC fetch + day-boundary state (~280 LOC, HIGH severity)

`vwap_distance` (training importance #1), `morning_range` (#7), `overnight_gap` (top-quartile). Requires entire new data class: `spx_5m_bars: List[dict]` with OHLC + day-boundary state. Highest-impact deferred work.

### 4.3 T-ACT-086 — `polygon:spx:open` writer (~20 LOC, MEDIUM severity)

8th A.7-family subclass instance. `shadow_engine.py:318` reads but no producer writes. Independent of T-ACT-082 critical-path; can ship any time.

### 4.4 Decision matrix for T-ACT-084/085 priority

Re-evaluate after T-ACT-082's deploy + 7 days of post-deploy production-accuracy data:

- **Path A** (T-ACT-082 alone closes the gap to within 5%): Park T-ACT-084/085 indefinitely.
- **Path B** (residual 5-15% gap): Schedule T-ACT-085 first (higher feature importance), then T-ACT-084.
- **Path C** (residual >15% gap): Coordinate T-ACT-085 + T-ACT-084 as a Phase 2 of Path Beta, escalate to HIGH priority.

T-ACT-086 priority is independent — ship any time the operator authorizes the small fix.

---

## §5 — Acceptance criteria

### 5.1 Unit / integration tests (verified pre-merge)

- ✅ 18/18 new tests pass (`test_spx_5m_basis_rv.py` + `test_t_act_082_feature_writers.py`)
- ✅ 43/43 nearby tests pass (`test_iron_butterfly_safety_gates.py`, `test_consolidation_s13.py`, `test_consolidation_s14.py`) — comment-only changes safe
- ✅ Zero linter errors on all 5 modified files
- ✅ Full backend test suite shows zero regressions vs T-ACT-076 baseline

### 5.2 Post-deploy verification (operator-observed, 30 minutes after merge + 7 days after merge)

```sql
-- 30 minutes post-merge: confirm new feature writers fired
-- (run from Railway-attached Redis or via the operator's debug endpoint)
KEYS polygon:spx:bb_pct_b
KEYS polygon:spx:macd_signal
KEYS polygon:vix:5d_change
GET polygon:spx:realized_vol_20d  -- value should be 5-min-basis 5-30%, not daily-basis ~15-20%

-- 7 days post-merge: confirm production accuracy recovers materially
-- toward the 52.92% LightGBM training holdout floor.
SELECT
  DATE_TRUNC('day', created_at) AS day,
  COUNT(*) AS labeled_rows,
  AVG(CASE WHEN outcome_correct THEN 1.0 ELSE 0.0 END) AS daily_accuracy,
  AVG(CASE WHEN model_source = 'lgbm_v1' AND outcome_correct THEN 1.0 ELSE 0.0 END)
    FILTER (WHERE model_source = 'lgbm_v1') AS lgbm_only_accuracy
FROM trading_prediction_outputs
WHERE outcome_correct IS NOT NULL
  AND created_at >= now() - interval '7 days'
GROUP BY 1
ORDER BY 1;
```

**Pass criteria for the 7-day window:**
- LightGBM-only daily accuracy averages >= 0.40 (vs <0.30 pre-T-ACT-082)
- Crosstab from T-ACT-076 §A.7 SQL shows pred=neutral rows still ≤10% (T-ACT-081 Path A confirmation)
- No new structured WARN events with `polygon_spx_daily_rv_failed` or `polygon_spx_current_write_failed` over the 7-day window

**Failure paths:** if the 7-day accuracy is still <0.35, escalate to T-ACT-085 BUNDLE per Path C above.

---

## §6 — A.7-family lens

T-ACT-082 closes the 6th A.7-family subclass: **feature-pipeline incompleteness**. Running tally over the past 30 days:

1. SPX `fetched_at` semantics flip silent (T-ACT-046, 2026-05-02)
2. `PostgrestAPIError` swallowed at persist site (T-ACT-047, 2026-05-03)
3. Persist-site audit gate (T-ACT-055, 2026-05-02)
4. Whitespace strip silent rejection (T-ACT-057, 2026-05-02)
5. Subscription-tier mismatch silent staleness (T-ACT-061, 2026-05-04)
6. Schema-CHECK constraint mismatch silent rejection (T-ACT-067 / F-068-A / closed via T-ACT-076 Scope B)
7. Class-space mismatch silent collapse (T-ACT-076, 2026-05-07 morning)
8. Feature-pipeline incompleteness — consumer reads, no producer writes (T-ACT-082, 2026-05-07 afternoon — THIS ENTRY)

Plus **T-ACT-086 (the 8th instance, queued)**: `polygon:spx:open` read at `shadow_engine.py:318`, no producer writes.

The cumulative 8-instance pattern over 7 days is sufficient evidence to elevate "A.7 silent-failure-class family" from a recurring lesson-learned to a first-order architectural concern. Recommended for the next governance review cycle: a periodic sweep cron (or test-time grep) that flags every Redis key read by `_read_redis(key, default)` with no matching producer write in the codebase.

---

## §7 — Files changed in this PR

### Code
- `backend/polygon_feed.py` (~370 LOC modified)
- `backend/prediction_engine.py` (~10 LOC comment-only)

### Tests
- `backend/tests/test_spx_5m_basis_rv.py` (NEW, 8 tests, ~280 LOC) — replaces `test_spx_daily_rv.py`
- `backend/tests/test_t_act_082_feature_writers.py` (NEW, 10 tests, ~270 LOC)
- `backend/tests/test_spx_daily_rv.py` (DELETED, was 7 tests / ~210 LOC, anti-Scope-B by design)
- `backend/tests/test_iron_butterfly_safety_gates.py` (comment-only, 1 docstring updated)

### Governance
- `trading-docs/08-planning/TASK_REGISTER.md` (T-ACT-082, T-ACT-083, T-ACT-084, T-ACT-085, T-ACT-086 entries; F-068-G reclassification reference; T-ACT-064 dependency note; Section 14 cross-references; closing audit-trail amendment)
- `trading-docs/06-tracking/HANDOFF_NOTE_2026-05-07_T_ACT_082_FEATURE_PIPELINE.md` (NEW — this file)

---

*Handoff note opened 2026-05-07 by Cursor. Operator-authorized Path Alpha + B.1.iii backfill + bundled T-ACT-083 governance + ~150 LOC test churn.*
