# AI Architecture Cross-Cutting Evidence Matrix — Phase 1 P1.2

> **Status:** Read-only cross-cutting matrix per CONSOLIDATED_PLAN_v1.2_APPROVED.md §2 Layer B and §7 Phase 1 P1.2.
> **Purpose:** Map shared dependencies, conflicts, and authority concerns across the 13 AI architecture specs BEFORE per-item audits begin in P1.3. Per the consolidated plan: "prevents auditing Items 1, 6, 10 separately and missing their shared dependency on attribution and calibration eligibility."
> **Authority:** Referenced (NOT modified) by all 13 spec audits in P1.3. Re-build this matrix only when the operator decides the underlying evidence pack baseline has materially drifted.
> **Builds on:** `trading-docs/08-planning/ai-architecture-audits/AI_ARCH_EVIDENCE_PACK.md` (P1.1, all 10 sections including Section 10 Redis Key Inventory). Treats the evidence pack as immutable input.
> **Verification rule:** Produced under the SPEC VERIFICATION PROTOCOL added to `.cursorrules` and `.lovable/rules.md` in Phase 0 P0.2. For dimensions 1–7 of the matrix every claim is falsifiable (path, line, file, decision ID); for dimensions 8–9 (calibration dependencies, training contamination), it is acceptable to write "TBD pending P1.3 spec audit" where the cross-cutting matrix can flag the dependency type but the per-item audit determines specifics. That scope boundary is explicit and intentional.

---

## 1. Snapshot Metadata

**Snapshot date:** 2026-04-26

**Repo HEAD commit on `main`:** `bed60b33b0bb81e7e0a5d0214dbff5121040dd74`

**Repo HEAD message:** `docs(ai-arch): P1.1 - AI architecture evidence pack (#56)`

**Branch the matrix was produced on:** `feature/PLAN-AIARCH-000-phase-1-p1-2-cross-cutting-matrix` (branched from `main` at `bed60b3`)

**Builds on:** `trading-docs/08-planning/ai-architecture-audits/AI_ARCH_EVIDENCE_PACK.md` (P1.1 output, all 10 sections including Section 10 Redis Key Inventory).

**Specs catalogued:** 13 (AI-SPEC-001 through AI-SPEC-013)

**Carry-forward findings from P1.1 tracked in this matrix:**

