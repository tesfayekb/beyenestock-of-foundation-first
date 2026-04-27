# Spec Verification Audit — AI-SPEC-010

> **Status:** First-pass redline (P1.3.4). Cursor primary-auditor sections (§1, §3, §4, §10.1) populated; first-pass drafts of §2, §5–§13 for Claude cross-check and GPT validation.
> **Binding format:** Follows `trading-docs/08-planning/ai-architecture-audits/_template.md` (P1.3.0).
> **Created:** 2026-04-26 (Phase 1 P1.3.4 of `CONSOLIDATED_PLAN_v1.2_APPROVED.md`).
> **Source spec:** `trading-docs/04-modules/ai-architecture/archive/raw-locked-specs-2026-04-26/ITEM_10_COUNTERFACTUAL_PNL_LOCKED.md` (745 lines, locked 2026-04-25, immutable).
> **Cluster A status:** **FOURTH AND FINAL Cluster A audit.** After this audit merges, Items 1, 2, 4, 10 are all audited and the operator checkpoint triggers per `CONSOLIDATED_PLAN_v1.2_APPROVED.md` §6.

---

## 1. Audit Header

| Field | Value |
|-------|-------|
| Spec ID | AI-SPEC-010 |
| Spec name | Counterfactual P&L Attribution |
| Stable ID | PLAN-CFACT-001 |
| Tier | **V0.1 Layer 1 SHIPPED** + V0.2 Layer 2 (immediate) + V0.2 (strategy-specific) + V0.3 (adversarial) + V0.4 (exit) — **graduated layered upgrade**, not a single-tier ship. **Cluster classification discrepancy:** matrix §1 line 52 marks Item 10 as Tier `V0.1`; spec §0 header (line 5) marks Tier `V0.2 immediate / V0.2 strategy-specific / V0.3 adversarial / V0.4 exit (graduated)`. Resolution: V0.1 = Layer 1 (already shipped at HEAD via commit `2400e98`); V0.2 onward = Layer 2 (proposed in this spec). Cluster A is correct because Items 5 / 6 / 9 (Cluster B) cannot promote to binding without Item 10 V0.2 outputs. **Tracked as `C-AI-010-2` for matrix amendment.** |
| Cluster | A (foundational) |
| Audit date | 2026-04-26 |
| Repo HEAD at audit time | `1237746e64a0a29048aa55c9053460b4afca7640` (P1.3.3 merged; AI-SPEC-004 audit landed) |
| Primary auditor | Cursor |
| Cross-check auditor | Claude |
| Architectural validator | GPT-5.5 Pro |
| Cross-cutting matrix reference | `CROSS_CUTTING_EVIDENCE_MATRIX.md` §3 (AI-SPEC-010 block, lines 304–326), §4 (`backend/counterfactual_engine.py` 406-line block, lines 468–476), §5 (`trading_positions` consumers line 505 + `trading_prediction_outputs` consumers lines 516–520), §6 (`feedback:counterfactual:*` lines 622–624), §7 (dependency graph — Item 10 depends on Item 4 for synthetic-counterfactual extension, lines 672, 684) |
| Evidence pack reference | `AI_ARCH_EVIDENCE_PACK.md` §6.1 (`backend/counterfactual_engine.py` 406 lines, line 256), §7.3 (counterfactual_pnl column triple, lines 368–380), §8 Item 10 (lines 444–455 — SCAFFOLD EXISTS observability-only), §9.6 (column-vs-table semantic mismatch, lines 552–557 — newly-discovered governance debt), §10.2 (`feedback:counterfactual:enabled` line 610), §10.3.2 line 697 (B1-5 wiring) |

---

## 2. Spec Intent Summary (verified by GPT)

**(First-pass draft for GPT-5.5 Pro to refine.)**

AI-SPEC-010 is **the only Cluster A spec where the architectural intent is "do not rewrite the existing scaffold"**: Item 10 takes the production-shipped 12E counterfactual engine (commit `2400e98`, 2026-04-20) and **layers** a calibration-grade attribution surface on top, leaving Layer 1 (existing engine + 3-column triple on `trading_prediction_outputs` + weekly missed-opportunity report) intact as legacy observability while Layer 2 (new `trade_counterfactual_cases` table + strategy-specific simulators + after-slippage P&L + multi-strategy outputs + `calibration_eligible` structural enforcement) becomes the canonical training-grade source for Items 5–9. The spec's load-bearing safety property is **"wrong labels are worse than missing labels"** (Spec §0 line 33, §15 line 728): the existing single-strategy default-to-`iron_condor` fallback at `counterfactual_engine.py:219` is replaced with `counterfactual_pnl = NULL` when `strategy_hint` is missing (Spec §3 lines 174–186), three-tier degradation explicitly tags `calibration_eligible = false` for approximate widths (Spec §2 lines 90–124), and downstream consumer accessors (Spec §6 — `get_meta_labeler_training_data` / `get_vol_engine_replay_cases` / `get_adversarial_block_outcomes` / `get_exit_optimizer_training_paths`) enforce `calibration_eligible = true` filtering structurally rather than by convention. The four-table architecture (`trade_counterfactual_cases` / `strategy_utility_labels` / `closed_trade_path_metrics` / optional `position_path_samples`) plus the actual / counterfactual / synthetic case-type weights (1.0 / 0.5 / 0.2 — Spec §4 line 202, Spec §10 line 510) **resolves AI-SPEC-002 `C-AI-002-2` in favor of a NEW table** — making this the audit that finally closes the table-vs-column architectural divergence flagged in P1.1 carry-forward #5 (PRE-P11-4) and re-flagged in AI-SPEC-002 P1.3.2 + AI-SPEC-004 P1.3.3 (`B-AI-004-8`). **Authority promotion path:** Layer 1 stays observability-only and `calibration_eligible = false`; Layer 2 advances from V0.2 immediate (data-integrity fixes + halt-day labeling) to V0.2 strategy-specific (full slippage model + multi-strategy simulators) to V0.3 adversarial (Item 7 attribution) to V0.4 exit (Item 9 path-metrics consumption).

---

## 3. Repo Evidence (verified by Cursor)

**Cursor primary ownership.** Every concrete claim verified against actual repo state at HEAD `1237746`.

### 3.1 File/Module References

Item 10 is the only Cluster A spec where **the file already exists**. Verified `git log --oneline -- backend/counterfactual_engine.py` returns 3 commits: `2400e98` (initial scaffold, +349 lines), `4970095` (health-status writes + UI status fix, +42/-6 lines), `fc64840` (Section 13 batch — minor edits, +27/- lines). Net at HEAD: 406 lines.

| Spec citation | Reality at HEAD `1237746` | Status |
|---|---|---|
| Spec §1 line 42 — `backend/counterfactual_engine.py (349 lines, 9 tests)` | File exists. **Line count drift: 406 lines at HEAD, +57 from 2400e98** (+42 from `4970095` health/UI fix; +21 net from `fc64840` Section 13 batch). **Test count drift: 11 tests at HEAD** (verified by `grep -c "^def test_" backend/tests/test_counterfactual_engine.py = 11`) — `4970095` added 2 new tests (`test_run_counterfactual_job_writes_idle_health_on_success`, `test_run_counterfactual_job_writes_error_health_on_exception`). | **verified — line/test count drift (Class A)** |
| Spec §1 line 43 — `_fetch_spx_price_after_signal() → Polygon I:SPX 1-min at t+30` | Function defined at `counterfactual_engine.py:65` (verified by `grep -n "^def _fetch_spx_price_after_signal" backend/counterfactual_engine.py`). Signature: `(predicted_at_iso: str, minutes: int = 30) -> Optional[float]`. Polygon URL template `_POLYGON_SPX_MINUTE_URL` at line 60–62 uses `/v2/aggs/ticker/I:SPX/range/1/minute/{t0}/{t1}` — exactly matches spec. Fail-open returns `None` on any Polygon failure. | **verified** |
| Spec §1 line 44 — `_simulate_pnl() → 3 branches (short-gamma/long-gamma/generic)` | Function defined at `counterfactual_engine.py:109`. Three explicit branches at lines 128 (`iron_butterfly` / `iron_condor` short-gamma), 134 (`long_straddle` / `calendar_spread` long-gamma), 141 (generic 0.5% SPX threshold). Uses `_DEFAULT_SPREAD_WIDTH = 5.0` (line 55), `_TYPICAL_CREDIT = 2.50` (line 58), `_WIN_CREDIT_PCT = 0.40` / `_LOSS_CREDIT_PCT = -1.50` (lines 56–57) — all hardcoded, no per-strategy externalization. **`confidence` parameter accepted but unused** (line 119 docstring: "intentionally unused today so the simulation remains interpretable and auditable"). | **verified — single-strategy contamination risk per spec §3** |
| Spec §1 line 45 — `label_counterfactual_outcomes() → EOD batch labeler` | Function defined at `counterfactual_engine.py:146`. Signature: `(redis_client=None) -> Dict[str, Any]`. Feature-flag gate at line 168 (`feedback:counterfactual:enabled`) — Redis-authoritative, fail-open ENABLED. **Hardcoded `strategy = "iron_condor"` at line 219** (verified by direct read, with comment lines 213–218 acknowledging "`strategy_hint` does not exist on this table — use a conservative iron_condor proxy"). Per-row try/except at line 242 prevents one-row failure from poisoning batch. | **verified — line 219 default behavior is the Class B contamination risk** |
| Spec §1 line 46 — `generate_weekly_summary() → Sunday report (gates >= 30 sessions)` | Function defined at `counterfactual_engine.py:265`. 30-session warmup gate at line 287 (`if closed_sessions < 30: return None`). Sorts by `total_missed_pnl` descending, returns top-3 (line 342). | **verified** |
| Spec §1 line 47 — `run_counterfactual_job() → scheduler entry` | Function defined at `counterfactual_engine.py:366`. **Health-status writes confirmed at lines 384 (success path, status='idle') and 398 (failure path, status='error')** — these are the Spec §13 Gap 4 fixes that landed in commit `4970095`, NOT in the original `2400e98` scaffold. Result: **Spec §13 Gap 4 is already RESOLVED at HEAD (Class B observation, not a Class B correction).** | **verified — Spec §13 Gap 4 already shipped (drift since spec lock)** |
| Spec §1 line 56 — `Daily 16:25 ET Mon-Fri (label no_trade rows)` | EOD job wired in `backend/main.py:1399–1409` (verified by `grep -n "counterfactual" backend/main.py`). `run_counterfactual_job_wrapper` defined at `main.py:200`. Job ID `counterfactual_eod_job` at line 1409. | **verified** |
| Spec §1 line 57 — `Weekly 18:30 ET Sunday (top-3 missed opportunities, gated >= 30 sessions)` | Weekly job wired in `backend/main.py:1416–1421`. `run_counterfactual_weekly_wrapper` at `main.py:217`. Job ID `counterfactual_weekly_job` at line 1421. | **verified** |
| Spec §13 line 657 — `useActivationStatus.ts: Counterfactual Tracking → 'live'` | Verified at `src/hooks/trading/useActivationStatus.ts:241–251`. **`builtStatus: 'live'`** at line 250 (already shipped via `4970095`). **Missing: `shippedDate: '2026-04-20'` (Spec §13 line 658) and `shippedCommit: '2400e98'` (Spec §13 line 659)** — these advisory fields are NOT in the entry at HEAD. The TypeScript interface for `ActivationFlag` does not declare these fields anywhere in the file (verified by reading the entire entry). | **partial — `builtStatus: 'live'` shipped; `shippedDate` + `shippedCommit` fields not added to interface or entry (Class B)** |

**Closest-existing-logic file (NOT cited by spec but architecturally relevant for Layer 2 buildout):**

