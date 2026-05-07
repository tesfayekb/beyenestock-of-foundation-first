# HANDOFF NOTE — F-068-I binary labeler fix (T-ACT-076 Position 1a) + F-068-A schema-CHECK widening

**Date opened:** 2026-05-06 (DIAGNOSE phase — recommendation)
**Date EXECUTE:** 2026-05-07
**PR:** `fix/t-act-076-binary-labeler-position-1a`
**Severity:** HIGH
**Owner:** Cursor (DIAGNOSE-FIRST + Q1-Q12 critique-first + EXECUTE)
**Authorizer:** tesfayekb (Phase 1 critique GREEN; Phase 2 YELLOW with three governance amendments)
**Status:** SHIPPED (pending operator review/merge)

---

## §1 — Executive summary

This PR ships **Position 1a** (the strict-binary labeler fix recommended in the F-068-I converged-recommendation prompt) for `backend/model_retraining.label_prediction_outcomes` so its class space matches the LightGBM model's training-script class space byte-for-byte. The mismatch was the **dominant cause** of the 6.1% post-hygiene accuracy anomaly — every cycle whose realized SPX move fell inside the ternary labeler's ±0.1% `DIRECTION_THRESHOLD` band was scored `outcome_correct=False` against an inference engine that architecturally cannot emit `direction='neutral'` on the LightGBM path.

Per Cursor's Q10 BUNDLE decision (operator-affirmed), this PR also ships **Scope B** (F-068-A closure) — a one-line `ALTER TABLE` migration widening the `trading_model_performance.drift_status` CHECK constraint to include `'ok'` and `'unknown'`, plus a narrow `PostgrestAPIError` classifier wrapping the weekly persist site. The bundle exists because shipping Scope A alone before the next Sunday cron creates a window in which the weekly run still silently fails on `drift_status='ok'`. Marginal review burden of bundling (~30 LOC + one trivial migration) is trivial vs. the activation-risk avoidance.

