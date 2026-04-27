# Spec Verification Audit — AI-SPEC-001

> **Status:** First-pass redline (P1.3.1). Cursor primary-auditor sections (§1, §3, §4, §10.1) populated; first-pass drafts of §2, §5–§13 for Claude cross-check and GPT validation.
> **Binding format:** Follows `trading-docs/08-planning/ai-architecture-audits/_template.md` (P1.3.0).
> **Created:** 2026-04-26 (Phase 1 P1.3.1 of CONSOLIDATED_PLAN_v1.2_APPROVED.md).
> **Source spec:** `trading-docs/04-modules/ai-architecture/archive/raw-locked-specs-2026-04-26/ITEM_1_AI_RISK_GOVERNOR_LOCKED.md` (1018 lines, locked 2026-04-25, immutable).

---

## 1. Audit Header

| Field | Value |
|-------|-------|
| Spec ID | AI-SPEC-001 |
| Spec name | AI Risk Governor with Capped Opportunity Lean |
| Stable ID | PLAN-AIGOV-001 |
| Tier | V0.1 |
| Cluster | A (foundational) |
| Audit date | 2026-04-26 |
| Repo HEAD at audit time | `b0cd6b3fba41a48b45e4e1512cb11c17e5df4873` (P1.3.0b merged; archive of raw locked specs landed) |
| Primary auditor | Cursor |
| Cross-check auditor | Claude |
| Architectural validator | GPT-5.5 Pro |
| Cross-cutting matrix reference | `CROSS_CUTTING_EVIDENCE_MATRIX.md` §3 (AI-SPEC-001 block, lines 84–106), §4 (`risk_engine.py`, `position_monitor.py`, `prediction_engine.py`, `execution_engine.py` blocks), §6 (`gex:*` and `risk:halt_threshold_pct` / `capital:sizing_phase` rows), §7 (dependency graph) |
| Evidence pack reference | `AI_ARCH_EVIDENCE_PACK.md` §6.1 (backend module map), §7.1 (existing tables), §7.2 (proposed tables), §8 Item 1 (lines 388–392), §9.4 (`_RISK_PCT` non-monotonic ladder), §10 (Redis key inventory) |

---

## 2. Spec Intent Summary (verified by GPT)

**(First-pass draft for GPT-5.5 Pro to refine.)**

AI-SPEC-001 introduces a structured-output LLM Risk Governor that sits above the existing rules-based `backend/risk_engine.py` and acts as a soft, defined-risk veto layer over short-gamma admissibility, capped sizing multipliers (`size_multiplier_cap ∈ {0, 0.25, 0.5, 1.0}`), and a small "capped opportunity lean" channel for defined-risk convex structures. The Governor is deliberately scoped so that it never selects strikes, never executes orders, never overrides constitutional gates (D-005 −3% halt, D-022 streak halts, D-010/D-011 time stops, paper-phase criteria), and never increases risk — every layer in the Final Arbiter composition rule (`min(constitutional_cap, rules_cap, governor_cap, meta_labeler_cap, adversarial_cap)`) can only reduce, never raise. Architectural ROI is framed as preventing regime-misclassified short-gamma exposure on Iran-day-style novelty events, not picking better trades. Authority promotion runs on three independent tracks (V0.1 advisory → V0.2 paper-binding → V0.2 small-live-veto, with the Opportunity Lean channel graduated separately) and is gated on replay-validated risk-score weights, statistical thresholds (≥200 replay decisions, ≥30 veto/reduce actions, useful-veto-rate Wilson lower-95 ≥ 0.40), and operational SLOs (JSON parse ≥99.5%, p95 latency ≤6s, prompt frozen ≥10 trading days).

---

## 3. Repo Evidence (verified by Cursor)

**Verification methodology:** Every concrete claim in the locked spec was verified against repo state at HEAD `b0cd6b3` using `git rev-parse`, `wc -l`, `grep -n`, direct file reads, and migration inventory. Where the spec does not cite a specific file/line/migration/SHA — and the bulk of AI-SPEC-001 is forward-looking architecture, not retrospective citation — the verification target is whichever existing scaffold the spec implicitly composes with.

### 3.1 File/Module References

The locked spec is overwhelmingly forward-looking; it makes few `backend/<file>.py:NN`-style citations. The references it does make (or implies) are tabled below.

| Spec Reference | Verification | Status |
|---------------|--------------|--------|
| Spec §1, §24: "refactored `synthesis_agent`" produces the Market State Card | `backend_agents/synthesis_agent.py` exists, **628 lines**. Reads `ai:macro:brief` + GEX signals (line 4 module docstring). Writes `ai:synthesis:latest` with TTL 8h. Existing schema returns `{direction, confidence, strategy, rationale, risk_level}` (lines 38–53) — a **fundamentally different shape** from the locked Governor schema (Section 3 — `event_class`, `novelty_score`, `uncertainty_score`, `signal_conflict_score`, `data_freshness_warning`, `allowed_strategy_classes`, `size_multiplier_cap`, `opportunity_lean_*`, etc.). | **partial — file exists; schema delta means "refactor" is materially a rewrite. Class B (see §10.2 B2).** |
| Spec §24: "**8 specialist agents** continue feeding Redis briefs that the Card consumes and summarizes" | `ls backend_agents/*.py` returns 8 files including `__init__.py`; **non-init files = 7**: `economic_calendar.py`, `feedback_agent.py`, `flow_agent.py`, `macro_agent.py`, `sentiment_agent.py`, `surprise_detector.py`, `synthesis_agent.py`. The 7 non-init agents include `synthesis_agent` itself (which the spec frames as the Card consumer, not a feeder), so the count of *upstream feeders* at HEAD is at most 6, not 8. | **wrong-count. Class A (see §10.1 A1).** |
| Spec §1: pre-Governor pipeline references Item 5 (Vol Fair-Value), Item 8 (OPRA Flow Summary), Item 6 (Meta-Labeler), Item 7 (Adversarial), Item 10 (Attribution) modules | `ls backend/ \| grep -iE 'vol_fair_value\|opra_alpha\|adversarial'` returns no matches at HEAD. Per evidence pack §8 Items 5/7/8/10: NOT YET IMPLEMENTED. Item 6 is scaffolded inside `backend/model_retraining.py` + `backend/execution_engine.py` (12K commit `bf41175`, dormant pending ≥100 closed paper trades). | **not-found for Items 5/7/8/10; partial for Item 6. Consistent with Cluster A foundational sequencing (Item 1 ships first; downstream items are explicit dependencies).** |
| Spec §10: "−3% daily halt (D-005)" | Implemented at `backend/risk_engine.py:481` (`check_daily_drawdown`) with 12F adaptive halt threshold reading `risk:halt_threshold_pct` Redis key (`risk_engine.py:504`) and falling back to −0.03 default. Defensive clamp [−0.05, −0.02] at `risk_engine.py:512`. Warning band at −1.5% with one-shot Redis sentinel (`risk_engine.py:531`+, debounced via `alert:drawdown_warning_sent_today`). | **verified. Spec compliance correct.** |
| Spec §10: "2:30 PM time stop (D-010)" | Enforced via `position_monitor.py:132` — `exit_reason="time_stop_230pm_d010"`. | **verified.** |
| Spec §10: "3:45 PM hard close (D-011)" | Enforced via `position_monitor.py:174` — `exit_reason="time_stop_345pm_d011"`. | **verified.** |
| Spec §10: "Streak halt" (i.e., D-022 5-consecutive-loss session halt) | Enforced at `backend/prediction_engine.py:688–691` (comment: "D-022: 5 consecutive losses = halt"). 3-consecutive-loss 50% reduction enforced at `backend/risk_engine.py:234–235` inside `_apply_sizing_gates()` (lines 203–259). Tested by `backend/tests/test_consolidation_s10.py` (T0-8: "5-consecutive-loss halt actually executes"). | **verified, but split across two files. Class B clarification (see §10.2 B7).** |
| Spec §10: "Phase sizing tiers" | `_RISK_PCT` table at `backend/risk_engine.py:79–84` (4 phases). Phase 2B `_DEBIT_RISK_PCT` at lines 103–111. Auto-advance gates in `backend/calibration_engine.evaluate_sizing_phase` (per inline comment block at `risk_engine.py:71–77`). | **verified.** |
| Spec §10: "Graduation rules (`paper_phase_criteria` GLC-001 through GLC-012)" | Table created in migration `supabase/migrations/20260417000001_paper_phase_criteria.sql`. RLS enabled, populated by INSERT at line 38+. Referenced in code by `backend/criteria_evaluator.py`, `backend/calibration_engine.py`, `backend/session_manager.py`, `backend/main.py`. | **verified.** |
| Spec §1, §3.B `retrieved_case_ids`, §16 retrieval_quality_score: "Supabase pgvector case retrieval" | `grep -rln "pgvector\|CREATE EXTENSION vector\|USING vector" supabase/migrations/` returns **no matches** across all 68 migration files. pgvector is **not enabled** at HEAD. Item 10 (`backend/counterfactual_engine.py`, 406 lines) is observability-only over real no-trade signals; no embeddings, no vector search. | **not-found. Class B (see §10.2 B1).** |
| Spec §6 Risk Score weights / §16 schema_quality_factor: dependency on Item 10's `calibration_eligible` flag | `grep -rln "calibration_eligible" backend/ supabase/migrations/` returns **zero matches** in production code/migrations. The label only exists inside the locked-spec archive and audit infrastructure docs. | **not-found in code. Class B (see §10.2 B5).** |
| Spec §3.B GovernorDecisionRecord persistence target | No `governor_decisions` table in `supabase/migrations/`. `grep -rln "risk_governor\|governor_decisions\|RiskGovernor" backend/ backend_agents/ supabase/` returns matches only in the archived spec files and audit infrastructure — zero matches in production code/migrations. | **not-yet-created. Class B (see §10.2 B4).** |