| File | Lines | Function | Layer 2 relationship |
|---|---|---|---|
| `backend/strategy_performance_matrix.py` | 229 | Regime × strategy ex-post aggregator (12D / D3); aggregates closed `trading_positions` rows into per-cell P&L statistics; written by EOD job, read by `strategy_selector.py:154`. | **DIFFERENT MECHANISM.** Per-cell aggregator over executed trades, not per-decision counterfactual. Layer 2 will likely consume this surface for Item 5 EV-attribution comparisons (Spec §9 lines 482–491) but does not subsume it. AI-SPEC-002 `B-AI-002-5` already flags `strategy_performance_matrix.py` integration disposition; Item 10 Layer 2 surface is independent. |
| `backend/calibration_engine.py` | n/a (existence verified) | Slippage z-score calibration substrate (per system memories — MarketMuse calibration engine writes `actual_slippage` per D-015, calibration log per D-019). | **CROSS-SPEC DEPENDENCY for Spec §5.** Spec §5 lines 364–376 reference `vix_z` / `spread_z` for slippage multipliers but do not name the producer. Likely source: `calibration_engine.py` outputs. Operator decision required on whether Item 10 Layer 2 reads `calibration_engine` outputs directly or via Item 5 (Vol Fair-Value Engine). **Tracked as `C-AI-010-3` (slippage z-score producer authority).** |
| `backend/risk_engine.py:234–235` + `backend/prediction_engine.py:688–691` | n/a | Halt-decision surface (3-loss reduction in `risk_engine.py`, 5-loss session halt in `prediction_engine.py`); D-022 split per AI-SPEC-001 `B-AI-001-7`. | **CROSS-SPEC DEPENDENCY for Spec §7.** Spec §7 lines 442–454 require halt-day blocked-cycle row creation (Item 10 owns the row insert; risk_engine + prediction_engine own the halt-trigger event). No halt-cycle row creation exists at HEAD. Bilateral wiring with both halt-decision sites required during Layer 2 V0.2 build. |

### 3.2 Supabase Schema References

#### Tables proposed by Spec §4 — all four absent at HEAD

Verified by `grep -rln "<table>" supabase/migrations/` against 68 migration files (count confirmed by `ls supabase/migrations/ | wc -l = 68`):

| Table | Spec section | Status at HEAD | Verification |
|---|---|---|---|
| `trade_counterfactual_cases` | Spec §4 lines 198–225 (full DDL) | **absent** | Zero matches across 68 migrations. Confirmed by evidence pack §7.2 line 358. **This is the spec section that authoritatively resolves AI-SPEC-002 `C-AI-002-2` in favor of a NEW table.** |
| `strategy_utility_labels` | Spec §4 lines 232–269 (full DDL) | **absent** | Zero matches. Evidence pack §7.2 line 359. |
| `closed_trade_path_metrics` | Spec §4 lines 276–294 (full DDL) | **absent** | Zero matches. **Already flagged as cross-spec theme** by AI-SPEC-002 `B-AI-002-2` and AI-SPEC-004 `B-AI-004-9` — Item 10 Spec §4 is the canonical owner per `closed_trade_path_metrics(position_id BIGINT PRIMARY KEY REFERENCES trading_positions(id))`. |
| `position_path_samples` (optional) | Spec §4 lines 299–308 (DDL marked "Optional: position_path_samples (only if needed)") | **absent** | Zero matches. Spec marks as optional ("Do NOT store tick-level paths"). |

#### Existing 3-column triple on `trading_prediction_outputs` (Layer 1 surface)

Verified by `grep "counterfactual" supabase/migrations/20260421_add_counterfactual_pnl.sql`:

| Column | Type | Migration | Spec §1 line | Status |
|---|---|---|---|---|
| `counterfactual_pnl` | `NUMERIC(10,2)` | `20260421_add_counterfactual_pnl.sql:8` | line 50 | **verified — Layer 1 surface** |
| `counterfactual_strategy` | `TEXT` | `20260421_add_counterfactual_pnl.sql:11` | line 51 | **verified — Layer 1 surface** |
| `counterfactual_simulated_at` | `TIMESTAMPTZ` | `20260421_add_counterfactual_pnl.sql:14` | line 52 | **verified — Layer 1 surface** |
| Partial index `idx_prediction_counterfactual_pending` | partial idx on `predicted_at DESC WHERE no_trade_signal = true AND counterfactual_pnl IS NULL` | `20260421_add_counterfactual_pnl.sql:34–36` | (not cited) | **verified — implicit infrastructure for the EOD labeler query path** |
| Migration header comment lines 16–24 | `'Pure observability — never read by any trading-decision path.'` + `'trading_prediction_outputs does not persist a per-prediction strategy hint'` | `20260421_add_counterfactual_pnl.sql:16–24` | implicit | **verified — the migration header is the canonical statement of Layer 1's observability-only contract; PRE-P11-4 carry-forward authoritative source** |

#### Spec §3 — three new columns on `trading_prediction_outputs` (decision-time strategy hint capture)

| Column | Type | Spec §3 line | Status at HEAD |
|---|---|---|---|
| `strategy_hint` | `TEXT` | line 150 | **absent** — `grep -rln "strategy_hint" supabase/migrations/` returns zero matches. |
| `strategy_structure` | `JSONB` | line 151 | **absent** — zero matches. |
| `candidate_source` | `TEXT` | line 152 | **absent** — zero matches. |

**Cross-spec implication:** AI-SPEC-002 P1.3.2 `B-AI-002-2` and `B-AI-002-7` both flagged that `trading_prediction_outputs` "does not persist a per-prediction strategy hint" (migration header line 23) — Item 10 Spec §3 is the canonical owner of the fix.

#### Spec §6 — `label_quality` enum value `legacy_observability_only` (lockdown migration)

| Spec section | Reality | Status |
|---|---|---|
| Spec §6 lines 423–432 — `UPDATE trade_counterfactual_cases SET label_quality = 'legacy_observability_only', calibration_eligible = false WHERE created_at < <Commit_4_deploy_date>` | `label_quality` column does not exist on Layer 1 columns; `calibration_eligible` column does not exist on Layer 1 columns. **`<Commit_4_deploy_date>` is unresolved** — it refers to "Commit 4" of the IC/IB target_credit fix sequence (per pre-AI track addendum Commit 4 = re-mark + NULL slippage cleanup, planned for Tuesday 2026-04-28; **not yet shipped at HEAD**). | **load-bearing decision pending** — operator must lock the cutover anchor date (Spec §6 line 429); tracked as `C-AI-010-5`. |

#### Other cross-spec absences relevant to Item 10

| Reference | Status at HEAD | Cross-spec audit |
|---|---|---|
| `strategy_attribution.case_id UUID REFERENCES trade_counterfactual_cases(id)` | Both tables absent. | AI-SPEC-002 `B-AI-002-7` + `C-AI-002-2`; **resolves now** in favor of Spec §4 trade_counterfactual_cases table. |
| `replay_eval_cases` reads from Item 10 surface | Both tables absent. | AI-SPEC-004 `B-AI-004-8`; **resolves now** in favor of Item 4 reading the new `trade_counterfactual_cases` table (option 1 in `C-AI-002-2`). |
| Item 1 Governor reads `schema_quality_factor` based on Item 10 `calibration_eligible` | Item 1's `schema_quality_factor` formula (Spec §16 of AI-SPEC-001) absent at HEAD. | AI-SPEC-001 `B-AI-001-5` (calibration_eligible producer chain). |

### 3.3 Redis Key References

Item 10's spec uses one production Redis key (`feedback:counterfactual:enabled`). Verified against evidence pack §10.2:

| Spec citation | Producer | Consumer | TTL | Status |
|---|---|---|---|---|
| `feedback:counterfactual:enabled` (Spec §0 by reference; not explicitly cited in spec text but implied by "feature flag wired in B1-5") | `set-feature-flag` Edge Function (out-of-tree) — wired to backend in Section 13 B1-5 (commit `fc64840`); `model:meta_label:enabled` follows same pattern | `backend/counterfactual_engine.py:168` (`raw = redis_client.get("feedback:counterfactual:enabled")`); fail-open ENABLED if Redis-down | operator-controlled | **verified — partial (out-of-tree producer; in-tree consumer)** |

**Spec §5 z-score Redis key references** (Spec §5 lines 364–376 — `vix_z`, `spread_z`):

| Spec assumption | HEAD reality | Status |
|---|---|---|
| `vix_z` value source | No `redis:vix_z` key. VIX value present at `polygon:vix:current` (per matrix §6 lines 600s); z-score not exposed as Redis key. **Source unclear in spec** — Class C escalation `C-AI-010-3`. | **producer-undefined** |
| `spread_z` value source | No `redis:spread_z` key. Bid-ask spread snapshots exist transiently in `tradier_feed.py` quote logic but are not z-scored or persisted. **Source unclear in spec** — Class C escalation `C-AI-010-3`. | **producer-undefined** |

### 3.4 Commit Hash References

Item 10's spec is the only Cluster A spec where the existing scaffold's commit is explicitly cited.

| Spec citation | Verification | Status |
|---|---|---|
| Spec §0 line 5 — `Sources: Existing 12E implementation (commit 2400e98, shipped 2026-04-20) + GPT-5.5 Pro audit Round 1 + Claude verification + GPT verification accept` | `git show 2400e98 --stat --format="%H%n%s%n%ai"` returns `2400e98eff36574ca3da33290c03650d91cd83fb` / `feat(learning): counterfactual engine D4 (12E)` / `2026-04-20 13:17:13 -0400`. Files touched: `backend/counterfactual_engine.py +349`, `backend/main.py +63`, `backend/tests/test_counterfactual_engine.py +332`, `supabase/migrations/20260421_add_counterfactual_pnl.sql +36`. **All four files match spec §1 lines 42 + 49 + 56 + 57.** | **verified** |
| Spec §1 line 39 implicit — "shipped 2026-04-20" | Confirmed by commit timestamp `2026-04-20 13:17:13 -0400`. | **verified** |
| Spec §0 line 4 — `Locked: 2026-04-25` | `git log --since=2026-04-25 --until=2026-04-25 -- backend/counterfactual_engine.py` returns no matches; spec was locked AFTER `4970095` (2026-04-20 14:07:14) and `fc64840` (2026-04-20 18:43:14). **Spec was therefore locked 5 days AFTER subsequent fixes had already shipped — but did not update the line/test counts to reflect HEAD reality.** | **verified — Class A drift** |
| Spec §13 line 659 — `shippedCommit: '2400e98'` (proposed value for `useActivationStatus.ts` entry) | Commit `2400e98` is correct as the original scaffold ship; the entry at HEAD has `builtStatus: 'live'` but lacks the `shippedCommit` field. | **verified — partial (advisory field not yet shipped)** |

**Subsequent commits after 2400e98 (NOT cited by spec but architecturally relevant — drift since spec lock):**

| Commit | Date | Lines touched in `counterfactual_engine.py` | Resolves which Spec §13 Gap |
|---|---|---|---|
| `4970095` | 2026-04-20 14:07 | +42/-6 (health-status writes; UI status fix; 2 new tests) | **Spec §13 Gap 4 — RESOLVED** (health writes now at lines 384, 398) and **Spec §13 Gap 5 — PARTIALLY RESOLVED** (`builtStatus: 'live'` shipped, but `shippedDate` + `shippedCommit` fields not added) |
| `fc64840` | 2026-04-20 18:43 | +27/-? net (Section 13 batch — feature flag check pattern alignment) | (no specific Spec §13 Gap; harmonizes feature-flag check with `model:meta_label:enabled` pattern) |

Result: **Spec §1's "What Already Exists (DO NOT REWRITE)" inventory is stale by 5 days at lock time. The DO NOT REWRITE guidance still applies architecturally — Layer 1 should not be rewritten — but the line / test counts and the Spec §13 Gap statuses must be updated in Phase 2 corrections.**