The fix dissolves **F-068-I** (training-inference class-space mismatch), dissolves **F-068-G** on average (S15 threshold-metric mismatch — accuracy distribution will return to normal binary-classifier territory once `'neutral'` actuals stop existing), and closes **F-068-A** (silent schema-CHECK rejection — the second A.7-family persist-site instance after T-ACT-047). It does **not** close F-068-B (data-window contamination, T-ACT-077 deferred to 2026-05-25) or F-068-H (dual-writer dashboard identity-switch — informational follow-up; the new inner classifier's WARN log will surface the dual-writer pattern observably going forward).

---

## §2 — Original-intent forensic (the binary labeler is the original design)

The forensic in the F-068-I recommendation prompt traced the labeler's class space backward through `git log --follow`:

| Date | Commit | Change | Outcome |
|---|---|---|---|
| 2026-04-17 morning | (initial) | `train_direction_model.py` ternary classifier with ±0.1% band | "Model collapse" — model learned to always predict `'neutral'` because the band dominated the training distribution |
| 2026-04-17 16:22 ET | `84617a1` | Reverted training script to strict binary (`r > 0` → `'bull'` else `'bear'`) | Model began learning a directional signal; ROC-AUC recovered |
| 2026-04-17 (same-day) | (missed) | `model_retraining.label_prediction_outcomes` was supposed to be reverted in lockstep but the change was missed | Production labeler remained ternary while training was binary |
| 2026-04-17 → 2026-05-06 | (silent) | Every cycle whose realized SPX move fell in ±0.1% scored `outcome_correct=False` against a binary-trained inference path | Post-hygiene accuracy collapsed to 6.1% |

**Reading:** This is not a "design dispute" between binary and ternary — it is an unfinished revert. The binary labeler is the original design; the ternary labeler is leftover from a known-bad experiment that was reverted on the training side and forgotten on the labeling side. **Position 1a is therefore not a tradeoff — it is the completion of a 3-week-old revert.**

---

## §3 — What changed (file-by-file)

### Scope A — Binary labeler (F-068-I dissolution)

**File:** `backend/model_retraining.py:140-147`

```python
# BEFORE (ternary, missed-revert)
spx_return = (spx_at_t30 - spx_at_signal) / spx_at_signal
DIRECTION_THRESHOLD = 0.001  # ±0.1%

if spx_return > DIRECTION_THRESHOLD:
    actual_direction = "bull"
elif spx_return < -DIRECTION_THRESHOLD:
    actual_direction = "bear"
else:
    actual_direction = "neutral"

# AFTER (binary, byte-for-byte aligned with train_direction_model.py:323-325)
spx_return = (spx_at_t30 - spx_at_signal) / spx_at_signal
actual_direction = "bull" if spx_return > 0 else "bear"
```

The `DIRECTION_THRESHOLD = 0.001` constant is removed entirely from the labeler. Strict `> 0` matches `train_direction_model.py:323-325`; `spx_return == 0.0` → `"bear"` (vanishingly rare under float division). The regression test `test_label_prediction_outcomes_never_emits_neutral` in `test_phase_a1.py` asserts both `'actual_direction = "neutral"'` and `'DIRECTION_THRESHOLD'` are absent from the function's source — defends against accidental future re-introduction.

### Scope B — `drift_status` CHECK widening (F-068-A closure)

**File:** `supabase/migrations/20260507_widen_drift_status_check.sql` (new)

Idempotent `DROP CONSTRAINT IF EXISTS` + `ADD CONSTRAINT` widens the CHECK to a five-value allowlist:

```sql
CHECK (drift_status IN (
  'normal', 'warning', 'critical',  -- original
  'ok', 'unknown'                    -- added 2026-05-07
))
```

CHECK-widening was preferred over function-layer remap on ROI grounds (Q10 sub-decision, operator-affirmed):
- No information loss — `'ok'` (computed-and-healthy) and `'unknown'` (insufficient observations) are semantically distinct from `'normal'`.
- Smaller diff — one ALTER TABLE vs. a multi-call-site rename.
- Doesn't change the daily `check_prediction_drift` contract, which also returns `'ok'`.

### Scope B — Narrow `PostgrestAPIError` classifier

**File:** `backend/model_retraining.py:11-17` (new import) and `~677-697` (narrow inner try/except)

Pattern is **byte-for-byte aligned** with the T-ACT-047 Choice C precedent at `prediction_engine.py:1641-1690`. Logs structured `weekly_model_performance_persistent_error` event at WARN with `pgrst_code` / `pgrst_details` / `pgrst_hint` / `drift_status_attempted`. Calls `write_health_status('prediction_engine', 'error')` with a `PERSISTENT[<code>]:` prefix. Fires `send_alert(CRITICAL, ...)` with the hint and `drift_status_attempted` in the body. Returns `{"error": "persistent_postgrest:<code>"}`. Non-postgrest exceptions fall through to the outer broad `except Exception` (preserved for compute-helper / network / audit-log failures).

The `drift_status_attempted` field is a T-ACT-076-specific differentiator vs. T-ACT-047 — it lets the operator distinguish F-068-A recurrence (e.g., from a future regression that re-narrows the CHECK) from other persist-class errors.

### Tests

**Re-purposed in `backend/tests/test_phase_a1.py`:**
- `test_label_prediction_outcomes_neutral_within_threshold` → `test_label_prediction_outcomes_tiny_positive_move_is_bull` — asserts the OLD ternary-band case (+0.05% return) is now classified `'bull'`.

**New in `backend/tests/test_phase_a1.py`:**
- `test_label_prediction_outcomes_zero_move_is_bear` — boundary contract (strict `> 0`).
- `test_label_prediction_outcomes_never_emits_neutral` — source-introspection regression guard.

**New in `backend/tests/test_t_act_076_weekly_perf_persistent_error.py` (5 tests):**
- `test_postgrest_error_logged_with_structured_fields` — WARN classification + structured fields including `drift_status_attempted='ok'`.
- `test_postgrest_error_writes_health_error_with_persistent_prefix` — `PERSISTENT[<code>]:` prefix convention.
- `test_postgrest_error_fires_critical_alert_with_hint` — CRITICAL alert body includes hint + `drift_status_attempted`.
- `test_non_postgrest_exception_falls_through_to_outer_handler` — Choice C scope guard (RuntimeError reaches outer ERROR).
- `test_successful_insert_returns_summary_no_warning` — happy-path no-warning regression guard.

---

## §4 — Q5 regime-dependent confound (Phase 2 amendment #1, explicit)

The Position 1a binary labeler dissolves F-068-G **on average** but exposes a regime-dependent risk surface that operator and Cursor both verified during Phase 1 critique.

Two inference paths in `prediction_engine.py` can still emit `direction='neutral'` after this fix:

| Path | Site | Trigger | Magnitude (qualitative) |
|---|---|---|---|
| AI-synthesis | `prediction_engine.py:974,978` | AI agent returns `'neutral'` with `confidence >= 0.55` | Small share — AI-synth is invoked on a subset of cycles |
| **Regime-fallback at `cv_stress > 70`** | `prediction_engine.py:1178-1192` | `cv_stress > 70` → `p_neutral = 0.40` is unambiguous argmax (LARGER of the two) | Fully regime-dependent; on calm weeks rare, on stressed weeks can be material |

Note: the default-regime branch at L1188 has `p_neutral = 0.35` tied with `p_bull = 0.35`; Python's `max()` returns the first equal-valued tuple = `'bull'`, so default is binary-correct (verified by operator).

**Quantitative outline (operator's analysis, recorded for the post-deploy decision matrix):**

- Net expected accuracy under Position 1a, calm weeks: ~0.90-0.95 × the model's underlying directional skill ≈ 47-50%.
- Above `RETRAIN_THRESHOLD = 0.45` → F-068-G stays dissolved.
- **Stressed weeks with `cv_stress > 70` firing on, say, 30% of cycles**: expected accuracy could fall to ~37%, BELOW `RETRAIN_THRESHOLD` and would correctly fire `'critical'` drift — but for the WRONG reason (structural class-mismatch on neutral preds, not model degradation).

**This means:**
- Expected post-deploy accuracy is ~47-50% on average but **regime-dependent**; on high-cv_stress weeks the regime-fallback path will produce more `pred='neutral'` rows that get scored false against binary labels.
- **F-068-G's dissolution is conditional on `cv_stress` distribution being typical.**
- T-ACT-081 is queued (NOT bundled, per scope discipline) to address this via a labeler guard once post-deploy data quantifies the actual magnitude.

---

## §5 — Q1-Q12 critique trace (Phase 1, all flags resolved)

| Q | Topic | Verdict | Resolution |
|---|---|---|---|
| Q1 | `DIRECTION_THRESHOLD` constant — should it be moved or deleted? | Delete | Removed entirely from labeler; the regression test asserts absence |
| Q2 | Schema compatibility — does `trading_prediction_outputs.outcome_direction` accept binary values? | Yes | Existing CHECK (`'bull','bear','neutral'`) is permissive; no migration needed |
| Q3 | Test dependencies — which tests assert ternary semantics? | One | `test_label_prediction_outcomes_neutral_within_threshold` re-purposed |
| Q4 | Inference correctness — does `prediction_engine` ever emit `'neutral'`? | Two paths | See Q5 — non-blocking |
| Q5 | Magnitude of the two neutral-emitting paths | 5-10% on average; regime-dependent | Documented in §4; T-ACT-081 queued |
| Q6 | Consumer dependencies on the old data distribution | None | GLC-001/002 evaluators count `outcome_correct` rows; binary collapse is a strict improvement |
| Q7 | Rollback strategy | Trivial | Revert one file + drop new migration |
| Q8 | ROI preservation | Strict improvement | Restoring the pre-S15 labeler-training alignment |
| Q9 | Governance documentation | Bundled | TASK_REGISTER + this handoff note |
| Q10 | BUNDLE Scope A + Scope B vs. sequence them | BUNDLE | Activation-risk asymmetry — Sunday cron between merges |
| Q10 sub | CHECK-widening vs. function-layer remap | Widen | ROI / diagnostic granularity |
| Q11 | Does T-ACT-076 close F-068-B (T-ACT-077 data-window hygiene)? | NO — DEFERRED, NOT CLOSED | Position 1a fixes labeler class-space; data-window contamination is orthogonal |
| Q12 | Should we add a labeler guard for `pred_direction='neutral'` now? | NO | Operator scope discipline rule (#3); queued as T-ACT-081 |

Phase 1 critique closed GREEN with two flags: Q5 (regime confound, documented) and Q11 (T-ACT-077 deferred, not closed). Operator authorized YELLOW with three Phase 2 amendments (handoff documentation of Q5; T-ACT-081 entry; SQL crosstab) — all governance/documentation, no scope expansion.

---

## §6 — Cross-references

- F-068-I (training-inference class-space mismatch) — DISSOLVED by Scope A.
- F-068-A (schema-CHECK silent rejection on `drift_status`) — CLOSED by Scope B; second A.7-family persist-site instance.
- F-068-G (S15 threshold-metric mismatch) — DISSOLVED by Scope A on average; conditional on `cv_stress` distribution per Q5.
- F-068-H (dual-writer dashboard identity-switch via `calibration_engine.write_model_performance` 22:00 UTC) — INFORMATIONAL FOLLOW-UP (not closed); the new inner classifier's WARN log will surface the dual-writer pattern observably.
- F-068-B (data-window contamination, Indices-Starter-stale era) — DEFERRED via T-ACT-077; re-evaluate 2026-05-25.
- T-ACT-047 Choice C (`PostgrestAPIError` classifier at `prediction_engine.py:1641-1690`) — pattern precedent; T-ACT-076 Scope B is byte-for-byte aligned to keep the two A.7-family persist sites in lock-step.
- T-ACT-081 — queued labeler guard for `pred_direction='neutral'` inputs; defer pending post-deploy magnitude quantification.
- HANDOFF NOTE Appendix A.7 — silent-failure-class family lens.
- `backend/scripts/train_direction_model.py:323-325` — the canonical class-space contract that Scope A aligns to.

---

## §A.7 — Post-deploy verification SQL (Phase 2 amendment #3, expanded)

Operator must run these SQL queries:
- **T+30min after deploy** — confirm labeler is binary AND no F-068-A regressions.
- **T+7 days after deploy** — confirm Q5 magnitude is ≤ 10% threshold for T-ACT-081 Path A.

### A.7.1 — Binary labeler verification

```sql
-- Confirms outcome_direction is exclusively in {'bull','bear'} after T-ACT-076 deploy.
-- Expected: zero rows with outcome_direction = 'neutral'. Any non-zero count
-- means a labeler regression OR a ternary row got written before the deploy
-- timestamp (filter via outcome_labeled_at if needed).
SELECT
  outcome_direction,
  COUNT(*) AS row_count,
  MIN(outcome_labeled_at) AS earliest_label,
  MAX(outcome_labeled_at) AS latest_label
FROM trading_prediction_outputs
WHERE outcome_labeled_at >= NOW() - INTERVAL '7 days'
  AND outcome_direction IS NOT NULL
GROUP BY outcome_direction
ORDER BY outcome_direction;
```

### A.7.2 — `pred_direction × outcome_direction` crosstab (Q5 magnitude — F-068-I §11.1)

```sql
-- Quantifies how often the inference engine emits direction='neutral'
-- (AI-synth + cv_stress > 70 regime-fallback paths from Q5) and how that
-- collides with the new binary labeler.
--
-- Expected post-deploy distribution:
--   pred_direction × outcome_direction:
--     bull × bull       = directionally correct
--     bull × bear       = directionally wrong
--     bear × bull       = directionally wrong
--     bear × bear       = directionally correct
--     neutral × bull    = Q5 confound row (AI-synth or cv_stress regime fallback)
--     neutral × bear    = Q5 confound row (AI-synth or cv_stress regime fallback)
--     anything × neutral = REGRESSION (labeler emitted neutral — investigate)
--
-- T-ACT-081 decision matrix uses (neutral_pred_count / total_count) to decide
-- between Path A (≤10%, park), Path B (10-25%, schedule fix), Path C (>25%,
-- escalate to coordinated labeler+evaluator change).
SELECT
  COALESCE(direction, 'NULL') AS pred_direction,
  COALESCE(outcome_direction, 'NULL') AS outcome_direction,
  COUNT(*) AS row_count,
  ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_of_total,
  AVG(CASE WHEN outcome_correct THEN 1.0 ELSE 0.0 END) AS conditional_accuracy
FROM trading_prediction_outputs
WHERE predicted_at >= NOW() - INTERVAL '7 days'
  AND outcome_direction IS NOT NULL
GROUP BY direction, outcome_direction
ORDER BY direction, outcome_direction;
```

### A.7.3 — Weekly-job persist-site health (F-068-A regression check)

```sql
-- Confirms the first Sunday weekly run after T-ACT-076 deploy successfully
-- wrote a trading_model_performance row when detect_drift returned drift_status='ok'.
-- Expected: a row with recorded_at within 5 minutes of the most recent Sunday
-- 22:05 UTC, and drift_status IN ('ok','normal','warning','critical','unknown').
-- If no row appears for the Sunday weekly window, check Railway logs for
-- weekly_model_performance_persistent_error events.
SELECT
  recorded_at,
  accuracy_5d,
  accuracy_20d,
  drift_status,
  drift_z_score,
  samples_since_retrain
FROM trading_model_performance
WHERE recorded_at >= NOW() - INTERVAL '8 days'
ORDER BY recorded_at DESC
LIMIT 5;
```

### A.7.4 — Dual-writer pattern observability (F-068-H informational)

```sql
-- Detects the F-068-H dual-writer pattern. Two writers exist on this table:
--   - calibration_engine.write_model_performance at 22:00 UTC (NULL accuracies,
--     drift_status='normal' — sentinel row from a partial computation)
--   - model_retraining.run_weekly_model_performance at 22:05 UTC (full row
--     with accuracies populated, drift_status from detect_drift)
-- A healthy Sunday produces ONE row with accuracies populated. Two rows
-- within a 10-minute window (one with NULL accuracies, one populated) is
-- the F-068-H signature — informational but worth observing post-deploy
-- to confirm the dual-writer is still firing as expected (and that the
-- correct row is being read by the dashboard).
SELECT
  recorded_at,
  accuracy_5d IS NULL AS sentinel_row,
  drift_status,
  recorded_at - LAG(recorded_at) OVER (ORDER BY recorded_at) AS time_since_prev
FROM trading_model_performance
WHERE recorded_at >= NOW() - INTERVAL '7 days'
ORDER BY recorded_at;
```

---

## §A.10 — Function-index status

`trading-docs/07-reference/function-index.md` does not currently exist in the repo (verified at HEAD `00bf518`). Per the workspace constitution rule "no invention without indexing", this PR does NOT create the index from scratch; instead it documents the contract change for `model_retraining.label_prediction_outcomes` here in §3 and in the TASK_REGISTER entry. When the function index is later created (out of scope for this PR), `label_prediction_outcomes` should be entered with the binary-class-space contract (`outcome_direction ∈ {'bull','bear'}`) and a forward-pointer to this handoff note for the F-068-I rationale.

---

## §B — File manifest

| File | Status | Lines | Purpose |
|---|---|---|---|
| `backend/model_retraining.py` | edited | +63/-13 | Scope A (binary labeler) + Scope B (`PostgrestAPIError` import + narrow inner classifier) |
| `supabase/migrations/20260507_widen_drift_status_check.sql` | new | +75 | Scope B (CHECK widening to five-value allowlist) |
| `backend/tests/test_phase_a1.py` | edited | +90/-15 | Re-purposed neutral test + 2 new binary-contract tests |
| `backend/tests/test_t_act_076_weekly_perf_persistent_error.py` | new | +280 | 5 tests for narrow `PostgrestAPIError` classifier (mirrors T-ACT-047 test structure) |
| `trading-docs/08-planning/TASK_REGISTER.md` | edited | +130/-1 | T-ACT-076 entry + T-ACT-081 queued entry + cross-references + audit-trail amendment |
| `trading-docs/06-tracking/HANDOFF_NOTE_2026-05-06_F068I_BINARY_LABELER_FIX.md` | new | this file | Original-intent forensic + Q1-Q12 critique trace + Phase 2 amendments + post-deploy SQL |

---

## §C — Verification status

- ✅ Targeted suite green: 14/14 in `tests/test_phase_a1.py` + `tests/test_t_act_076_weekly_perf_persistent_error.py` (9 pre-existing pass + 2 amended/renamed pass + 3 new pass + 5 new pass)
- ✅ Sibling pattern still green: 5/5 in `tests/test_t_act_047_persistent_error_classification.py` (T-ACT-047 unchanged)
- ✅ Existing model-retraining tests still green: 4/4 in `tests/test_model_retraining.py`
- ✅ Full backend suite zero regressions: baseline `38 failed + 10 errors + 784 passed` → post-merge `38 failed + 10 errors + 791 passed`. Delta exactly +7 = 5 new in `test_t_act_076_weekly_perf_persistent_error.py` + 2 new in `test_phase_a1.py` (re-purposed test counts the same).
- ✅ Pre-existing failures (38+10) are tracked under T-ACT-074 (`test_databento_feed.py` test isolation) and T-ACT-075 (suite-wide pre-existing failure inventory + triage). T-ACT-076 does not touch any of those test files.
- 🟡 Post-deploy validation pending — operator runs §A.7 SQL T+30min and T+7d.

---

## §D — Risks / follow-up

| Risk | Severity | Mitigation |
|---|---|---|
| Q5 regime-dependent confound on stressed weeks (`cv_stress > 70`) | Medium | T-ACT-081 queued; post-deploy SQL §A.7.2 quantifies actual magnitude before any further action |
| Migration not applied before next Sunday cron | High | PR description includes the migration filename in bold; operator must confirm migration applied before merge |
| Hypothetical re-introduction of ternary band | Low | `test_label_prediction_outcomes_never_emits_neutral` source-introspection regression guard |
| F-068-H dual-writer pattern unchanged by this PR | Low / Informational | §A.7.4 query observability; not blocking |
| F-068-B input-row contamination unaffected | Medium | T-ACT-077 deferred to 2026-05-25; T-ACT-076 explicitly disclaims closure |

---

*Owner: Cursor / Authorizer: tesfayekb / Phase 1 critique: GREEN with two flags / Phase 2 EXECUTE: shipped 2026-05-07 with three governance amendments incorporated.*