### 3.2 Supabase Schema References

| Spec Reference | Verification | Status |
|---------------|--------------|--------|
| `trading_positions` (Spec §3.B `candidate_id` / `decision_id` linkage; Governor reads/writes for halt and sizing) | Created in `supabase/migrations/20260416172751_0ef832ac-…sql:159`. RLS enabled (`authenticated_read_positions`, `service_write_positions`). Indexes at lines 210–212. | **verified — table exists.** |
| `trading_sessions` (Spec §3.B `session_id`) | Same migration `20260416172751_*.sql:32`. | **verified.** |
| `trading_signals` (implicit pre-Governor candidate source) | Same migration `20260416172751_*.sql:111`. | **verified.** |
| `trading_prediction_outputs` (Spec §3.B implicit linkage via `candidate_id`) | Same migration `20260416172751_*.sql:68`. | **verified.** |
| `trading_calibration_log` (Spec §6 V0.1 Replay Calibration ledger) | Same migration `20260416172751_*.sql:294`. | **verified.** |
| `paper_phase_criteria` (Spec §10 GLC-001..012) | Migration `20260417000001_paper_phase_criteria.sql`. | **verified.** |
| `trading_positions.exit_reason` CHECK constraint (Spec §11 Failure Mode → Governor halt path proposes new exit reasons) | Migration `20260421_exit_reason_comprehensive.sql`. AST-based enforcement test at `backend/tests/test_exit_reason_constraint.py` (per `backend/position_monitor.py:28–30` comment). | **verified — constraint exists; new exit_reason additions must extend BOTH the CHECK constraint AND the in-file taxonomy in `position_monitor.py`.** |
| `ai_governor_versions` (Spec §14 — proposed CREATE TABLE) | `grep -rln "ai_governor_versions" supabase/ backend/` returns zero matches. | **not-yet-created. Class B (see §10.2 B3).** |
| `governor_decisions` (Spec §3.B implicit persistence target for `GovernorDecisionRecord`) | No such migration. | **not-yet-created. Class B (see §10.2 B4).** |
| pgvector extension + `pgvector_governor_cases` / equivalent retrieval tables (Spec §1, §16) | No `CREATE EXTENSION vector` in any migration. | **not-yet-created. Class B (see §10.2 B1).** |
| `case_type IN ('actual', 'override', …)` taxonomy on a case-store table (Spec §16 + §22) | No case-store table at HEAD. Item 10's `counterfactual_engine.py` writes `counterfactual_pnl` columns on `trading_prediction_outputs` (per evidence pack §9.6 / matrix carry-forward #5) — that is a column triple, not a case store with `case_type`. | **not-yet-created. Class B (see §10.2 B4).** |

### 3.3 Redis Key References

The locked spec does **not** name specific Redis keys. It references the *concepts* `data_freshness_warning` (in `GovernorLLMOutput` and Failure Mode table), retrieval-cache invalidation (Section 15), and "Redis briefs that the Card consumes" (Section 24). The verifications below cover the implicit dependencies surfaced by matrix §6 and evidence pack §10.