---

## 4. Existing Partial Implementation (verified by Cursor)

**Item 10 is the ONLY Cluster A spec where substantial production scaffold already exists at HEAD.** This section is therefore substantive (unlike AI-SPEC-001 / 002 / 004 §4 which were brief).

| Aspect | Existing State | Source |
|---|---|---|
| Functional scaffold | **YES — production-shipped.** `backend/counterfactual_engine.py` 406 lines at HEAD (originally +349 at `2400e98`; +57 from subsequent fixes). 5 functions: `_fetch_spx_price_after_signal()` line 65, `_simulate_pnl()` line 109, `label_counterfactual_outcomes()` line 146, `generate_weekly_summary()` line 265, `run_counterfactual_job()` line 366. | Evidence pack §6.1 line 256, §8 Item 10 lines 444–455. Direct read of `counterfactual_engine.py` lines 1–406. |
| Schema in place | **PARTIAL — column triple, NOT table.** 3 columns on `trading_prediction_outputs`: `counterfactual_pnl NUMERIC(10,2)`, `counterfactual_strategy TEXT`, `counterfactual_simulated_at TIMESTAMPTZ` + partial index `idx_prediction_counterfactual_pending`. **Layer 1 surface only** — Layer 2 surface (`trade_counterfactual_cases`, `strategy_utility_labels`, `closed_trade_path_metrics`, optional `position_path_samples` + 3 new columns `strategy_hint` / `strategy_structure` / `candidate_source`) absent at HEAD. | Migration `supabase/migrations/20260421_add_counterfactual_pnl.sql` lines 7–37. PRE-P11-4 carry-forward + evidence pack §7.3. |
| Feature flag wiring | **YES.** `feedback:counterfactual:enabled` Redis key wired in B1-5 (commit `fc64840`). Consumer at `counterfactual_engine.py:168`. Producer: `set-feature-flag` Edge Function (out-of-tree). Fail-open ENABLED. | Evidence pack §10.2 line 610; matrix §6 line 623. |
| Tests covering scope | **YES — 11 tests at HEAD** (spec says 9; +2 from `4970095`). Test file: `backend/tests/test_counterfactual_engine.py`. Tests: `test_simulate_pnl_condor_win/loss/straddle_win` (lines 30–69 — pure-math `_simulate_pnl`), `test_label_counterfactual_skips_when_no_spx_price/exit_price_unavailable/writes_correct_columns` (lines 136–227 — EOD labeler), `test_weekly_summary_skips_when_insufficient_sessions/runs_when_sufficient_sessions` (lines 232–313 — 30-session warmup gate), `test_run_counterfactual_job_fail_open` (line 316 — Supabase outage fail-open), `test_run_counterfactual_job_writes_idle_health_on_success/error_health_on_exception` (lines 337–390 — Spec §13 Gap 4 health writes, added by `4970095`). | Direct file inspection `backend/tests/test_counterfactual_engine.py` lines 1–390. |
| EOD orchestration | **YES.** `run_counterfactual_job_wrapper` at `backend/main.py:200`; daily 4:25 PM ET job at `main.py:1399–1409` (id `counterfactual_eod_job`). `run_counterfactual_weekly_wrapper` at `main.py:217`; weekly Sunday 6:30 PM ET job at `main.py:1416–1421` (id `counterfactual_weekly_job`). | Direct grep on `backend/main.py` confirms both wrappers and both schedule entries. |
| Frontend surface | **PARTIAL.** `src/hooks/trading/useActivationStatus.ts:241–251` — `builtStatus: 'live'` at line 250 (shipped via `4970095`). **Missing per Spec §13 Gap 5: `shippedDate: '2026-04-20'` and `shippedCommit: '2400e98'` fields not present in entry or `ActivationFlag` interface.** | Direct read of `useActivationStatus.ts:241–251`. |
| Health monitoring | **YES — Spec §13 Gap 4 RESOLVED.** Health writes at `counterfactual_engine.py:384` (success path, status='idle') and `counterfactual_engine.py:398` (failure path, status='error') — both wrapped in own try/except so observability never masks the real job result (matches Spec §13 lines 631–646 pattern). Tests `test_run_counterfactual_job_writes_idle_health_on_success` + `test_run_counterfactual_job_writes_error_health_on_exception` cover both paths. | Direct read of `counterfactual_engine.py:380–406` + `test_counterfactual_engine.py:337–390`. |
| Documentation references | **YES.** `TASK_REGISTER.md` §12E line 841 — D4 Counterfactual Engine, marked SHIPPED (commit `2400e98`). `MASTER_PLAN.md` references via Section 13 B1-5 wiring (commit `fc64840`). Item 11 UI Observability Sprint references via `0149877` (out of Item 10 scope). | Evidence pack §6.1 line 200, §10.3.2 line 697. |

**Architectural significance for the audit:** Item 10's scaffold is the **only V0.1 production-grade AI-architecture surface** that already ships, runs daily, and has health monitoring + tests + UI status. Spec's "DO NOT REWRITE" architectural commitment (Spec §0 line 14) is therefore not abstract — Layer 1 IS the production-shipped engine. Layer 2 is a **separate, parallel calibration-grade engine** that ships in V0.2 alongside (not on top of) Layer 1. **The `simulation_status` taxonomy (Spec §2 Tier 1/2/3) explicitly distinguishes Layer 1 outputs (`legacy_observability_only`) from Layer 2 outputs (`calibration_grade` / `approximate_width` / `insufficient_strategy_context`).**

---

## 5. The Ten Audit Dimensions

Per `CONSOLIDATED_PLAN_v1.2_APPROVED.md` §2 Layer B, every spec is evaluated against these 10 dimensions. Cross-cutting matrix §3 lines 304–326 gave a summary view; this section gives per-item depth verified against HEAD `1237746`.

| # | Dimension | Finding | Source / Evidence |
|---|-----------|---------|-------------------|
| 1 | File/module exists | **PARTIAL — Layer 1 SHIPPED, Layer 2 absent.** Layer 1: `backend/counterfactual_engine.py` 406 lines at HEAD (5 functions verified at lines 65, 109, 146, 265, 366). Layer 2: spec proposes calibration-grade engine but does not specify the file or module — open as `B-AI-010-1`. | §3.1 verification + §4 above. |
| 2 | DB table/column | **PARTIAL — column triple SHIPPED, table architecture proposed.** Layer 1: 3 columns on `trading_prediction_outputs` shipped via `20260421_add_counterfactual_pnl.sql`. Layer 2: 4 new tables (`trade_counterfactual_cases`, `strategy_utility_labels`, `closed_trade_path_metrics`, optional `position_path_samples`) + 3 new columns (`strategy_hint`, `strategy_structure`, `candidate_source`) — all absent at HEAD. **Spec §4 is the authoritative architectural source for the table architecture, resolving AI-SPEC-002 `C-AI-002-2` in favor of NEW table.** | §3.2 verification + PRE-P11-4 carry-forward resolution. |
| 3 | Redis keys | **`feedback:counterfactual:enabled` SHIPPED** (consumer `counterfactual_engine.py:168`; out-of-tree producer; fail-open ENABLED). Spec §5 references `vix_z` / `spread_z` z-score producers — **producer-undefined at HEAD** (Class C escalation `C-AI-010-3`). | §3.3 verification. |
| 4 | Current behavior matches spec | **Layer 1 = exact match for legacy observability;** Layer 2 = **no current behavior.** Layer 1's hardcoded `iron_condor` default at line 219 is **explicitly identified by the spec itself (§3 lines 174–186) as the dangerous behavior to replace** in Layer 2. The spec is internally coherent: Layer 1 is preserved as legacy-observability with `calibration_eligible = false`; Layer 2 introduces the corrected behavior. | §3.1 + §3.2 + spec §3. |
| 5 | Spec is future design? | **NO — partially built (Layer 1 shipped 2026-04-20; Layer 2 proposed).** This is the only Cluster A spec where "partially built" is the accurate framing — for Items 1, 2, 4, the entire spec is forward-design. | §4 above. |
| 6 | Governance conflict | **YES — emergent.** Migration `20260421_add_counterfactual_pnl.sql` header (lines 4–5) explicitly states `'Pure observability — never read by any trading-decision path.'` Layer 2 promotes Item 10 to **calibration-grade input feeding Items 5–9** (Spec §0 line 8 — "Calibration-grade attribution data feeding Items 5-9"). This contradicts the migration header's observability-only contract and requires explicit governance update — **either D-023 enrichment OR a new D-XXX OR a `system-state.md` `counterfactual_engine` field tracking Layer 1 vs Layer 2 phase.** | Migration `20260421_add_counterfactual_pnl.sql:4–5` vs Spec §0 line 8. |
| 7 | Authority level proposed | **Layer 1 = `legacy_observability_only` (no authority — read-only by operator dashboards).** Layer 2 = **advisory authority** for Items 5–9 (calibration-grade after-slippage P&L is consumed by training but does not gate trade execution). Per Spec §15 line 728: "Items 5-9 utility labels use `counterfactual_pnl_after_slippage`." Counterfactual_pnl_after_slippage is training-grade input, not a trade-time gate. | Spec §15 + Spec §6 (API enforcement of `calibration_eligible` filtering). |
| 8 | Calibration dependencies | **HIGH — Item 10 V0.2 Layer 2 is the producer for `calibration_eligible = true` rows on the counterfactual surface; consumed by Items 1, 5, 6, 9.** Item 1 Governor `schema_quality_factor` (AI-SPEC-001 `B-AI-001-5`) reads `calibration_eligible` from Item 2 + Item 10 surfaces. Item 4 Replay Harness reads `trade_counterfactual_cases` (AI-SPEC-004 `B-AI-004-8` — bilateral with `C-AI-002-2`). Items 5 (Vol Fair-Value), 6 (Meta-Labeler), 9 (Exit Optimizer) per matrix §3 line 322 + spec §6 — all blocked on Item 10 V0.2 Layer 2 ship. **Layer 2's chain-archive prerequisite is bilateral with Item 4 `C-AI-004-4`.** | Matrix §3 line 322; AI-SPEC-002 + AI-SPEC-004 audits; spec §6 + §15. |
| 9 | Training contamination risk | **HIGH if Layer 2 ships without Spec §3 fix; LOW if shipped with fix.** Today's Layer 1 hardcodes `iron_condor` at line 219 for ALL no-trade rows regardless of what the rules engine actually computed. If Items 5–9 train on Layer 1 outputs, they'll learn that "every no-trade should have been an iron_condor" — systematic mislabeling. **Spec §3 (replace default-to-iron_condor with NULL when strategy_hint missing) is the load-bearing fix that prevents this contamination.** Spec also enforces structurally via Spec §6 API filtering (`get_meta_labeler_training_data` always filters `calibration_eligible = true`). | `counterfactual_engine.py:213–223` (hardcoded `iron_condor` proxy with explicit comment acknowledging the limitation); spec §3 + §6 + §15 line 729. |
| 10 | Implementation owner | Cursor. | T-Rule 1. |

---

## 6. Missing Pieces

What the spec assumes will exist (Layer 2) but doesn't at HEAD:

### 6.1 Files / modules