| # | Finding | Affected specs |
|---|---------|----------------|
| 1 | `gex:updated_at` consumer-only orphan (no producer in code) | AI-SPEC-005, AI-SPEC-013 |
| 2 | `gex:atm_iv` consumer-only orphan (sole consumer `macro_agent.py:214`) | AI-SPEC-001, AI-SPEC-005 |
| 3 | MASTER_PLAN debit-spread feature flags (`strategy:bull_debit_spread:enabled` / `strategy:bear_debit_spread:enabled`) named in plan but absent from code | AI-SPEC-007, AI-SPEC-011, AI-SPEC-012 |
| 4 | `_safe_redis()` is **called** in `prediction_engine.py:120` (against the prompt's framing); its `age_key="gex:updated_at"` has no producer, so the staleness branch always falls through fail-open at line 142–143 (`if ts_raw is None: return raw, True`). Net effect at HEAD: GEX freshness gate is functionally a no-op. | AI-SPEC-005, AI-SPEC-013 (correction noted in §3 Notes; flagged in Risks) |
| 5 | `counterfactual_pnl` is a column triple on `trading_prediction_outputs` (per `20260421_add_counterfactual_pnl.sql`), NOT a separate table — see evidence pack §7.3 / §9.6 | AI-SPEC-010, AI-SPEC-012 |

---

## 2. Spec Identity Map

Stable IDs and clusters per CONSOLIDATED_PLAN_v1.2_APPROVED.md §5. The MASTER_PLAN itself does NOT yet use the `PLAN-{MODULE}-NNN` ID convention internally (per evidence pack §4.2 — MASTER_PLAN currently uses phase labels); these IDs are introduced by the consolidated plan and will be wired into MASTER_PLAN in Phase 5 P5.X.

| AI-SPEC ID | Item Name | Stable ID | Tier | Cluster |
|------------|-----------|-----------|------|---------|
| AI-SPEC-001 | AI Risk Governor | PLAN-AIGOV-001 | V0.1 | A (foundational) |
| AI-SPEC-002 | Strategy Attribution | PLAN-ATTR-001 | V0.1 | A (foundational) |
| AI-SPEC-003 | Synthetic Counterfactual Cases | PLAN-CASE-001 | V0.4 | C (governance/maturation) |
| AI-SPEC-004 | Replay Harness | PLAN-REPLAY-001 | V0.1 | A (foundational) |
| AI-SPEC-005 | Volatility Fair-Value (HAR-RV) | PLAN-VOL-001 | V0.2 | B (alpha-generation) |
| AI-SPEC-006 | Meta-Labeler | PLAN-META-001 | V0.2 | B (alpha-generation) |
| AI-SPEC-007 | Adversarial Pre-Trade Review | PLAN-ADV-001 | V0.4 | C (governance/maturation) |
| AI-SPEC-008 | OPRA Flow Alpha | PLAN-OPRA-001 | V0.2 | B (alpha-generation) |
| AI-SPEC-009 | Exit Optimizer | PLAN-EXIT-001 | V0.2 | B (alpha-generation) |
| AI-SPEC-010 | Counterfactual P&L Attribution | PLAN-CFACT-001 | V0.1 | A (foundational) |
| AI-SPEC-011 | Event-Day Playbooks | PLAN-EVENT-001 | V0.3 | C (governance/maturation) |
| AI-SPEC-012 | Dynamic Capital Allocation | PLAN-ALLOC-001 | V0.3 | C (governance/maturation) |
| AI-SPEC-013 | Realized-vs-Modeled Drift Detection | PLAN-DRIFT-001 | V0.3 | C (governance/maturation) |

**Cluster definitions (per consolidated plan §5):**

- **Cluster A (foundational, V0.1):** Must exist before B/C have data to learn from. Items 1, 2, 4, 10.
- **Cluster B (alpha-generation, V0.2):** Edge-claim work that depends on Cluster A's labels and replay surface. Items 5, 6, 8, 9.
- **Cluster C (governance/maturation, V0.3–V0.4):** Maturation, governance, and replay-validated behaviour. Items 3, 7, 11, 12, 13.

---

## 3. Cross-Cutting Evidence Matrix (CORE — per consolidated plan §2 Layer B)

Each spec evaluated against the 10 audit dimensions verbatim from the consolidated plan:

> 1. Current file/module exists — actual path verified, not assumed
> 2. Current DB table/column exists — migration evidence only
> 3. Redis key exists — producer/consumer evidence (use Section 10 of evidence pack)
> 4. Current behavior matches spec — exact / partial / no
> 5. Spec is future design — mark as proposed, not existing
> 6. Governance conflict — MASTER_PLAN / approved-decisions / TASK_REGISTER
> 7. Authority level — advisory / paper-binding / production-binding / disabled
> 8. Calibration dependency — historical data, labels, replay, archived chains
> 9. Training contamination risk — legacy / synthetic / approximate data
> 10. Implementation owner — Cursor only (T-Rule 1)

For dimensions 1–7 every cell is falsifiable (path, line, file, decision ID). For 8–9, "TBD pending P1.3 spec audit" is permitted where the cross-cutting layer can flag dependency type but per-item audit determines specifics.

---

### AI-SPEC-001 — AI Risk Governor

**Cluster:** A (foundational)
**Tier:** V0.1
**Stable ID:** PLAN-AIGOV-001

| # | Dimension | Finding | Source / Evidence |
|---|-----------|---------|-------------------|
| 1 | File/module exists | **NO.** No file matches `governor` in `backend/`. Closest existing logic: `backend/risk_engine.py` (688 lines) — rule-based risk caps, Kelly sizing, daily −3% halt, `_RISK_PCT` phase ladder (lines 78–83), `_DEBIT_RISK_PCT` overrides (lines 103–111). | Evidence pack §6.1, §8 Item 1; risk_engine functions verified at `risk_engine.py:30, 134, 203, 262, 474, 614, 643, 683`. |
| 2 | DB table/column | **NO** standalone Governor table. Reads/writes existing tables: `trading_positions` (read-write per spec), `trading_sessions` (read for session state), `trading_prediction_outputs` (read for prediction → halt decisions). | Evidence pack §7.1: all three tables exist (`20260416172751_*.sql`). |
| 3 | Redis keys | **Reads:** `risk:halt_threshold_pct` (verified producer `calibration_engine.py:368`); `capital:sizing_phase` (verified producer `calibration_engine.py:641`); `gex:net`, `gex:confidence`, `gex:flip_zone` (all verified producers in `gex_engine.py:163–167`); `polygon:vix:current` (partial); **`gex:atm_iv` (consumer-only orphan — see carry-forward #2)**. **Writes:** new `governor:*` namespace would be added per spec; none exist at HEAD. | Evidence pack §10.2; carry-forward finding #2 (§10.3.3). |
| 4 | Current behavior matches spec | **NO.** No Governor exists; rule-based risk_engine runs. Existing `risk_engine.check_daily_drawdown()` (line 474) and `_apply_sizing_gates()` (line 203) are rule-based per D-005, D-021, D-022 — they predate any Governor concept. | risk_engine.py verified at HEAD `bed60b3`. |
| 5 | Future design? | **YES — proposed, not existing.** | Evidence pack §8 Item 1: "NOT YET IMPLEMENTED." |
| 6 | Governance conflict | **YES.** Three potential conflicts: (a) D-005 daily −3% halt is HARDCODED, NO OVERRIDE (T-Rule 5); the Governor must NEVER override or relax this. (b) D-022 consecutive-loss circuit breaker is automated and mandatory; the Governor must compose with this rather than replacing it. (c) D-021 regime-disagreement 50% reduction is implemented as VVIX Z-score + `regime_agreement` flag (per D-021 IMPLEMENTATION NOTE); the Governor cannot reintroduce HMM/LightGBM until explicitly tasked in Phase 3A. | `approved-decisions.md` D-005 (lines 33–36), D-021 (lines 100–120), D-022 (lines 122–125); constitution T-Rules 4, 5. |
| 7 | Authority level proposed | **paper-binding initially → production-binding after gate.** Per consolidated plan tier V0.1 Cluster A, the Governor is binding in the paper-trading regime; promotion to production-binding requires the 90-day A/B gate (per system-state.md `live_trading: blocked_until_90day_AB_test_passes`). | system-state.md lines 7–8; MASTER_PLAN line 287–288. |
| 8 | Calibration dependencies | TBD pending P1.3 spec audit. **Cross-cutting flag:** depends on AI-SPEC-002 (attribution) for sizing inputs, on AI-SPEC-013 (drift detection) for demotion paths. | See §7 dependency graph. |
| 9 | Training contamination risk | TBD pending P1.3 spec audit. **Cross-cutting flag:** any Governor that learns from historical labels carries the same legacy-data risk as Item 6 — the 12K meta-label scaffold is dormant pending 100 closed paper trades, so training data is currently insufficient. | system-state.md line 36; evidence pack §8 Item 6. |
| 10 | Implementation owner | Cursor (per T-Rule 1; only Cursor implements). | constitution.md T-Rule 1. |

**Notes:**
- **Conflict with AI-SPEC-009 (Exit Optimizer):** Item 1 mentions "halt path writes new exit reasons via Risk Governor" but at HEAD `risk_engine.py` contains **zero** `exit_reason` occurrences (verified by `grep`). All exit reasons at HEAD live in `position_monitor.py` lines 132, 174, 211, 225, 379, 458, 549, 616, 625, 765, 781, 805 — taxonomy: `time_stop_230pm_d010`, `time_stop_345pm_d011`, `emergency_backstop`, `watchdog_engine_silent`, `eod_reconciliation_stale_open`, `straddle_pre_event_exit`, `take_profit_debit_100pct`, `stop_loss_debit_100pct`, `take_profit_40pct`, `cv_stress_exit_d017`, `stop_loss_150pct_credit`. **The Governor cannot add a halt-path exit reason to `risk_engine.py` without also touching `position_monitor.py`** — this is a cross-spec module boundary that P1.3 must resolve.
- **Conflict with AI-SPEC-012 (Capital Allocation):** Both modify `risk_engine.py`. Item 12 also targets the `_RISK_PCT` ladder fix (carry-forward governance debt §9.4 — ladder is non-monotonic at HEAD: Phase 1 0.010 > Phase 2 0.0075). Both specs cannot independently rewrite this ladder; sequencing required.
- **Carry-forward #2:** `gex:atm_iv` is consumed by `macro_agent.py:214` but has no producer. If Item 1 cites this key, P1.3 must clarify whether it is read-as-input or produce-and-read.

---

### AI-SPEC-002 — Strategy Attribution

**Cluster:** A (foundational)
**Tier:** V0.1
**Stable ID:** PLAN-ATTR-001

| # | Dimension | Finding | Source / Evidence |
|---|-----------|---------|-------------------|
| 1 | File/module exists | **NO.** No file matches "attribution" in `backend/`. Closest existing logic: `backend/strategy_performance_matrix.py` (229 lines, 12D — D3 Regime × Strategy Performance Matrix) provides regime × strategy aggregation but not per-trade attribution. | Evidence pack §6.1, §8 Item 2. |
| 2 | DB table/column | **NO.** Three tables referenced by spec do not exist: `strategy_attribution`, `trade_counterfactual_cases`, `strategy_utility_labels`. Spec also reads from `trading_positions` (exists) for source data. | Evidence pack §7.2 — all three confirmed by `grep` returning zero matches across all 68 migration files. |
| 3 | Redis keys | **Reads/writes:** new `attribution:*` namespace per spec. None exist at HEAD. The closest existing per-cell write is `strategy_matrix:{regime}:{strategy}` (dynamic pattern, written by `strategy_performance_matrix.py`, read by `strategy_selector.py:154`). | Evidence pack §10.2 (`strategy_matrix:*` row). |
| 4 | Current behavior matches spec | **NO.** Per-trade utility labels are not currently written anywhere. `strategy_performance_matrix.py` aggregates ex-post but does not label per-trade. | Evidence pack §8 Item 2. |
| 5 | Future design? | **YES — proposed, not existing.** | Evidence pack §8 Item 2. |
| 6 | Governance conflict | **NO direct conflict** with locked decisions, but creates dependency: every B/C cluster spec that learns from labels (Items 5, 6, 8, 9, 11, 13) implicitly assumes Item 2 has shipped first. This is the rationale for placing Item 2 in Cluster A. | See §7 dependency graph. |
| 7 | Authority level proposed | **advisory.** Attribution is a labeling layer; it does not gate trading decisions directly. Per consolidated plan §5 Tier V0.1 Cluster A, attribution provides inputs but not authority. | Per consolidated plan §5. |
| 8 | Calibration dependencies | TBD pending P1.3 spec audit. **Cross-cutting flag:** Item 2 itself is the calibration source for everyone else. It depends on `trading_positions` row history (closed positions) reaching 100+ rows per system-state.md gate; today's count is below this threshold. | system-state.md "Phase Gate for Real Capital Deployment" (line 36): "Minimum 100 closed paper trades for meta-label model." |
| 9 | Training contamination risk | **HIGH on legacy data.** Pre-Item-2 closed positions in `trading_positions` lack any utility label; backfilling labels for historical positions requires reconstructing context (regime, GEX, VVIX) from logs that may not be retained. P1.3 spec audit must determine cutover policy. | TBD pending P1.3. |
| 10 | Implementation owner | Cursor. | T-Rule 1. |

**Notes:**
- Item 2 is the **single most-depended-on item** in the cluster. Per §7 dependency graph, Items 1, 5, 6, 8, 9, 11, 12, 13 all depend on attribution labels (directly or via Item 6). This makes Item 2 the critical path for V0.1.

---

### AI-SPEC-003 — Synthetic Counterfactual Case Generation

**Cluster:** C (governance/maturation)
**Tier:** V0.4
**Stable ID:** PLAN-CASE-001

| # | Dimension | Finding | Source / Evidence |
|---|-----------|---------|-------------------|
| 1 | File/module exists | **NO.** No "synthetic" / "case_generation" file. The existing `counterfactual_engine.py` (Item 10 / 12E) is observability over **real** no-trade signals, not synthetic case generation — these are different problems. | Evidence pack §6.1, §8 Item 3, §8 Item 10. |
| 2 | DB table/column | **NO.** No `synthetic_*` table. Item 2's proposed `trade_counterfactual_cases` is for real-trade counterfactuals; Item 3 needs a separate synthetic-case table not yet specified at the schema level. | Evidence pack §7.2. |
| 3 | Redis keys | None at HEAD; new namespace per spec (TBD per item). | Evidence pack §10.2 (no entries). |
| 4 | Current behavior matches spec | **NO.** Synthetic case generation is conceptually distinct from observability; nothing at HEAD performs this. | Evidence pack §8 Item 3. |
| 5 | Future design? | **YES — proposed, not existing.** Tier V0.4 (latest tier per consolidated plan §5). | Evidence pack §8 Item 3. |
| 6 | Governance conflict | **NO direct conflict.** Cluster C placement signals it is downstream of A and B. | Per consolidated plan §5. |
| 7 | Authority level proposed | **advisory.** Synthetic cases are training data, not trade-time gates. | Per consolidated plan §5 V0.4. |
| 8 | Calibration dependencies | TBD pending P1.3 spec audit. **Cross-cutting flag:** depends on AI-SPEC-004 (replay harness) and AI-SPEC-010 (real counterfactual baseline) — synthetic cases must be validated against real-trade behavior before they are admissible as training inputs. | See §7 dependency graph. |
| 9 | Training contamination risk | **HIGH — synthetic by definition.** Synthetic data poisoning is the central governance challenge of this spec. P1.3 must define provenance flags, segregation rules, and replay validation requirements. | TBD pending P1.3. |
| 10 | Implementation owner | Cursor. | T-Rule 1. |

**Notes:**
- Tier V0.4 placement means this is the **last** spec to ship in the V0.x sequence. P1.3 audit can be deprioritized relative to V0.1/V0.2 specs.

---

### AI-SPEC-004 — Replay Harness

**Cluster:** A (foundational)
**Tier:** V0.1
**Stable ID:** PLAN-REPLAY-001

| # | Dimension | Finding | Source / Evidence |
|---|-----------|---------|-------------------|
| 1 | File/module exists | **NO.** `ls backend/ \| grep -iE 'replay'` returns no matches. No replay infrastructure at HEAD. | Evidence pack §6.1, §8 Item 4. |
| 2 | DB table/column | **NO.** Four tables referenced by spec do not exist: `replay_eval_runs`, `replay_eval_cases`, `replay_eval_results`, `item_promotion_records`. | Evidence pack §7.2 — all four confirmed missing. |
| 3 | Redis keys | None at HEAD; potential new namespace per spec (`replay:*`, TBD). | Evidence pack §10.2 (no entries). |
| 4 | Current behavior matches spec | **NO.** Closest existing surface is the test suite (`backend/tests/`), which is unit-level, not historical replay. Phase 3B `shadow_engine.py` (456 lines) runs daily A/B comparisons forward — not the same as the spec's offline replay over archived option chains. | Evidence pack §6.1 (`shadow_engine.py`); MASTER_PLAN lines 272–276. |
| 5 | Future design? | **YES — proposed, not existing.** | Evidence pack §8 Item 4. |
| 6 | Governance conflict | **NO direct conflict.** **Touchpoint:** the spec implies archived option-chain storage; T-Rule 1 (foundation isolation) requires any replay tables to use `trading_` prefix per T-Rule 2. | constitution.md T-Rules 1, 2. |
| 7 | Authority level proposed | **advisory.** Replay results inform but do not directly gate live trading. Promotion records (`item_promotion_records`) ARE binding for spec-promotion governance. | Per consolidated plan §5 V0.1. |
| 8 | Calibration dependencies | TBD pending P1.3 spec audit. **Cross-cutting flag:** depends on archived option-chain data (which the consolidated plan §1 lists as a known archival gap). Item 4 cannot be calibration-grade without that archive. | TBD pending P1.3. |
| 9 | Training contamination risk | **HIGH on archive completeness.** Replay correctness depends on chain-archive fidelity. Missing strikes/expiries silently corrupt eval results. | TBD pending P1.3. |
| 10 | Implementation owner | Cursor. | T-Rule 1. |

**Notes:**
- Item 4 is the **second most-depended-on item** in Cluster A. Items 3, 6, 13 all depend on replay-validated baselines. Together with Item 2, Item 4 forms the V0.1 critical path.
- Spec governance decision needed in P1.3: how does `item_promotion_records` interact with the existing `paper_phase_criteria` table (12 go-live criteria per D-013)? Both gate promotion; clarity on which is authoritative is needed.

---

### AI-SPEC-005 — Volatility Fair-Value Engine (HAR-RV)

**Cluster:** B (alpha-generation)
**Tier:** V0.2
**Stable ID:** PLAN-VOL-001

| # | Dimension | Finding | Source / Evidence |
|---|-----------|---------|-------------------|
| 1 | File/module exists | **NO.** No HAR-RV file in `backend/`. **Closest existing logic:** `backend/polygon_feed.py:realized_vol_20d` Redis writer (12A, fixed in B1-2 to use 21:00 UTC EOD gate) — provides one input (20-day daily realized vol) to a future HAR-RV model. | Evidence pack §6.1, §8 Item 5. |
| 2 | DB table/column | **NO** new table mandatory. Spec likely reads `trading_prediction_outputs` for output-vs-realized comparison; that table exists. | Evidence pack §7.1. |
| 3 | Redis keys | **Reads:** `polygon:spx:realized_vol_20d` (verified, evidence pack §10.2; producer `polygon_feed.py` 12A; consumer `prediction_engine`); `polygon:vvix:z_score`, `polygon:vix:z_score_daily` (both verified `setex 7200s`); `gex:net` (verified). **Carry-forward #1 / #4 risk:** Item 5 likely uses `_safe_redis()` for staleness, but the staleness path is non-functional at HEAD because `gex:updated_at` has no producer (see §1 metadata, carry-forward #4). | Evidence pack §10.2; HEAD verification of `prediction_engine.py:120`. |
| 4 | Current behavior matches spec | **NO.** HAR-RV (heterogeneous autoregressive realized volatility) requires a fitted regression model; nothing at HEAD computes a fair-value forecast. | Evidence pack §8 Item 5. |
| 5 | Future design? | **YES — proposed, not existing.** | Evidence pack §8 Item 5. |
| 6 | Governance conflict | **POTENTIAL CONFLICT with D-016** (Volatility Blending: `sigma = max(realized, 0.70 × implied)`). HAR-RV would replace or augment the realized-vol input to D-016; P1.3 must determine whether HAR-RV becomes the new "realized" feeder OR whether D-016 is amended. T-Rule 4: D-016 cannot be modified, deferred, or reinterpreted without explicit owner approval and a new decision record. | approved-decisions.md D-016 (lines 90–93); constitution T-Rule 4. |
| 7 | Authority level proposed | **advisory → paper-binding.** Per consolidated plan §5 V0.2 Cluster B, fair-value outputs feed strategy selection but do not directly halt; promotion to paper-binding goes through Item 4 (replay) validation. | Per consolidated plan §5. |
| 8 | Calibration dependencies | TBD pending P1.3 spec audit. **Cross-cutting flag:** depends on AI-SPEC-002 (calibration labels) + multi-year realized-vol history. Today's `polygon:spx:realized_vol_20d` writer (12A) is the primary input; need to verify the EOD ring buffer has enough days populated. | TBD pending P1.3. |
| 9 | Training contamination risk | **MEDIUM.** Realized-vol history is approximate before B1-2 fix (12A EOD gate moved 19 → 21 UTC); any realized-vol data written before commit `fc64840` (2026-04-20) was potentially mistimed. | Evidence pack §5.2 B1-2. |
| 10 | Implementation owner | Cursor. | T-Rule 1. |

**Notes:**
- **Carry-forward #4 contradiction:** the original P1.2 prompt characterized `_safe_redis()` as "defined but never called". Verification at HEAD shows it IS called once (`prediction_engine.py:120` with `age_key="gex:updated_at"`). The functional issue is different: because `gex:updated_at` has no producer, the function falls through fail-open at line 142–143 (`if ts_raw is None: return raw, True`). Item 5 audits should treat the freshness gate as a no-op until `gex:updated_at` is wired, NOT as missing infrastructure.

---

### AI-SPEC-006 — Meta-Labeler

**Cluster:** B (alpha-generation)
**Tier:** V0.2
**Stable ID:** PLAN-META-001

| # | Dimension | Finding | Source / Evidence |
|---|-----------|---------|-------------------|
| 1 | File/module exists | **PARTIAL — SCAFFOLD EXISTS (dormant).** Scaffold lives **inside** `backend/model_retraining.py` (1177 lines total) and `backend/execution_engine.py` (gate at line 358). No standalone `backend/meta_label*.py` file exists. | Evidence pack §6.1, §8 Item 6. Verified: `execution_engine.py:358` reads `model:meta_label:enabled`. |
| 2 | DB table/column | Reads `trading_prediction_outputs` (existing, evidence pack §7.1). The 12K scaffold uses `outcome_label` columns added by `20260422_ensure_prediction_outcome_columns.sql`. No dedicated `meta_label_*` migration. | Evidence pack §5.1, §7.1. |
| 3 | Redis keys | **`model:meta_label:enabled`** — feature flag wired in B1-5 (commit `fc64840`); consumer `execution_engine.py:358`; producer is `set-feature-flag` Edge Function (out-of-tree). Fail-open ENABLED. | Evidence pack §10.2 (`model:meta_label:enabled` row). |
| 4 | Current behavior matches spec | **PARTIAL.** Scaffold is dormant; activates at ≥100 closed paper trades per system-state.md (line 36). At HEAD, 9 features (was 10 before B1-4 dropped the constant `signal_weak`); inference path is wired in `execution_engine.py:358`. The model itself has no trained weights yet. | Evidence pack §8 Item 6 (last 4 bullets). |
| 5 | Future design? | **PARTIAL — scaffold-yes, model-no.** Per dimension 5's text: "Spec is future design — mark as proposed, not existing." Scaffold infrastructure is implemented; the trained model and its threshold logic are not. | Evidence pack §8 Item 6. |
| 6 | Governance conflict | **POTENTIAL CONFLICT with D-015** (Slippage Model: "Predictive LightGBM, not static" — IMPLEMENTATION NOTE: never built; meta-label model in Phase 3A will capture real slippage data for future training). The meta-labeler may consume slippage labels generated as a side-effect of its own training data. P1.3 must trace this loop. **Conflict with D-021** (Regime Guard HMM ≠ LightGBM): D-021 prohibits building HMM/LightGBM until explicitly tasked in Phase 3A; the meta-label scaffold uses LightGBM, which IS the explicit Phase 3A task. So D-021 is **resolved** for this spec — but P1.3 must confirm. | approved-decisions.md D-015 (lines 84–88), D-021 (lines 100–120). |
| 7 | Authority level proposed | **paper-binding (gated dormant currently).** Inference gate at `execution_engine.py:358` is wired but fail-open; activating real-capital binding requires the 90-day A/B gate. | system-state.md line 8; MASTER_PLAN line 287–288. |
| 8 | Calibration dependencies | TBD pending P1.3 spec audit. **Cross-cutting flag:** depends on AI-SPEC-002 (labels) + AI-SPEC-004 (replay validation). Activation gated on ≥100 closed paper trades. | system-state.md line 36. |
| 9 | Training contamination risk | **HIGH on dormant features.** B1-4 dropped `signal_weak` from 12K/12M feature vectors because it was constant; if any other features become constant in production data, training silently degrades. P1.3 must specify monitoring. | Evidence pack §5.2 B1-4. |
| 10 | Implementation owner | Cursor. | T-Rule 1. |

**Notes:**
- The meta-label scaffold is the **template** for how Cluster B specs should ship: scaffold + dormant + feature flag + activation gate. P1.3 should explicitly cite this pattern when scoping Items 5, 8, 9.

---

### AI-SPEC-007 — Adversarial Pre-Trade Review

**Cluster:** C (governance/maturation)
**Tier:** V0.4
**Stable ID:** PLAN-ADV-001

| # | Dimension | Finding | Source / Evidence |
|---|-----------|---------|-------------------|
| 1 | File/module exists | **NO.** No file matches "adversarial" or "pretrade_review" in `backend/` or `backend_agents/`. | Evidence pack §6.1, §8 Item 7. |
| 2 | DB table/column | **NO** dedicated table at HEAD. Spec likely writes review records to a new `trading_pretrade_reviews` table (TBD). | Evidence pack §7. |
| 3 | Redis keys | None at HEAD; new namespace per spec. | Evidence pack §10.2 (no entries). |
| 4 | Current behavior matches spec | **NO.** Pre-trade review is conceptually adversarial (red-team an AI proposal); nothing at HEAD performs this. | Evidence pack §8 Item 7. |
| 5 | Future design? | **YES — proposed, not existing.** Tier V0.4 (last). | Evidence pack §8 Item 7. |
| 6 | Governance conflict | **TOUCHPOINT with `strategy:bull_debit_spread:enabled` / `strategy:bear_debit_spread:enabled` governance debt** (carry-forward #3): if the spec proposes adversarial review of strategy-flag changes, the absent debit-spread flags are a governance hole that pre-trade review would likely flag. **NO direct conflict** with locked decisions. | Evidence pack §10.3.1; MASTER_PLAN lines 59–60. |
| 7 | Authority level proposed | **advisory → paper-binding.** Per consolidated plan §5 V0.4: review can BLOCK a trade in paper but should not in production until validated. Promotion to production-binding through Item 4 (replay) and Item 1 (Governor authority). | Per consolidated plan §5. |
| 8 | Calibration dependencies | TBD pending P1.3 spec audit. **Cross-cutting flag:** depends on AI-SPEC-001 (Governor authority hierarchy) + AI-SPEC-006 (meta-labeler trust). Adversarial review must know what the meta-labeler trusts to attack it. | See §7 dependency graph. |
| 9 | Training contamination risk | **MEDIUM.** Adversarial training data is by nature counter-factual; the spec must define how adversarial cases are excluded from real-trade label training (Item 2). | TBD pending P1.3. |
| 10 | Implementation owner | Cursor. | T-Rule 1. |

**Notes:**
- Item 7 is the **only Cluster C item** that directly touches Item 1 (Governor authority). P1.3 must define this hand-off carefully.

---

### AI-SPEC-008 — OPRA Flow Alpha

**Cluster:** B (alpha-generation)
**Tier:** V0.2
**Stable ID:** PLAN-OPRA-001

| # | Dimension | Finding | Source / Evidence |
|---|-----------|---------|-------------------|
| 1 | File/module exists | **NO.** No "opra_alpha" file. The existing `backend/databento_feed.py` (447 lines) ingests OPRA trades but only writes `databento:opra:trades` Redis list — no alpha-extraction logic. `backend_agents/flow_agent.py` (343 lines) is the closest relevant agent (consumes Unusual Whales / put-call ratios). | Evidence pack §6.1, §8 Item 8. |
| 2 | DB table/column | **NO** dedicated table. Spec likely reads from `trading_signals` (existing) and writes alpha-flag rows. | Evidence pack §7.1. |
| 3 | Redis keys | **Reads:** `databento:opra:trades` (verified producer `databento_feed.py:348` lpush, 300s TTL); `databento:opra:gex_block` and `databento:opra:confidence_impact` (both verified producer `databento_feed.py:419, 428`). **New writes:** likely `opra:alpha:*` namespace per spec (TBD). | Evidence pack §10.2. |
| 4 | Current behavior matches spec | **NO.** OPRA alpha extraction is not performed; trades are ingested only for GEX computation. | Evidence pack §8 Item 8. |
| 5 | Future design? | **YES — proposed, not existing.** | Evidence pack §8 Item 8. |
| 6 | Governance conflict | **POTENTIAL CONFLICT with D-008** (Data Budget ~$150–200/month). Item 8 may imply richer OPRA processing or supplementary feeds (e.g., Unusual Whales paid tier from MASTER_PLAN backlog #18). T-Rule 4: D-008 binding. | approved-decisions.md D-008 (lines 48–51); MASTER_PLAN backlog item 18. |
| 7 | Authority level proposed | **advisory.** Flow alpha is one input among many; Item 8 should not directly halt or enable per consolidated plan §5 V0.2. | Per consolidated plan §5. |
| 8 | Calibration dependencies | TBD pending P1.3 spec audit. **Cross-cutting flag:** depends on AI-SPEC-002 (attribution to test alpha-claim). Without attribution, alpha claims are unfalsifiable. | See §7 dependency graph. |
| 9 | Training contamination risk | **MEDIUM.** OPRA trade ingestion is short-window (300s TTL on `databento:opra:trades`); training data for flow-alpha must be archived externally. P1.3 must specify the archival path. | TBD pending P1.3. |
| 10 | Implementation owner | Cursor. | T-Rule 1. |

**Notes:**
- Item 8's training-data archival need overlaps with AI-SPEC-004 (Replay Harness) — both need archived OPRA flow. P1.3 should consider whether they share infrastructure.

---

### AI-SPEC-009 — Exit Optimizer

**Cluster:** B (alpha-generation)
**Tier:** V0.2
**Stable ID:** PLAN-EXIT-001

| # | Dimension | Finding | Source / Evidence |
|---|-----------|---------|-------------------|
| 1 | File/module exists | **NO.** No "exit_optimizer" file. **Existing exit logic** lives in `backend/position_monitor.py` (858 lines): rule-based time stops (D-010 2:30 PM short-gamma at line 132, D-011 3:45 PM long-gamma at line 174) and CV_Stress conditions (D-017 at line 781). | Evidence pack §6.1, §8 Item 9. |
| 2 | DB table/column | Reads `trading_positions` (exists). Spec likely writes optimizer outputs back to `trading_positions.exit_reason` (existing column, populated by `position_monitor.py`). | Evidence pack §7.1. |
| 3 | Redis keys | **Reads:** existing position state (mostly via DB, not Redis). May read `gex:nearest_wall`, `gex:flip_zone` (verified producers) for exit-aware decisions. **New writes:** TBD per spec. | Evidence pack §10.2. |
| 4 | Current behavior matches spec | **NO.** Existing exits are rule-based (D-010, D-011, D-017); spec proposes learned exit timing. | Evidence pack §8 Item 9. |
| 5 | Future design? | **YES — proposed, not existing.** | Evidence pack §8 Item 9. |
| 6 | Governance conflict | **HARD CONFLICT with D-010 + D-011** (T-Rule 6: Mandatory Time Stops — automated and CANNOT be overridden). Per T-Rule 4, D-010 and D-011 are final and binding. Item 9 cannot override these stops; it can only add additional, *earlier* exit conditions or alter intra-position exits before the time stops fire. **HARD CONFLICT with D-017** (CV_Stress only triggers when P&L ≥ 50% of max profit) — Item 9 must respect this floor. | approved-decisions.md D-010 (lines 58–61), D-011 (lines 63–66), D-017 (lines 95–98); constitution T-Rules 4, 6. |
| 7 | Authority level proposed | **paper-binding (with hard caps).** Item 9 can shift exit timing within the D-010/D-011/D-017 envelope but cannot violate it. | Constitutional limit. |
| 8 | Calibration dependencies | TBD pending P1.3 spec audit. **Cross-cutting flag:** depends on AI-SPEC-002 (attribution per-exit-reason) — to learn exit-optimal timing, you need labels per exit_reason. | See §7 dependency graph. |
| 9 | Training contamination risk | **HIGH on legacy exit data.** Pre-spec exits have no learned-vs-rule label; backfilling requires reconstructing whether each exit fired due to rule (D-010/D-011) or earlier signal. P1.3 must specify cutover. | TBD pending P1.3. |
| 10 | Implementation owner | Cursor. | T-Rule 1. |

**Notes:**
- Item 9's **constitutional ceiling** is the hardest of any spec: D-010, D-011, D-017 are all binding. Spec wording must explicitly acknowledge these as inviolable.
- **Cross-spec module conflict:** Item 9 reads exit_reasons from `position_monitor.py`; Item 1 (Governor) writes new exit_reasons. Sequencing required so the taxonomies don't drift.

---

### AI-SPEC-010 — Counterfactual P&L Attribution

**Cluster:** A (foundational)
**Tier:** V0.1
**Stable ID:** PLAN-CFACT-001

| # | Dimension | Finding | Source / Evidence |
|---|-----------|---------|-------------------|
| 1 | File/module exists | **YES — SCAFFOLD EXISTS (observability-only).** `backend/counterfactual_engine.py` (406 lines at HEAD; +349 at commit `2400e98`). Functions verified: `_fetch_spx_price_after_signal()` line 65, `_simulate_pnl()` line 109, `label_counterfactual_outcomes()` line 146, `generate_weekly_summary()` line 265, `run_counterfactual_job()` line 366. EOD job runs at 4:25 PM ET (per evidence pack §8 Item 10). | Evidence pack §6.1, §8 Item 10. Verified: line numbers from `grep '^def\\|run_counterfactual'` against HEAD. |
| 2 | DB table/column | **PARTIAL — column triple, not table.** `20260421_add_counterfactual_pnl.sql` adds 3 columns to `trading_prediction_outputs`: `counterfactual_pnl NUMERIC(10,2)`, `counterfactual_strategy TEXT`, `counterfactual_simulated_at TIMESTAMPTZ`, plus a partial index. **Per migration header: "Pure observability — never read by any trading-decision path."** | Evidence pack §7.3. **Carry-forward #5.** |
| 3 | Redis keys | **`feedback:counterfactual:enabled`** — feature flag wired in B1-5; consumer `counterfactual_engine.py:168`; producer is `set-feature-flag` Edge Function. Fail-open ENABLED if Redis-down. | Evidence pack §10.2 (`feedback:counterfactual:enabled` row). |
| 4 | Current behavior matches spec | **PARTIAL — observability shipped; attribution surface to other specs not shipped.** Today the columns are written daily but never read by trading decisions; the data flow into Items 1, 2, 6, 12 is not wired. | Evidence pack §8 Item 10. |
| 5 | Future design? | **PARTIAL.** The observability scaffold is done; the spec's downstream integration with Items 1, 2, 12 is proposed. | Evidence pack §8 Item 10. |
| 6 | Governance conflict | **NO direct conflict.** Migration explicitly states "never read by any trading-decision path" — a deliberate scope limit consistent with T-Rule 8's sequential build order. | `20260421_add_counterfactual_pnl.sql` header. |
| 7 | Authority level proposed | **disabled (observability-only at HEAD) → advisory after wiring.** Promotion to advisory requires P1.3 spec audit + downstream wiring. | Migration header. |
| 8 | Calibration dependencies | TBD pending P1.3 spec audit. **Cross-cutting flag:** depends on AI-SPEC-004 (replay) for synthetic counterfactuals. Real counterfactuals are already produced; synthetic counterfactuals are AI-SPEC-003. | See §7 dependency graph. |
| 9 | Training contamination risk | **LOW for observability use; HIGH if downstream specs consume as labels.** Today's counterfactuals use a single static strategy (`iron_condor` default) — that is a contamination risk if downstream training treats it as the optimal counterfactual rather than the conservative one. | Evidence pack §7.3. |
| 10 | Implementation owner | Cursor. | T-Rule 1. |

**Notes:**
- **Carry-forward #5:** `counterfactual_pnl` is a column triple, not a table. P1.3 must use this framing when discussing schema impact.
- **Cross-spec dependency:** Item 12 (Capital Allocation) cites counterfactual P&L as an input. P1.3 must verify the column-not-table framing in Item 12's schema requirements.

---

### AI-SPEC-011 — Event-Day Playbooks

**Cluster:** C (governance/maturation)
**Tier:** V0.3
**Stable ID:** PLAN-EVENT-001

| # | Dimension | Finding | Source / Evidence |
|---|-----------|---------|-------------------|
| 1 | File/module exists | **NO.** No "playbook" file. **Closest existing logic:** `backend_agents/economic_calendar.py:_compute_earnings_proximity_score()` (B1-3, 2026-04-20) — produces a 0–1 proximity score consumed by `prediction_engine`, but is not a playbook. | Evidence pack §6.2, §8 Item 11. |
| 2 | DB table/column | **NO** dedicated table. Spec likely reads `trading_signals` and `trading_sessions` plus the `earnings_calendar` table (Phase 5A, exists per `20260426_earnings_system.sql`). | Evidence pack §7.1. |
| 3 | Redis keys | **Reads:** `calendar:today:intel` (verified producer `economic_calendar.py:402`), `calendar:earnings_proximity_score` (verified producer `economic_calendar.py:427` from B1-3, 86400s TTL). **Touchpoint with carry-forward #3:** Item 11 may propose new strategy flags for event-day strategies; if so, the bull/bear debit-spread flag governance debt is on the playbook surface. | Evidence pack §10.2. |
| 4 | Current behavior matches spec | **NO.** Earnings-proximity score exists; event-day playbooks (which strategy to run on FOMC day, NFP day, CPI day) are not codified. | Evidence pack §8 Item 11. |
| 5 | Future design? | **YES — proposed, not existing.** | Evidence pack §8 Item 11. |
| 6 | Governance conflict | **NO direct conflict.** **Touchpoint with Rule 5** (MASTER_PLAN: Feature Flags for Every New Strategy — OFF by default until 20+ paper trades). Any new strategy in a playbook needs a feature flag. | MASTER_PLAN lines 54–63. |
| 7 | Authority level proposed | **paper-binding.** Per consolidated plan §5 V0.3 Cluster C, playbooks shape strategy selection. | Per consolidated plan §5. |
| 8 | Calibration dependencies | TBD pending P1.3 spec audit. **Cross-cutting flag:** depends on AI-SPEC-002 (attribution per regime) — playbooks need regime-attributed historical performance to choose strategies. | See §7 dependency graph. |
| 9 | Training contamination risk | **MEDIUM.** Event-day samples are sparse (FOMC ~8/yr, NFP ~12/yr, CPI ~12/yr); small-sample bias is inherent. P1.3 must specify minimum-sample requirements. | TBD pending P1.3. |
| 10 | Implementation owner | Cursor. | T-Rule 1. |

**Notes:**
- Carry-forward #3 surfaces here: if Item 11 adds event-day strategies (long_call, long_put), they need feature flags. The MASTER_PLAN-named bull/bear debit flags do NOT exist in code; Item 11 must not assume they do.

---

### AI-SPEC-012 — Dynamic Capital Allocation

**Cluster:** C (governance/maturation)
**Tier:** V0.3
**Stable ID:** PLAN-ALLOC-001

| # | Dimension | Finding | Source / Evidence |
|---|-----------|---------|-------------------|
| 1 | File/module exists | **NO.** No `capital_allocation_snapshots` migration. **Existing capital tracking:** `backend/capital_manager.py` (266 lines) — does not expose a snapshot table or dynamic-allocation engine. **Sizing-phase auto-advance** (12N, ladder per `_RISK_PCT` in `risk_engine.py:78–83`) is the closest existing surface. | Evidence pack §6.1, §8 Item 12. |
| 2 | DB table/column | **NO.** `capital_allocation_snapshots` referenced by spec does not exist. **Reads:** `trading_positions` (exists), `trading_sessions` (exists), `trading_prediction_outputs.counterfactual_pnl` (column triple per carry-forward #5). | Evidence pack §7.2; §7.3. |
| 3 | Redis keys | **Reads:** `capital:deployment_pct` (verified producer `main.py:1698`), `capital:leverage_multiplier` (verified producer `main.py:1700`), `capital:live_equity` (verified producer `capital_manager.py:160`), `capital:sizing_phase` and `capital:sizing_phase_advanced_at` (verified producers in `calibration_engine.py`). **Writes:** new namespace per spec (TBD). **Touchpoint with carry-forward #3:** if spec proposes per-strategy allocation, debit-spread flag absence is a governance hole. | Evidence pack §10.2. |
| 4 | Current behavior matches spec | **NO.** Sizing phase advances automatically (12N) but capital is allocated by static `_RISK_PCT[phase]` lookup; no dynamic per-regime allocation. | Evidence pack §6.1; risk_engine.py lines 78–83. |
| 5 | Future design? | **YES — proposed, not existing.** | Evidence pack §8 Item 12. |
| 6 | Governance conflict | **HARD CONFLICT with D-004** (Capital Allocation: Core + Satellites + Reserve, RCS-dynamic). Item 12 must compose with D-004's existing structure. **HARD CONFLICT with D-005** (T-Rule 5: −3% daily halt hardcoded, NO override). **HARD CONFLICT with D-014** (Position Sizing: 4 phases with advance criteria and automatic regression). **CONFLICT with carry-forward #4 (governance debt §9.4):** the `_RISK_PCT` ladder is non-monotonic at HEAD (Phase 1 0.010 > Phase 2 0.0075). Item 12 explicitly does NOT fix this per consolidated plan; the fix is a separate task before Day 40 of paper trading. **CONFLICT with AI-SPEC-001:** both modify `risk_engine.py`. | approved-decisions.md D-004, D-005, D-014; evidence pack §9.4. |
| 7 | Authority level proposed | **paper-binding → production-binding.** Per consolidated plan §5 V0.3, capital allocation is binding within the D-005/D-014 envelope. | system-state.md "Phase Gate for Real Capital Deployment". |
| 8 | Calibration dependencies | TBD pending P1.3 spec audit. **Cross-cutting flag:** depends on AI-SPEC-001 (Governor) + AI-SPEC-002 (attribution) + AI-SPEC-013 (drift demotion paths). Multi-input dependency. | See §7 dependency graph. |
| 9 | Training contamination risk | **MEDIUM.** Capital allocation has feedback loops (more capital → more trades → more labels → more allocation); P1.3 must specify safeguards. | TBD pending P1.3. |
| 10 | Implementation owner | Cursor. | T-Rule 1. |

**Notes:**
- Item 12 has the **most cross-spec dependencies** (1, 2, 13). It is the keystone of Cluster C and should be sequenced last among the V0.3 specs.
- **`risk_engine.py` collision with Items 1 and 13:** all three modify the same file; sequencing required.

---

### AI-SPEC-013 — Realized-vs-Modeled Drift Detection

**Cluster:** C (governance/maturation)
**Tier:** V0.3
**Stable ID:** PLAN-DRIFT-001

| # | Dimension | Finding | Source / Evidence |
|---|-----------|---------|-------------------|
| 1 | File/module exists | **PARTIAL — SCAFFOLD EXISTS (model-output drift only — does NOT yet cover realized-vs-modeled metric drift).** Drift logic lives inside `backend/model_retraining.py` (1177 lines total, 37 occurrences of `drift`); commit `db4c9d9` (2026-04-20). No standalone drift module. | Evidence pack §6.1, §8 Item 13. Verified: 37 `drift` matches in `model_retraining.py`. |
| 2 | DB table/column | **NO.** Three tables referenced by spec do not exist: `drift_metric_snapshots`, `drift_alerts`, `drift_policy_versions`. | Evidence pack §7.2. |
| 3 | Redis keys | **Reads:** `polygon:spx:realized_vol_20d` (verified, source for realized-side comparison); model output keys (TBD per spec). **Carry-forward #4:** `gex:updated_at` staleness check is a no-op at HEAD; if Item 13 cites freshness gates, this is the limiting fact. | Evidence pack §10.2; §10.3.3. |
| 4 | Current behavior matches spec | **PARTIAL.** Model-output drift alerts shipped (12L); realized-vs-modeled metric drift is the gap. | Evidence pack §8 Item 13. |
| 5 | Future design? | **PARTIAL — scaffold-yes, full-spec-no.** | Evidence pack §8 Item 13. |
| 6 | Governance conflict | **POTENTIAL CONFLICT with D-018** (VVIX Thresholds: Adaptive Z-score vs 20-day rolling baseline) — Item 13 may propose alternative drift definitions; must compose with D-018, not replace. **POTENTIAL CONFLICT with D-021** (HMM ≠ LightGBM IMPLEMENTATION NOTE: do not build HMM/LightGBM until explicitly tasked in Phase 3A). | approved-decisions.md D-018, D-021. |
| 7 | Authority level proposed | **advisory → paper-binding.** Drift alerts are advisory at HEAD (12L); promotion to paper-binding (auto-demotion of strategies under drift) requires P1.3 design. | Per consolidated plan §5 V0.3. |
| 8 | Calibration dependencies | TBD pending P1.3 spec audit. **Cross-cutting flag:** depends on AI-SPEC-002 (calibration source) + AI-SPEC-004 (replay baselines). | See §7 dependency graph. |
| 9 | Training contamination risk | **MEDIUM.** Drift detection compares modeled-vs-realized; if modeled values are themselves drift-corrupted (e.g., VVIX baseline not warmed up — `polygon:vvix:baseline_ready`), drift-of-drift is hard to disentangle. | Evidence pack §10.2 (`polygon:vvix:baseline_ready`). |
| 10 | Implementation owner | Cursor. | T-Rule 1. |

**Notes:**
- **`risk_engine.py` collision with Items 1 and 12:** if Item 13's drift-triggered authority demotion requires a `risk_engine.py` modification, all three Cluster A/C specs (1, 12, 13) modify the same file. Sequencing critical.
- **Carry-forward #4 contradiction (also surfaces in Item 5):** the prompt's claim about `_safe_redis()` being uncalled is wrong; the function is called once at `prediction_engine.py:120`. Item 13 audit must not treat staleness infrastructure as missing — it exists and is exercised, but its `age_key` source has no producer.

---

## 4. Shared Module Touchpoints

Modules touched by 2+ specs only. Single-touch modules omitted. Source of truth: AI_ARCH_EVIDENCE_PACK.md §6 backend module map.

### `backend/risk_engine.py` (688 lines)

| AI-SPEC | Touchpoint | Type |
|---------|------------|------|
| AI-SPEC-001 | Risk Governor halt logic; new exit reasons (but see Notes — exit_reasons live in position_monitor, not risk_engine, so the spec must extend BOTH files) | Modifies (extends sizing gates + halt path) |
| AI-SPEC-009 | Reads `_DEBIT_RISK_PCT` (lines 103–111) for sizing-aware exit timing | Reads |
| AI-SPEC-012 | Phase ladder fix (carry-forward #4); sizing multipliers | Modifies (rewrites `_RISK_PCT` lines 78–83) |
| AI-SPEC-013 | Drift-triggered authority demotion may require new sizing-gate path | Modifies (adds demotion path) |

**Conflict risk:** **HIGH** — Items 1 + 12 + 13 all modify `risk_engine.py` in different ways. Sequencing required so the changes compose cleanly. P1.3 must define the order.

### `backend/prediction_engine.py` (999 lines)

| AI-SPEC | Touchpoint | Type |
|---------|------------|------|
| AI-SPEC-005 | Adds HAR-RV fair-value output to feature set | Modifies (adds feature) |
| AI-SPEC-006 | Reads prediction outputs for meta-label inference | Reads |
| AI-SPEC-008 | OPRA flow alpha as new feature | Modifies (adds feature) |
| AI-SPEC-013 | Realized-vs-modeled drift on prediction outputs | Reads (drift comparison) |

**Conflict risk:** MEDIUM — Items 5 + 8 both add new features to the prediction pipeline; merge-order matters but conflicts are localized. **Carry-forward #4** lives here: `_safe_redis()` at line 100 is called once at line 120; the GEX freshness gate is non-functional at HEAD because `gex:updated_at` has no producer.

### `backend/strategy_selector.py` (1541 lines)

| AI-SPEC | Touchpoint | Type |
|---------|------------|------|
| AI-SPEC-007 | Adversarial review may block strategy selection | Modifies (adds gate) |
| AI-SPEC-009 | Exit Optimizer may interact with butterfly gate to choose exit-aware strategies | Reads + Modifies |
| AI-SPEC-011 | Event-Day Playbooks select strategies on event days | Modifies (adds gate) |
| AI-SPEC-012 | Capital Allocation feeds size constraints to strategy selection | Reads |

**Conflict risk:** MEDIUM — strategy_selector is already the largest backend module (1541 lines). Multiple specs adding gates risks gate ordering bugs. P1.3 must define gate-stage ordering.

### `backend/position_monitor.py` (858 lines)

| AI-SPEC | Touchpoint | Type |
|---------|------------|------|
| AI-SPEC-001 | Risk Governor halt path adds new exit_reason values (lines 132, 174, 211, 225, 379, 458, 549, 616, 625, 765, 781, 805 are existing; Governor adds more) | Modifies (extends taxonomy) |
| AI-SPEC-009 | Exit Optimizer modifies exit timing within D-010/D-011/D-017 envelope | Modifies (intra-envelope decisions) |

**Conflict risk:** MEDIUM — both specs touch the exit decision surface. Constitutional ceiling (T-Rule 6, D-010, D-011) must be preserved by both.

### `backend/execution_engine.py` (870 lines)

| AI-SPEC | Touchpoint | Type |
|---------|------------|------|
| AI-SPEC-001 | Risk Governor may pre-empt execution on halt | Modifies (adds gate) |
| AI-SPEC-006 | Meta-label inference gate at line 358 | Modifies (already partial — gate exists, model dormant) |
| AI-SPEC-007 | Adversarial review may block execution | Modifies (adds gate) |

**Conflict risk:** MEDIUM — three gates added to one place. Per `set-feature-flag` Edge Function logic, all gates fail-open — this is a deliberate safety choice but means gate ordering matters when multiple gates fail-open simultaneously.

### `backend/model_retraining.py` (1177 lines)

| AI-SPEC | Touchpoint | Type |
|---------|------------|------|
| AI-SPEC-006 | Meta-label scaffold at 12K (commit `bf41175`) — `train_meta_label_model()` and `run_meta_label_champion_challenger()` | Modifies (already shipped; spec extends) |
| AI-SPEC-013 | Drift alert scaffold at 12L (commit `db4c9d9`) — 37 `drift` occurrences | Modifies (already shipped; spec extends) |

**Conflict risk:** MEDIUM — both scaffolds shipped on the same day (2026-04-20) and live in the same 1177-line file. P1.3 specs for Items 6 and 13 must be reviewed together to keep the file from becoming a "god module".

### `backend/counterfactual_engine.py` (406 lines)

| AI-SPEC | Touchpoint | Type |
|---------|------------|------|
| AI-SPEC-003 | Synthetic Counterfactual Cases — separate from this file but shares concepts | Conceptual neighbor |
| AI-SPEC-010 | Owns this file (12E scaffold; commit `2400e98`) | Modifies (already partial — spec extends) |
| AI-SPEC-012 | Reads `trading_prediction_outputs.counterfactual_pnl` for capital-allocation inputs | Reads (column triple per carry-forward #5) |

**Conflict risk:** LOW — Item 10 owns the file; Items 3 and 12 read its outputs but do not modify it.

### `backend/strategy_performance_matrix.py` (229 lines)

| AI-SPEC | Touchpoint | Type |
|---------|------------|------|
| AI-SPEC-002 | Strategy Attribution provides per-trade labels that aggregate up to this matrix | Provides inputs |
| AI-SPEC-011 | Event-Day Playbooks read regime × strategy aggregates from this matrix | Reads |
| AI-SPEC-012 | Capital Allocation may scale capital by per-cell performance | Reads |

**Conflict risk:** LOW — read-only consumers (11, 12) plus an upstream input provider (2). No write conflicts.

### Modules touched by exactly 1 spec (omitted from this section per the 2+ rule)

For completeness in P1.3 audits: `backend/strike_selector.py` (touched by Item 1 only — strike selection is risk-aware), `backend/databento_feed.py` (Item 8 OPRA feed touchpoint), `backend/polygon_feed.py` (Item 5 realized-vol input), `backend/calibration_engine.py` (Item 12 sizing-phase auto-advance only). These will be re-audited in P1.3 per spec.

---

## 5. Shared Supabase Tables

Tables touched by 2+ specs only. Source of truth: AI_ARCH_EVIDENCE_PACK.md §7.

### `trading_positions` (created 20260416172751, evidence pack §7.1)

| AI-SPEC | Read | Write | Purpose |
|---------|------|-------|---------|
| AI-SPEC-001 | yes | yes | Governor reads for halt/sizing decisions; writes audit fields on Governor-induced halts |
| AI-SPEC-002 | yes | yes | Attribution writes per-trade utility labels (proposed) |
| AI-SPEC-009 | yes | yes | Exit Optimizer writes new `exit_reason` values within D-010/D-011/D-017 envelope |
| AI-SPEC-010 | yes | no  | Counterfactual P&L reads closed positions (read-only per migration header) |
| AI-SPEC-012 | yes | no  | Capital Allocation reads for capacity tracking |

**Schema migration required:** **YES** if Item 2 ships (new utility-label columns) and possibly if Item 1 ships (Governor audit columns). **None required for Item 9** (writes existing `exit_reason` column with new values).

### `trading_prediction_outputs` (created 20260416172751; ALTERed by 20260421_add_counterfactual_pnl.sql, 20260422_add_prediction_features.sql, 20260422_ensure_prediction_outcome_columns.sql)

| AI-SPEC | Read | Write | Purpose |
|---------|------|-------|---------|
| AI-SPEC-001 | yes | no  | Governor reads predictions for halt/sizing decisions |
| AI-SPEC-006 | yes | yes | Meta-label inference writes back to `outcome_label` columns (added by `20260422_ensure_prediction_outcome_columns.sql`) |
| AI-SPEC-010 | yes | yes | Counterfactual job writes `counterfactual_pnl` / `counterfactual_strategy` / `counterfactual_simulated_at` (column triple per §7.3, NOT a separate table per carry-forward #5) |
| AI-SPEC-012 | yes | no  | Capital Allocation reads counterfactual columns to steer per-strategy capital |
| AI-SPEC-013 | yes | yes | Drift detection reads model outputs and writes drift-flag columns (proposed) |

**Schema migration required:** **YES** for Item 13 (drift-flag columns proposed). Possibly for Item 12 (snapshot ID column to join `capital_allocation_snapshots`). **None required for Item 10** (already shipped).

### `trading_sessions` (created 20260416172751)

| AI-SPEC | Read | Write | Purpose |
|---------|------|-------|---------|
| AI-SPEC-001 | yes | yes | Governor reads/writes session-level halt state |
| AI-SPEC-012 | yes | no  | Capital Allocation reads session capital state |
| AI-SPEC-013 | yes | no  | Drift detection reads session-level realized-vs-modeled comparisons |

**Schema migration required:** Likely **YES** for Item 1 (Governor halt-state columns) and possibly Item 12 (allocation-snapshot pointer).

### `trading_signals` (created 20260416172751)

| AI-SPEC | Read | Write | Purpose |
|---------|------|-------|---------|
| AI-SPEC-007 | yes | yes | Adversarial review reads signals; writes review verdicts |
| AI-SPEC-008 | yes | yes | OPRA Flow Alpha writes new alpha-flag rows |
| AI-SPEC-011 | yes | no  | Event-Day Playbooks read regime/signal context |

**Schema migration required:** Possibly **YES** for Items 7 and 8 (new flag/verdict columns).

### `trading_calibration_log` (created 20260416172751)

| AI-SPEC | Read | Write | Purpose |
|---------|------|-------|---------|
| AI-SPEC-001 | no  | yes | Governor calibration events |
| AI-SPEC-005 | no  | yes | HAR-RV calibration fits |
| AI-SPEC-006 | no  | yes | Meta-label retrain events (already partially used by 12K/12M) |
| AI-SPEC-013 | no  | yes | Drift policy version updates |

**Schema migration required:** **NO** — append-only log; existing schema sufficient.

### `paper_phase_criteria` (created 20260417000001)

| AI-SPEC | Read | Write | Purpose |
|---------|------|-------|---------|
| AI-SPEC-001 | yes | no  | Governor reads paper-phase gate state |
| AI-SPEC-004 | yes | yes | Replay Harness may add a "replay validation" criterion |
| AI-SPEC-012 | yes | no  | Capital Allocation reads gate state |

**Schema migration required:** Possibly **YES** for Item 4 (new criterion column or row).

### Tables NOT YET CREATED but referenced by 2+ specs (per evidence pack §7.2)

#### `item_promotion_records` — referenced by Items 1, 4, 12, 13

| AI-SPEC | Role |
|---------|------|
| AI-SPEC-001 | Records Governor authority promotions |
| AI-SPEC-004 | Owner: Replay Harness writes promotion records |
| AI-SPEC-012 | Reads promotion records for allocation decisions |
| AI-SPEC-013 | Reads promotion records to know what is currently promoted vs demoted |

**Status:** NO MIGRATION exists (verified across 68 migration files). Item 4 should own the migration since it is the producer.

#### `replay_eval_runs` / `replay_eval_cases` / `replay_eval_results` — referenced by Item 4 (sole owner) and consumed conceptually by Items 3, 6, 13

| AI-SPEC | Role |
|---------|------|
| AI-SPEC-003 | Synthetic counterfactual cases must be replay-validated (reads) |
| AI-SPEC-004 | Owner |
| AI-SPEC-006 | Meta-labeler model versions must pass replay before activation (reads) |
| AI-SPEC-013 | Drift detection compares against replay baselines (reads) |

**Status:** NO MIGRATION exists. Item 4 must ship these as part of its scaffold.

---

## 6. Shared Redis Keys

Cross-references against AI_ARCH_EVIDENCE_PACK.md §10.

### Pattern: `gex:*`

| Key | AI-SPEC | Producer | Consumer | TTL | Status |
|-----|---------|----------|----------|-----|--------|
| `gex:net` | AI-SPEC-001 (reads), AI-SPEC-005 (reads) | `gex_engine.py:163` | `synthesis_agent.py:224`; shadow_engine | no TTL set | verified |
| `gex:nearest_wall` | AI-SPEC-001 (reads), AI-SPEC-009 (reads) | `gex_engine.py:165` | `strike_selector.py:298`; strategy_selector | no TTL set | verified |
| `gex:flip_zone` | AI-SPEC-001 (reads), AI-SPEC-009 (reads) | `gex_engine.py:166` | `synthesis_agent.py:226`; prediction_engine | no TTL set | verified |
| `gex:by_strike` | AI-SPEC-001 (reads), AI-SPEC-005 (reads) | `gex_engine.py:164` | strategy_selector butterfly gate | no TTL set | verified |
| `gex:confidence` | AI-SPEC-001 (reads) | `gex_engine.py:64, 167` | `strike_selector.py:299` | no TTL set | verified |
| `gex:wall_history` | AI-SPEC-001 (reads, indirectly via wall-stability gate) | `gex_engine.py:120` (setex via 12C) | strategy_selector wall-stability gate | 3600s | verified |
| **`gex:atm_iv`** | **AI-SPEC-001 (consumer if cited), AI-SPEC-005 (consumer if cited)** | **NONE FOUND** | `macro_agent.py:214` (sole consumer) | n/a | **partial — consumer-only orphan (carry-forward #2)** |
| **`gex:updated_at`** | **AI-SPEC-005 (freshness gate), AI-SPEC-013 (drift staleness)** | **NONE FOUND** | `prediction_engine.py:123` (passed as `age_key` to `_safe_redis`) | n/a | **partial — consumer-only orphan (carry-forward #1 / #4)** |

**Status flag:** §10.3 found `gex:atm_iv` and `gex:updated_at` as consumer-only orphans. P1.3 audits for Items 1, 5, 13 must resolve. **Operational risk noted in evidence pack §10.3.3:** because `gex:updated_at` has no producer, the `_safe_redis()` staleness check in `prediction_engine.py:120` always falls through fail-open (line 142–143). The freshness gate is non-functional at HEAD.

### Pattern: `polygon:spx:*`

| Key | AI-SPEC | Producer | Consumer | TTL |
|-----|---------|----------|----------|-----|
| `polygon:spx:realized_vol_20d` | AI-SPEC-005 (primary input), AI-SPEC-013 (drift comparison) | `polygon_feed.py` 12A | main.py:2061; prediction_engine; tests | 86400s |
| `polygon:spx:return_5m/30m/1h/4h` | AI-SPEC-005 (HAR-RV multi-horizon inputs), AI-SPEC-008 (flow timing) | `polygon_feed.py:874–877` | prediction_engine | 300s each |
| `polygon:spx:macd_signal/bb_pct_b/vwap_distance/morning_range` | AI-SPEC-005 (regime context), AI-SPEC-008 (alpha context) | `polygon_feed.py` (technical-indicator block) | prediction_engine | UNVERIFIED at exact line |

**Status flag:** Multiple `polygon:spx:*` keys are partial (producer line not pinned). P1.3 must read `polygon_feed.py` directly to confirm exact write locations before either spec's audit signs off.

### Pattern: `model:meta_label:*` and `feedback:counterfactual:*`

| Key | AI-SPEC | Producer | Consumer | TTL |
|-----|---------|----------|----------|-----|
| `model:meta_label:enabled` | AI-SPEC-006 (gate), AI-SPEC-013 (drift may demote) | `set-feature-flag` Edge Function (out-of-tree) → `main.py:2568–2576` Railway path | `execution_engine.py:358` | operator-controlled |
| `feedback:counterfactual:enabled` | AI-SPEC-010 (gate), AI-SPEC-012 (consumes outputs) | `set-feature-flag` Edge Function → Railway path | `counterfactual_engine.py:168` | operator-controlled |

**Status flag:** Both flags fail-open ENABLED. Per evidence pack §10.5, the producer-of-record is the operator (mediated by Edge Function authentication and Railway admin-key validation), not autonomous backend logic.

### Pattern: `risk:*` and `capital:*`

| Key | AI-SPEC | Producer | Consumer | TTL |
|-----|---------|----------|----------|-----|
| `risk:halt_threshold_pct` | AI-SPEC-001 (reads), AI-SPEC-012 (reads) | `calibration_engine.py:368` | main.py:2081; risk_engine.py:504 | setex TTL |
| `capital:sizing_phase` | AI-SPEC-001 (reads), AI-SPEC-012 (reads + may write) | `calibration_engine.py:641` (12N writer) | main.py:2150; risk_engine.py | setex TTL |
| `capital:sizing_phase_advanced_at` | AI-SPEC-012 (audit field) | `calibration_engine.py:647` (B2-1 commit `41bb1ab`) | main.py:2153; LearningPage UI | 1-year TTL |
| `capital:deployment_pct` | AI-SPEC-012 (writes for ramp control) | `main.py:1698` | capital_manager flow | no TTL set |
| `capital:leverage_multiplier` | AI-SPEC-012 (writes for Kelly cap pairing) | `main.py:1700` | capital_manager flow | no TTL set |
| `capital:live_equity` | AI-SPEC-012 (input) | `capital_manager.py:160` (CAPITAL_CACHE_KEY) | calibration_engine.py:332 | CAPITAL_CACHE_TTL |

**Status flag:** Items 1 and 12 share heavy read-side overlap on `risk:*` and `capital:*`. Write conflicts only emerge if Item 12 modifies `_RISK_PCT` while Item 1 reads it for Governor sizing.

### Pattern: `strategy:*:enabled`

| Key | AI-SPEC | Status | Notes |
|-----|---------|--------|-------|
| `strategy:iron_butterfly:enabled` | AI-SPEC-007 (review touchpoint), AI-SPEC-011 (playbook touchpoint), AI-SPEC-012 (allocation per strategy) | verified consumer (`main.py:1833`) | Operator-controlled |
| `strategy:long_straddle:enabled` | same as above | verified consumer (`main.py:1834`) | Operator-controlled |
| `strategy:calendar_spread:enabled` | same as above | verified consumer (`main.py:1835`) | Operator-controlled |
| `strategy:earnings_straddle:enabled` | same as above | verified consumer (`main.py:1850`; `main_earnings.py:92`) | Default OFF per MASTER_PLAN line 386 |
| **`strategy:bull_debit_spread:enabled`** | AI-SPEC-007, AI-SPEC-011, AI-SPEC-012 | **NOT FOUND IN CODE (carry-forward #3)** | MASTER_PLAN line 59 names it; no consumer in any Python file |
| **`strategy:bear_debit_spread:enabled`** | AI-SPEC-007, AI-SPEC-011, AI-SPEC-012 | **NOT FOUND IN CODE (carry-forward #3)** | MASTER_PLAN line 60 names it; no consumer in any Python file |

**Status flag:** Carry-forward #3 surfaces here. P1.3 audits for Items 7, 11, 12 must NOT assume the bull/bear debit-spread feature flags exist. The actual Phase 2B sizing path is `_DEBIT_RISK_PCT["debit_call_spread"]` / `_DEBIT_RISK_PCT["debit_put_spread"]` at `risk_engine.py:105–106`, which has no flag gate.

### Pattern: `databento:opra:*` (Item 8 territory; touched only by Item 8 in cross-cutting sense)

Listed for completeness despite the 2+ rule, because Item 8 is the only consumer at HEAD but Item 4 (Replay Harness) will need archived versions:

- `databento:opra:trades` (verified producer `databento_feed.py:348`, 300s TTL)
- `databento:opra:gex_block` and `databento:opra:confidence_impact` (verified producers in `databento_feed.py`)

These three keys are short-window; **Item 4 (Replay Harness) needs an archive of these data outside Redis** to replay over historical OPRA flow. P1.3 spec audits for Items 4 and 8 must coordinate the archival boundary.

---

## 7. Inter-Spec Dependency Graph

Plain-text DAG. Form: `Item X → depends on → Item Y` means Item X cannot be calibration-grade until Item Y exists. Multiple arrows = AND.

### 7.1 Foundational layer (Cluster A — must exist before B/C have data to learn from)

- **AI-SPEC-002 (Attribution)** — no dependencies (writes labels for everyone else). **Critical-path root for V0.1.**
- **AI-SPEC-004 (Replay Harness)** — no dependencies (provides historical evaluation surface). **Critical-path root for V0.1.**
- **AI-SPEC-010 (Counterfactual P&L)** → depends on → AI-SPEC-004 (replay) for synthetic-counterfactual validation extension; current observability scaffold has no spec dependency (already shipped at HEAD).
- **AI-SPEC-001 (Risk Governor)** → depends on → AI-SPEC-002 (attribution for sizing inputs).

### 7.2 Alpha layer (Cluster B)

- **AI-SPEC-005 (Vol Fair-Value HAR-RV)** → depends on → AI-SPEC-002 (calibration labels).
- **AI-SPEC-006 (Meta-Labeler)** → depends on → AI-SPEC-002 (training labels) + AI-SPEC-004 (replay validation).
- **AI-SPEC-008 (OPRA Flow)** → depends on → AI-SPEC-002 (attribution to test alpha-claim) + AI-SPEC-004 (archived OPRA flow for back-testing).
- **AI-SPEC-009 (Exit Optimizer)** → depends on → AI-SPEC-002 (attribution per-exit-reason).

### 7.3 Governance/maturation layer (Cluster C)

- **AI-SPEC-003 (Synthetic Counterfactual)** → depends on → AI-SPEC-004 (replay) + AI-SPEC-010 (real counterfactual baseline).
- **AI-SPEC-007 (Adversarial)** → depends on → AI-SPEC-001 (Governor authority) + AI-SPEC-006 (meta-labeler trust).
- **AI-SPEC-011 (Event Playbooks)** → depends on → AI-SPEC-002 (attribution per regime).
- **AI-SPEC-012 (Capital Allocation)** → depends on → AI-SPEC-001 (Governor) + AI-SPEC-002 (attribution) + AI-SPEC-013 (drift demotion paths).
- **AI-SPEC-013 (Drift Detection)** → depends on → AI-SPEC-002 (calibration source) + AI-SPEC-004 (replay baselines).

### 7.4 Cycle check

**No formal cycles found** under the strict reading "Item X depends on Item Y for calibration-grade behavior."

**Soft cycle (potential, requires P1.3 resolution):** AI-SPEC-012 (Capital Allocation) depends on AI-SPEC-013 (Drift Detection) for demotion paths; AI-SPEC-013's authority promotion (advisory → paper-binding) might in turn require Item 12's capital framework to know what to demote. This is a sequencing question rather than a cycle: ship Item 13 in advisory-only mode first, ship Item 12 next, then promote Item 13 to paper-binding.

**Hardware cycle (resolved by Cluster A precedence):** Items 1, 12, 13 all modify `risk_engine.py`. The dependency graph says Item 1 ships first (depends only on Item 2); Item 13 ships next; Item 12 ships last. Module-level merge order: 1 → 13 → 12.

### 7.5 Critical path to V0.1 deployment

**Minimum set of items that must ship for V0.1:**

1. **AI-SPEC-002 (Attribution)** — labels for all downstream learning.
2. **AI-SPEC-004 (Replay Harness)** — validation surface for promotion.
3. **AI-SPEC-001 (Risk Governor)** — authority hierarchy in paper-binding mode.
4. **AI-SPEC-010 (Counterfactual P&L)** — already partial; needs downstream wiring to Items 1, 12.

**Items NOT on V0.1 critical path** (deferred to V0.2 / V0.3 / V0.4): 3, 5, 6, 7, 8, 9, 11, 12, 13.

**Implication for sequencing:** P1.3 audits should be scheduled in the order 2 → 4 → 1 → 10 → (everything else). Items 2 and 4 are leaf nodes in the dependency DAG; Items 1 and 10 directly depend on them; everything else depends on 1, 2, 4, or 10 transitively.

---

*Phase 1 P1.2 — produced 2026-04-26 by Cursor AI under SPEC VERIFICATION PROTOCOL. Builds on AI_ARCH_EVIDENCE_PACK.md (P1.1, immutable input). Owner: tesfayekb.*