| Spec Reference (concept) | Producer | Consumer | Status |
|---------------|----------|----------|--------|
| Implicit `gex:*` namespace (Governor consumes via Item 5 / Market State Card; matrix §6 lists `gex:net`, `gex:nearest_wall`, `gex:flip_zone`, `gex:by_strike`, `gex:confidence`, `gex:wall_history`) | `backend/gex_engine.py:163–167` (most), `gex_engine.py:64, 167` (`gex:confidence`), `gex_engine.py:120` (`gex:wall_history`, setex 3600s) | `prediction_engine.py:886`, `synthesis_agent.py:224–226`, `strike_selector.py:298–299`, `strategy_selector` | **verified.** |
| `gex:atm_iv` (potential Governor input via Item 5 / IV-rank features) | **NONE FOUND** | `backend_agents/macro_agent.py:214` (sole consumer) | **partial — consumer-only orphan. Carry-forward #2 (see §8 row 2).** |
| `gex:updated_at` (potential freshness gate input — `data_freshness_warning`) | **NONE FOUND** | only docstring example at `prediction_engine.py:120` (inside docstring lines 107–131) — not an actual call site | **partial — consumer-only orphan. Carry-forward #1 (see §8 row 1).** |
| Implicit "freshness gate" (Spec §11 `data_freshness_warning`, Section 16 `data_freshness_flags`) | `backend/prediction_engine.py:100` defines `_safe_redis()` | **NO EXTERNAL CALLER.** `grep -rn "_safe_redis"` across `backend/`, `backend_agents/`, `backend_earnings/`, `src/` returns exactly two matches: the definition at line 100 and the in-docstring example at line 120 (lines 107–131 are the docstring envelope) | **dead code. Carry-forward #4 (see §8 row 4 + §10.2 B6).** |
| `risk:halt_threshold_pct` (D-005 12F adaptive threshold; Governor implicitly composes with `governor_cap → min` of constitutional_cap which reads this key) | `backend/calibration_engine.py:368` (setex by weekly job once `closed_trades >= 100`) | `backend/main.py:2081`, `backend/risk_engine.py:504` | **verified.** |
| `capital:sizing_phase` (D-014 phase lookup; Governor's `size_multiplier_cap` composes against current `_RISK_PCT[phase]`) | `backend/calibration_engine.py:641` (12N writer) | `backend/main.py:2150`, `backend/risk_engine.py` (sizing-phase lookup) | **verified.** |
| `alert:drawdown_warning_sent_today` (Section 21 cost circuit + Section 18 alerts pattern; one-shot sentinel pattern) | `backend/risk_engine.py:535` (set + read at same site) | same | **verified — pattern Governor can reuse for "Loud Alert Trigger" (Section 18).** |
| `model:meta_label:enabled` (existing feature-flag pattern Item 1's `agents:ai_risk_governor:enabled` would mirror) | Redis (set via Edge Function `set_feature_flag`) | `backend/execution_engine.py:519` (and other call sites), via `_flag()` helper | **verified — pattern exists; Governor flag does not yet.** |
| Implicit "8 specialist agents feeding Redis briefs" (Spec §24) | `backend_agents/macro_agent.py:87` (`ai:macro:brief`), `flow_agent.py`, `sentiment_agent.py`, `surprise_detector.py`, `economic_calendar.py`, `feedback_agent.py` (6 brief-style writers) + `synthesis_agent.py` (consumer/synthesizer) | `synthesis_agent.py:90` reads `ai:macro:brief`; `prediction_engine.py:433` reads `ai:synthesis:latest` | **partial — count is 7 agents, not 8 (see §10.1 A1); brief production paths verified.** |

### 3.4 Commit Hash References

The locked spec (1018 lines) cites **no commit hashes**. Provenance line at line 1018 references "Round 2 GPT-5.5 Pro design + Items 5-10 integration audit + Claude verification + GPT verification accept over 2026-04-25" — a process attribution, not a commit reference.

| Spec Reference | Verification | Status |
|---------------|--------------|--------|
| (no commit-hash citations in spec) | n/a | **n/a — pure future design.** |

---

## 4. Existing Partial Implementation (verified by Cursor)

Per evidence pack §8 Item 1: **NOT YET IMPLEMENTED.** What exists at HEAD that the Governor must compose with (not replace), be aware of (architectural sequencing), or extend (file-touchpoint additions):

| Aspect | Existing State | Source |
|--------|---------------|--------|
| Functional scaffold (Risk Governor itself) | **None.** No `backend/risk_governor.py`, no `backend/governor*` files, no `RiskGovernor` class. `grep -rln "risk_governor\|RiskGovernor\|AI Risk Governor" backend/ backend_agents/` returns zero matches in production code. | Evidence pack §8 Item 1 (lines 388–392); direct grep at HEAD `b0cd6b3`. |
| Closest existing rule-based cap engine | `backend/risk_engine.py` — **688 lines**. Implements D-005, D-014, D-019, D-020, D-021, D-022, B4-Kelly (per module docstring lines 3, 7). Functions per matrix §3 dim 1 evidence: `risk_engine.py:30, 134, 203 (_apply_sizing_gates), 262 (compute_position_size), 474 (D-005), 614, 643, 683`. | Evidence pack §6.1; risk_engine.py direct read. |
| `_RISK_PCT` ladder Governor's `size_multiplier_cap` composes with | `backend/risk_engine.py:79–84` — Phase 1 0.010, Phase 2 0.0075, Phase 3 0.010, Phase 4 0.010 (manual). **Non-monotonic Phase 1 > Phase 2** by design (paired with 2026-04-20 SPX width widening per inline comment block at lines 70–77 + 79–82). Item 12 will rewrite this; Item 13 ladder follow-up was intended but not landed. | Evidence pack §9.4 (Phase 2 risk ladder non-monotonic). |
| Schema in place (Governor reads/writes existing tables) | `trading_sessions`, `trading_prediction_outputs`, `trading_signals`, `trading_positions` (all in `supabase/migrations/20260416172751_*.sql`), `trading_calibration_log` (same migration), `paper_phase_criteria` (`20260417000001_paper_phase_criteria.sql`), `trading_positions.exit_reason` CHECK constraint (`20260421_exit_reason_comprehensive.sql`). | Evidence pack §7.1; direct migration inspection. |
| Schema NOT in place (Governor-specific tables required by spec) | `ai_governor_versions` (Section 14), `governor_decisions` (implicit from §3.B record schema), pgvector + case-store tables (Section 16), `case_type` taxonomy table. None exist; none in `supabase/migrations/`. | Evidence pack §7.2; grep across all 68 migrations. |
| Feature-flag wiring (for Governor on/off + cost circuit breaker) | **No** Governor-specific flag at HEAD. Pattern in use: `agents:ai_synthesis:enabled` (synthesis_agent.py module docstring lines 10–11, default OFF), `model:meta_label:enabled` (12K, fail-open ENABLED, evidence pack §8 Item 6), `strategy:ai_hint_override:enabled` (`execution_engine.py:519`). All flags are read via the `_flag()` helper and set via the `set_feature_flag` Edge Function. | Evidence pack §10 (feature-flag namespace); direct grep. |
| Tests covering scope (existing safety-net the Governor must not regress) | `backend/tests/test_risk_engine.py` (D-005 regression cases, lines 46+, 56+); `backend/tests/test_adaptive_halt_threshold.py` (12F `risk:halt_threshold_pct` adaptive); `backend/tests/test_fix_group10.py` (D-005 unrealized P&L inclusion); `backend/tests/test_consolidation_s10.py` (T0-8: 5-consecutive-loss session halt actually calls `update_session(halted)` — not just an audit log); `backend/tests/test_exit_reason_constraint.py` (AST-based — every hardcoded `exit_reason` literal must be in the migration CHECK constraint). | Direct file inspection; test file inventory. |
| Documentation references | **TASK_REGISTER:** no Section 14A entry yet (consolidated plan §5 reserves Section 14A for Risk Governor). **MASTER_PLAN:** no Phase 3A AI Governor entry yet (P1 consolidated plan flags this as new). **system-state.md:** no `ai_risk_governor` operational state. **constitution.md:** T-Rule 5 (Capital Preservation Is Absolute) covers D-005/D-022 non-overridability — Governor design in Section 10 explicitly defers, so no T-Rule clarification is needed. | Direct file grep across `trading-docs/`. |
| Synthesis-style structured-output precedent (closest functional analog) | `backend_agents/synthesis_agent.py` — 628 lines. Provider-pluggable (Anthropic/OpenAI per `config.AI_PROVIDER`), JSON-only output `{direction, confidence, strategy, rationale, risk_level}` (lines 38–53). **Schema is materially different** from the locked `GovernorLLMOutput` (Section 3): synthesis_agent has 5 simple fields; Governor has 18+ fields including event taxonomy, novelty/uncertainty/conflict scores, `allowed_strategy_classes`/`blocked_strategy_classes` enums, opportunity-lean fields, freshness flags, retrieval case IDs. Treating the Governor as "refactored synthesis_agent" understates the schema surface — a full rewrite is a more accurate framing. | `backend_agents/synthesis_agent.py:32–94` direct read; spec §3 schema. |

**Net partial-implementation status:** the Governor itself does not exist; one structured-output LLM agent (`synthesis_agent`) exists with a small subset of the Governor's surface area; the rule-based cap engine the Governor must compose with is fully shipped; the persistence schema for Governor decisions and versioning is **not** in place; the freshness-gate substrate the Governor's `data_freshness_warning` depends on is dead code (carry-forward #4).

---

## 5. The Ten Audit Dimensions

Per CONSOLIDATED_PLAN_v1.2_APPROVED.md §2 Layer B and the cross-cutting matrix §3 AI-SPEC-001 block (lines 84–106). The matrix gave a summary view; this section gives per-item depth with falsifiable claims.

| # | Dimension | Finding | Source / Evidence |
|---|-----------|---------|-------------------|
| 1 | File/module exists | **NO.** No `backend/risk_governor*.py`. Closest existing logic: `backend/risk_engine.py` (688 lines, rule-based). One precedent for structured-output LLM agents: `backend_agents/synthesis_agent.py` (628 lines, different schema). | `risk_engine.py` verified at HEAD; `synthesis_agent.py` verified at HEAD; matrix §3 dim 1. |
| 2 | DB table/column | **partial.** Reads/writes existing core tables (`trading_positions`, `trading_sessions`, `trading_prediction_outputs`, `trading_calibration_log`, `paper_phase_criteria`) — all present. Governor-specific tables (`ai_governor_versions` per §14, `governor_decisions` per §3.B implicit, pgvector case store per §1/§16) are **all** not-yet-created. | Migration `20260416172751_*.sql` (core tables); migration `20260417000001_paper_phase_criteria.sql`; grep returns zero matches for proposed tables. |
| 3 | Redis keys | **partial.** Reads existing keys (verified): `gex:net`, `gex:nearest_wall`, `gex:flip_zone`, `gex:by_strike`, `gex:confidence`, `gex:wall_history`, `risk:halt_threshold_pct`, `capital:sizing_phase`. **Consumer-only orphans (carry-forwards #1, #2):** `gex:updated_at`, `gex:atm_iv`. **Dead infrastructure (carry-forward #4):** `_safe_redis()` defined but never called — Governor's `data_freshness_warning` cannot rely on it without first wiring callers. New `governor:*` namespace per spec — none exist at HEAD. | Evidence pack §10.2; matrix §6 `gex:*` and `risk:halt_threshold_pct` rows; matrix §1 carry-forwards; direct grep on `_safe_redis`. |
| 4 | Current behavior matches spec | **NO.** No Governor exists. Rule-based `risk_engine` runs alone. The Final Arbiter composition rule (Section 1: `min(constitutional_cap, rules_cap, governor_cap, …)`) collapses at HEAD to `min(constitutional_cap, rules_cap)`. There is no LLM-driven structured-output veto layer, no opportunity-lean channel, no risk_score formula, no replay-calibrated thresholds. | matrix §3 AI-SPEC-001 dim 4; direct file inspection. |
| 5 | Future design? | **YES — proposed, not existing.** Tier V0.1 Cluster A; foundational anchor for Items 2–4 (Cluster A) and Items 5–10 (Clusters B/C) per spec line 1018. Spec §28 lists "V0.1 Ship Scope (4-6 Weeks)" with 11 build items; current scaffold covers approximately item 7 partially (`paper_phase_criteria` exists for graduation rules) — none of items 1–6, 8–11 are built. | Evidence pack §8 Item 1; spec §28. |
| 6 | Governance conflict | **YES — three explicit (constitutional non-overridability), one structural (sizing composition), one taxonomy (strategy enum overlap):** (a) D-005 −3% halt is HARDCODED, NO OVERRIDE (T-Rule 5); spec §10 explicitly defers — **compliant**. (b) D-022 streak halt automated and mandatory; spec §10 explicitly defers — **compliant**. (c) D-010/D-011 time stops (T-Rule 6); spec §10 explicitly defers — **compliant**. (d) D-014 4 sizing phases; spec §7 introduces `size_multiplier_cap ∈ {0, 0.25, 0.5, 1.0}` that *composes* with `_RISK_PCT[phase]` — Section 1 Composition Rule says each layer can only reduce. This is structurally compatible with D-014 *but* introduces a new authority channel that does not currently have a sanctioning D-XXX (consolidated plan §5 reserves D-023 for AI authority boundary). (e) D-021 regime guard — spec §9 LLM/ML reconciliation could be read as proposing a parallel regime channel; spec §10 explicitly says "Governor sees the post-gate result and operates within those bounds" so D-021's `regime_agreement` flag remains the binding regime gate — **compliant** but worth flagging in §7.3 to prevent drift in implementation. | approved-decisions.md D-005 (lines 33–36), D-010 (58–61), D-011 (63–66), D-014 (78–81), D-021 (115–120 with IMPLEMENTATION NOTE), D-022 (122–125); constitution T-Rules 4, 5, 6; matrix §3 AI-SPEC-001 dim 6. |
| 7 | Authority level proposed | **advisory at V0.1 → paper-binding at V0.2 (short-gamma vetoes only) → small-live auto-veto after V0.2 graduation.** Opportunity Lean is on a **separate** track: paper-only at V0.1 ≤0.25x → live at V0.2 ≤0.25x → live ≤0.5x. **Current actual authority of any analog (synthesis_agent):** advisory only (default OFF per `config.AI_PROVIDER` flag, fail-closed on errors). | Spec §4, §12, §13; `synthesis_agent.py:10–14` (default OFF + Priority-0 read in `prediction_engine.py:428–433`); system-state.md `live_trading: blocked_until_90day_AB_test_passes`. |
| 8 | Calibration dependencies | **HIGH — multi-input dependency chain.** (i) AI-SPEC-002 Strategy Attribution (utility-aware sizing inputs to `risk_score` formula §6); (ii) AI-SPEC-004 Replay Harness (V0.1 Replay Calibration step §6 — required to set initial weights before binding); (iii) AI-SPEC-005 Vol Fair-Value (Market State Card upstream feature `iv_rv_ratio`, `strategy_ev_table`, `short_gamma_ev_warning`, etc.); (iv) AI-SPEC-008 OPRA Flow Summary (20 deterministic flow features into Card); (v) AI-SPEC-013 Drift Detection (V0.2 paper-binding promotion gate refers to "drift-clean status" per consolidated plan §5 + matrix §7); (vi) ≥200 replay/advisory decision cards + ≥30 Governor veto/reduce actions before V0.2 paper-binding (spec §12); (vii) ≥100 closed paper trades for meta-label cluster activation (system-state.md "Phase Gate for Real Capital Deployment"). Pre-Item-2 historical positions in `trading_positions` lack utility labels — backfill policy is TBD. | Spec §6, §12; matrix §7 dependency graph; system-state.md gate language. |
| 9 | Training contamination risk | **MEDIUM-HIGH.** (a) Replay risk-score weight calibration depends on point-in-time Market State Card reconstruction over historical sessions where data freshness flags were not captured (the freshness substrate is currently dead code per carry-forward #4) — replay results before the freshness gate is wired must be flagged as approximate. (b) Pre-Item-10 case-store has no `calibration_eligible` flag, so any pgvector retrieval against historical predictions risks contaminated retrieval — Section 16 explicitly hard-codes `schema_quality_factor = 0.00` for legacy/contaminated rows but this guard depends on the `calibration_eligible` label existing in code, which it does not at HEAD. (c) The 2026-04-20 SPX width-widening (paired with `_RISK_PCT` Phase 1 doubling) creates a regime break in any pre-vs-post sizing comparison — replay weight optimization must respect this break. (d) Synthesis_agent's 5-field schema is not a valid training proxy for the 18-field Governor schema; existing `ai:synthesis:latest` archives cannot be relabeled forward. | Spec §6 (Replay Calibration), §16 (schema_quality_factor); evidence pack §5.2 B1-2, §9.4 (`_RISK_PCT` non-monotonic); carry-forward #4 (`_safe_redis` dead code). |
| 10 | Implementation owner | Cursor. | constitution.md T-Rule 1; cross-cutting matrix dim 10. |

---

## 6. Missing Pieces

What the spec assumes exists but doesn't, exhaustively. Cross-references §3.1, §3.2, §3.3.

**Files referenced in spec but absent:**
- No `backend/risk_governor.py` (or equivalent module). The Governor itself does not exist.
- No Market State Card generator beyond the existing `synthesis_agent.py` (which has a different schema — see Class B B2).
- No `backend/replay_harness*.py` (Item 4 dependency for Section 6 calibration).
- No `backend/vol_fair_value*.py` (Item 5 dependency for Market State Card features).
- No `backend/opra_alpha*.py` (Item 8 dependency for OPRA flow summary).
- No `backend/adversarial_review*.py` (Item 7 dependency for triggered-trade path).
- No standalone `backend/strategy_attribution*.py` (Item 2 dependency for utility-aware sizing inputs and per-trade labels).

**Tables referenced but not yet created:**
- `ai_governor_versions` (Spec §14 — full DDL provided in spec).
- `governor_decisions` (Spec §3.B `GovernorDecisionRecord` is the row shape; persistence target not named but implicit).
- pgvector case-store (Spec §1, §16) — extension itself is not enabled, no migration creates it.
- `case_type`-bearing case store (Spec §16, §22) for `actual` / `override` / synthetic-counterfactual taxonomy.
- `governor_human_overrides` or equivalent (Spec §22 — "Every operator override creates an attribution case" with 7 fields).
- `strategy_attribution.calibration_eligible` column (Item 10 cross-dependency Spec §16) — column does not exist in any current table.

**Redis keys with no producer (would block Governor freshness-warning logic if relied on):**
- `gex:updated_at` (carry-forward #1).
- `gex:atm_iv` (carry-forward #2).

**Functions called by spec but not yet defined:**
- A working caller of `prediction_engine._safe_redis()` — the function is dead code at HEAD (carry-forward #4). Without this, `data_freshness_warning` and `data_freshness_flags` (Spec §3 LLM output, §11 failure mode) cannot be reliably populated.
- A risk_score deterministic computation function (Spec §6 V0.1 formula) — not present in any module.
- A retrieval_quality_score computation function (Spec §16 formula) — not present.
- A LightGBM/LLM disagreement reconciler (Spec §9 + §17) — not present in any module.
- A decision-cache layer with the cache key per Spec §15 — not present.
- A cost circuit-breaker per Spec §21 monthly budget logic — not present.

**Feature flags assumed but not in code:**
- `agents:ai_risk_governor:enabled` (or equivalent) — does not exist; would mirror `agents:ai_synthesis:enabled`.
- A "Governor authority level" flag for the V0.1 advisory → V0.2 paper-binding promotion (Spec §12) — does not exist.
- An opportunity-lean enable flag (separate track per Spec §13) — does not exist.
- Cost-circuit-breaker thresholds (Spec §21) — no flag/key infrastructure at HEAD.

**Migrations / extensions / governance not yet present:**
- `CREATE EXTENSION IF NOT EXISTS vector;` — not present.
- D-023 (AI authority boundary; consolidated plan §5 placeholder) — not in `approved-decisions.md`.
- TASK_REGISTER §14A (Risk Governor implementation) — not present.
- MASTER_PLAN Phase 3A AI Governor entry — not present.
- system-state.md `ai_risk_governor` operational state — not present.

---

## 7. Contradictions

**(First-pass draft for Claude cross-check refinement.)**

### 7.1 Internal Contradictions

- **Spec §24 vs. spec §1 on synthesis_agent role.** §1 places "Market State Card (refactored synthesis_agent)" as a discrete pipeline stage *upstream of* the Governor. §24 says "The Market State Card is a refactored synthesis_agent that produces structured input." Both readings work, but the existing `synthesis_agent.py` produces a small JSON `{direction, confidence, strategy, rationale, risk_level}` and is *also* the system's current pre-market AI synthesizer. The spec never disambiguates whether the existing schema is replaced, augmented, or run in parallel during transition. This ambiguity is a soft Class B (B2) — not strictly self-contradictory, but operationally unclear.
- **Spec §3 LLM Output vs. §6 risk_score.** §3 says "risk_score is NOT in LLM output. The LLM provides components; deterministic code computes final risk_score." §6 risk_score formula uses `0.30 * calibrated_event_uncertainty + 0.25 * signal_conflict + 0.20 * novelty + 0.15 * data_freshness_penalty + 0.10 * recent_strategy_drift`. But `calibrated_event_uncertainty` is not the same as the LLM's `uncertainty_score` — it requires a calibration step from "LLM bucketed confidence" (§9) to "calibrated event uncertainty". The spec does not specify where this calibration step happens (LLM? deterministic post-processor? replay harness?). Soft Class B.
- **Spec §8 Rule 2 vs. §7 Size Mapping.** Rule 2 says `novelty ≥ 0.80 AND uncertainty ≥ 0.70 → governor_size_cap = 0.25` (and review_required). But §7 size mapping says `risk_score >= 0.75 → cap = 0`. With Rule 2's gate hit, computed `risk_score` would be at least `0.30*0.70 + 0.25*x + 0.20*0.80 + 0.15*y + 0.10*z = 0.21 + 0.16 + (variable) = 0.37 + variable`. The deterministic-code path could compute `risk_score >= 0.75` (block) while Rule 2 would force `cap = 0.25` (reduce). The spec doesn't state precedence. Likely Class B (clarification: Rule 2 overrides §7 when triggered? or §7 takes precedence and Rule 2 is a floor?).
- **Spec §12 V0.2 paper → small live: prerequisite ambiguity.** "Statistical: ≥ 60 paper sessions, ≥ 50 Governor veto/reduce actions". 50 vetoes over 60 paper sessions averages 0.83 vetoes/session — high block-rate. But §12 V0.1 → V0.2 floor is "block_rate among eligible short-gamma ≤ 35% (unless veto_value improves by ≥ +4R)". Whether 50 vetoes over 60 sessions clears this floor depends on eligible-trade volume per session, which the spec does not specify. Class B clarification needed for downstream operator implementation.

### 7.2 Cross-Spec Contradictions

(Sourced from `CROSS_CUTTING_EVIDENCE_MATRIX.md` §3, §4, §6, §7. Item references are matrix-indexed.)

- **AI-SPEC-001 ↔ AI-SPEC-009 (Exit Optimizer): module-boundary issue (matrix §4 risk_engine.py block; matrix §3 AI-SPEC-001 Notes line 104).** Spec §11 Failure Mode states LLM-unavailable / fallback path produces new constraint behavior on *short-gamma blocks*. Section 1 Composition Rule places `governor_cap` BEFORE execution. But all `exit_reason` literals at HEAD live in `position_monitor.py:132,174,225,379,458,549,616,625,765,781,805` — `risk_engine.py` has **zero** `exit_reason` occurrences. Any new Governor-driven halt-path exit reason must be added in `position_monitor.py` (with the AST-tested CHECK constraint extension), not in `risk_engine.py`. The spec does not address this two-file boundary. Item 9 will own the exit_reason taxonomy refactor; Item 1 must coordinate.
- **AI-SPEC-001 ↔ AI-SPEC-012 (Capital Allocation): risk_engine.py write collision (matrix §4; matrix §3 AI-SPEC-001 Notes line 105).** Both Item 1 (size_multiplier_cap composition) and Item 12 (`_RISK_PCT` rewrite) modify `risk_engine.py`. Item 12 also targets the non-monotonic ladder fix (evidence pack §9.4 — Phase 1 0.010 > Phase 2 0.0075). Both specs cannot independently rewrite the same file region; the cross-cutting matrix proposed merge order **1 → 13 → 12** for `risk_engine.py`. The Item 1 spec does not pin this sequencing.
- **AI-SPEC-001 ↔ AI-SPEC-013 (Drift Detection): authority promotion-gate dependency (matrix §7 dependency graph).** Spec §12 V0.2 paper-binding promotion criteria do not explicitly mention "drift-clean status" but the consolidated plan §5 Cluster C dependency graph and matrix §7 line 685–687 record AI-SPEC-001 → AI-SPEC-007 (Adversarial) and AI-SPEC-012 → AI-SPEC-001 + AI-SPEC-013, implying Item 13's drift gate is upstream of authority promotion. The Item 1 spec is internally consistent (its V0.1 → V0.2 gate is operational + statistical, not drift-dependent), but downstream Cluster C specs assume Item 13 demotion paths exist. If Item 13 is not yet operational, Item 1's V0.2 → small-live gate has no demotion fallback.
- **AI-SPEC-001 ↔ AI-SPEC-010 (Counterfactual P&L Attribution): pgvector / case-store dependency (matrix §3 AI-SPEC-010 block).** Spec §1 places "Supabase pgvector case retrieval" upstream of the Governor, and §16 retrieval_quality_score depends on a case store with `case_type` taxonomy and `calibration_eligible` flag. At HEAD, Item 10's `counterfactual_engine.py` writes `counterfactual_pnl` columns on `trading_prediction_outputs` (carry-forward #5) — this is observability, not a retrievable case store. Both pgvector enablement AND a richer case-store schema are prerequisites. Item 10 must extend before Item 1 can be calibration-grade.
- **AI-SPEC-001 ↔ AI-SPEC-002 (Strategy Attribution): calibration-input dependency (matrix §7 line 673).** Spec §6 risk_score formula's `recent_strategy_drift` weight implicitly consumes per-strategy attribution labels that Item 2 produces. Item 2 itself is also Cluster A V0.1 (parallel build), so this is a sequencing dependency rather than a contradiction — but it constrains shipping order.
- **AI-SPEC-001 ↔ AI-SPEC-005/006/007/008: upstream pipeline dependencies (Spec §1 + §2).** Spec §1 places Items 5, 6, 8 as deterministic-feature upstream and Item 7 as selective-downstream. None of these exist at HEAD (per evidence pack §8 Items 5, 6 partial scaffold only, 7, 8). The Item 1 V0.1 ship scope (Spec §28) includes "Strategy-aware attribution" (Item 2), "Replay harness" (Item 4), "Counterfactual ledgers" (Item 10) but not Items 5/6/7/8 — meaning the spec internally accepts that V0.1 Governor ships before its full upstream pipeline. The Market State Card "V0.1 includes only" list (Spec §24) confirms: V0.1 Card admits Item 5 EV summary "if available" and Item 8 flow summary "when available", with degraded behavior otherwise. **Not a contradiction; sequencing is internally consistent.**

### 7.3 Governance Contradictions

- **Spec §10 vs. T-Rule 5 + D-005:** Spec §10 explicitly says "Governor cannot override -3% daily halt (D-005)". This is **compliant** with T-Rule 5. No contradiction.
- **Spec §10 vs. T-Rule 6 + D-010/D-011:** Spec §10 explicitly defers to "2:30 PM time stop (D-010)" and "3:45 PM hard close (D-011)". **Compliant.**
- **Spec §10 vs. D-022:** Spec §10 explicitly defers to "Streak halt". **Compliant.**
- **Spec §7 size_multiplier_cap vs. D-014:** Spec §7 introduces a new sizing-cap channel `{0, 0.25, 0.5, 1.0}` that composes (`min`) with `_RISK_PCT[phase]` per Spec §1 Composition Rule. D-014 itself does not currently mention an AI-driven cap. T-Rule 4 ("Locked Decisions Are Final") could be read as requiring a NEW D-XXX (D-023 per consolidated plan §5) to *sanction* the Governor's authority over sizing. This is **not a contradiction** in the strict sense (D-014 is not violated; the Governor only reduces) but it **lacks a sanctioning decision record**. → Class C C1 (operator decision: ratify D-023 wording or rule the Governor's `size_multiplier_cap` falls inside D-014's existing scope).
- **Spec §23 strategy taxonomy vs. existing code naming:** Spec §23 lists `directional_debit: debit_call_spread, debit_put_spread`. `risk_engine.py:105–106` (`_DEBIT_RISK_PCT`) uses `debit_call_spread`/`debit_put_spread` (matches spec). But `synthesis_agent.py:40–41` and the MASTER_PLAN feature-flag boilerplate use `bull_debit_spread`/`bear_debit_spread`. This is a **system-wide naming inconsistency** that Item 1 will surface (since the Governor's `allowed_strategy_classes` enum is the new authoritative taxonomy) but did not create. Class A correction proposed in §10.1 to flag and align.
- **Spec §13 V0.2 live opportunity-lean criterion "no strategy bucket with negative cumulative R if n ≥ 10":** Strategy-bucket P&L tracking implicitly assumes per-strategy attribution exists (Item 2 dependency). T-Rule 9 (Paper Phase Is Mandatory) is satisfied because the lean track explicitly stays paper-only at V0.1 and gates live transition on per-bucket accounting. **Compliant** with T-Rule 9.
- **Spec §14 Champion/Challenger Asynchronous architecture:** Governor versioning is robust (no mutable aliases, snapshot pinning, prompt frozen ≥10 days). T-Rule 4 (Locked Decisions Are Final) is satisfied because version-status transitions are explicitly recorded. **Compliant.**

---

## 8. Carry-Forward Findings From P1.1 / P1.2

| Finding | Applies to this spec? | Implication |
|---------|----------------------|-------------|
| #1: `gex:updated_at` consumer-only orphan | **yes (indirect).** | Spec's `data_freshness_warning` and `data_freshness_flags` (§3 LLM Output, §11 Failure Mode) require a working freshness gate. The existing GEX-freshness substrate has no producer for `gex:updated_at` AND no caller for `_safe_redis()` (see #4). Item 1 implementation must wire BOTH the producer for `gex:updated_at` AND a caller of (or replacement for) `_safe_redis()` before `data_freshness_warning` can be honest. → §10.2 B6. |
| #2: `gex:atm_iv` consumer-only | **yes (indirect).** | Spec §1 implies the Governor receives `iv_rv_ratio` and IV-rank features via Item 5 (Vol Fair-Value) Market State Card inputs; `gex:atm_iv` is a candidate input for that pipeline. Sole consumer at `macro_agent.py:214` has no producer. If Item 1's Card eventually consumes this key, the producer must ship first. → §10.2 B6 (umbrella Class B with #1 and #4). |
| #3: MASTER_PLAN debit-spread feature flag debt | **no (not directly).** | Spec §23 strategy taxonomy uses `debit_call_spread`/`debit_put_spread` (matches `risk_engine.py:105–106`), not the missing `bull_debit_spread`/`bear_debit_spread` flags. The Governor controls strategy *classes* (Spec §23: `directional_debit`), not exact strikes. The strategy-flag governance debt is Item 7 (Adversarial) / Item 11 (Event Playbooks) / Item 12 (Capital Allocation) territory per matrix §3. **However**, the spec/code naming inconsistency (Class A, see §10.1 A2) is the same family of issue surfaced by carry-forward #3 — flag for downstream cleanup. |
| #4: `_safe_redis()` is dead code at HEAD | **yes (high impact).** | Spec §3 LLM output has `data_freshness_warning` and `data_freshness_flags` fields; Spec §11 Failure Mode lists "Data freshness fail → Block new short-gamma. No lean." The freshness substrate at HEAD is dead code: `_safe_redis()` defined at `prediction_engine.py:100` but never called (verified by P1.2 correction with `cat -A` on docstring lines 107–131). Item 1's freshness logic cannot be honest until `_safe_redis()` (or a replacement) has a real caller AND `gex:updated_at` (or whichever staleness source the spec settles on) has a producer. → §10.2 B6. |
| #5: `counterfactual_pnl` is column triple, not table | **yes (medium impact).** | Spec §3.B `GovernorDecisionRecord` includes `item10_case_id: uuid \| null` — referencing Item 10's case-store. At HEAD, Item 10's "case store" is three columns (`counterfactual_pnl_*`) on `trading_prediction_outputs`, not a separable case table with stable `case_id` IDs. The Governor cannot reference an `item10_case_id` until Item 10 grows a real case store with rowid identity. → cross-references §10.2 B4 (governor_decisions persistence) and Item 10's audit (P1.3.10). |

---

## 9. Risk Rating

**Rating:** **HIGH**

**Rationale:** Item 1 is the foundational anchor of Cluster A V0.1 (per spec §1 + §28); it composes with `risk_engine.py` (3-spec collision file with Items 12 + 13), spans `position_monitor.py` for halt-path exit_reasons (Item 9 boundary), depends on five upstream specs (Items 2, 4, 5, 8, 10) of which only Item 6 has a partial scaffold (dormant), and rests on freshness-gate infrastructure that is dead code at HEAD (carry-forward #4). The locked spec is internally consistent and constitutionally compliant on D-005/D-010/D-011/D-022 deferrals, but introduces a new sizing-authority channel (`size_multiplier_cap`) that lacks a sanctioning D-XXX. The non-monotonic `_RISK_PCT` ladder (evidence pack §9.4) is a pre-existing governance-debt landmine that any sizing-multiplier work will trip over. Multiple Class B implementation-status corrections are needed before the spec can be acted on without rework.

**Categories:**
- Spec-vs-code drift severity: **medium** (the spec itself is correct as forward design; the drift is "spec assumes infrastructure that isn't built/wired yet" rather than "spec describes code wrongly").
- Number of Class A corrections: **2** (see §10.1).
- Number of Class B corrections: **8** (see §10.2).
- Number of Class C corrections: **3** (see §10.3).
- Cross-cutting impact (specs affected): **8** (Items 2, 4, 5, 6, 7, 8, 9, 10, 12, 13 per matrix §3 + §4 + §7 — Item 1 is depended on by 7+ specs; Item 1 depends on 5+ specs).

---

## 10. Spec Corrections Required

### 10.1 Class A — Mechanical Errors

| # | Spec Section | Spec Says | Correct Value | Source of Truth |
|---|--------------|-----------|---------------|----------------|
| A1 | Section 24 (Market State Card Contract — final paragraph) | "The 8 specialist agents continue feeding Redis briefs that the Card consumes and summarizes." | **7 specialist agents** (or 6 upstream feeders + synthesis_agent itself). At HEAD the `backend_agents/` directory contains 7 non-init `.py` files: `economic_calendar.py`, `feedback_agent.py`, `flow_agent.py`, `macro_agent.py`, `sentiment_agent.py`, `surprise_detector.py`, `synthesis_agent.py`. If the spec's "8" includes a not-yet-built agent (e.g., a planned dedicated event-window agent), name it explicitly; otherwise correct to the actual count. | `ls backend_agents/*.py \| grep -v __init__` at HEAD `b0cd6b3`. |
| A2 | Section 23 (Strategy-Class Taxonomy — `directional_debit` row) | "directional_debit: debit_call_spread, debit_put_spread" | **Either** (i) keep spec wording (matches `risk_engine.py:105–106` `_DEBIT_RISK_PCT` keys) and document that `synthesis_agent.py:40–41` and MASTER_PLAN feature-flag boilerplate's `bull_debit_spread`/`bear_debit_spread` are the variant naming that needs system-wide alignment in a separate task; **or** (ii) propose a single canonical taxonomy and flag the rename surface. **Recommended action:** keep spec wording as the canonical Governor enum; add Class A note that a separate cleanup pass aligns `synthesis_agent` and feature-flag names. | `risk_engine.py:105–106`; `synthesis_agent.py:40–41`; MASTER_PLAN line 59–60. |

### 10.2 Class B — Implementation Status / Content Omissions

| # | Spec Section | Spec Says | Reality | Proposed Correction |
|---|--------------|-----------|---------|--------------------|
| B1 | Section 1 (Final Decision Stack — "Supabase pgvector case retrieval") + Section 16 (Retrieval Quality Score) | Implies pgvector is enabled and a populated case-store with embeddings exists. | `grep -rln "pgvector\|CREATE EXTENSION vector\|USING vector" supabase/migrations/` returns zero matches across all 68 migrations at HEAD. pgvector extension is **not enabled**. No embedding infrastructure exists in `backend/`. | Add Class B note to Section 1 and Section 16: pgvector enablement + case-store schema with embedding columns is a **pre-V0.1 implementation prerequisite**, not an existing capability. Section 28 V0.1 Ship Scope item 1 ("Supabase schema for AI decisions, attribution, replay, thresholds, pgvector memory") is the build target — clarify that pgvector is part of "Item 1 V0.1 schema" specifically, not assumed-present. |
| B2 | Section 1 + Section 24 ("refactored synthesis_agent" / "Market State Card is a refactored synthesis_agent") | Implies an in-place refactor of an existing module with similar surface area. | `backend_agents/synthesis_agent.py` (628 lines) produces a 5-field JSON `{direction, confidence, strategy, rationale, risk_level}`. The locked Governor schema (Section 3) has 18+ fields including event taxonomy, novelty/uncertainty/conflict scores, `allowed_strategy_classes`/`blocked_strategy_classes` enums, opportunity-lean fields, freshness flags, retrieval case IDs. The schema delta is too large for "refactor"; this is a full rewrite (with synthesis_agent's structured-output infrastructure as scaffolding). | Spec is **observability of architectural intent only** — implementation will be a full rewrite, not a refactor. Consolidated-plan annotation: classify as "rewrite using synthesis_agent.py provider scaffolding as starting point" to set correct implementer expectation. |
| B3 | Section 14 (Versioning and Rollback — `ai_governor_versions` table DDL) | Provides full DDL as if the table is part of the spec deliverable. | Migration not present at HEAD; `grep -rln "ai_governor_versions" supabase/` returns zero. | Confirm classification: spec proposes the DDL; Phase 4/Phase 2 work creates the migration. No Class B *correction* to the spec wording — tag as "scheduled buildout" so the audit trail shows it's tracked. |
| B4 | Section 3.B (GovernorDecisionRecord) | Implies a `governor_decisions` (or equivalent) persistence target with the documented row shape. | No table at HEAD. | Same as B3: spec defines the row shape; persistence target name is not specified by the spec and should be set in TASK_REGISTER §14A.2. Recommended canonical name: `ai_governor_decisions` (matches the `ai_governor_versions` namespace). |
| B5 | Section 16 (`schema_quality_factor` formula referencing `calibration_eligible = true`) | Implies `calibration_eligible` is an attribute on retrievable cases at query time. | `grep -rln "calibration_eligible" backend/ supabase/migrations/` returns zero matches in production code. The label only lives in the locked spec archive and audit infra docs. | Cross-spec sequencing: Item 1 cannot enforce `schema_quality_factor = 0.00 for contaminated rows` until Item 10 (Counterfactual P&L) extends `trading_prediction_outputs` (or its successor case store) with `calibration_eligible`. Add Class B note to Section 16: depends on AI-SPEC-010 deliverable. |
| B6 | Section 3 LLM Output (`data_freshness_warning`, `data_freshness_flags`) + Section 11 Failure Mode ("Data freshness fail") + Section 16 ("data freshness penalty") | Treats data freshness as a working signal the Governor reads. | Carry-forward #4: `_safe_redis()` at `prediction_engine.py:100` is dead code (no callers). Carry-forward #1: `gex:updated_at` has no producer. The freshness substrate is **non-functional** at HEAD. | Add Class B note: Item 1's freshness logic depends on (a) wiring a real caller of `_safe_redis()` (or replacement) AND (b) standing up producers for `gex:updated_at` and any other staleness keys the Card reads. Section 28 V0.1 Ship Scope must include "freshness substrate buildout" as a sub-item or Section 24 must mark `data_freshness_warning` as MVP-deferred. |
| B7 | Section 10 (Constitutional Gates — "Streak halt", "Phase sizing tiers") | Lists the gates as one-line bullet items. | "Streak halt" is split across two files: 3-loss reduction at `risk_engine.py:234–235` and 5-loss session halt at `prediction_engine.py:688–691`. "Phase sizing tiers" `_RISK_PCT` lives at `risk_engine.py:79–84` and is **non-monotonic** at HEAD (Phase 1 0.010 > Phase 2 0.0075 — evidence pack §9.4) by paired-design with the 2026-04-20 SPX width widening. | Add implementer-facing Class B note: (a) D-022 enforcement is split between `risk_engine.py` and `prediction_engine.py`; the Governor's "Final Arbiter" composition rule must read from BOTH paths (or its caller must be aware). (b) The current `_RISK_PCT` ladder is non-monotonic by design pending Item 12 / separate ladder fix; the Governor's `size_multiplier_cap` must NOT widen this regression. |
| B8 | Section 12 V0.2 Paper-Binding promotion gate ("≥ 200 replay/advisory decision cards") | Implies Item 4 (Replay Harness) is operational by the time the gate is evaluated. | Item 4 (Replay Harness) is itself V0.1 Cluster A future design (evidence pack §8 Item 4 — NOT YET IMPLEMENTED). At V0.1 ship, the replay decision-card stream may not yet exist in volume sufficient to clear ≥200. | Add Class B note: gate eligibility requires Item 4 to ship first AND accumulate ≥200 cards. If Item 4 ships in Week 4 of V0.1 and produces 3-5 replay decisions per simulated session, the calendar to ≥200 cards is realistic; if cadence is lower, V0.2 paper-binding promotion is calendar-blocked on Item 4 throughput. Operator should verify Item 4's expected card production rate before committing to Spec §12 thresholds. |

### 10.3 Class C — Architectural Intent Corrections

| # | Spec Section | Issue | Conflicting D-XXX or Rule | Resolution Required |
|---|--------------|-------|--------------------------|--------------------|
| C1 | Section 7 (Size Mapping — `size_multiplier_cap` over 4 buckets `{0, 0.25, 0.5, 1.0}`) | Spec proposes paper-binding (V0.2) and small-live-binding (post-V0.2 graduation) authority for an LLM-driven sizing reducer that composes (`min`) with `_RISK_PCT[phase]`. While the composition rule "each layer can only reduce" satisfies T-Rule 5 (Capital Preservation Is Absolute) literally — the Governor cannot *increase* risk — the existing decision base does not contain a D-XXX explicitly sanctioning an LLM as a sizing-authority channel. | T-Rule 4 (Locked Decisions Are Final) + D-014 (Position Sizing — current scope is rules-only auto-advance with manual Phase 4); consolidated plan §5 reserves D-023 placeholder for "AI authority boundary". | **Operator decision:** ratify a new D-023 wording sanctioning the Governor's `size_multiplier_cap` channel under T-Rule 4, **OR** rule that the Governor's reductive-only authority falls inside D-014's existing "automatic regression" provision and no new D-XXX is needed. Default per consolidated plan: ratify D-023 with explicit scope ("LLM-driven sizing reducer; cannot increase any cap; cannot override D-005/D-010/D-011/D-022; promotion to live-binding requires V0.2 graduation criteria + 90-day A/B per system-state.md"). |
| C2 | Section 12 V0.1 Advisory → V0.2 Paper-Binding gate AND Section 13 Lean Live 0.25x → 0.5x gate | Both promotion gates use a mix of statistical thresholds (≥200 cards, ≥30 actions, Wilson lower-95 ≥ 0.40, etc.) and operational SLOs (parse rate ≥99.5%, prompt frozen ≥10 days). They do **not** explicitly require operator approval of each promotion event, and §17 ("Authority degradation requires explicit operator action") only addresses *demotion*. Whether automated promotion is intended — and if so, how it composes with constitution T-Rule 9 (Paper Phase Is Mandatory, 45 days minimum, 12 GLC criteria) and D-013 (Paper Phase) — is not specified. | T-Rule 9 + D-013 + system-state.md `live_trading: blocked_until_90day_AB_test_passes` (line 7–8). | **Operator decision:** spec §12 / §13 promotion gates must explicitly state whether (a) all promotions are automated when criteria pass, (b) all promotions require operator approval per event, or (c) only V0.2 → live promotion requires explicit operator approval (with paper-binding promotions automated). Default per T-Rule 9 + system-state.md: any transition that affects live capital (V0.2 → small-live veto, lean live 0.25x → 0.5x) requires explicit operator approval; paper-binding-only promotions can be automated subject to GLC-001..012 cleanliness. |
| C3 | Section 4 ("Capped opportunity lean") + Section 5 (Opportunity Lean Constraints) | The opportunity-lean channel introduces a new *positive-direction* trade rationale (the Governor "allows" a directional defined-risk trade based on event-source quality and price confirmation) that is fundamentally different from the rest of the Governor's reductive-only authority. Even at ≤0.25x paper-only, this is the **only** Governor surface that proposes a trade rather than gating one. The architecture-statement principle (Section 27: "AI controls admissibility and size ceilings, not trade execution") is in tension with a positive-direction lean recommendation — the lean is admissibility-of-a-new-strategy-class, not just sizing-cap on an already-proposed trade. | T-Rule 5 (Capital Preservation Is Absolute) — the lean is reductive in dollar terms (small size, defined risk) but additive in *trade count*, which can erode expectancy. T-Rule 9 (Paper Phase Is Mandatory) is satisfied by V0.1 paper-only constraint. Spec §27 self-flag: "the dangerous assumption is that semantic event-risk detection has enough precision to improve Sharpe AFTER false veto costs"; the lean compounds this risk. | **Operator decision:** ratify the lean channel as a sanctioned new authority (and likely document in D-023 alongside C1), **OR** cut the lean channel from V0.1 and re-introduce as a separate spec (AI-SPEC-001b or AI-SPEC-014) that ships only after the core Governor passes graduation. Default per consolidated plan §5 conservative-first principle: defer lean channel to a separate spec; Item 1 V0.1 ships as veto-only. |

---

## 11. Governance Updates Required

What governance documents must change for AI-SPEC-001 to integrate cleanly:

- [x] `approved-decisions.md` — **new D-XXX needed: D-023 (AI Authority Boundary).** Wording must cover (a) Governor's `size_multiplier_cap` channel composing with `_RISK_PCT`, (b) explicit non-overridability of D-005/D-010/D-011/D-014/D-021/D-022 with reductive-only constraint, (c) opportunity-lean channel disposition (cf. C3 — either folded into D-023 or deferred to separate spec), (d) promotion-gate authority handoff between automated criteria and operator approval (cf. C2). Per consolidated plan §5.
- [ ] `approved-decisions.md` — existing D-XXX modified: **none required.** Spec defers cleanly to D-005, D-010, D-011, D-014, D-021, D-022 without amendment.
- [x] `MASTER_PLAN.md` — **new phase entry needed:** "Phase 3A: AI Risk Governor V0.1" (or equivalent), per Spec §28 V0.1 ship-scope (4–6 weeks; 11 build items).
- [ ] `MASTER_PLAN.md` — Phase update needed for existing phases: not directly; existing phases (12A–12N, B1, B4, etc.) remain. Add a new sub-phase block for Item 1.
- [x] `TASK_REGISTER.md` — **new section needed: §14A** (Risk Governor implementation). Sub-items per §12.2 below.
- [x] `system-state.md` — **operational state change:** add `ai_risk_governor: { phase: 'not_started' \| 'v0.1_advisory' \| 'v0.2_paper_binding' \| 'v0.2_small_live' \| 'production' \| 'demoted', authority_promoted_at: timestamp \| null, last_demotion_reason: text \| null }` (or equivalent) to operational state schema. Tracks promotion-gate progression per Spec §12 + §17.
- [ ] `constitution.md` — T-Rule clarification needed: **flag only — do not propose.** T-Rule 5 already covers D-005 non-overridability; T-Rule 6 covers D-010/D-011 time stops; T-Rule 4 covers locked-decision finality. The Governor design respects all three. If D-023 is ratified to sanction LLM-driven sizing authority, T-Rule 4 will need a one-line note that D-023 is the explicit AI-authority-boundary record (no rule change; just a pointer for future readers).

Cross-cutting matrix §3 dimension 6 already flagged the D-005, D-014, D-021, D-022 touchpoints; the matrix did not propose D-023 wording (out of scope at P1.2).

---

## 12. TASK_REGISTER Implications

### 12.1 Pre-implementation tasks (must complete before P1.3.1 audit can close)

These items block the audit from being marked "approved" at §14:

- **Operator decision on C1** (D-023 wording for AI authority boundary, or rule that no new D-XXX is needed under D-014's existing scope).
- **Operator decision on C2** (promotion-gate authority handoff: automated vs. operator-approved per transition).
- **Operator decision on C3** (opportunity-lean channel disposition: include in V0.1 or defer to separate spec).
- **Cross-spec sequencing decision:** confirm matrix §4 proposed merge order **1 → 13 → 12** for `risk_engine.py` — if Item 13 ships before Item 1 the proposed sequencing changes.
- **Class A A1 + A2 corrections:** mechanical fixes batch-cleared at end of Phase 1 (Gate 1) per template §10 batch rule — no operator approval per item.
- **Class B consolidated list:** B1–B8 require operator approval as a single batch per template §10.2 rule.

### 12.2 Implementation tasks (Cursor work after Phase 4 doc integration)

High-level decomposition of Section 14A (Risk Governor) into TASK_REGISTER-able sub-items. Not full task specs — enough to populate §14A:

- **14A.0 — Pre-V0.1 schema bootstrap (3-5 days):**
  - 14A.0.1 — Migration: `CREATE EXTENSION IF NOT EXISTS vector;`
  - 14A.0.2 — Migration: `ai_governor_versions` (full DDL per Spec §14)
  - 14A.0.3 — Migration: `ai_governor_decisions` (row shape per Spec §3.B)
  - 14A.0.4 — Migration: pgvector case-store table for retrieval (`ai_governor_cases` or extend `trading_prediction_outputs` with embedding column — Item 10 cross-coordination required)
  - 14A.0.5 — Migration: extend `trading_positions.exit_reason` CHECK constraint with new `governor_halt_*` values (cross-coordination with Item 9 boundary)
  - 14A.0.6 — Add `governor_halt_*` exit_reason literals to `position_monitor.py` taxonomy (matches AST test pattern at `test_exit_reason_constraint.py`)
- **14A.1 — Freshness substrate (1-2 days):**
  - 14A.1.1 — Wire a real caller of `_safe_redis()` in `prediction_engine.py` (or replace the function with one that's actually called by the Card generator)
  - 14A.1.2 — Stand up producer for `gex:updated_at` (likely in `gex_engine.py` near existing `gex:net` setter at line 163)
  - 14A.1.3 — Stand up producer for `gex:atm_iv` (carry-forward #2)
  - 14A.1.4 — Integration test: freshness gate triggers `data_freshness_warning = true` when keys are stale
- **14A.2 — Market State Card generator (5-7 days):**
  - 14A.2.1 — Decision: full rewrite vs. extending `synthesis_agent.py` (Class B B2). Default: rewrite using synthesis_agent's provider-pluggable scaffolding.
  - 14A.2.2 — Card schema implementation per Spec §24 (≤6-10k tokens)
  - 14A.2.3 — Item 5 / Item 8 input wiring with degraded-mode fallback (Spec §24 says "when available")
- **14A.3 — Governor LLM agent (5-7 days):**
  - 14A.3.1 — Structured-output schema enforcement per Spec §3 (Validator Layer Spec §19)
  - 14A.3.2 — Risk score deterministic computation per Spec §6 V0.1 formula
  - 14A.3.3 — Size mapping per Spec §7
  - 14A.3.4 — Deterministic fallback rules per Spec §8 (Rules 1–4)
  - 14A.3.5 — Failure-mode behavior per Spec §11
- **14A.4 — Final Arbiter composition rule (3-5 days):**
  - 14A.4.1 — `final_size = min(constitutional_cap, rules_cap, governor_cap, meta_labeler_cap, adversarial_cap_if_present)` per Spec §1
  - 14A.4.2 — Cross-coordination with Item 6 meta-labeler scaffold (already exists at `model_retraining.py` + `execution_engine.py`)
  - 14A.4.3 — Cross-coordination with Item 7 adversarial path (selective; future)
- **14A.5 — Decision caching (Spec §15) (2-3 days)**
- **14A.6 — Champion/Challenger asynchronous architecture (Spec §14, async section) (4-6 days)**
- **14A.7 — Cost circuit breaker (Spec §21) (1-2 days)**
- **14A.8 — Observability dashboard (Spec §18) (3-4 days; UI shipped via Lovable + backend endpoints)**
- **14A.9 — Replay calibration (cross-coordination with Item 4 / Section 14B) (5-7 days; Item 4 must be operational first per Spec §6 V0.1 Replay Calibration)**
- **14A.10 — Promotion-gate machinery (Spec §12 + §13) (3-5 days; depends on §17 demotion paths from Item 13 for full V0.2 → live readiness)**

### 12.3 Calibration / Data dependencies

What labeled data must exist before AI-SPEC-001 is calibration-grade (cross-ref dimension 8):

- **Item 2 (Strategy Attribution)** must produce per-trade utility labels for Spec §6 `recent_strategy_drift` weight.
- **Item 4 (Replay Harness)** must produce ≥200 replay/advisory decision cards before Spec §12 V0.1→V0.2 paper-binding gate can be evaluated.
- **Item 5 (Vol Fair-Value)** must produce `iv_rv_ratio`, `strategy_ev_table`, `short_gamma_ev_warning`, `vol_engine_confidence`, `skew_z`, `surface_risk_flags` for Market State Card per Spec §2.
- **Item 8 (OPRA Flow)** must produce 20 deterministic flow features for Card per Spec §2.
- **Item 10 (Counterfactual P&L Attribution)** must extend the case-store with a `case_type` taxonomy (`actual` / `override` / synthetic) and a `calibration_eligible` flag per Spec §16; current 3-column scaffold (carry-forward #5) is insufficient.
- **Item 13 (Drift Detection)** must produce drift-clean signals for the V0.2 → small-live promotion path (Spec §12 + §17 demotion fallback).
- ≥100 closed paper trades for meta-label cluster activation (system-state.md Phase Gate). This is a parallel constraint on Item 6 readiness.

---

## 13. Recommended Status

Pick exactly one. (One of these checkboxes must be checked.)

- [ ] **spec_accurate_repo_missing** — Spec is correct as written; nothing exists in repo yet; ready for clean buildout.
- [ ] **spec_accurate_repo_partial** — Spec is correct; partial scaffold exists (cite); spec describes the full target.
- [ ] **spec_needs_factual_correction_only** — Spec has Class A errors only; intent is sound; mechanical fixes will land in Phase 2.
- [ ] **spec_has_semantic_drift_from_locked_intent** — Spec has Class B corrections that change implementation meaning but not architectural goal. Phase 2 corrections + operator approval.
- [x] **spec_conflicts_with_existing_governance** — Spec contains Class C item(s) requiring new D-XXX or revision before integration. (Three Class C items: C1 D-023 sanctioning of size_multiplier_cap authority; C2 promotion-gate handoff between automated criteria and operator approval; C3 opportunity-lean channel disposition.)
- [ ] **spec_should_be_split_into_separate_proposal** — Spec scope is too broad and should be decomposed before integration. Operator decision.

> **Note on the choice:** Class A and Class B counts are both high (2 + 8) and non-trivial, but the determining factor is the Class C trio. Per template §10.3 ("Class C corrections block the redline from closing"), the redline cannot move to Phase 2 corrections until the operator decides on D-023 (C1), promotion-gate handoff (C2), and lean channel disposition (C3). The recommended status reflects that operator decisions, not just doc edits, are the next blocker.

---

## 14. Sign-Off

| Auditor | Sign-off Status | Date | Notes |
|---------|----------------|------|-------|
| Primary (Cursor) | pending | 2026-04-26 | First-pass redline produced. §1, §3, §4, §10.1 fully populated by Cursor; §2, §5–§13 are best-effort first drafts for Claude / GPT review. Cursor flags C1 + C2 + C3 as Class C operator-decision blockers; flags B1–B8 as Class B implementation-status corrections needing consolidated operator approval; flags A1 + A2 as Class A mechanical errors batchable at Gate 1. Cursor cannot self-sign "approved" because §13 status is `spec_conflicts_with_existing_governance`. |
| Cross-check (Claude) | pending | YYYY-MM-DD | Awaiting cross-spec contradiction review (§7.2) and carry-forward verification (§8). |
| Validator (GPT-5.5 Pro) | pending | YYYY-MM-DD | Awaiting §2 spec-intent validation and §10.3 Class C escalation review. |
| Operator | pending | YYYY-MM-DD | Awaiting decisions on C1, C2, C3 and consolidated approval of Class B B1–B8. |

If all four sign-offs are "approved", the redline is closed and the spec moves to Phase 2 correction application.

If any auditor signs "dispute", the redline returns to whoever first claimed verified for re-verification.

If operator signs "requires-revision", redline reopens with operator's notes.

---

## Redline File Location

`trading-docs/08-planning/ai-architecture-audits/AI-SPEC-001.md`

---

## Process Notes

1. **Single binding format:** This redline follows `_template.md` (P1.3.0) verbatim — same 14 sections, same headings, same trailer sections.

2. **Three-AI authority split (per consolidated plan §2 audit roles):**
   - Cursor = primary auditor (§3 + §4 verification of repo evidence)
   - Claude = cross-check auditor (§7.2 cross-spec contradictions, §8 carry-forward applicability)
   - GPT-5.5 Pro = architectural validator (§2 spec intent, §10.3 Class C escalations)

3. **Workflow status:**
   - Step 1 ✅ — Locked spec + template + evidence pack + matrix received.
   - Step 2 ✅ — Cursor §1–§6 filled from repo evidence.
   - Step 3 (next) — Claude reviews §1–§6, refines §7–§8.
   - Step 4 (after Claude) — GPT validates §2 spec intent and §10.3 Class C escalations.
   - Step 5 ✅ (this commit) — redline committed to `trading-docs/08-planning/ai-architecture-audits/AI-SPEC-001.md`.
   - Step 6 (after Steps 3–4) — Operator reviews §10–§14; signs §14 or returns for revision.

4. **Class A corrections do NOT need operator approval per-item.** Batch-cleared at end of Phase 1 (Gate 1).

5. **Class B corrections need operator approval as a consolidated list,** not per-correction. B1–B8 should be reviewed together.

6. **Class C corrections block the redline from closing** until operator either approves a new D-XXX (D-023) or rejects the spec change. C1, C2, C3 are operator-only decisions.

7. **No code changes during audit.** Phase 1 is read-only. Code changes happen in Phase 2 + downstream.

---

## Out of Scope For The Per-Item Audit

The following are NOT done as part of this audit:

- Modifying the locked spec at `archive/raw-locked-specs-2026-04-26/ITEM_1_AI_RISK_GOVERNOR_LOCKED.md` (immutable).
- Writing new D-XXX entries to `approved-decisions.md` (Phase 5).
- Updating `MASTER_PLAN.md` (Phase 5).
- Creating tables/migrations (downstream implementation, P-Phase 4+).
- Writing test cases (downstream implementation).
- Auditing other specs (one redline per spec).

If during this audit a contradiction with another spec was discovered, it is documented in §7.2 and the cross-cutting matrix tracks it. No other spec's audit is opened early.