- **Layer 2 calibration-grade engine** — file location not specified. Spec §0 line 14 says "Do not rewrite the current `counterfactual_engine.py`" but does not name the new module. Candidates: (a) `backend/counterfactual_engine_v2.py` (parallel module; matches Spec's "two layers" framing); (b) `backend/calibration_grade_attribution.py` (descriptive); (c) extend existing engine with `_v2` functions (rejected by Spec §0 line 14). **Class B `B-AI-010-1`.**
- **Strategy-specific simulators** — Spec §12 line 605 ("Resolved by Tier 1 simulators") references per-strategy simulators; not yet specified at file level. Likely `backend/replay_strategy_simulators.py` or per-strategy modules (`backend/sim_iron_condor.py`, etc.). Bilateral with AI-SPEC-004 `B-AI-004-2` (8 `replay_*.py` files).
- **API enforcement accessor functions** — Spec §6 lines 395–410 propose `get_meta_labeler_training_data()`, `get_vol_engine_replay_cases()`, `get_adversarial_block_outcomes()`, `get_exit_optimizer_training_paths()`. None exist at HEAD. Likely live alongside Layer 2 engine.
- **Halt-day blocked-cycle row creation** — Spec §7 lines 442–454 require `risk_engine.py` halt-trigger to create counterfactual rows with `case_type = "counterfactual"`, `counterfactual_reason = "halt_block"`, `simulation_status = "pending_eod_label"`. No such logic at HEAD; bilateral with `risk_engine.py:234–235` (3-loss reduction) and `prediction_engine.py:688–691` (5-loss session halt).

### 6.2 Tables / schema

- 4 new tables (Spec §4): `trade_counterfactual_cases`, `strategy_utility_labels`, `closed_trade_path_metrics`, `position_path_samples` — all absent.
- 3 new columns on `trading_prediction_outputs` (Spec §3): `strategy_hint TEXT`, `strategy_structure JSONB`, `candidate_source TEXT` — all absent. (Migration header at `20260421_add_counterfactual_pnl.sql:23` explicitly notes the gap.)
- `simulation_status` / `simulation_confidence` / `width_source` / `width_table_version` / `label_version` / `label_quality` / `calibration_eligible` columns — proposed for both Layer 1 retrofit (lockdown) and Layer 2 schema. Layer 1 lockdown migration absent (`C-AI-010-5`).
- Versioned width table — Spec §2 lines 128–138 propose `width_table_version` / `vix_bucket` / `strategy_type` / `time_bucket` / `default_short_delta` / `default_long_delta` / `default_width` columns (likely a new `vix_spread_width_table` table or YAML config). Not formalized in spec; lives implicitly in code as `_DEFAULT_SPREAD_WIDTH = 5.0` constant at `counterfactual_engine.py:55`.

### 6.3 Redis keys

- Spec §5 z-score producers (`vix_z`, `spread_z`) — producer authority undefined at HEAD; Class C `C-AI-010-3`.
- No new `counterfactual:*` namespace proposed in spec for Layer 2 hot-path data; Layer 2 appears to be entirely Supabase-backed.

### 6.4 Functions called by spec but not yet defined

- `write_health_status("counterfactual_engine", ...)` — Spec §13 Gap 4 fix; **already shipped at HEAD** (lines 384, 398) via `4970095`. Class B observation only.
- `_simulate_pnl()` strategy-specific replacement (per Spec §12 line 605) — current single function at `counterfactual_engine.py:109` becomes Layer 1 legacy; Layer 2 needs per-strategy simulators.
- Slippage formula composition (Spec §5 lines 332–376): `base_strategy_slippage * time_multiplier * vol_multiplier * spread_multiplier * size_multiplier` with cap at `3.0 * normal_strategy_slippage`. No implementation at HEAD.
- `counterfactual_pnl_after_slippage` calculation. No implementation at HEAD; bilateral with `calibration_engine.py` slippage estimates.

### 6.5 Feature flags assumed but not in code

- No new flags proposed; Layer 2 reuses `feedback:counterfactual:enabled` (Layer 1 + Layer 2 share the master kill-switch).
- **Implicit flag for Layer 2 vs Layer 1 routing** — spec is silent on whether a separate flag (`feedback:counterfactual:layer2:enabled`) is needed during Layer 2 rollout. **Class B `B-AI-010-X` — recommend explicit flag for canary-style rollout.**

---

## 7. Contradictions

### 7.1 Internal Contradictions

- **Spec §0 line 14 ("Do not rewrite") vs Spec §3 lines 174–186 ("Replace Default-to-iron_condor Behavior")** — spec simultaneously forbids rewriting Layer 1 AND requires changing Layer 1's `_simulate_pnl()` default-strategy fallback. Resolution must be either: (a) `_simulate_pnl()` IS modified in Layer 1 (small surgical change, not a "rewrite") with new `simulation_status = 'insufficient_strategy_context'` return; OR (b) all such changes happen in Layer 2's new engine and Layer 1 is frozen forever. Spec implies (a) but does not state explicitly. **Tracked as `C-AI-010-1`.**
- **Spec §0 line 5 (Tier "V0.2 immediate / V0.2 strategy-specific / V0.3 adversarial / V0.4 exit") vs CROSS_CUTTING_EVIDENCE_MATRIX.md §1 line 52 (Tier "V0.1")** — matrix classifies Item 10 as Tier V0.1; spec classifies as graduated V0.2-V0.4. Resolution: V0.1 = Layer 1 (already shipped); V0.2+ = Layer 2 (proposed). Matrix should be amended to show graduated tier. **Tracked as `C-AI-010-2`.**
- **Spec §6 lines 423–432 cutover anchor (`<Commit_4_deploy_date>`) vs unresolved Commit 4** — spec uses "Commit 4 deploy date" as the cutover for legacy-observability lockdown, but Commit 4 of the IC/IB target_credit fix sequence (re-mark + NULL slippage cleanup) is not yet shipped at HEAD. Anchor is a moving target. **Tracked as `C-AI-010-5`.**

### 7.2 Cross-Spec Contradictions

| Cross-spec interaction | Status | Resolution |
|---|---|---|
| **AI-SPEC-002 `C-AI-002-2` (table-vs-column architectural divergence)** | **RESOLVED by AI-SPEC-010 spec §4** in favor of option 1 (Item 10 ships `trade_counterfactual_cases` as a NEW table; existing column triple becomes Layer 1 legacy observability). | Move `C-AI-002-2` from register §1 to §4 (Resolved Findings) with resolution date 2026-04-26 and note "Resolved by AI-SPEC-010 spec §4 — Item 10 ships `trade_counterfactual_cases` as a NEW table per Spec §4 lines 198–225; existing 3-column triple on `trading_prediction_outputs` deprecates to Layer 1 legacy observability surface (`label_quality = 'legacy_observability_only'` per Spec §6 lines 423–432)." |
| **AI-SPEC-002 `B-AI-002-7` (table-vs-column escalation pointer)** | **RESOLVED transitively** by `C-AI-002-2` resolution. | Left in register §2 as resolved-pointer; no separate move (per register protocol, Class B items remain in §2 until consolidated approval). |
| **AI-SPEC-002 `B-AI-002-2` (`closed_trade_path_metrics` substrate gap)** | **RESOLVED** — Item 10 Spec §4 lines 276–294 is the authoritative owner of `closed_trade_path_metrics(position_id BIGINT PRIMARY KEY REFERENCES trading_positions(id))`. | Cross-spec theme in register §5 updates: `closed_trade_path_metrics substrate gap` status changes from "open — confirmed in 2 audits" to "resolved by AI-SPEC-010 spec §4 — Item 10 owns the substrate; Item 2 reads from it." Item 2's V0.1 ship scope can rely on Item 10 V0.2 ship for the substrate (sequencing: Item 2 V0.1 either (a) ships with NULL placeholders for path-metric columns and backfills after Item 10 V0.2, or (b) waits for Item 10 V0.2 schema landing). |
| **AI-SPEC-004 `B-AI-004-8` (bilateral with `C-AI-002-2`)** | **RESOLVED** — Item 4 reads from Item 10's NEW `trade_counterfactual_cases` table per option 1 of `C-AI-002-2`. Spec §1 line 37 of AI-SPEC-004 ("reads from `trade_counterfactual_cases`") becomes accurate after Item 10 V0.2 ship. | Update register §2 `B-AI-004-8` "Proposed Correction" cell: option 1 confirmed by AI-SPEC-010 audit; spec wording stays as-is. |
| **AI-SPEC-001 `B-AI-001-5` (`calibration_eligible` consumer chain)** | **PARTIALLY RESOLVED** — Item 10 V0.2 Layer 2 is the canonical producer of `calibration_eligible` on the counterfactual surface. AI-SPEC-002 P1.3.2 was correct that Item 2 is producer for trade attribution; AI-SPEC-010 confirms Item 10 V0.2 Layer 2 is producer for counterfactual attribution. Two-producer model. | No register move; theme in §5 already tracks this. |
| **AI-SPEC-003 (Synthetic Counterfactual) ↔ AI-SPEC-010 boundary** | **PARTIALLY UNRESOLVED.** Item 10 Spec §4 line 202 includes `case_type` enum value `synthetic` AND `case_weight = 0.2`; Item 10 owns the table. Spec §10 lines 502–522 mention synthetic case generation but defer to Item 6 selection-bias mitigation. Item 3 (Cluster C, V0.4) is the owner of synthetic case **generation**. **Unresolved:** does Item 3 generate synthetic cases that Item 10 stores? Or does Item 10 own only natural counterfactuals and Item 3 has its own table? **Tracked as `C-AI-010-4`.** | Operator decision required at audit close. Default position (per consolidated plan §5 conservative-first principle): Item 10 owns `trade_counterfactual_cases` storage; Item 3 generates synthetic case rows that INSERT into Item 10's table with `case_type = 'synthetic'`, `case_weight = 0.2`. Item 3 is downstream consumer-of-storage, not separate-table-owner. |
| **AI-SPEC-005 (Vol Fair-Value Engine) ↔ AI-SPEC-010 §9** | **CROSS-SPEC TIE-IN.** Spec §9 lines 482–493 capture per-decision `item5_predicted_ev` / `realized_counterfactual_utility` / `prediction_error` for Item 5 attribution. Item 10 stores these on `trade_counterfactual_cases` rows. Item 5's V0.1/V0.2 ship is bilateral with Item 10 V0.2 ship. | Cluster B audit at P1.3.5 (Item 5) will close this; flagged here for completeness. |
| **AI-SPEC-007 (Adversarial Review) ↔ AI-SPEC-010 §8** | **CROSS-SPEC TIE-IN.** Spec §8 lines 462–476 store `adversarial_*` fields on counterfactual cases for Item 7 calibration. Item 7 (Cluster C, V0.3) ships after Item 10 V0.3. | Cluster C audit at P1.3.7 (Item 7) will close this. |
| **AI-SPEC-009 (Exit Optimizer) ↔ AI-SPEC-010 §4 path metrics** | **CROSS-SPEC TIE-IN.** Item 9 (Cluster B, V0.2-V0.4) reads `closed_trade_path_metrics` per matrix §5 line 294. Item 10 V0.2 ships the substrate; Item 9 V0.4 consumes. | Cluster B audit at P1.3.9 (Item 9) will close this. |
| **AI-SPEC-001 (Risk Governor) ↔ AI-SPEC-010** | **CROSS-SPEC TIE-IN.** Item 1's `schema_quality_factor` formula (AI-SPEC-001 `B-AI-001-5`) reads `calibration_eligible` from Item 10's case rows. Item 1 V0.1 ship is calendar-blocked on Item 10 V0.2 Layer 2 ship for the formula's schema_quality_factor input. | Cross-spec sequencing: Item 1 V0.1 ships **scaffolding** (which can land independently); Item 1 V0.2 paper-binding promotion is blocked on Item 10 V0.2 schema landing. Same pattern as Item 4 V0.1 scaffolding-vs-V0.2 calibration-grade per `C-AI-004-4`. |
| **AI-SPEC-004 (Replay Harness) `C-AI-004-4` chain-archive prerequisite** | **BILATERAL.** Item 10 V0.2 Layer 2's after-slippage P&L over historical decisions also depends on archived option-chain data (specifically Spec §5 base_strategy_slippage = legs × half_spread_estimate, where half_spread_estimate is per-strike-per-time bid-ask data). | Same operator decision as `C-AI-004-4` resolves both: (a) forward archival, (b) paid historical, or (c) Layer 2 ships without after-slippage P&L until archive matures. **Tracked as cross-reference to `C-AI-004-4`, not a new Class C.** |

### 7.3 Governance Contradictions

- **Migration header `20260421_add_counterfactual_pnl.sql:4–5`** ('Pure observability — never read by any trading-decision path.') vs **Spec §0 line 8** ("Calibration-grade attribution data feeding Items 5-9"). Layer 2 promotion changes the contract from "never read" to "read by Items 5–9 training accessors." This requires governance update — at minimum a `system-state.md` `counterfactual_engine` field tracking Layer 1 vs Layer 2 phase, and possibly D-023 enrichment if Layer 2 outputs are ever consumed by trade-time gates. **The spec correctly distinguishes Layer 2 as advisory authority (training input, not trade-time gate)** per Spec §15 — observability commitment is preserved at the trade-execution boundary even if data flows into training. **Class B observation requiring governance clarification (B-AI-010-X).**
- **Spec §6 "API-Level Calibration_eligible Enforcement" (lines 391–432)** introduces structural enforcement at the function-signature layer: `get_meta_labeler_training_data() ALWAYS filters: calibration_eligible = true`. This is a constitutional-style rule that should be encoded in D-023 alongside the AI authority boundary, OR a new D-XXX. Default position: D-023 enrichment (Item 10 V0.2 Layer 2's `calibration_eligible` enforcement is part of the broader AI authority boundary).
- **No D-XXX directly required** for Item 10 itself; all governance updates fold into D-023 enrichment + MASTER_PLAN Phase 3D entry + TASK_REGISTER §14D + system-state.md `counterfactual_engine` field.

---

## 8. Carry-Forward Findings From P1.1 / P1.2 / P1.3.1 / P1.3.2 / P1.3.3

| Finding | Applies to this spec? | Implication |
|---------|----------------------|-------------|
| #1: `gex:updated_at` consumer-only orphan | **NO** — Item 10 is EOD batch over closed sessions; no live freshness gate. Layer 2 reads decision-time snapshot (`entry_snapshot JSONB` per Spec §4 line 207) rather than live Redis. | n/a |
| #2: `gex:atm_iv` consumer-only | **NO** — same reason as #1; Item 10 doesn't read GEX live. | n/a |
| #3: MASTER_PLAN debit-spread feature flag debt | **NO** — spec doesn't add new strategy flags; Layer 1 + Layer 2 reuse `feedback:counterfactual:enabled`. | n/a |
| #4: `_safe_redis()` is dead code at HEAD | **NO** — Item 10 is EOD batch, not a live freshness-gated path. | n/a |
| #5: `counterfactual_pnl` is column triple, not table (PRE-P11-4) | **YES — AUTHORITATIVE.** Item 10 Spec §4 is the canonical resolution surface for the column-vs-table semantic mismatch flagged in evidence pack §9.6 + matrix carry-forward #5. **This audit resolves the carry-forward in favor of "Item 10 V0.2 Layer 2 ships a NEW table; existing column triple becomes Layer 1 legacy observability surface."** | Cross-spec theme in register §5 updates from "open — confirmed in 1 audit" to "resolved by AI-SPEC-010 audit (option 1 — new table; existing columns deprecate)." |

### Plus P1.3.2 themes

| Theme | Applies? | Implication |
|---|---|---|
| FK dependency cascade | **YES — Item 10 is FK target.** Item 10's `trade_counterfactual_cases.id BIGSERIAL PRIMARY KEY` (Spec §4 line 200) is the FK target consumed by AI-SPEC-002 `strategy_attribution.case_id` (B-AI-002-3) and AI-SPEC-002 `strategy_utility_labels.case_id` (Spec §4 line 234 — also owned by Item 10). Item 10 has zero outbound FK dependencies on unshipped tables (it references `trading_prediction_outputs(id)` and `trading_positions(id)`, both shipped). | Cross-spec sequencing: Item 10 V0.2 schema-landing **unblocks** Item 2 + Item 4 + Item 6 + Item 7 + Item 9 FK-target dependencies. Item 10 V0.2 should land BEFORE Item 2 V0.1 if Item 2 V0.1 wants FK constraints active (per `B-AI-002-3` two-phase plan). |
| `closed_trade_path_metrics` substrate gap | **YES — RESOLVED by Item 10 Spec §4.** Item 10 owns the substrate per Spec §4 lines 276–294. | Theme moves from "open — confirmed in 2 audits" to "resolved by AI-SPEC-010 spec §4." Items 2 + 4 + 9 read; Item 10 writes. |
| Decision outcome enum coordination across authority surfaces | **PARTIAL — adjacent but not the same enum.** Item 10's `counterfactual_reason TEXT` enum (Spec §4 line 209–210: `no_trade | governor_block | meta_skip | adversarial_block | halt_block | alternative_strategy`) is independent of AI-SPEC-002's `decision_outcome` enum (8 values: `opened_traded | blocked_governor | blocked_meta_labeler | blocked_adversarial | skipped_rules | blocked_constitutional | halted_blocked_cycle | synthetic_case`). The two enums share concepts (`blocked_governor`, `halt_block`, `synthetic_case`) but are not byte-identical. | Cross-spec: D-023 wording must clarify the relationship. Default position: independent enums (Item 2 = decision-side; Item 10 = counterfactual-reason-side); operator confirms or unifies. **Class B `B-AI-010-X`.** |
| Legacy `attribution_*` columns on `trading_positions` | **NO** — Item 10 doesn't query the dead `attribution_*` columns. | n/a |

### Plus P1.3.3 themes

| Theme | Applies? | Implication |
|---|---|---|
| `paper_phase_criteria` vs `item_promotion_records` authority overlap | **PARTIAL — consumer.** Item 10 itself doesn't gate on `item_promotion_records` (it's data infrastructure, not authority-promoted). However, **downstream consumers Items 1, 5, 6, 9 read Item 10's `calibration_eligible` and ARE gated on `item_promotion_records`** per AI-SPEC-004 `C-AI-004-3`. | No new register entry needed; cross-spec sequencing: Item 10 V0.2 schema-landing must precede consumer items' authority promotion attempts. |
| Decision-card definition / counting ambiguity (Spec §12 200-card threshold) | **PARTIAL — distinct concept.** Item 10's `case_type` enum (`actual / counterfactual / synthetic`) is adjacent to Item 4's `replay_eval_cases.calibration_eligible = true` decision-card concept. Item 4 reads Item 10's cases per matrix §5 + AI-SPEC-004 `B-AI-004-9`. | Cross-spec tie-in only; no new escalation. D-023 wording from `C-AI-004-2` already specifies "decision card = `replay_eval_cases.calibration_eligible = true`"; Item 10's cases feed Item 4's surface but are not themselves "decision cards" by that definition. |
| Archived option-chain data substrate (V0.1 hard prerequisite) | **YES — bilateral with `C-AI-004-4`.** Item 10 V0.2 Layer 2's after-slippage P&L over historical decisions depends on the same chain-archive substrate as Item 4. Spec §5 base_strategy_slippage formula needs per-strike-per-time bid-ask data. | Cross-reference `C-AI-004-4` rather than a new escalation. Same operator decision (forward archival / paid historical / V0.1 advisory-only deferral) resolves both. **Update cross-spec theme in register §5: "Archived option-chain data substrate" — affected specs list extends to include AI-SPEC-010.** |
| News/event `published_at` field substrate (point-in-time gating) | **PARTIAL — bilateral.** Spec §7 halt-day blocked-cycle labeling needs decision-time event taxonomy; less direct than Item 4's leakage concern. | No new escalation; cross-reference `B-AI-004-6` if Item 10 Layer 2 wires event_unavailable handling. |
| LightGBM artifact-log substrate (model-state-source for replay) | **NO** — Item 10 is post-hoc P&L labeling over realized market path; doesn't reconstruct model state. | n/a |

---

## 9. Risk Rating

**Rating:** **HIGH**

**Rationale:** Item 10 is architecturally distinct from prior Cluster A audits — it has the most existing scaffold AND simultaneously resolves the most cross-spec architectural divergences. The line/test count drift in the spec is mechanical (Class A) and easily corrected; but four substantive concerns drive the HIGH rating: (1) the table-vs-column resolution closes `C-AI-002-2` (and transitively `B-AI-002-7`, `B-AI-004-8`, PRE-P11-4 carry-forward), affecting THREE prior audits; (2) Layer 2 module organization is unspecified (Class B `B-AI-010-1` — significant implementation contract gap); (3) six-plus cross-spec read consumers (Items 1, 2, 4, 5, 6, 7, 9) depend on Item 10 V0.2 Layer 2 ship — V0.1 critical-path FK-target sequencing is bilateral with most other Cluster A + B audits; (4) the chain-archive prerequisite (bilateral with `C-AI-004-4`) is load-bearing for Spec §5 after-slippage P&L. Risk rating is HIGH — not CRITICAL — because Layer 1 already ships and is observability-only (no V0.1 trading-decision dependency on Layer 2); the architectural divergences resolve cleanly via the spec's own authoritative DDL; and chain-archive prerequisite is shared with Item 4 (already gated by `C-AI-004-4`).

**Categories:**
- Spec-vs-code drift severity: **medium** (Layer 1 line/test count drift is Class A; Layer 2 is forward-design with ~12 sub-buildouts)
- Number of Class A corrections: **2** (line count 349→406; test count 9→11)
- Number of Class B corrections: **11** (Layer 2 module location; new tables; new columns; iron_condor fallback fix; Activation page partial-resolution; API enforcement accessors; halt-day blocked-cycle row creation; versioned width table; Layer 2 routing flag; counterfactual_reason vs decision_outcome enum coordination; advisory `system-state.md` field for Layer 1/Layer 2 phase tracking)
- Number of Class C corrections: **5** (Layer 1/2 cutover policy; cluster/tier classification reconciliation; slippage z-score producer authority; Item 3/Item 10 boundary; Layer 1 lockdown cutover anchor)
- Cross-cutting impact (specs affected): **6** (Items 1, 2, 4, 5, 6, 7, 9 all read Item 10's surface — confirmed by matrix §3 line 322, evidence pack §8 Item 10, AI-SPEC-002 + AI-SPEC-004 audits, spec §6 + §15)

---

## 10. Spec Corrections Required

Per `CONSOLIDATED_PLAN_v1.2_APPROVED.md` §3, three correction classes:

### 10.1 Class A — Mechanical Errors

Wrong file paths, stale line numbers, mistyped names, wrong counts. Any AI corrects; Cursor verifies. Rubber-stamped at end.

| # | Spec Section | Spec Says | Correct Value | Source of Truth |
|---|--------------|-----------|---------------|-----------------|
| A1 | Spec §1 line 42 | "`backend/counterfactual_engine.py (349 lines, 9 tests)`" — line count claim | **406 lines at HEAD** (`wc -l backend/counterfactual_engine.py = 406` confirmed by direct read). +57 lines from `2400e98` baseline (+42 from `4970095` health/UI fix; +21 net from `fc64840` Section 13 batch). | `wc -l backend/counterfactual_engine.py`; `git log --oneline -- backend/counterfactual_engine.py` returns 3 commits: 2400e98, 4970095, fc64840. |
| A2 | Spec §1 line 42 | "`backend/counterfactual_engine.py (349 lines, 9 tests)`" — test count claim | **11 tests at HEAD** (`grep -c "^def test_" backend/tests/test_counterfactual_engine.py = 11`). +2 tests from baseline: `test_run_counterfactual_job_writes_idle_health_on_success` (line 337) + `test_run_counterfactual_job_writes_error_health_on_exception` (line 363) — both added by commit `4970095` as part of the Spec §13 Gap 4 fix. | Direct file read; commit `4970095` introduced the new tests. |

### 10.2 Class B — Implementation Status / Content Omissions

"Exists" should be "planned"; "live" should be "observability-only"; spec assumes data being captured that isn't. GPT or Claude proposes; Cursor verifies. Operator approves consolidated list.

| # | Spec Section | Spec Says | Reality | Proposed Correction |
|---|--------------|-----------|---------|---------------------|
| B1 | Spec §0 line 14 + Spec §11 line 558 (Layer 2 calibration-grade engine) | "Layer 2: Calibration-Grade Attribution Engine (new)" — proposed but file/module not named. | No `backend/counterfactual_engine_v2.py` or equivalent at HEAD. Spec §11 V0.2 ship items 9–15 reference Layer 2 functions but do not specify the module file. | Add Class B note to Spec §0 + §11: Layer 2 engine file location is **`backend/counterfactual_engine_v2.py`** (recommended canonical name; matches Item 1's `ai_governor_*` namespace pattern from `B-AI-001-4`). Spec §11 V0.2 ship scope explicitly names this module. |
| B2 | Spec §3 lines 148–153 + Spec §4 lines 198–225, 232–269, 276–294, 299–308 (4 new tables + 3 new columns) | DDL provided as if part of spec deliverable; migration filename unspecified. | All 7 schema artifacts absent at HEAD. | No correction to spec wording — tag as "scheduled buildout"; clarify in Spec §11 V0.2 ship scope that Item 10 V0.2 Layer 2 includes 4 new migrations (one per table) + 1 ALTER TABLE migration on `trading_prediction_outputs` for the 3 new columns. Recommended filename pattern: `2026MMDD_add_counterfactual_layer2_*.sql`. |
| B3 | Spec §3 lines 174–186 + `counterfactual_engine.py:213–223` (replace default-to-iron_condor fallback) | Spec proposes Layer 1 + Layer 2 behavior change: when `strategy_hint` missing, return `counterfactual_pnl = NULL` with `simulation_status = "insufficient_strategy_context"`. | Layer 1 at HEAD hardcodes `strategy = "iron_condor"` at line 219 with explicit comment lines 213–218 acknowledging the limitation. **Bilateral edit to existing Layer 1 `_simulate_pnl()` AND new Layer 2 simulator.** | Add Class B note: V0.2 ship scope includes a small surgical Layer 1 edit to `counterfactual_engine.py:213–223` — replace `strategy = "iron_condor"` fallback with NULL-return path when `strategy_hint` is missing on the source row. **This is consistent with Spec §0 "do not rewrite" architectural commitment** because it is a bug fix to a known dangerous behavior (per Spec §3 lines 174–186), not a rewrite of the engine. Update tests to cover NULL-return path. |
| B4 | Spec §13 lines 651–660 (`useActivationStatus.ts` Counterfactual Tracking entry) | "`builtStatus: 'live'`, `shippedDate: '2026-04-20'`, `shippedCommit: '2400e98'`" — three fields proposed. | At HEAD `src/hooks/trading/useActivationStatus.ts:241–251`: `builtStatus: 'live'` (line 250) shipped via `4970095`; **`shippedDate` and `shippedCommit` fields are NOT in the entry** and the `ActivationFlag` interface does not declare these fields anywhere in the file. | Add Class B note: Spec §13 Gap 5 is **partially resolved** at HEAD. Remaining work for V0.2 ship: extend `ActivationFlag` interface to include `shippedDate?: string` and `shippedCommit?: string`; add the values to the Counterfactual Tracking entry; consider applying same fields to other `builtStatus: 'live'` entries for consistency. Low-risk frontend-only change. |
| B5 | Spec §6 lines 391–410 (API enforcement of `calibration_eligible`) | "`get_meta_labeler_training_data()`, `get_vol_engine_replay_cases()`, `get_adversarial_block_outcomes()`, `get_exit_optimizer_training_paths()` — function signatures with structural filtering" | None exist at HEAD; `grep -rln "get_meta_labeler_training_data\|get_vol_engine_replay_cases\|get_adversarial_block_outcomes\|get_exit_optimizer_training_paths" backend/` returns zero matches. | No correction to spec wording — tag as "scheduled buildout"; clarify in Spec §11 V0.2 ship scope that Layer 2 module exposes these 4 accessor functions with `calibration_eligible = true` filtering enforced at function-signature layer (not application convention). `diagnostic_opt_in` flag explicit + audit-logged per Spec §6 lines 414–419. |
| B6 | Spec §5 lines 332–376 (slippage formula) | `estimated_slippage = base_strategy_slippage * time_multiplier * vol_multiplier * spread_multiplier * size_multiplier`; `vol_multiplier = 1.0 + 0.25 * max(0, vix_z)`; `spread_multiplier = 1.0 + 0.30 * max(0, spread_z)` | No implementation at HEAD; `vix_z` and `spread_z` producer-undefined (escalates to `C-AI-010-3`). `half_spread_estimate` for `base_strategy_slippage` — bilateral with chain-archive prerequisite (`C-AI-004-4`). | Add Class B note: V0.2 ship scope includes the slippage formula implementation as a Layer 2 utility module (likely `backend/replay_slippage_model.py` or method on Layer 2 engine), with explicit dependency declaration on `vix_z` / `spread_z` producers (resolved by `C-AI-010-3`) and `half_spread_estimate` source (bilateral with `C-AI-004-4`). |
| B7 | Spec §7 lines 442–454 (halt-day blocked-cycle row creation) | "On halt activation: Continue rules-engine candidate computation (without execution). Create row in `trade_counterfactual_cases`: `case_type = 'counterfactual'`, `counterfactual_reason = 'halt_block'`, ..." | No halt-cycle row creation at HEAD. `risk_engine.py:234–235` (3-loss reduction) and `prediction_engine.py:688–691` (5-loss session halt) are the halt-trigger sites — neither writes counterfactual rows. **Cross-spec coordination with AI-SPEC-001 `B-AI-001-7` D-022 split.** | Add Class B note: V0.2 ship scope includes wiring at both halt-trigger sites (`risk_engine.py` AND `prediction_engine.py`) to insert `trade_counterfactual_cases` rows with `simulation_status = 'pending_eod_label'`. EOD job picks them up next run. Bilateral coordination with Item 1 V0.1 ship (`B-AI-001-7` D-022 enforcement). |
| B8 | Spec §2 lines 128–138 (Versioned Width Table) | "`width_table_version`, `vix_bucket`, `strategy_type`, `time_bucket`, `default_short_delta`, `default_long_delta`, `default_width`" — versioned table format proposed. | Hardcoded `_DEFAULT_SPREAD_WIDTH = 5.0` at `counterfactual_engine.py:55`. No externalized width table at HEAD. | Add Class B note: V0.2 ship scope externalizes the width table as either (a) a new `vix_spread_width_table` Supabase table with operator-controlled writes; OR (b) a YAML config file checked into `backend/config/`. Default position: option (a) with versioned rows, enabling reproduction of historical Tier 2 simulations after table calibration. |
| B9 | Spec §0 + §11 (Layer 2 vs Layer 1 routing) | Spec is silent on whether Layer 2 needs its own feature flag for canary-style rollout. | At HEAD, `feedback:counterfactual:enabled` (single flag) gates the entire Layer 1 EOD job. | Add Class B note: V0.2 ship scope adds **`feedback:counterfactual:layer2:enabled`** (Redis key, fail-closed DISABLED initially per Phase 0 conservative-first principle) to gate Layer 2 EOD job independently of Layer 1. Allows operator to run Layer 1 + Layer 2 in parallel during validation, then disable Layer 1 once Layer 2 graduates. Reuses `set-feature-flag` Edge Function pattern. |
| B10 | Spec §4 line 209–210 vs AI-SPEC-002 Spec §2 (counterfactual_reason vs decision_outcome enum) | Item 10's `counterfactual_reason` enum (6 values): `no_trade | governor_block | meta_skip | adversarial_block | halt_block | alternative_strategy`. Item 2's `decision_outcome` enum (8 values, see AI-SPEC-002 audit): different vocabulary. | The two enums share concepts (`blocked_governor` ↔ `governor_block`; `halted_blocked_cycle` ↔ `halt_block`) but are not byte-identical. | Add Class B note: Spec §4 line 209–210 must clarify whether `counterfactual_reason` and `decision_outcome` are **independent vocabularies** (Item 2 = decision-side; Item 10 = counterfactual-reason-side) or **mapped 1:1**. Default position: independent vocabularies with documented mapping table — Item 10 V0.2 ship includes a `counterfactual_reason ↔ decision_outcome` mapping function in the Layer 2 engine, exposed for cross-spec consumers. Folds into D-023 wording (decision-outcome enum coordination). |
| B11 | Migration `20260421_add_counterfactual_pnl.sql:4–5` ('Pure observability — never read by any trading-decision path.') vs Spec §0 line 8 ("Calibration-grade attribution data feeding Items 5-9") | Layer 1 migration header asserts observability-only contract; Layer 2 promotes data flow into training. Governance contract change. | At HEAD, the migration header is the canonical statement of Layer 1's contract; Spec §0 implicitly changes the contract for Layer 2. | Add Class B note: V0.2 ship scope includes governance update — `system-state.md` adds `counterfactual_engine` field tracking `{ layer_1_phase: 'shipped', layer_2_phase: 'not_started | v0.2_scaffolding | v0.2_active | demoted', calibration_eligible_classifier_active: bool, chain_archive_capable: bool }`. The Layer 1 migration header stays as-is (preserves observability contract); Layer 2's new `trade_counterfactual_cases` migration header explicitly declares "Calibration-grade — read by training accessors per Spec §6; advisory authority only — never gates trade execution." |

### 10.3 Class C — Architectural Intent Corrections

Operator-only authority. Default: reject unless clear reason. Resolution requires NEW D-XXX or spec revision to comply with existing D-XXX.

| # | Spec Section | Issue | Conflicting D-XXX or Rule | Resolution Required |
|---|--------------|-------|--------------------------|---------------------|
| C1 | Spec §0 line 14 ("Do not rewrite the current `counterfactual_engine.py`") + Spec §3 lines 174–186 (replace default-to-iron_condor fallback) | Internal contradiction: spec simultaneously forbids rewriting Layer 1 AND requires changing Layer 1's `_simulate_pnl()` default-strategy fallback. The change is small (return NULL when `strategy_hint` missing) but the architectural commitment is explicit. | T-Rule 2 (Governance Documents Are Authoritative) — spec consistency; T-Rule 4 (Locked Decisions Are Final) — once spec is integrated, the cutover policy must be unambiguous | Operator decision required between two options: (option 1) **Treat the Spec §3 change as a "small surgical bug fix" not a rewrite** — Layer 1 is modified in-place via a tiny PR (replace line 219 hardcoded `iron_condor` with NULL-return path when `strategy_hint` missing); existing tests updated to cover NULL path. Spec §0 "do not rewrite" wording is preserved as architectural commitment against full rewrite, not against bug fixes. Lowest-cost. (option 2) **Freeze Layer 1 entirely; the Spec §3 fix lives ONLY in Layer 2's new engine** — Layer 1 continues hardcoded `iron_condor` fallback indefinitely (with operator-known contamination risk for Layer 1 outputs); Layer 2 ships the corrected logic; downstream consumers MUST consume Layer 2 outputs only. Higher-cost (Layer 2 must ship before any consumer trains on counterfactual data). **Default position (per consolidated plan §5 conservative-first principle):** option 1 (surgical bug fix to Layer 1 with documentation update). Folds into Spec §0 wording amendment in Phase 2. |
| C2 | Spec §0 line 5 (Tier "V0.2 immediate / V0.2 strategy-specific / V0.3 adversarial / V0.4 exit") vs `CROSS_CUTTING_EVIDENCE_MATRIX.md` §1 line 52 (Tier "V0.1") | Cluster / tier classification discrepancy. Matrix marks V0.1; spec marks V0.2-V0.4 graduated. Affects Cluster A audit completeness assessment (does P1.3.4 close Cluster A if Item 10 is partially V0.1 already-shipped?). | T-Rule 2 — governance documents must align; matrix is downstream of spec but should be amendable when spec lock formalizes the tier | Operator decision: ratify the layered framing — **V0.1 = Layer 1 (already shipped at commit `2400e98`); V0.2 onward = Layer 2 (proposed in this spec).** Cluster A is correct because Items 5 / 6 / 9 (Cluster B) cannot promote to binding without Item 10 V0.2 outputs; Cluster A audit is therefore complete after P1.3.4 with the understanding that "Cluster A complete" means "all four Cluster A specs audited" — not "all V0.1 work done" (Layer 2 V0.2 ships in Phase 4 alongside Cluster B). Matrix §1 line 52 amended in Phase 2 to show graduated tier. **No new D-XXX required.** |
| C3 | Spec §5 lines 363–376 (`vix_z`, `spread_z` z-score producer authority) | Slippage formula references `vix_z` / `spread_z` without defining producer authority. No `vix_z` / `spread_z` Redis key at HEAD; closest existing surfaces: `polygon:vix:current` + `tradier_feed.py` quote logic. Z-score calculation is bilateral with AI-SPEC-001 (Card features include vix_z) and AI-SPEC-005 (Vol Fair-Value Engine). | T-Rule 2 — governance ownership of cross-spec data producers must be unambiguous; cross-spec coordination with D-023 | Operator decision: assign z-score producer authority to one of three options: (option 1) **AI-SPEC-001 owns z-score producers** as part of Card feature engineering; AI-SPEC-005 + AI-SPEC-010 + Item 7 read from Item 1's namespace. Concentrates Card feature ownership. (option 2) **AI-SPEC-005 owns z-score producers** as part of Vol Fair-Value Engine's volatility surface; Items 1, 7, 10 read. Concentrates volatility ownership. (option 3) **Shared producer with explicit Redis namespace** (e.g., `features:vix_z`, `features:spread_z`) owned by the calibration_engine per D-019; consumers read via stable interface. Most decoupled. **Default position (per consolidated plan §5 conservative-first principle):** option 3 (shared producer in stable namespace). Resolves bilateral concerns; encoded in D-023 wording alongside other cross-spec data producer ownership. |
| C4 | Spec §4 line 202 (`case_type` enum includes `synthetic`) + Spec §10 lines 502–522 (synthetic case generation) vs AI-SPEC-003 Synthetic Counterfactual (Cluster C, V0.4) | Item 10 owns the table `trade_counterfactual_cases` that stores synthetic cases (per Spec §4 line 202: `case_type TEXT -- actual | counterfactual | synthetic`). But Item 3 (AI-SPEC-003) is the canonical owner of synthetic case **generation**. Spec §10 mentions synthetic generation procedure but defers to Item 6 / Item 3 ownership. **Unresolved:** does Item 3 INSERT into Item 10's table, or does Item 3 own a separate `synthetic_counterfactual_cases` table? | T-Rule 2 — cross-spec architectural ownership must be unambiguous; consolidated plan §5 conservative-first principle (re-use existing surfaces) | Operator decision between two options: (option 1) **Item 3 generates synthetic cases that INSERT into Item 10's `trade_counterfactual_cases` table with `case_type = 'synthetic'`, `case_weight = 0.2`** — Item 3 is downstream consumer-of-storage, not separate-table-owner. Item 3 retains ownership of the generation algorithm + provenance flags. Single canonical table for all case types; Items 5-9 read uniform data. Lowest-cost. (option 2) **Item 3 owns separate `synthetic_counterfactual_cases` table** mirroring `trade_counterfactual_cases` schema; Items 5-9 read via UNION across both. Cleaner separation of provenance but duplicated infrastructure. **Default position (per consolidated plan §5 conservative-first principle):** option 1 (Item 3 INSERTs into Item 10's table). Encoded in Item 3 P1.3.X audit (Cluster C — future). **No new D-XXX required.** |
| C5 | Spec §6 lines 423–432 (Old Rows Lockdown — `<Commit_4_deploy_date>` cutover anchor) | Lockdown migration uses `<Commit_4_deploy_date>` as cutover for legacy-observability lockdown of pre-Layer-2 rows. "Commit 4" refers to the IC/IB target_credit fix sequence's 4th commit (re-mark + NULL slippage cleanup) — **not yet shipped at HEAD** (planned for Tuesday 2026-04-28 per pre-AI track addendum A1). Anchor is a moving target until Commit 4 ships. | T-Rule 4 (Locked Decisions Are Final) — once spec is integrated, the cutover anchor must be unambiguous; T-Rule 5 (Capital Preservation) — contaminated calibration data must be reliably excluded | Operator decision required: lock the cutover anchor to one of three options: (option 1) **Concrete commit hash** — once Commit 4 of the IC/IB sequence ships, replace `<Commit_4_deploy_date>` with the actual deploy timestamp (e.g., `2026-04-28T16:00:00-04:00`). Layer 1 backfill runs on that date. Most explicit. (option 2) **Date-of-Layer-2-deployment anchor** — cutover = Layer 2 first-deploy date (whatever that is); Layer 1 rows before that timestamp marked legacy_observability_only regardless of Commit 4 status. Decouples Item 10 V0.2 from IC/IB sequence. (option 3) **Per-row classifier** — instead of a date cutover, evaluate each Layer 1 row at backfill time: if `strategy_hint` missing OR `simulation_status` missing OR Commit-4-touched-the-trade-period, mark legacy_observability_only. Most rigorous; highest-cost. **Default position (per consolidated plan §5 conservative-first principle):** option 1 (concrete commit hash post-Commit-4 ship). Lowest-cost; preserves operator-explicit governance. **Folds into existing D-023 wording (Layer 1/Layer 2 cutover policy) — no new D-XXX strictly required.** |

---

## 11. Governance Updates Required

What governance documents must change for this spec to integrate cleanly. List all that apply:

- [ ] **`approved-decisions.md` — D-023 enrichment** (proposed in AI-SPEC-001 §11; addended by AI-SPEC-002 §11 + AI-SPEC-004 §11; Item 10 audit adds further enrichment). D-023 wording must additionally encode:
  - **(g) Layer 1/Layer 2 cutover policy for `trade_counterfactual_cases`** — Layer 1 (existing 3-column triple on `trading_prediction_outputs`) is `legacy_observability_only` after `<Commit_4_deploy_date>` (or operator-locked anchor per `C-AI-010-5`); Layer 2 (new `trade_counterfactual_cases` table) is the canonical calibration-grade surface for Items 5–9 training accessors.
  - **(h) `calibration_eligible` API enforcement contract** — accessor functions `get_meta_labeler_training_data` / `get_vol_engine_replay_cases` / `get_adversarial_block_outcomes` / `get_exit_optimizer_training_paths` MUST filter `calibration_eligible = true` at function-signature layer; `diagnostic_opt_in = true` requires explicit logging + monitoring warning.
  - **(i) Item 10 V0.2 Layer 2 advisory authority** — Layer 2 outputs are training inputs only; never gate trade execution. Layer 2's `counterfactual_pnl_after_slippage` is the canonical training-grade label; `simulated_pnl_gross` is audit-only.
  - **(j) `counterfactual_reason ↔ decision_outcome` enum mapping** — Item 10's `counterfactual_reason` (6 values) is independent of Item 2's `decision_outcome` (8 values); D-023 references the canonical mapping function that lives in Layer 2's engine module.
- [ ] **`approved-decisions.md` — possible new D-XXX for slippage z-score producer authority** (AI-SPEC-010 §11, conditional on `C-AI-010-3` resolution). If operator chooses option 3 (shared producer in `features:*` namespace), a new D-XXX may be warranted to formalize the cross-spec data-producer ownership. **Default: option 3 — folds into D-023 wording, no new D-XXX needed.**
- [ ] **`approved-decisions.md` — no other D-XXX modifications required by AI-SPEC-010 standalone.** Spec defers cleanly to D-005, D-010, D-011, D-013, D-022 without amendment. Item 10 is data infrastructure with advisory authority; respects all 10 T-Rules.
- [ ] **`MASTER_PLAN.md` — new phase entry: Phase 3D (or equivalent) — Counterfactual P&L V0.2 Layer 2** (AI-SPEC-010 §11). Per Spec §11 V0.2 ship-scope: **3–6 weeks for V0.2 immediate** (data integrity fixes — items 1–8 of Spec §11) + **8–12 weeks for V0.2 strategy-specific** (items 9–15 of Spec §11). 12 build items decomposed at `AI-SPEC-010.md` §12.2. Sequencing: Phase 3D ships AFTER Phase 3A (Item 1) + Phase 3B (Item 2) schema-landing milestones (so Items 1 + 2 can read Item 10's V0.2 surface) AND parallel-track with Phase 3C (Item 4) chain-archive substrate (bilateral with `C-AI-004-4`). V0.3 + V0.4 graduations sequenced after Phase 3D V0.2 active.
- [ ] **`TASK_REGISTER.md` — new section: §14D — Counterfactual P&L V0.2 Layer 2 implementation** (AI-SPEC-010 §11). Sub-items per `AI-SPEC-010.md` §12.2 (14D.0 schema bootstrap — 4 new tables + 3 new columns + lockdown migration; 14D.1 Layer 2 engine module `backend/counterfactual_engine_v2.py` with strategy-specific simulators; 14D.2 small surgical fix to Layer 1 `counterfactual_engine.py:213–223` per `C-AI-010-1` option 1; 14D.3 slippage formula implementation with `vix_z` / `spread_z` consumer wiring per `C-AI-010-3`; 14D.4 4 API enforcement accessor functions with `calibration_eligible = true` structural filter; 14D.5 halt-day blocked-cycle row creation at `risk_engine.py` + `prediction_engine.py` halt-trigger sites; 14D.6 versioned width table — table or YAML; 14D.7 EOD job orchestration extension — Layer 2 EOD job runs alongside Layer 1; 14D.8 `feedback:counterfactual:layer2:enabled` Redis flag with fail-closed DISABLED default; 14D.9 `useActivationStatus.ts` extension for `shippedDate` + `shippedCommit` fields; 14D.10 cutover migration to lock legacy Layer 1 rows; 14D.11 tests covering Layer 1 NULL-fallback, Layer 2 strategy-specific simulators, halt-day blocked-cycle row creation, API accessor `calibration_eligible` filtering; 14D.12 deprecate Layer 1 weekly summary OR run Layer 1 + Layer 2 weekly summaries in parallel during transition).
- [ ] **`system-state.md` — operational state addition: `counterfactual_engine` field** (AI-SPEC-010 §11). Tracks `{ layer_1_phase: 'shipped', layer_2_phase: 'not_started | v0.2_scaffolding | v0.2_active | demoted', last_eod_run_at: timestamp | null, last_eod_run_status: 'success' | 'partial' | 'failed' | null, calibration_eligible_classifier_active: bool, chain_archive_capable: bool, layer_1_legacy_observability_only_lockdown_date: timestamp | null }`. Tracks Layer 2 progression per Spec §11 + governance contract change (Layer 1 stays observability-only; Layer 2 is calibration-grade with advisory authority).
- [ ] **`system-state.md` — operational state addition: cross-reference with `replay_harness.chain_archive_status` field** (AI-SPEC-004 §11). Item 10 V0.2 Layer 2 reads chain-archive substrate for after-slippage P&L; tracks bilateral resolution with Item 4 `C-AI-004-4` via the existing `replay_harness.chain_archive_status` field (no separate field needed for Item 10).
- [ ] **`constitution.md` — pointer note only — no rule change** (AI-SPEC-010 §11). If D-023 is enriched per items (g)–(j) above, T-Rule 4 needs a one-line note that D-023 is the explicit AI-authority-boundary record covering Item 10 Layer 1/Layer 2 cutover, `calibration_eligible` API enforcement, advisory authority for Layer 2 outputs, and counterfactual_reason / decision_outcome enum coordination. T-Rule 5 / T-Rule 6 / T-Rule 9 already cover D-005 / D-010 / D-011 / D-013 non-overridability; Layer 2 advisory authority respects all three (Layer 2 outputs feed training, never gate execution). T-Rule 10 (Silent Failures Are Forbidden) already aligned — Layer 2 engine maintains Layer 1's fail-open per-row try/except + structured error logging + health-status writes pattern.

---

## 12. TASK_REGISTER Implications

What concrete tasks does P1.3 audit imply for downstream work?

### 12.1 Pre-implementation tasks (must complete before P1.3 audit can close)

- Operator decision on `C-AI-010-1` (Layer 1 surgical-fix vs Layer-1-frozen)
- Operator decision on `C-AI-010-2` (graduated tier classification — matrix amendment)
- Operator decision on `C-AI-010-3` (slippage z-score producer authority)
- Operator decision on `C-AI-010-4` (Item 3 / Item 10 boundary for synthetic case storage)
- Operator decision on `C-AI-010-5` (Layer 1 lockdown cutover anchor)
- D-023 wording approved with items (g)–(j) above (encoded in same operator review batch as AI-SPEC-001 / AI-SPEC-002 / AI-SPEC-004 dispositions)
- Cross-spec confirmation that `C-AI-002-2` resolution (option 1 — new table) is operator-ratified; if so, register §4 (Resolved Findings) gets the `C-AI-002-2` row moved by P1.3.4 commit
- Cross-spec confirmation that AI-SPEC-002 P1.3.2 default position on `B-AI-002-2` (`closed_trade_path_metrics` substrate gap) is updated to "resolved by AI-SPEC-010 spec §4 — Item 10 owns the substrate"

### 12.2 Implementation tasks (Cursor work after Phase 4 doc integration)

- **14D.0** — Schema bootstrap: 4 migrations (`trade_counterfactual_cases`, `strategy_utility_labels`, `closed_trade_path_metrics`, optional `position_path_samples`) + 1 ALTER TABLE migration on `trading_prediction_outputs` for `strategy_hint` / `strategy_structure` / `candidate_source` columns + 1 lockdown migration applying `label_quality = 'legacy_observability_only'` to Layer 1 rows pre-`<C-AI-010-5-anchor>`.
- **14D.1** — Layer 2 engine module `backend/counterfactual_engine_v2.py` with strategy-specific simulators. Architecture: per-strategy `simulate_iron_condor()`, `simulate_iron_butterfly()`, `simulate_put_credit_spread()`, `simulate_call_credit_spread()`, `simulate_long_straddle()`, `simulate_debit_call_spread()`, `simulate_debit_put_spread()` (canonical naming per cross-spec theme). Reuses Layer 1's `_fetch_spx_price_after_signal` infrastructure for market path; uses `strategy_structure` JSONB for actual strikes (Tier 1 calibration-grade) or VIX_SPREAD_WIDTH_TABLE defaults (Tier 2 approximate) or NULL (Tier 3 insufficient_strategy_context).
- **14D.2** — Small surgical fix to Layer 1 `counterfactual_engine.py:213–223` per `C-AI-010-1` option 1: replace `strategy = "iron_condor"` fallback with NULL-return path + `simulation_status = "insufficient_strategy_context"` write. Update existing tests; preserve Layer 1's "DO NOT REWRITE" architectural commitment by treating this as a bug fix.
- **14D.3** — Slippage formula implementation in Layer 2 module with `vix_z` / `spread_z` consumer wiring per `C-AI-010-3` (option 3 — shared `features:*` namespace producer). `base_strategy_slippage * time_multiplier * vol_multiplier * spread_multiplier * size_multiplier` with cap at `3.0 * normal_strategy_slippage`. Bilateral with `C-AI-004-4` chain-archive substrate for `half_spread_estimate`.
- **14D.4** — 4 API enforcement accessor functions in Layer 2 module: `get_meta_labeler_training_data()`, `get_vol_engine_replay_cases()`, `get_adversarial_block_outcomes()`, `get_exit_optimizer_training_paths()`. Each filters `calibration_eligible = true` structurally; `diagnostic_opt_in = true` parameter requires explicit audit logging.
- **14D.5** — Halt-day blocked-cycle row creation: hooks at `risk_engine.py:234–235` (3-loss reduction) and `prediction_engine.py:688–691` (5-loss session halt) — both halt-trigger sites INSERT `trade_counterfactual_cases` row with `simulation_status = 'pending_eod_label'`. Bilateral coordination with AI-SPEC-001 V0.1 ship (`B-AI-001-7` D-022 enforcement).
- **14D.6** — Versioned width table — recommended canonical: new `vix_spread_width_table` Supabase table with `width_table_version` / `vix_bucket` / `strategy_type` / `time_bucket` / `default_short_delta` / `default_long_delta` / `default_width` columns. Operator-controlled writes; Layer 2 reads at simulation time with version captured on each `trade_counterfactual_cases` row.
- **14D.7** — EOD job orchestration extension: Layer 2 EOD job runs alongside Layer 1 EOD job. Both gated by `feedback:counterfactual:enabled`; Layer 2 additionally gated by `feedback:counterfactual:layer2:enabled`. Schedule: Layer 1 at 16:25 ET (existing); Layer 2 at 16:30 ET (new, 5 min after Layer 1 to avoid contention). Wired in `backend/main.py` alongside existing `run_counterfactual_job_wrapper`.
- **14D.8** — `feedback:counterfactual:layer2:enabled` Redis flag with fail-closed DISABLED default per Phase 0 conservative-first principle. Reuses `set-feature-flag` Edge Function pattern.
- **14D.9** — `useActivationStatus.ts` extension: extend `ActivationFlag` interface with `shippedDate?: string` + `shippedCommit?: string`; add values for Counterfactual Tracking entry (`shippedDate: '2026-04-20'`, `shippedCommit: '2400e98'`). Apply same fields to other `builtStatus: 'live'` entries for consistency.
- **14D.10** — Cutover migration applying `label_quality = 'legacy_observability_only'` to Layer 1 rows before the `C-AI-010-5`-locked anchor; migration runs once, idempotent.
- **14D.11** — Tests covering Layer 1 NULL-fallback, Layer 2 strategy-specific simulators, halt-day blocked-cycle row creation, API accessor `calibration_eligible` filtering, slippage formula correctness, versioned width table consumption.
- **14D.12** — Deprecate Layer 1 weekly summary OR run Layer 1 + Layer 2 weekly summaries in parallel during transition; operator decision at V0.2 ship time. Default: parallel summaries with explicit "Layer 1 (legacy)" / "Layer 2 (calibration-grade)" headers.

### 12.3 Calibration / Data dependencies

- `trade_counterfactual_cases` populated with sufficient `case_type = 'actual' | 'counterfactual'` rows (synthetic deferred to `C-AI-010-4` resolution) — minimum operator-set threshold (e.g., 90 sessions per Spec §6 sample-size tiers, mirroring Item 4)
- `closed_trade_path_metrics` populated for executed trades back to operator-set lookback (minimum 30 days per Spec §11 V0.2 immediate item 7)
- `vix_spread_width_table` initial calibration from real trade data (`width_table_version = 1` populated; operator-controlled bumps thereafter)
- `features:vix_z` / `features:spread_z` producer ships (per `C-AI-010-3` option 3)
- Chain-archive substrate matures (bilateral with `C-AI-004-4`); without it, Layer 2's after-slippage P&L is approximate (Tier 2 only)
- Layer 1 cutover anchor locked (per `C-AI-010-5` option 1 — Commit 4 deploy date)

---

## 13. Recommended Status

Pick exactly one. (One of these checkboxes must be checked.)

- [ ] **spec_accurate_repo_missing** — Spec is correct as written; nothing exists in repo yet; ready for clean buildout.
- [ ] **spec_accurate_repo_partial** — Spec is correct; partial scaffold exists (cite); spec describes the full target.
- [ ] **spec_needs_factual_correction_only** — Spec has Class A errors only; intent is sound; mechanical fixes will land in Phase 2.
- [x] **spec_has_semantic_drift_from_locked_intent** — Spec has Class B corrections that change implementation meaning but not architectural goal. Phase 2 corrections + operator approval.
- [ ] **spec_conflicts_with_existing_governance** — Spec contains Class C item(s) requiring new D-XXX or revision before integration.
- [ ] **spec_should_be_split_into_separate_proposal** — Spec scope is too broad and should be decomposed before integration. Operator decision.

**Rationale for `spec_has_semantic_drift_from_locked_intent`:** Item 10's spec is architecturally sound (the layered Layer 1 / Layer 2 framing resolves the table-vs-column carry-forward authoritatively in favor of a NEW table; the `wrong labels are worse than missing labels` principle is consistent with the rest of the AI architecture; the `calibration_eligible` structural enforcement matches AI-SPEC-002 producer model). However, **two correctable drifts** prevent `spec_accurate_repo_partial`: (1) Class A line/test count drift (349→406 / 9→11) means the spec's "What Already Exists" inventory is stale by 5 days at lock time; (2) Class B Layer 2 module location is unspecified, leaving implementation contract ambiguous. Class C items are operator-disposition (5 items), not blocking architectural conflicts — `C-AI-010-1` (surgical-fix vs frozen-Layer-1) is internal-spec consistency; `C-AI-010-2` (matrix amendment) is downstream-doc; `C-AI-010-3` / `C-AI-010-4` / `C-AI-010-5` are cross-spec ownership clarifications, not new D-XXX requirements. Same status as AI-SPEC-004 (medium drift, multiple Class B + C, none architecturally blocking) — not as severe as `spec_blocking`.

---

## 14. Sign-Off

| Auditor | Sign-off Status | Date | Notes |
|---------|----------------|------|-------|
| Primary (Cursor) | **approved (first pass)** | 2026-04-26 | §1, §3, §4, §10.1 fully populated from repo evidence at HEAD `1237746`. §2, §5–§13 first-pass drafts for Claude / GPT review. **Cluster A audit complete after this redline merges.** |
| Cross-check (Claude) | pending | — | Review §7, §8 cross-spec implications; verify table-vs-column resolution logic; verify five Class C escalations correctly classified. |
| Validator (GPT-5.5 Pro) | pending | — | Validate §2 Spec Intent Summary; review §10.3 Class C escalations + D-023 enrichment proposals; cross-check Layer 1 / Layer 2 architectural commitment is coherent across spec §0 and §3. |
| Operator | pending | — | Final approval at audit close; Cluster A operator checkpoint triggers after this redline merges. |

If all four sign-offs are "approved", the redline is closed and the spec moves to Phase 2 correction application.

---

## Update Log

| Date | Author | Action |
|------|--------|--------|
| 2026-04-26 | Cursor (P1.3.4) | Initial redline created. §1, §3, §4, §10.1 populated from repo evidence at HEAD `1237746`. §2, §5–§13 first-pass drafts. AUDIT_FINDINGS_REGISTER.md updated in same commit (Class C / B / A entries; theme updates including `C-AI-002-2` resolution moving to register §4; `closed_trade_path_metrics` substrate gap theme resolution; `counterfactual_pnl` column-not-table theme resolution; `counterfactual_engine` field for system-state.md; D-023 enrichment items (g)–(j); Phase 3D + §14D additions). **Cluster A audit complete.** |

---

## Redline File Location

`trading-docs/08-planning/ai-architecture-audits/AI-SPEC-010.md`
