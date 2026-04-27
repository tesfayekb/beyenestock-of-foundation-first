# Spec Verification Audit — AI-SPEC-002

> **Status:** First-pass redline (P1.3.2). Cursor primary-auditor sections (§1, §3, §4, §10.1) populated; first-pass drafts of §2, §5–§13 for Claude cross-check and GPT validation.
> **Binding format:** Follows `trading-docs/08-planning/ai-architecture-audits/_template.md` (P1.3.0).
> **Created:** 2026-04-26 (Phase 1 P1.3.2 of `CONSOLIDATED_PLAN_v1.2_APPROVED.md`).
> **Source spec:** `trading-docs/04-modules/ai-architecture/archive/raw-locked-specs-2026-04-26/ITEM_2_STRATEGY_AWARE_ATTRIBUTION_LOCKED.md` (1149 lines, locked 2026-04-26, immutable).

---

## 1. Audit Header

| Field | Value |
|-------|-------|
| Spec ID | AI-SPEC-002 |
| Spec name | Strategy-Aware Attribution Schema |
| Stable ID | PLAN-ATTR-001 |
| Tier | V0.1 |
| Cluster | A (foundational) |
| Audit date | 2026-04-26 |
| Repo HEAD at audit time | `6be9809be3988b297074a2ea972bda755a074ce3` (P1.3.1b merged; running register backfilled with pre-audit findings) |
| Primary auditor | Cursor |
| Cross-check auditor | Claude |
| Architectural validator | GPT-5.5 Pro |
| Cross-cutting matrix reference | `CROSS_CUTTING_EVIDENCE_MATRIX.md` §3 (AI-SPEC-002 block, lines 110–131), §4 (`backend/strategy_performance_matrix.py` block lines 478–486; `trading_positions` block lines 498–510), §5 (shared Supabase tables), §7 (dependency graph — Item 2 as critical-path root, lines 668–705), §8 (carry-forward #5 — `counterfactual_pnl` columns vs table) |
| Evidence pack reference | `AI_ARCH_EVIDENCE_PACK.md` §6.1 (backend module map — confirms no `attribution` files), §7.1 (existing `trading_positions` schema), §7.2 (proposed tables — three Item 2 tables absent), §8 Item 2 (lines 393–398 — NOT YET IMPLEMENTED), §9.6 (`counterfactual_pnl` columns-not-table), §10 (Redis key inventory — no `attribution:*` namespace, `strategy_matrix:*` exists) |

---

## 2. Spec Intent Summary (verified by GPT)

**(First-pass draft for GPT-5.5 Pro to refine.)**

AI-SPEC-002 introduces a four-table architecture (`trading_positions` / `trade_counterfactual_cases` / `strategy_attribution` / `strategy_utility_labels`) that separates execution from attribution from learning labels so that Items 5, 6, 7, 9, 10, 11, and 13 can train on calibration-grade strategy-specific outcome labels rather than generic per-trade P&L. The spec's load-bearing safety property is the `calibration_eligible` flag, enforced structurally at three layers (database trigger on `contamination_reason IS NOT NULL` → `calibration_eligible = false`; application accessor; meta-labeler training accessor in Item 6) so contaminated, partial, or low-quality rows cannot enter the learning loop. Path metrics, fill prices, and outcome enums are **immutable** post-write — material corrections happen via `supersedes_attribution_id` pointers and a new `is_current = false` flag rather than UPDATE — so audit history is preserved and training queries always read the canonical row. Authority level is purely advisory (labels do not gate trades); the spec's V0.1 critical risk is training contamination on legacy data, mitigated by `simulation_status='legacy_observability_only'` + `calibration_eligible=false` for any pre-Commit-4 / pre-Item-2 row.

---

## 3. Repo Evidence (verified by Cursor)

**Verification methodology:** Every concrete schema / file / FK / Redis-namespace claim in the locked spec was verified against repo state at HEAD `6be9809` using `grep -rln`, `wc -l`, direct file reads, and migration inventory. AI-SPEC-002 is overwhelmingly forward-design — it cites no commit hashes — so verification focuses on (a) what exists today that overlaps the spec's scope, (b) what the spec assumes exists but doesn't, and (c) which referenced columns / tables / FK targets actually map to current `supabase/migrations/` artifacts.

### 3.1 File/Module References

The spec's only direct backend file citation is `backend/eod_attribution_engine.py` (Section 6 — schedule 16:35 ET). Implicit references are surfaced from cross-cutting matrix §3 (closest existing logic) and §4 (`strategy_performance_matrix.py` touchpoints).

| Spec Reference | Verification | Status |
|---------------|--------------|--------|
| Spec §6 Job Specification: `backend/eod_attribution_engine.py` (16:35 ET schedule, idempotent, process_date param) | `test -f backend/eod_attribution_engine.py` returns absent. `test -f backend/attribution_engine.py` absent. `test -d backend/eod_jobs/` absent. `grep -rln "attribution" backend/ backend_agents/ backend_earnings/` returns **zero matches**. Evidence pack §8 Item 2 line 397 corroborates: "No file matches 'attribution' in `backend/`." | **not-yet-created. Class B (see §10.2 B1 tagged "scheduled buildout").** |
| Implicit (cross-cutting matrix §3 line 118): closest existing logic is `backend/strategy_performance_matrix.py` | File exists, **229 lines**. Reads `trading_positions` (`status='closed'`, `position_mode='virtual'`, last 90 days; `strategy_type, entry_regime, net_pnl, status` only) at lines 35–43. Aggregates per `(regime, strategy_type)` cell with single-pass profit_factor/win_rate/avg_pnl computation (lines 53–95). Writes Redis key `strategy_matrix:{regime}:{strategy}` with TTL 86400×90 at line 104. Sizing reducer `get_matrix_sizing_multiplier()` at line 130 (returns 0.75 when `trade_count ≥ 10 AND win_rate < 0.40`). Entry point `run_matrix_update()` at line 185, scheduled in `backend/main.py:1391`. Tests at `backend/tests/test_strategy_performance_matrix.py`. **Aggregates ex-post over batches; does NOT label per-trade.** | **verified — file exists at HEAD; scope is regime × strategy aggregation only, NOT per-trade attribution. Spec is silent on whether this file should be refactored to consume `strategy_attribution` once Item 2 ships, coexist as an independent reducer, or be deprecated. Class B (see §10.2 B5).** |
| Spec §6 Phase 1 step 2.a: "Fetch path metrics from `closed_trade_path_metrics`" | `grep -rln "closed_trade_path_metrics"` across `supabase/migrations/`, `backend/`, `backend_agents/`, `backend_earnings/`, `src/` returns matches **only** in two archived spec files (`ITEM_2_STRATEGY_AWARE_ATTRIBUTION_LOCKED.md` and `ITEM_10_COUNTERFACTUAL_PNL_LOCKED.md`). Zero references in production code or migrations. The **table does not exist anywhere in the codebase.** No `mae_R` / `mfe_R` / `peak_unrealized_pnl` columns in any migration. | **not-yet-created — substrate gap. Class B (see §10.2 B2 — V0.1 ship-scope omits path-metrics substrate).** |
| Spec §1 / §16 Architectural Commitment: "`trading_positions` remains the execution ledger only — Don't overload it with attribution" | `grep -nE "attribution_(direction\|structure\|timing\|vol)"` against the baseline migration `supabase/migrations/20260416172751_*.sql:203–206` shows the table **already has 4 attribution columns**: `attribution_direction BOOLEAN`, `attribution_structure BOOLEAN`, `attribution_timing BOOLEAN`, `attribution_vol BOOLEAN`. `grep -rln "attribution_direction\|attribution_structure\|attribution_timing\|attribution_vol" backend/` returns zero matches in any backend file (only the migration, `MARKETMUSE_MASTER.md` doc, and `src/integrations/supabase/types.ts`). **Columns exist as schema; no production code path writes them.** | **partial contradiction with spec architectural intent — the table is already overloaded with 4 dead attribution columns. Class C (see §10.3 C3) — operator decision required on disposition.** |
| Implicit reference: `backend/main.py` EOD job orchestration (16:35 ET schedule sits within existing EOD chain) | `backend/main.py:238 run_matrix_update_job`, `:256 run_eod_criteria_evaluation`, `:596 run_eod_reconciliation_job`. Counterfactual labeler EOD at 4:25 PM ET (per `20260421_add_counterfactual_pnl.sql` comment line 19). **No `run_eod_attribution_job` defined.** | **not-yet-created — orchestration slot needs to be added in `main.py` when Item 2 ships. Surfaced in §12.2.** |
| Implicit reference: `backend/counterfactual_engine.py` (Item 10 EOD labeler — referenced in §12 Integration With Other Items as the producer of counterfactual outcomes for blocked decisions) | File exists at HEAD (per cross-cutting matrix §4 lines 462–476 — 406 lines per evidence pack §8 Item 10). Per migration comment line 4 of `20260421_add_counterfactual_pnl.sql`: "Pure observability — never read by any trading-decision path." Today writes 3 columns on `trading_prediction_outputs` for no-trade signals; does NOT produce a `trade_counterfactual_cases` row ledger. | **partial — Item 10 has a scaffold but it is column-shaped, not table-shaped. Carry-forward #5 applies HIGH-IMPACT (see §8 row 5 + §10.2 B7 + §10.3 C2).** |

### 3.2 Supabase Schema References

The spec's §2, §8, and §15 V0.1 Ship Scope enumerate three new tables with full DDL plus FK references to four other tables. The verifications below cover all schema artifacts the spec relies on.

| Spec Reference | Verification | Status |
|---------------|--------------|--------|
| `strategy_attribution` (Spec §2 — full DDL: id, case_id, position_id, decision_id, meta_labeler_decision_id, adversarial_decision_id, candidate_id, decision_outcome enum, case_type enum, strategy_hint, strategy_type/class enums, strategy_structure JSONB, structure_quality enum, simulation_status enum, calibration_eligible BOOLEAN, attribution_schema_version, label_version, time/market state, pricing/P&L, path metrics, Item 5 fields, outcome classification, strategy_metrics JSONB with GIN index, data_quality_flags TEXT[] with array CHECK, contamination_reason CHECK, supersedes_attribution_id, is_current, timestamps) | `grep -rln "strategy_attribution" supabase/migrations/` returns **zero matches across all 68 migration files at HEAD `6be9809`**. Evidence pack §7.2 + cross-cutting matrix §3 line 119 corroborate. | **not-yet-created. Class B (see §10.2 B2 — V0.1 deliverable, tag as "scheduled buildout").** |
| `trade_counterfactual_cases` (Spec §1 — referenced as Item 10 deliverable; `case_id UUID REFERENCES trade_counterfactual_cases(id)`) | `grep -rln "trade_counterfactual_cases" supabase/migrations/` returns **zero matches**. Item 10's existing scaffold is `counterfactual_pnl` / `counterfactual_strategy` / `counterfactual_simulated_at` columns on `trading_prediction_outputs` (per `20260421_add_counterfactual_pnl.sql:8–14` and per migration comment line 21–24: "trading_prediction_outputs does not persist a per-prediction strategy hint"). Carry-forward #5 / PRE-P11-4 of running register §0.2: column-not-table. | **not-yet-created and architecturally divergent from Item 10's existing column-shaped scaffold. Class B (see §10.2 B7) + Class C (see §10.3 C2).** |
| `strategy_utility_labels` (Spec §8 — full DDL: attribution_id FK, case_id, position_id, strategy_type, utility_score, y_take BOOLEAN, label_version, label_formula_version, calibration_eligible, reason_codes TEXT[]) | `grep -rln "strategy_utility_labels" supabase/migrations/` returns **zero matches**. | **not-yet-created. Class B (see §10.2 B2).** |
| FK target `ai_governor_decisions(decision_id)` (Spec §2 line 44) | `grep -rln "ai_governor_decisions"` across `supabase/migrations/` and `backend/` returns matches **only in archived spec files and audit infrastructure docs**. Zero matches in production code/migrations. AI-SPEC-001 audit `B-AI-001-4` (running register §2) noted this table needs canonical naming and is part of Item 1's V0.1 buildout. | **not-yet-created — Item 1 dependency. Class B (see §10.2 B3 — FK dependency cascade).** |
| FK target "future Item 6 table" — `meta_labeler_decision_id UUID NULL` (Spec §2 line 45 inline comment "references future Item 6 table") | Spec gives no canonical name. `grep -rln "meta_labeler_decisions"` returns zero matches in code/migrations. | **not-yet-created — Item 6 dependency, no canonical name in spec. Class B (see §10.2 B3).** |
| FK target "future Item 7 table" — `adversarial_decision_id UUID NULL` (Spec §2 line 46 inline comment "references future Item 7 table") | Spec gives no canonical name. `grep -rln "adversarial_decisions"` returns zero matches in code/migrations. | **not-yet-created — Item 7 dependency, no canonical name in spec. Class B (see §10.2 B3).** |
| FK target `trading_positions(position_id)` (Spec §2 line 43: `position_id UUID NULL REFERENCES trading_positions(position_id)`) | `trading_positions` exists at `supabase/migrations/20260416172751_*.sql:159`. **Primary key is `id UUID` (line 160), not `position_id`.** No `position_id` column anywhere on `trading_positions`. The spec's FK references a column that does not exist. | **wrong-column-name. Class A (see §10.1 A1).** |
| `trading_positions` source columns (Spec §6 EOD engine implies copy from `entry_credit`, `entry_debit`, `gross_pnl`, `slippage_estimate`, `net_pnl_after_slippage`, `realized_R`, `entry_spx`, `exit_spx`, `entry_vix`, `exit_vix`, `mae_R`, `mfe_R`, etc.) | Migration `20260416172751_*.sql:168–202` defines actual columns: `entry_credit`, `entry_slippage`, `entry_spx_price`, `gross_pnl`, `slippage_cost`, `net_pnl`, `peak_pnl`, `current_pnl`, `exit_credit`, `exit_slippage`, `exit_spx_price`, plus `entry_regime`, `entry_rcs`, `entry_cv_stress`, `entry_touch_prob`, `entry_greeks JSONB`. **No `entry_vix` / `exit_vix` columns on `trading_positions`** — VIX context lives elsewhere (likely Redis or `trading_prediction_outputs.snapshot`). **No `mae_R` / `mfe_R` columns** — the only path metric is `peak_pnl` and `current_pnl`. **No `realized_R` column** — only raw `gross_pnl` / `net_pnl` (dollars, not R). **No `entry_debit` column** — debit strategies use the same `entry_credit` field with sign convention (verified by migration `20260419_add_strategy_types.sql` adding `debit_*` strategy_type values). | **partial — source columns are not all on `trading_positions`. The EOD engine pseudocode in §6 silently assumes a `closed_trade_path_metrics` table with these fields exists; per row above, that table does not exist. Class B (see §10.2 B2).** |
| `trading_positions.strategy_type` enum (Spec §2 strategy_type CHECK) | Migration `20260419_add_strategy_types.sql:11–22` defines exactly the 10 values the spec lists: `put_credit_spread`, `call_credit_spread`, `iron_condor`, `iron_butterfly`, `debit_put_spread`, `debit_call_spread`, `long_put`, `long_call`, `long_straddle`, `calendar_spread`. | **verified — enum match.** |
| `trading_positions.exit_reason` taxonomy (relevant to spec's `outcome_mode` per-strategy enum which includes `forced_close_1430`, `forced_close_halt`, etc.) | Migration `20260421_exit_reason_comprehensive.sql:48–78` is the source of truth — comprehensive 22-value allowlist including legacy 11 (`profit_target`, `stop_loss`, `time_stop_230pm`, `time_stop_345pm`, `touch_prob_threshold`, `cv_stress_trigger`, `state4_degrading`, `portfolio_stop`, `circuit_breaker`, `capital_preservation`, `manual`) and 11 D-rule-specific values (`take_profit_40pct`, `stop_loss_150pct_credit`, `take_profit_debit_100pct`, `stop_loss_debit_100pct`, `cv_stress_exit_d017`, `time_stop_230pm_d010`, `time_stop_345pm_d011`, `emergency_backstop`, `watchdog_engine_silent`, `eod_reconciliation_stale_open`, `straddle_pre_event_exit`). **Spec's `outcome_mode` enum (Section 4) does NOT match this taxonomy** — e.g., spec's `forced_close_1430` corresponds to `time_stop_230pm` / `time_stop_230pm_d010`; spec's `forced_close_halt` corresponds to multiple values (`emergency_backstop`, `circuit_breaker`, `capital_preservation`, etc.). | **mismatch — spec's `outcome_mode` enum needs an explicit mapping function from real `exit_reason` values; spec is silent. Class B (see §10.2 B4).** |
| `trading_positions.attribution_*` legacy columns (`attribution_direction`, `attribution_structure`, `attribution_timing`, `attribution_vol` — all `BOOLEAN`) | Migration `20260416172751_*.sql:203–206` (baseline). `grep -rln "attribution_(direction\|structure\|timing\|vol)" backend/` returns **zero matches in production code**. The columns are dead — present in schema, never written or read. | **dead schema. Spec §1 architectural commitment ("don't overload trading_positions with attribution") is contradicted by HEAD reality. Class C (see §10.3 C3 — operator decision required).** |
| `trading_positions.prediction_id` / `decision_context` (added by `20260421_add_decision_context.sql`) | Migration adds two columns: `decision_context JSONB` (snapshot of feature flags + model config at trade entry) and `prediction_id UUID REFERENCES trading_prediction_outputs(id)`. Spec does **not** reference either column; the spec's own `candidate_id UUID NULL` and `decision_id UUID NULL REFERENCES ai_governor_decisions(decision_id)` are different fields. | **note — spec missed an existing FK channel. Future cross-spec coordination question for §12.3 (whether `strategy_attribution.candidate_id` should equal `trading_positions.prediction_id`). Class B (see §10.2 B8).** |
| `trading_prediction_outputs` (referenced indirectly via `prediction_id` FK above and via Item 10 column-not-table scaffold) | Created in `20260416172751_*.sql:68`. Has `counterfactual_pnl NUMERIC(10,2)`, `counterfactual_strategy TEXT`, `counterfactual_simulated_at TIMESTAMPTZ` from `20260421_add_counterfactual_pnl.sql`. RLS enabled. | **verified — table exists. The 3 counterfactual columns exist; the spec's `trade_counterfactual_cases` table does not. See B7.** |
| Trigger: "contamination_reason IS NOT NULL → calibration_eligible MUST be false" (Spec §2 "Critical Database-Level Rule" line 245) | Spec describes the trigger but does not provide DDL for it. Spec §15 V0.1 Ship Scope item 4 lists "Trigger enforcing contamination_reason → calibration_eligible = false" as required. No such trigger exists at HEAD (table itself doesn't exist). | **not-yet-created — part of V0.1 buildout. Class B (see §10.2 B2 — but flag explicitly that the trigger DDL is not in §2 spec text and must be authored during implementation).** |

### 3.3 Redis Key References

The spec proposes a new `attribution:*` Redis namespace (Section §3.3 implication; the spec text itself does not enumerate concrete Redis keys but the cross-cutting matrix §3 line 120 calls out the new namespace).

| Spec Reference (concept) | Producer | Consumer | Status |
|---------------|----------|----------|--------|
| Implicit `attribution:*` namespace (cross-cutting matrix §3 line 120) | **NONE** | **NONE** | **not-yet-created. Zero current usage. Spec is silent on whether the EOD engine writes any cache keys (e.g., last-attribution-run timestamp, run-status sentinel) or operates as pure Supabase write. Class B (see §10.2 B6 — observability gap; engine may also benefit from a `health:eod_attribution` sentinel similar to `strategy_matrix` health writes).** |
| `strategy_matrix:{regime}:{strategy}` (existing per-cell cache written by `strategy_performance_matrix.py:104`, TTL 86400 × 90 = 90 days) | `backend/strategy_performance_matrix.py:104` | `backend/strategy_selector.py:154` (sizing reducer); `backend/main.py:1982` (`_build_strategy_matrix_summary()` admin readback) | **verified — existing namespace. No write conflict with proposed `attribution:*` since they are disjoint key prefixes. Cross-spec integration question is at the Supabase-source level, not Redis (see B5).** |
| `health:strategy_matrix` / `trading_system_health` row (existing observability writeback by `strategy_performance_matrix.run_matrix_update`) | `backend/strategy_performance_matrix.py:200–212` (`write_health_status` writes `strategy_matrix` row with `details={cells_updated, positions_analyzed}`) | Engine Health admin page (per inline comment line 188) | **verified — pattern to mirror. Item 2's EOD engine should write a similar `health:eod_attribution` row for operator visibility. Surfaced in §12.2 as a buildout sub-item.** |

### 3.4 Commit Hash References

The locked spec (1149 lines) cites **no commit hashes**. Provenance line at line 1149 references "Round 2 GPT-5.5 Pro design + Items 6/10 integration audit + Claude verification + GPT verification accept on 2026-04-26" — process attribution, not commit reference.

| Spec Reference | Verification | Status |
|---------------|--------------|--------|
| (no commit-hash citations in spec) | n/a | **n/a — pure future design.** |

---

## 4. Existing Partial Implementation (verified by Cursor)

Per evidence pack §8 Item 2 (lines 393–398): **NOT YET IMPLEMENTED.** Confirmed by direct verification at HEAD `6be9809`. The closest existing logic is `backend/strategy_performance_matrix.py` (12D — "D3 Regime × Strategy Performance Matrix"); cross-cutting matrix §4 lines 478–486 documents its touchpoints.

| Aspect | Existing State | Source |
|--------|---------------|--------|
| Functional scaffold | **No.** No file matches `attribution` in `backend/` or `backend_agents/` or `backend_earnings/` (verified `grep -rln "attribution" backend/` returns zero production matches; only test fixtures in `backend/tests/test_consolidation_s4.py`, `backend/mark_to_market.py`, `backend/execution_engine.py` mention path-metric concepts but not "attribution" as a labeling concern). Closest existing logic is `backend/strategy_performance_matrix.py` (229 lines) which aggregates over batches by `(regime, strategy_type)` and produces a Redis-cached sizing reducer; it does **not** label per-trade and does **not** persist outcome enums. Distinct in shape and purpose from AI-SPEC-002. | Evidence pack §8 Item 2 lines 393–398; cross-cutting matrix §3 line 118; direct file inspection. |
| Schema in place | **No, with one negative-precedent overlap.** Three Item 2 tables (`strategy_attribution`, `trade_counterfactual_cases`, `strategy_utility_labels`) absent from all 68 migration files at HEAD. The `trading_positions` table (`20260416172751_*.sql:159`) does not have any of the spec's per-trade attribution columns. **Counter-finding:** `trading_positions` already carries 4 dead `attribution_*` BOOLEAN columns from the baseline migration that contradict spec §1's "execution ledger only" architectural commitment (see §3.2 row + §10.3 C3). Item 10's existing 3-column scaffold (`counterfactual_pnl`, `counterfactual_strategy`, `counterfactual_simulated_at` on `trading_prediction_outputs` per `20260421_add_counterfactual_pnl.sql`) is column-shaped, not table-shaped — diverges from Item 2's `trade_counterfactual_cases` FK target (PRE-P11-4 carry-forward #5). | Evidence pack §7.1 (existing `trading_positions`); §7.2 (proposed Item 2 tables); §9.6 (`counterfactual_pnl` columns vs table). |
| Feature flag wiring | **No.** `grep -rln "agents:strategy_attribution\|attribution_engine_enabled\|strategy_attribution:enabled"` returns zero matches. No flag pattern exists. (The closest precedent is `model:meta_label:enabled` at `backend/execution_engine.py:519` — Item 2's EOD engine could mirror this gating pattern when graduating from MVP to live, but no equivalent flag is wired today.) | Direct grep. |
| Tests covering scope | **No.** `backend/tests/test_strategy_performance_matrix.py` covers the closest existing logic (regime × strategy aggregation, lines 197–198 reference `strategy_matrix:pin_range:iron_butterfly` and `strategy_matrix:pin_range:iron_condor` Redis keys). `backend/tests/test_counterfactual_engine.py` covers Item 10's column-shaped scaffold. **No `test_strategy_attribution.py` or `test_eod_attribution_engine.py` exist.** | Direct file inspection. |
| Documentation references | **None at HEAD.** No TASK_REGISTER section (TASK_REGISTER.md does not yet have a §14B for Strategy Attribution). MASTER_PLAN.md does not yet have a phase entry for AI-SPEC-002. Both gaps surfaced as governance updates in §11. | TASK_REGISTER, MASTER_PLAN. |

The pattern-overlap with `strategy_performance_matrix.py` (cross-cutting matrix §4 line 482: "Strategy Attribution provides per-trade labels that aggregate up to this matrix") is a **read-only consumer relationship** — once Item 2 ships, `strategy_performance_matrix.py` could either (a) continue reading `trading_positions` directly (coexist), (b) be refactored to read `strategy_attribution` (single source of truth), or (c) be deprecated in favor of an attribution-derived view. Spec is silent on which path. See §10.2 B5.

---

## 5. The Ten Audit Dimensions

**(First-pass for Claude to refine; cross-cutting matrix §3 lines 110–131 is the starting point.)**

| # | Dimension | Finding | Source / Evidence |
|---|-----------|---------|-------------------|
| 1 | File/module exists | **No.** Zero `attribution` files in any backend tree. Closest existing logic `backend/strategy_performance_matrix.py` (229 lines) aggregates regime × strategy ex-post; does not label per-trade. EOD engine `backend/eod_attribution_engine.py` is unimplemented. | §3.1; evidence pack §8 Item 2; matrix §3 line 118 |
| 2 | DB table/column exists | **No.** Three new tables (`strategy_attribution`, `trade_counterfactual_cases`, `strategy_utility_labels`) absent from all 68 migration files. `closed_trade_path_metrics` (the spec's path-metrics source for copy-on-insert) also absent. `trading_positions` (existing, FK target for `position_id`) has its PK as `id` not `position_id`, plus 4 dead legacy `attribution_*` BOOLEAN columns that contradict spec §1 architectural commitment. | §3.2; matrix §3 line 119 |
| 3 | Redis keys | **New `attribution:*` namespace not in use.** Existing `strategy_matrix:*` namespace (written by `strategy_performance_matrix.py:104`, consumed by `strategy_selector.py:154` and `main.py:1982`) is disjoint and continues independently. Item 2's EOD engine likely benefits from a `health:eod_attribution` sentinel pattern mirroring the existing `strategy_matrix` health writeback (matrix §4 line 482). | §3.3; matrix §6 (`strategy_matrix:*` row) |
| 4 | Current behavior matches spec | **No.** Per-trade utility labels are not currently computed or written anywhere. The 4 dead `attribution_*` columns on `trading_positions` look like an abandoned simpler attribution attempt that was never wired into EOD logic. `strategy_performance_matrix.py` aggregates ex-post and feeds sizing — orthogonal to label production. | §3.2; §4 |
| 5 | Spec is future design | **Yes — proposed, not existing.** Spec is overwhelmingly forward-looking schema + EOD engine design with explicit V0.1 ship scope at §15. **Partially-built ≠ no:** the legacy 4 BOOLEAN attribution columns on `trading_positions` are an existing non-trivial overlap that the spec does not acknowledge or address. | Spec §15; §4 |
| 6 | Governance conflict | **None directly with locked D-001..D-022.** Item 2 is observational labeling (advisory authority per matrix §3 line 124); does not gate trading decisions. Indirect interactions: (a) the `decision_outcome` enum coordinates with AI-SPEC-001's pending D-023 scope (see C-AI-001-1 in running register §1) — see §10.3 C1; (b) the legacy `attribution_*` columns on `trading_positions` cross MASTER_PLAN's V0 schema baseline (see §10.3 C3). | §10.3 C1 + C3 |
| 7 | Authority level proposed | **Advisory.** Spec produces labels and does not gate decisions. `calibration_eligible` is a queryable flag enforced structurally by trigger + application accessor + Item 6 training accessor; downstream specs (5, 6, 7, 9, 10, 11, 13) consume it but Item 2 does not gate. | Matrix §3 line 124; consolidated plan §5 Tier V0.1 Cluster A |
| 8 | Calibration dependencies | **Item 2 IS the calibration source for everyone else.** Cross-spec dependency reversed compared to other items: Items 1, 5, 6, 7, 9, 10, 11, 12, 13 all depend on labels Item 2 produces. Item 2's own dependency is on `trading_positions` row history reaching ≥100 closed paper trades per system-state.md line 36 (today's count is below threshold). Spec also depends on the `closed_trade_path_metrics` substrate (currently nonexistent — §3.1 row + §10.2 B2). | Matrix §3 line 125 + §7 dependency graph lines 668–705; system-state.md line 36 |
| 9 | Training contamination risk | **HIGH on legacy data.** Pre-Item-2 closed `trading_positions` rows lack labels. Spec §10 Backfill Rules § "Pre-Commit-4 contaminated rows" mark these as `simulation_status='legacy_observability_only'` + `calibration_eligible=false` — but spec is silent on the **broader cutover** for non-contaminated legacy rows that simply lack strategy-aware attribution context (no `strategy_hint` captured at decision time). Without an explicit cutover policy, Item 6 / Item 9 training queries could accidentally include legacy rows lacking strategy-aware structure (see B6). | Spec §10; §10.2 B6 |
| 10 | Implementation owner | Cursor | (constant) |

---

## 6. Missing Pieces

Spec §2 / §6 / §15 describe a coherent four-table architecture and an EOD engine, but several of the artifacts the spec assumes exist do not exist at HEAD. The list below distinguishes between **what Spec §15 V0.1 Ship Scope formally lists as Item 2 deliverables** (expected to be missing) and **what Spec §2 / §6 / §7 silently reference but does NOT list as Item 2 deliverables** (substrate gaps that block Item 2's V0.1 readiness).

### Files referenced in spec but absent (Item 2 deliverables — listed in Spec §15)

- `backend/eod_attribution_engine.py` — Spec §6 schedule 16:35 ET; explicitly listed in Spec §15 item 5.
- Backfill / cutover script for legacy `trading_positions` rows — implied by Spec §10 but not formally listed in §15.

### Tables referenced but not yet created (mix of Item 2 deliverables and substrate gaps)

- `strategy_attribution` — listed in Spec §15 item 1 (Item 2 deliverable).
- `strategy_utility_labels` — listed in Spec §15 item 2 (Item 2 deliverable).
- `trade_counterfactual_cases` — implied by Spec §1 but **NOT listed in Item 2's V0.1 ship scope** because spec frames it as Item 10's deliverable. See B7 + C2 — Item 10's existing scaffold is column-shaped (`trading_prediction_outputs.counterfactual_*`), not table-shaped.
- `closed_trade_path_metrics` — referenced by Spec §6 Phase 1 step 2.a as a precondition for path-metric copy-on-insert; **NOT listed anywhere in Item 2 ship scope §15** and not in any other spec's ship scope at HEAD. Substrate gap (B2).
- `ai_governor_decisions` — Item 1 deliverable per AI-SPEC-001 audit `B-AI-001-4`. Item 2 has FK reference to `decision_id`; sequencing constraint.
- `meta_labeler_decisions` (canonical name unknown) — Item 6 deliverable. Item 2 has nullable FK.
- `adversarial_decisions` (canonical name unknown) — Item 7 deliverable. Item 2 has nullable FK.

### Redis keys with no producer

- New `attribution:*` namespace — none exist at HEAD; spec is silent on whether engine writes any cache keys.
- `health:eod_attribution` (proposed mirror of existing `health:strategy_matrix` pattern) — surfaced in §12.2 buildout list.

### Functions called by spec but not yet defined

- `compute_strategy_metrics(position, path_metrics, item5_snapshot, item8_snapshot)` (Spec §3 per-strategy logic; Spec §6 Phase 1 step 2.d) — no implementation.
- `classify_outcome_mode(strategy_type, exit_reason, strategy_metrics)` (Spec §4; Spec §6 Phase 1 step 2.e) — no implementation; this is also the function that needs the `exit_reason` → `outcome_mode` mapping table addressed in §10.2 B4.
- `compute_counterfactual_after_slippage(case, item10_engine)` (Spec §6 Phase 2 step 2.b) — Item 10 dependency; today's `counterfactual_engine.py` produces `counterfactual_pnl` per no-trade row, not a case-by-case ledger.
- DB trigger function for `contamination_reason → calibration_eligible = false` (Spec §2 line 245) — DDL not provided in spec.

### Feature flags assumed but not in code

- `agents:strategy_attribution:enabled` (or equivalent gating flag for the EOD engine) — not present at HEAD; not explicitly named in Spec §15. Pattern would mirror `model:meta_label:enabled` used by Item 6 scaffold (`backend/execution_engine.py:519`).

---

## 7. Contradictions

**(First-pass for Claude to refine — cross-cutting impact tracked in matrix §3, §4, §7.)**

### 7.1 Internal Contradictions

- **§1 vs reality of `trading_positions`:** Spec §1 architectural commitment says `trading_positions` "remains the execution ledger — execution ledger only — Don't overload it with attribution." The actual baseline migration `20260416172751_*.sql:203–206` already adds 4 BOOLEAN attribution columns (`attribution_direction`, `attribution_structure`, `attribution_timing`, `attribution_vol`) to `trading_positions`. The spec does not acknowledge these columns, does not propose to deprecate them, and does not address whether the spec's "execution ledger only" promise requires their removal. (Class C — §10.3 C3.)
- **§2 line 43 vs `trading_positions` PK:** Spec writes `position_id UUID NULL REFERENCES trading_positions(position_id)`. The actual PK is `id UUID` (line 160 of baseline migration). No `position_id` column exists. (Class A — §10.1 A1.)
- **§6 Phase 1 step 2.a vs §15:** Spec §6 EOD engine pseudocode reads "Fetch path metrics from `closed_trade_path_metrics`" as if it is an existing table. Spec §15 V0.1 Ship Scope does not list building `closed_trade_path_metrics` as part of Item 2's deliverables. The spec assumes a substrate exists that does not exist anywhere in the codebase. (Class B — §10.2 B2.)

### 7.2 Cross-Spec Contradictions

- **AI-SPEC-001 (Risk Governor) — `decision_outcome` enum coordination:** Spec §2 `decision_outcome` enum includes `blocked_governor` but no value for **Governor sizing reductions** (where the Governor caps but does not block). AI-SPEC-001 audit `C-AI-001-1` (running register §1) flagged D-023 to govern Item 1's `size_multiplier_cap` channel — a sizing reduction that is neither `opened_traded` nor `blocked_governor`. Without coordination, Item 1 may write decisions Item 2's CHECK constraint rejects. (Class C — §10.3 C1.)
- **AI-SPEC-001 — FK dependency cascade:** Spec §2 line 44 `decision_id UUID NULL REFERENCES ai_governor_decisions(decision_id)` requires Item 1's `ai_governor_decisions` table (canonical name proposed in `B-AI-001-4`). Cross-spec sequencing: Item 1 must ship the table before Item 2's `strategy_attribution` migration can land with the FK. Per matrix §7 dependency graph line 673, AI-SPEC-001 itself depends on AI-SPEC-002 (Governor reads attribution labels) — soft circular dependency resolved by graph staging (Item 2 ships first as label producer; Item 1 ships next reading labels; both add their FK / consumer wiring as separate migrations). (Class B — §10.2 B3.)
- **AI-SPEC-006 (Meta-Labeler) — FK to "future Item 6 table":** Spec §2 line 45 `meta_labeler_decision_id UUID NULL  -- references future Item 6 table` gives no canonical name. Item 6 scaffold lives inside `backend/model_retraining.py` + `backend/execution_engine.py` (per evidence pack §8 Item 6); no decisions table exists. AI-SPEC-006's audit (P1.3.6) will need to propose the canonical name. Until then, Item 2's spec carries an anonymous FK. (Class B — §10.2 B3.)
- **AI-SPEC-007 (Adversarial Review) — FK to "future Item 7 table":** Spec §2 line 46 `adversarial_decision_id UUID NULL  -- references future Item 7 table` — same pattern as Item 6. (Class B — §10.2 B3.)
- **AI-SPEC-010 (Counterfactual P&L) — table-vs-column architectural divergence:** Spec §1 frames `trade_counterfactual_cases` as Item 10's deliverable. Item 10's existing scaffold is `counterfactual_pnl` / `counterfactual_strategy` / `counterfactual_simulated_at` columns on `trading_prediction_outputs` (matrix carry-forward #5 / register PRE-P11-4 / migration `20260421_add_counterfactual_pnl.sql:8–14`). The spec does not address whether Item 10 will pivot to a table-shaped case ledger to satisfy Item 2's FK target, or whether Item 2 should reference `trading_prediction_outputs` directly with `case_id = trading_prediction_outputs.id`. **HIGH-IMPACT — this is the strongest cross-spec contradiction in this audit.** (Class B + Class C — §10.2 B7 + §10.3 C2.)
- **`backend/strategy_performance_matrix.py` integration silence:** Per matrix §4 line 482, "Item 2 provides per-trade labels that aggregate up to this matrix" — but Spec §12 Integration With Other Items does not list Items 11, 12, or `strategy_performance_matrix.py` as integration touchpoints. Spec is silent on whether the existing 229-line matrix file should be refactored (consume `strategy_attribution`), coexist (current behavior, redundant aggregation), or be deprecated. (Class B — §10.2 B5.)
- **`exit_reason` taxonomy vs `outcome_mode` taxonomy:** Spec §4 `outcome_mode` per-strategy enum does not have a documented mapping from the actual `exit_reason` allowlist in `20260421_exit_reason_comprehensive.sql:48–78` (22 values). The EOD attribution engine at Spec §6 step 2.e ("Classify outcome_mode") needs an explicit `exit_reason → outcome_mode` mapping function; spec does not provide one. (Class B — §10.2 B4.)

### 7.3 Governance Contradictions

- **D-005 / D-022 / D-010 / D-011:** No direct conflict — Item 2 is observational labeling; does not gate trades.
- **T-Rule 2 (Governance Documents Are Authoritative):** Spec proposes 3 new tables and an EOD engine but does not call out that the implementation must be preceded by a TASK_REGISTER entry and a MASTER_PLAN phase entry. Surfaced as governance update in §11.
- **MASTER_PLAN.md V0 / Phase 2B legacy:** The 4 dead `attribution_*` columns on `trading_positions` were added in the V0 baseline migration (2026-04-16). They predate the locked spec but contradict its architectural commitment. Whether to remove, deprecate, or retain them is an operator decision (C3) with constitutional clean-up implications.

If a contradiction with a D-XXX requires a NEW D-XXX entry to resolve, that's escalated to Class C — see §10.3 C1 (folds into AI-SPEC-001's pending D-023 scope).

---

## 8. Carry-Forward Findings From P1.1 / P1.2

| Finding | Applies to this spec? | Implication |
|---------|----------------------|-------------|
| #1: `gex:updated_at` consumer-only orphan (PRE-P11-6) | **No.** Item 2 is EOD batch over closed positions; does not consume real-time GEX freshness. | n/a |
| #2: `gex:atm_iv` consumer-only (PRE-P11-5) | **No.** Item 2 records `entry_vix` / `exit_vix` / `realized_vs_expected_ratio` from snapshots taken at decision time (Item 5) — not from live `gex:atm_iv`. | n/a |
| #3: MASTER_PLAN debit-spread feature flag debt (PRE-P11-7) | **Indirectly.** Item 2's `strategy_type` enum (10 values) matches the migration `20260419_add_strategy_types.sql` exactly, including `debit_call_spread` / `debit_put_spread` (matches `risk_engine.py:105–106` naming). The spec **does NOT use** the `bull_debit_spread` / `bear_debit_spread` naming from `synthesis_agent.py:40–41` and MASTER_PLAN feature-flag boilerplate. So Item 2 confirms the `risk_engine.py` side of the cross-spec strategy-class taxonomy theme. (See cross-spec themes update in running register §5.) | confirms strategy-class taxonomy theme (theme status changes from "1 audit" to "2 audits") |
| #4: `_safe_redis()` is dead code at HEAD (PRE-P12-1) | **No.** Item 2 has no freshness-gate dependency. The EOD attribution engine runs at 16:35 ET against closed positions; data freshness flags surface in `data_quality_flags TEXT[]` (Spec §2) populated at entry time and EOD time, not via `_safe_redis()`. | n/a (Item 2 does not interact with the freshness substrate) |
| #5: `counterfactual_pnl` is column triple, not table (PRE-P11-4) | **YES — HIGH-IMPACT.** Item 2's FK `case_id UUID REFERENCES trade_counterfactual_cases(id)` references a table that Item 10 has not shipped — Item 10's existing scaffold is the 3-column triple on `trading_prediction_outputs`. This is the strongest cross-spec contradiction in this audit. (See §7.2 + §10.2 B7 + §10.3 C2.) | **C2 + B7** — operator decision required on Item 10's case-ledger architecture (table or column-shaped continuation); without resolution, Item 2's `case_id` FK is unsatisfiable for the blocked-decision Phase 2 of the EOD engine (Spec §6 Phase 2). |

---

## 9. Risk Rating

**Rating: HIGH**

**Rationale:** Item 2 is the V0.1 critical-path root (matrix §7 line 670: "no dependencies — writes labels for everyone else") yet introduces 4 substrate gaps that block clean shipping: (1) three new tables with no migrations, (2) the `closed_trade_path_metrics` source-of-truth substrate is unspecified anywhere, (3) FK targets on Items 1 / 6 / 7 / 10 require those specs to ship coordinated DDL, and (4) the legacy `attribution_*` columns on `trading_positions` directly contradict spec §1 architectural intent. The training-contamination risk is HIGH on legacy data per dimension 9. The cross-spec impact is broader than AI-SPEC-001's because every B/C-cluster spec implicitly depends on Item 2's labels.

**Categories:**
- Spec-vs-code drift severity: **high** (3 missing tables; FK target column wrong; legacy columns contradict architectural commitment).
- Number of Class A corrections: **1**.
- Number of Class B corrections: **8**.
- Number of Class C corrections: **3**.
- Cross-cutting impact (specs affected): **9** of 13 — directly: AI-SPEC-001 (decision_id FK + decision_outcome enum), AI-SPEC-005 (calibration source), AI-SPEC-006 (meta_labeler_decision_id FK + training labels), AI-SPEC-007 (adversarial_decision_id FK), AI-SPEC-009 (path metrics for forward-EV training), AI-SPEC-010 (case_id FK — table-vs-column), AI-SPEC-011 (regime × strategy attribution), AI-SPEC-012 (capital allocation reads), AI-SPEC-013 (calibration source for drift demotion paths). Per matrix §7 dependency graph lines 668–705.

---

## 10. Spec Corrections Required

Per `CONSOLIDATED_PLAN_v1.2_APPROVED.md` §3, three correction classes.

### 10.1 Class A — Mechanical Errors

**Cursor primary ownership.** Mechanical wrongness verified against repo at HEAD. Rubber-stamped at end of audit phase (Gate 1).

| # | Spec Section | Spec Says | Correct Value | Source of Truth |
|---|--------------|-----------|---------------|----------------|
| A1 | §2 line 43 (Core Identity Fields) | `position_id UUID NULL REFERENCES trading_positions(position_id)` | `position_id UUID NULL REFERENCES trading_positions(id)` (the FK target column is `id`, not `position_id`) | `supabase/migrations/20260416172751_*.sql:160` — `id UUID PRIMARY KEY DEFAULT gen_random_uuid()`. No `position_id` column exists on `trading_positions`. |

(No A2 — the spec's other column-name discrepancies, e.g., `entry_spx` vs actual `entry_spx_price`, are NOT Class A because the spec defines its own `strategy_attribution` table; those names are the spec's own. The Class A error is specifically the FK reference, which must point to a real existing column.)

### 10.2 Class B — Implementation Status / Content Omissions

**(First-pass for Claude/GPT to refine; operator approves consolidated list, not per-correction.)**

| # | Spec Section | Spec Says | Reality | Proposed Correction |
|---|--------------|-----------|---------|--------------------|
| B1 | Spec §6 (EOD Attribution Engine) + §15 V0.1 Ship Scope item 5 (`backend/eod_attribution_engine.py`) | Names a backend file with full job specification | File does not exist at HEAD. Verified by `test -f backend/eod_attribution_engine.py` returning absent. No `attribution` files anywhere in `backend/`, `backend_agents/`, `backend_earnings/`. | No correction to spec wording — tag as "scheduled buildout"; clarify in Spec §15 that Item 2 includes both the engine file and integration into `backend/main.py` EOD orchestration chain (proposed slot: between `run_matrix_update_job` at 16:30 ET and `run_eod_reconciliation_job` at 16:40 ET, per existing pattern). |
| B2 | Spec §15 V0.1 Ship Scope items 1, 2 (`CREATE TABLE strategy_attribution` + `CREATE TABLE strategy_utility_labels`) and §6 Phase 1 step 2.a ("Fetch path metrics from `closed_trade_path_metrics`") | Lists 3 new-table migrations and assumes `closed_trade_path_metrics` source table exists | All 3 listed tables absent from 68 migrations at HEAD; **`closed_trade_path_metrics` is also absent from the codebase entirely** (verified by `grep -rln "closed_trade_path_metrics"` returning matches only in archived spec files). Path-metric column names (`mae_R`, `mfe_R`, `peak_unrealized_pnl`, etc.) are not present on any current table. | Add Class B note: V0.1 ship scope must additionally include the `closed_trade_path_metrics` source-of-truth substrate (table + intraday writer integration into `position_monitor.py`) OR explicitly defer all path-metric copy-on-insert columns of `strategy_attribution` to V0.2 with NULL placeholders for V0.1. |
| B3 | Spec §2 lines 44–46 (FK fields `decision_id`, `meta_labeler_decision_id`, `adversarial_decision_id`) | References "future" tables for Items 1, 6, 7 | `ai_governor_decisions` not yet shipped (Item 1 V0.1 deliverable, canonical name proposed in AI-SPEC-001 `B-AI-001-4`). `meta_labeler_decisions` and `adversarial_decisions` have NO canonical name in spec — inline comments say only "references future Item 6 table" and "references future Item 7 table". | Add Class B note: cross-spec FK dependency cascade — Item 2's `strategy_attribution` migration must follow Items 1, 6, 7 schema landings OR be split into two migrations (initial without these FK constraints, follow-up adding constraints once dependent specs ship). Also: assign canonical names to the Item 6 and Item 7 decision tables in their respective P1.3.6 / P1.3.7 audits to unblock Item 2's FK declarations. |
| B4 | Spec §4 (`outcome_mode` Per Strategy taxonomy — 8 strategies × ~10 outcome values each + universal blocked enums) + §6 Phase 1 step 2.e ("Classify outcome_mode") | Defines outcome enums (e.g., `forced_close_1430`, `forced_close_halt`, `pricing_slippage_loss`, `theta_decay_capture`) without a mapping function from real `exit_reason` values | Actual `exit_reason` allowlist at `supabase/migrations/20260421_exit_reason_comprehensive.sql:48–78` has 22 values (e.g., `time_stop_230pm`, `time_stop_230pm_d010`, `time_stop_345pm_d011`, `take_profit_40pct`, `stop_loss_150pct_credit`, `cv_stress_exit_d017`, `emergency_backstop`, `circuit_breaker`, `eod_reconciliation_stale_open`). Spec's `outcome_mode` enum cannot be derived without an explicit mapping. | Add Class B note: Spec §4 must include (or §6 step 2.e must reference) an explicit `(exit_reason, strategy_type, strategy_metrics) → outcome_mode` mapping function. The mapping is the load-bearing classifier for the EOD engine; without it, Item 2's promise of "calibration-grade strategy-specific outcome labels" cannot be operationalized. |
| B5 | Spec §12 Integration With Other Items + cross-cutting matrix §4 line 482 | Lists Item 5 / 6 / 7 / 9 / 10 as integration partners; **silent on `backend/strategy_performance_matrix.py`** | Existing 229-line file aggregates `(regime, strategy_type)` cells and feeds sizing reducer. Per matrix §4: "Item 2 provides per-trade labels that aggregate up to this matrix" — but Item 2 spec does not address whether the matrix should be refactored (consume `strategy_attribution`), coexist (current behavior — redundant aggregation), or be deprecated (single source of truth). | Add Class B note: Spec §12 must include an integration disposition for `backend/strategy_performance_matrix.py`. Recommended default (least disruptive): refactor the matrix's per-cell aggregator to read from `strategy_attribution WHERE calibration_eligible = true` once Item 2 ships and ≥30 days of attributed rows exist; keep `trading_positions` direct read as fallback when attribution coverage < 30 days. Cross-spec coordination with AI-SPEC-011 / AI-SPEC-012 (matrix §4 lines 483–484 list both as readers). |
| B6 | Spec §10 Backfill Rules ("Pre-Commit-4 contaminated rows" only) | Specifies cutover policy ONLY for Pre-Commit-4 contaminated rows | Broader population of legacy non-contaminated `trading_positions` rows (closed positions before Item 2 ships, lacking `strategy_hint` captured at decision time) is unaddressed. Without explicit cutover, Item 6 / Item 9 training queries could either (a) silently skip these rows (coverage gap) or (b) include them with NULL strategy fields (training contamination — high risk per dimension 9). | Add Class B note: Spec §10 must add a "Legacy Cutover Policy" sub-section specifying that all closed `trading_positions` rows with `entry_at < attribution_engine_first_run_date` either (a) get a backfill INSERT into `strategy_attribution` with `simulation_status='legacy_observability_only'` + `calibration_eligible=false` + `strategy_hint=NULL`, OR (b) are explicitly excluded by Item 6 / Item 9 training accessors via a cutover-date filter. |
| B7 | Spec §1 + §2 line 42 (`case_id UUID REFERENCES trade_counterfactual_cases(id)`) + §6 Phase 2 ("counterfactual cases for process_date") | Treats `trade_counterfactual_cases` as Item 10's deliverable | Item 10's existing scaffold is column-shaped (`counterfactual_pnl`, `counterfactual_strategy`, `counterfactual_simulated_at` on `trading_prediction_outputs` per `20260421_add_counterfactual_pnl.sql:8–14`). The migration comment line 21–24 explicitly states "trading_prediction_outputs does not persist a per-prediction strategy hint" — meaning the existing column-shaped design cannot satisfy Item 2's requirement (Spec §6 Phase 2 step 2.a: "Require strategy_hint and strategy_structure"). PRE-P11-4 carry-forward applies HIGH-IMPACT. | No correction to Item 2's spec wording — escalate to Class C (§10.3 C2). Operator decision required on Item 10's case-ledger architecture (table-shaped pivot to satisfy Item 2's FK, OR Item 2 reference `trading_prediction_outputs` directly with `case_id = trading_prediction_outputs.id` and absorb the strategy-hint capture responsibility). |
| B8 | Spec §2 (Core Identity Fields — `candidate_id UUID NULL`) | Defines a `candidate_id` field with no FK target | `trading_positions` already has `prediction_id UUID REFERENCES trading_prediction_outputs(id)` (added by `20260421_add_decision_context.sql:9–10`). Spec does not address whether `strategy_attribution.candidate_id` should equal `trading_positions.prediction_id` (canonical pre-decision candidate) or a separate Item 1 / Item 6 candidate ID. | Add Class B note: Spec §2 must clarify the source-of-truth FK target for `candidate_id`. Recommended default: `candidate_id UUID NULL REFERENCES trading_prediction_outputs(id)` — re-uses existing infrastructure and matches the `prediction_id` channel already wired through `decision_context`. |

### 10.3 Class C — Architectural Intent Corrections

**(First-pass for GPT-5.5 Pro to validate; operator-only authority.)** Default position: reject unless clear reason. Resolution requires NEW D-XXX or spec revision to comply with existing D-XXX or to set governance scope.

| # | Spec Section | Issue | Conflicting D-XXX or Rule | Resolution Required |
|---|--------------|-------|--------------------------|--------------------|
| C1 | Spec §2 `decision_outcome` enum (8 values: `opened_traded`, `blocked_governor`, `blocked_meta_labeler`, `blocked_adversarial`, `skipped_rules`, `blocked_constitutional`, `halted_blocked_cycle`, `synthetic_case`) + §5 Decision_id Linkage Constraints | Enum is binary-coded for "opened OR blocked"; has no value for **Governor sizing reductions** where the Governor caps but does not block (size_multiplier_cap channel proposed in AI-SPEC-001 §7 + audited as `C-AI-001-1` in running register §1). Without coordination with AI-SPEC-001's pending D-023 wording, Item 1's `size_multiplier_cap` writes will fail Item 2's CHECK constraint. | T-Rule 4 (Locked Decisions Are Final) + cross-spec coordination via D-023 (proposed in AI-SPEC-001 §11; AI authority boundary scope) | Operator decision needed: (option 1) extend Spec §2 `decision_outcome` enum to include `cap_governor` (or `reduced_governor`) before Item 2 ships, OR (option 2) D-023 wording explicitly requires AI-SPEC-001 to write `opened_traded` (not `blocked_*`) for size-cap decisions and Item 1's authority is limited to size-cap-not-block. Either way, the resolution must be encoded in D-023 alongside the AI-SPEC-001 `C-AI-001-1` / `C-AI-001-2` / `C-AI-001-3` dispositions. |
| C2 | Spec §1 (Four-Table Architecture) + §2 line 42 (`case_id UUID REFERENCES trade_counterfactual_cases(id)`) + §6 Phase 2 (blocked-decisions counterfactual generation) | Spec's four-table architecture promises a `trade_counterfactual_cases` ledger Item 10 will own. Item 10's existing scaffold (12E commit) is `counterfactual_pnl` / `counterfactual_strategy` / `counterfactual_simulated_at` columns on `trading_prediction_outputs` — column-shaped, not table-shaped (per matrix carry-forward #5 / register PRE-P11-4 / migration comment). Spec is silent on whether Item 10 must pivot to a table-shaped ledger to satisfy Item 2's FK. The two architectures are NOT compatible without explicit coordination. | T-Rule 2 (Governance Documents Are Authoritative) — cross-spec architectural conflict; no D-XXX yet covers Item 10's table-vs-column shape | Operator decision required between three options: (option 1) Item 10 ships `trade_counterfactual_cases` as a new table; existing `counterfactual_pnl` columns on `trading_prediction_outputs` either deprecate or backfill into the new table — preserves Item 2's spec as-is. (option 2) Item 2 references `trading_prediction_outputs` directly: rename `case_id` to `prediction_id` (or keep `case_id` as alias, FK-targets `trading_prediction_outputs(id)`); Item 2 absorbs strategy-hint capture responsibility because `trading_prediction_outputs` does not persist it today — preserves Item 10's existing scaffold. (option 3) Defer the blocked-decisions Phase 2 of the EOD engine to V0.2; V0.1 Item 2 ships covering only opened positions (Phase 1) and synthetic cases (Phase 3) — preserves both specs' independence at cost of postponing counterfactual-as-training-label. **Default position (per consolidated plan §5 conservative-first principle):** option 2 (re-use existing column-shaped scaffold), with explicit cross-spec note that Item 10 V0.2 may revisit. |
| C3 | Spec §1 architectural commitment ("`trading_positions` remains the execution ledger only — Don't overload it with attribution") | Reality: `trading_positions` already has 4 dead `attribution_*` BOOLEAN columns from baseline migration `20260416172751_*.sql:203–206`. No production code path writes them (verified by `grep -rln "attribution_(direction\|structure\|timing\|vol)" backend/` returning zero matches). Spec does not address. | T-Rule 2 + V0 baseline schema documented in `MARKETMUSE_MASTER.md:351–356` — pre-existing schema commitment | Operator decision required on disposition: (option 1) **deprecate-in-place** — add a comment to the migration noting the columns are abandoned and never written; Item 2's `strategy_attribution` is the canonical attribution surface; queries that filter on `attribution_*` will return all NULL (or all 0) for current rows. Lowest-cost. (option 2) **formally remove via DROP COLUMN migration** — sequenced before Item 2's `strategy_attribution` migration; risk: any historical row with non-NULL values would lose data. (option 3) **repurpose** — define what each `attribution_direction` / `_structure` / `_timing` / `_vol` SHOULD mean in light of the four-table architecture, and write a backfill from `strategy_attribution` rows. Highest-cost. **Default position:** option 1 (deprecate-in-place with migration comment), unless a Phase 2 audit discovers the columns are silently consumed by some downstream query. |

---

## 11. Governance Updates Required

- [x] **approved-decisions.md — D-023 scope must include `decision_outcome` enum coordination** (per §10.3 C1). D-023 is already proposed in AI-SPEC-001 §11 as the AI authority boundary D-XXX; AI-SPEC-002's audit confirms the same D-023 must additionally enumerate Item 2's outcome value contributions. Folds into existing pending D-023 wording, not a new D-XXX.
- [ ] **approved-decisions.md — existing D-XXX modifications:** None required. Item 2 defers cleanly to D-005 / D-010 / D-011 / D-013 / D-022 (no gating authority); D-014 (sizing) is unaffected because attribution is observational.
- [x] **MASTER_PLAN.md — new phase entry: Phase 3B (or sequencing alongside AI-SPEC-001 Phase 3A) — Strategy-Aware Attribution V0.1** (~3-4 weeks per Spec §15). Sub-items: 3 new-table migrations, `closed_trade_path_metrics` substrate, `backend/eod_attribution_engine.py`, EOD orchestration integration, backfill / cutover script, tests.
- [x] **TASK_REGISTER.md — new section: §14B — Strategy Attribution implementation.** Sub-items proposed in §12.2 (14B.0 baseline schema bootstrap, 14B.1 path-metrics substrate, 14B.2 EOD engine, 14B.3 outcome-mode mapping, 14B.4 utility-label derivation, 14B.5 cutover script, 14B.6 trigger DDL, 14B.7 observability + tests, 14B.8 cross-spec FK reconciliation).
- [x] **system-state.md — operational state addition: `strategy_attribution` field.** Tracks `{ phase: 'not_started' | 'v0.1_engine_running' | 'v0.1_calibration_eligible' | 'v0.2_path_metrics_complete', last_run_at: timestamp | null, last_run_status: text | null, calibration_eligible_row_count: integer, total_attribution_row_count: integer }` (or equivalent). Tracks engine progression from initial run to calibration-grade label production.
- [x] **system-state.md — operational state addition: `closed_trade_path_metrics_substrate` field** (boolean or phase enum). Tracks whether the path-metrics source-of-truth table is in place and being written by the intraday position monitor — gate on Item 2 V0.1 calibration-grade promotion.
- [ ] **constitution.md — T-Rule clarification needed:** No. Item 2 is observational labeling; T-Rules 1, 4, 5, 6, 9 are unaffected. (If C3 resolves to "repurpose" the legacy `attribution_*` columns, T-Rule 2 governance pointer might need updating; default disposition does not require it.)

---

## 12. TASK_REGISTER Implications

### 12.1 Pre-implementation tasks (must complete before P1.3 audit can close)

- Operator decision on §10.3 C1 (`decision_outcome` enum coordination with D-023 — folds into AI-SPEC-001 D-023 wording).
- Operator decision on §10.3 C2 (`trade_counterfactual_cases` table-vs-column architectural shape — drives Item 10's eventual deliverable).
- Operator decision on §10.3 C3 (legacy `trading_positions.attribution_*` columns disposition).
- Resolution of cross-spec FK dependency cascade (B3) — coordinate canonical names for Item 1 / Item 6 / Item 7 decision tables in their respective P1.3.X audits before Item 2's `strategy_attribution` migration is authored.
- Confirm whether `closed_trade_path_metrics` substrate is part of Item 2's ship scope (B2) or a separate prerequisite spec.

### 12.2 Implementation tasks (Cursor work after Phase 4 doc integration)

- **14B.0 — baseline schema bootstrap.** Migrations: `strategy_attribution`, `strategy_utility_labels` (full DDL per Spec §2 + §8). FK constraints initially declared as `ON DELETE NO ACTION` referencing tables that may not exist yet — defer constraint creation to follow-up migration when dependent specs ship.
- **14B.1 — path-metrics substrate.** Migration for `closed_trade_path_metrics` (column list per Spec §2 "Path Metrics" sub-section). Wire intraday writer in `backend/position_monitor.py` (cadence: 60s normal, 15-30s stress per Spec §10 Intraday Fields).
- **14B.2 — `backend/eod_attribution_engine.py`.** 16:35 ET schedule wired into `backend/main.py` EOD orchestration chain (between matrix update at 16:30 and reconciliation at 16:40). Idempotent re-run support. Failure handling per Spec §6 ("Never silently drop").
- **14B.3 — outcome-mode mapping function.** `backend/attribution/outcome_classifier.py` — implements `(exit_reason, strategy_type, strategy_metrics) → outcome_mode` per Spec §4. Tests must enumerate every `exit_reason` allowlist value (22 values per `20260421_exit_reason_comprehensive.sql`).
- **14B.4 — utility-label derivation.** `backend/attribution/utility_labels.py` — implements `strategy_utility_labels` derivation per Spec §8. Item 6 training accessor stub.
- **14B.5 — cutover / backfill script.** `backend/scripts/strategy_attribution_cutover.py` — one-time batch covering pre-Item-2 closed `trading_positions` rows with `simulation_status='legacy_observability_only'` + `calibration_eligible=false`. Per Spec §10 + §10.2 B6.
- **14B.6 — DB trigger DDL.** Trigger or RLS-equivalent enforcing `contamination_reason IS NOT NULL → calibration_eligible = false` (Spec §2 line 245). Application accessor mirror in `backend/attribution/accessors.py`.
- **14B.7 — observability + tests.** `backend/tests/test_strategy_attribution.py`, `backend/tests/test_eod_attribution_engine.py`, `backend/tests/test_outcome_classifier.py`. Engine writes `health:eod_attribution` row to `trading_system_health` mirroring the `strategy_matrix` pattern.
- **14B.8 — cross-spec FK reconciliation.** Follow-up migrations adding FK constraints to `ai_governor_decisions` (Item 1), Item 6 / Item 7 decisions tables, and `trade_counterfactual_cases` (Item 10) — sequenced as those specs ship.

### 12.3 Calibration / Data dependencies

- ≥100 closed paper trades (per system-state.md line 36) before V0.1 attribution promotes to "calibration-grade" status; today's count is below threshold.
- ≥30 days of `closed_trade_path_metrics` history before path-metric integrity claims (Spec §11 ROI Priority items 4, 5) can be validated.
- Items 1 / 6 / 7 / 10 FK target tables must ship before Item 2's `strategy_attribution` schema can declare the corresponding FK constraints. V0.1 ships with NULL FKs; FK constraints land in 14B.8 follow-up migrations.

---

## 13. Recommended Status

- [ ] **spec_accurate_repo_missing** — Spec is correct as written; nothing exists in repo yet; ready for clean buildout.
- [ ] **spec_accurate_repo_partial** — Spec is correct; partial scaffold exists (cite); spec describes the full target.
- [ ] **spec_needs_factual_correction_only** — Spec has Class A errors only; intent is sound; mechanical fixes will land in Phase 2.
- [x] **spec_has_semantic_drift_from_locked_intent** — Spec has Class B corrections that change implementation meaning but not architectural goal. Phase 2 corrections + operator approval.
- [ ] **spec_conflicts_with_existing_governance** — Spec contains Class C item(s) requiring new D-XXX or revision before integration.
- [ ] **spec_should_be_split_into_separate_proposal** — Spec scope is too broad and should be decomposed before integration. Operator decision.

**Justification for the chosen status:** The 8 Class B corrections are substantive and change implementation meaning (substrate gaps, FK dependency cascade, missing cutover, missing outcome-mode mapping) but the architectural goal — a four-table label-quality substrate with `calibration_eligible` as the load-bearing safety property — is sound and unaltered. The 3 Class C items are cross-spec coordination questions (C1 folds into AI-SPEC-001's pending D-023; C2 is an Item 10 architectural decision; C3 is a legacy-schema disposition). None of them strictly REQUIRE a NEW D-XXX before integration — C1 piggybacks on D-023, C2 is bilateral with AI-SPEC-010 audit, C3 is sub-D-XXX cleanup. So `spec_conflicts_with_existing_governance` would over-state. `spec_has_semantic_drift_from_locked_intent` correctly captures: spec intent is preserved, but implementation as written would not work without the corrections.

---

## 14. Sign-Off

| Auditor | Sign-off Status | Date | Notes |
|---------|----------------|------|-------|
| Primary (Cursor) | approved (first-pass redline; primary sections §1, §3, §4, §10.1 fully populated; first-pass drafts of §2, §5–§13 for cross-check refinement) | 2026-04-26 | Class A: 1 item (FK column-name error). Class B: 8 items (substrate gaps + cross-spec FK cascade). Class C: 3 items (D-023 enum coord, Item 10 table-vs-column, legacy attribution_* columns). Risk rating: HIGH. Recommended status: `spec_has_semantic_drift_from_locked_intent`. |
| Cross-check (Claude) | pending | — | §7 cross-spec contradictions and §8 carry-forward findings drafted first-pass; awaiting Claude refinement. |
| Validator (GPT-5.5 Pro) | pending | — | §2 intent summary and §10.3 Class C escalations drafted first-pass; awaiting GPT validation. |
| Operator | pending | — | Class C items require operator decisions before redline closes (C1, C2, C3 dispositions). |

If all four sign-offs are "approved", the redline is closed and the spec moves to Phase 2 correction application.

---

## Appendix — Verification Notes

**Repo HEAD verification:** `git rev-parse HEAD` at audit time returned `6be9809be3988b297074a2ea972bda755a074ce3` (P1.3.1b merge — running register backfilled with pre-audit findings). Branch: `feature/PLAN-AIARCH-000-phase-1-p1-3-2-audit-spec-002-strategy-attribution`.

**Migration count verification:** `ls supabase/migrations/*.sql | wc -l` returned `68`. All searches for absent tables (`strategy_attribution`, `trade_counterfactual_cases`, `strategy_utility_labels`, `closed_trade_path_metrics`, `ai_governor_decisions`, `meta_labeler_decisions`, `adversarial_decisions`) confirmed against this count.

**Cross-references to running register at HEAD `6be9809`:**
- `C-AI-001-1` (running register §1) — basis for §10.3 C1 cross-spec coordination claim.
- `B-AI-001-4` (running register §2) — basis for §3.2 ai_governor_decisions canonical-name claim.
- `PRE-P11-4` (running register §0.2) — basis for §8 carry-forward #5 + §10.2 B7 + §10.3 C2.
- `PRE-P11-7` (running register §0.2) — basis for §8 carry-forward #3 cross-spec strategy-class taxonomy theme confirmation.
- §5 cross-spec themes (running register) — strategy-class taxonomy + calibration_eligible flag + (NEW themes proposed in this audit's register update).

**Methodology footnote:** Class B / C distinctions follow `CONSOLIDATED_PLAN_v1.2_APPROVED.md` §3 + template `_template.md` §10. Class B captures implementation-meaning drift that does not change architectural goal; Class C captures architectural-intent conflicts that require operator authority. The 3 Class C items in this audit each represent a genuine multi-option decision space rather than a mechanical or known-correct fix.
