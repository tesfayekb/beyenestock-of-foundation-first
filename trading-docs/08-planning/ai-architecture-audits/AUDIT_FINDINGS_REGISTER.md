# AI Architecture Audit Findings Register

> **Purpose:** Single source of truth for all findings across Phase 1 audits (P1.3.1 through P1.3.13) and Phase 0/1 governance work.
>
> **Status:** Living document. Updated after each per-item audit merges to main.
>
> **Created:** 2026-04-26 (Phase 1 P1.3.1b of `CONSOLIDATED_PLAN_v1.2_APPROVED.md`)
> **Last updated:** 2026-04-26
> **Last updated by:** P1.3.1b (initial creation, populated from PR #60 / AI-SPEC-001 audit)
> **Repo HEAD at creation time:** `f456922cdafcf0f99b757958dab0309aa9d08248` (P1.3.1 merged).

---

## How To Use This Register

- **Operator:** read this when making batch governance decisions, when assessing Gate 1 readiness, or when deciding which findings to prioritize for Phase 2 corrections. The register is the one-glance view of "what's open, what's resolved, and what crosses multiple specs"; the per-item redlines (`AI-SPEC-001.md`, `AI-SPEC-002.md`, …) remain the per-spec source of truth for the full evidence chain behind each entry.
- **Future audit Cursors (P1.3.2 through P1.3.13):** **APPEND** new findings from your per-item audit to the appropriate sections below. Do **NOT** modify entries from prior audits unless the audit explicitly resolves a prior finding (in which case **move** the row to §4 "Resolved Findings" with date + resolution note + reference to the resolving audit). Increment the `Update Log` with a new row each time you append.
- **Claude (cross-check) and GPT (validator):** consult this register during cross-spec review to identify themes and contradictions. If a per-item audit's §7.2 (cross-spec contradictions) or §8 (carry-forward findings) surfaces a theme that is already in §5 here, link the new audit's spec ID into that theme's "Affected Specs" cell rather than creating a duplicate row.

> **Update mandate:** Each subsequent per-item audit (P1.3.2 → P1.3.13) MUST update this register as part of its workflow. The audit redline file is the per-spec evidence; this register is the cross-spec roll-up. PRs that produce a per-item redline without updating this register will be returned for completion before merge.

> **ID convention:** Open findings use `<class>-<spec-id>-<n>` (e.g., `C-AI-001-1` = Class C, AI-SPEC-001, item 1; `B-AI-002-3` = Class B, AI-SPEC-002, item 3). Class A items roll up by spec rather than per-item to avoid noise (Class A is mechanical and batch-cleared at Gate 1). Pre-audit findings (Phase 0 / Phase 1 infrastructure work) use the `PRE-P{phase}-N` prefix and live in §0 below.

---

## 0. Pre-Audit Findings (Phase 0 / Phase 1 Infrastructure)

These findings emerged during Phase 0 governance setup and Phase 1 audit infrastructure work (P1.1 evidence pack, P1.2 cross-cutting matrix, P1.3.0 audit template, P1.3.0b raw spec archive). They are NOT per-item audit findings — they predate the per-item audits — but they are real findings that affect the audit and integration work and must be tracked alongside per-item findings so that the register's stated purpose ("single source of truth for ALL findings") holds.

Findings are categorized by source phase. Each finding has an ID prefix indicating origin:

- **PRE-P0-N** — Phase 0 governance setup
- **PRE-P11-N** — P1.1 evidence pack
- **PRE-P12-N** — P1.2 cross-cutting matrix
- **PRE-P130-N** — P1.3.0 audit template
- **PRE-P130B-N** — P1.3.0b raw spec archive

### 0.1 Phase 0 Findings (PRs #54, #55)

| ID | Source PR / File | Finding | Status | Resolution Path |
|----|------------------|---------|--------|------------------|
| PRE-P0-1 | PR #54 / `feature-proposals.md` lines 26, 84 | `master-plan.md` literal references should be `MASTER_PLAN.md` (case mismatch on case-sensitive filesystems). Verified at HEAD: line 26 contains "MUST be added to `master-plan.md` before implementation begins"; line 84 contains "Reference to PLAN-XXX-NNN in master-plan.md". | open — deferred | Phase 4 (when `feature-proposals.md` is opened to add FP-001 entry); operator approved deferral 2026-04-26 |
| PRE-P0-2 | PR #55 / `.cursorrules` + `.lovable/rules.md` | Pre-existing structural divergence: `## PHASE GATE VERIFICATION PROTOCOL (MANDATORY)` is at `.cursorrules` line 264 vs `.lovable/rules.md` line 136. Pre-existing, NOT introduced by P0.2. (Cross-listed in evidence pack §9.5.) | open — pre-existing debt | Separate parity audit task (out of scope for current Phase 1 plan) |
| PRE-P0-3 | PR #55 / `.cursorrules` + `.lovable/rules.md` | Section naming drift: `.cursorrules` line 123 says "REFERENCE INDEX MAINTENANCE"; `.lovable/rules.md` line 123 says "REFERENCE INDEX MAINTENANCE AND RECONCILIATION". (Cross-listed in evidence pack §9.5.) | open — pre-existing debt | Same parity audit task as PRE-P0-2 |
| PRE-P0-4 | PR #55 + PR #58 / `.cursorrules` line 36 | `.cursorrules` line 36 references "11 rules" but `constitution.md` defines exactly 10 T-Rules (T-Rule 1 Foundation Isolation through T-Rule 10 Silent Failures Are Forbidden). Verified at HEAD by `grep -nE '^### T-Rule [0-9]+' trading-docs/00-governance/constitution.md`. | open — pre-existing debt | Phase 5 cleanup |

### 0.2 P1.1 Evidence Pack Findings (PR #56)

| ID | Source Section | Finding | Status | Resolution Path |
|----|----------------|---------|--------|------------------|
| PRE-P11-1 | Evidence pack §9.1 | `trading-docs/00-governance/change-control-policy.md` missing — referenced by `.cursorrules`, `.lovable/rules.md`, and `feature-proposals.md` but file does not exist at HEAD. | open — pre-existing governance debt | Separate cleanup task per consolidated plan §1; will affect subsequent audit §11 governance update entries |
| PRE-P11-2 | Evidence pack §9.2 | Reference indexes missing in `trading-docs/07-reference/`: `function-index.md`, `event-index.md`, `config-index.md`, `env-var-index.md` (all four absent at HEAD per evidence pack §9.2 lines 507–512). | open — pre-existing governance debt | Separate cleanup task per consolidated plan §1; SPEC VERIFICATION PROTOCOL operates without these indexes |
| PRE-P11-3 | Evidence pack §9.4 | `_RISK_PCT` ladder non-monotonic at HEAD: Phase 1 (0.010) > Phase 2 (0.0075). Re-introduced by 2026-04-20 width widening (different mechanism than B1-1 originally addressed). Already cross-referenced as cross-spec theme in §5 of this register. | open — pre-existing governance debt | Separate task before Day 40 of paper trading; explicitly not fixed by AI-SPEC-012 (Item 12 sizing) |
| PRE-P11-4 | Evidence pack §9.6 (newly discovered) | `counterfactual_pnl` is 3 columns on `trading_prediction_outputs`, NOT a separate table. The migration filename `20260421_add_counterfactual_pnl.sql` is correct, but the artifact is `ALTER TABLE ... ADD COLUMN`. P1.2 / P1.3 audits must treat as columns, not as a table. | open — newly discovered during P1.1 | Phase 2 corrections to AI-SPEC-010, AI-SPEC-012; flagged in matrix carry-forward #5 |
| PRE-P11-5 | Evidence pack §10.3.3 line 687 | `gex:atm_iv` consumer-only orphan: sole consumer at `backend_agents/macro_agent.py:214`, no producer in any production code. Already cross-referenced as matrix carry-forward #2 and tracked in §5 of this register. | open — pre-existing operational risk | Resolution path: per-spec audits for AI-SPEC-001, AI-SPEC-005 will document; eventual fix wires producer in `gex_engine.py` after recompute |
| PRE-P11-6 | Evidence pack §10.3.3 line 688 | `gex:updated_at` consumer-only orphan: referenced as `age_key` in `_safe_redis()` docstring example at `prediction_engine.py:123` (inside docstring, not an actual call site). Already cross-referenced as matrix carry-forward #1. **Mechanism note:** evidence pack §10.3.3 originally framed this as "fail-open fallthrough"; matrix v1.1 corrected the mechanism to "the gate function is dead code". The conclusion (no effective freshness gate) is unchanged. | open — pre-existing operational risk | Resolution path: AI-SPEC-005 / AI-SPEC-013 audits will document; eventual fix wires both `_safe_redis()` caller AND producer |
| PRE-P11-7 | Evidence pack §10.3.1 (lines 670–675) | `strategy:bull_debit_spread:enabled` and `strategy:bear_debit_spread:enabled` named in `MASTER_PLAN.md` lines 59–60 but NOT present anywhere in code despite Phase 2B (Bull/Bear Debit Spreads) being declared COMPLETE in `MASTER_PLAN.md`. Phase 2B Rule 5 ("New strategies are gated by Redis flags") appears violated. | open — governance debt with naming inconsistency | Resolution path: cross-spec theme already in §5 (strategy-class taxonomy); affects AI-SPEC-007 / AI-SPEC-011 / AI-SPEC-012 audits |

### 0.3 P1.2 Cross-Cutting Matrix Findings (PR #57)

| ID | Source Section | Finding | Status | Resolution Path |
|----|----------------|---------|--------|------------------|
| PRE-P12-1 | Matrix §1 carry-forward #4 (corrected v1.1) | `_safe_redis()` is defined at `prediction_engine.py:100` but never called from outside its own docstring (line 120 inside docstring lines 107–131). Function is dead code at HEAD. GEX freshness gate is non-functional because the gate function is dead code, NOT because `gex:updated_at` lacks a producer. Already tracked in §5 of this register as cross-spec theme. | open — pre-existing operational risk | Resolution path: AI-SPEC-005 / AI-SPEC-013 audits will plan freshness substrate buildout (caller + producer both needed) |
| PRE-P12-2 | Matrix §4 `risk_engine.py` block | 3-spec collision: AI-SPEC-001 + AI-SPEC-012 + AI-SPEC-013 all modify `backend/risk_engine.py`. Module-level merge order proposed: **1 → 13 → 12**. | open — sequencing constraint | Resolution path: hard sequencing rule for P1.3 / Phase 2; the `_RISK_PCT` ladder fix (PRE-P11-3) must land BEFORE Item 12 begins |
| PRE-P12-3 | Matrix §7 dependency graph | Soft sequencing question between AI-SPEC-012 and AI-SPEC-013: Item 12 depends on Item 13 demotion paths; Item 13 promotion may need Item 12 capital framework. | open — soft sequencing | Resolution path: P1.3 Item 12 + Item 13 audits reviewed together; ship Item 13 advisory-only first, Item 12 next, then promote Item 13 |
| PRE-P12-4 | Matrix §1 metadata + §3 corrections | `AI_ARCH_EVIDENCE_PACK.md` §10.2 line 617 + §10.3.3 line 688 carry the same `_safe_redis` mischaracterization that v1.1 corrected in the matrix. Cursor flagged but did not fix (immutable input from P1.1). | open — minor doc inconsistency | Resolution path: future cleanup task; conclusion in evidence pack §10.3.3 is correct, only mechanism description is wrong; defer to separate amendment task |

### 0.4 P1.3.0 Audit Template Findings (PR #58)

| ID | Source | Finding | Status | Resolution Path |
|----|--------|---------|--------|------------------|
| PRE-P130-1 | Cursor risks/follow-up (PR #58) | Constitution rule-count mismatch (`.cursorrules` line 36 says "11 rules" vs `constitution.md`'s 10 T-Rules) — same as PRE-P0-4. Surfaced again during P1.3.0 cross-check. | open — duplicate of PRE-P0-4 | See PRE-P0-4 resolution path |

### 0.5 P1.3.0b Raw Spec Archive Findings (PR #59)

| ID | Source | Finding | Status | Resolution Path |
|----|--------|---------|--------|------------------|
| PRE-P130B-1 | Cursor risks/follow-up (PR #59) | `trading-docs/04-modules/` already existed at branch base with pre-existing `README.md` and `exit-engine.md`. Phase 4 placement of validated module documentation as siblings of new `archive/` directory still works. | informational only — no action | Phase 4 module placement |
| PRE-P130B-2 | Cursor risks/follow-up (PR #59) | Tarball delivered as `.tar` (uncompressed) instead of `.tar.gz` per prompt's anticipated format. `tar -xf` worked transparently; checksums verified clean. | informational only — no action | Future-prompt accuracy improvement if delivery format changes |

### 0.6 Cross-Reference With Sections 1–6

Several Phase 0 / Phase 1 findings ALSO appear elsewhere in the register. The cross-references below are intentional — findings can appear in §0 (origin record) AND §5 (cross-spec theme view) AND §1–§3 (per-audit Class C/B/A entries) — each section serves a different purpose. The register should be read top-to-bottom for discovery, but operator decisions reference whichever section is most actionable.

| Pre-audit ID | Also tracked in | Per-audit ID (where applicable) | Purpose of the cross-reference |
|--------------|-----------------|--------------------------------|-------------------------------|
| PRE-P11-3 (`_RISK_PCT` non-monotonic) | §5 cross-spec themes; §2 Class B | B-AI-001-7 (AI-SPEC-001 §10.2 B7) | §0 records origin in evidence pack §9.4; §5 tracks the multi-spec impact; §2 records Item 1's specific buildout constraint ("must not worsen") |
| PRE-P11-4 (`counterfactual_pnl` columns vs table) | will appear in §2 Class B when AI-SPEC-010 / AI-SPEC-012 audits complete | (TBD by P1.3.10 / P1.3.12) | §0 records origin in evidence pack §9.6; future per-item audits will surface the correction in §2 |
| PRE-P11-5 (`gex:atm_iv` orphan) | §5 cross-spec themes (theme: `_safe_redis()` dead code family); AI-SPEC-001 §8 yes-impact | (referenced by B-AI-001-6 indirectly) | §0 records the consumer-only finding in evidence pack §10.3.3; §5 tracks it as part of the freshness substrate theme |
| PRE-P11-6 (`gex:updated_at` orphan) | §5 cross-spec themes (theme: `_safe_redis()` dead code family); §2 Class B | B-AI-001-6 (AI-SPEC-001 §10.2 B6) | §0 records the consumer-only finding; §2 records Item 1's V0.1-prerequisite buildout (caller + producer) |
| PRE-P11-7 (debit-spread feature flags) | §5 cross-spec themes (strategy-class taxonomy); §3 Class A | A2 within AI-SPEC-001 row of §3 | §0 records origin in MASTER_PLAN lines 59–60 vs `risk_engine.py:105–106`; §3 records the per-spec mechanical correction; §5 tracks the system-wide cleanup |
| PRE-P12-1 (`_safe_redis()` dead code) | §5 cross-spec themes; §2 Class B | B-AI-001-6 (AI-SPEC-001 §10.2 B6) | §0 records origin in matrix §1 carry-forward #4 (v1.1 corrected); §5 tracks it as a multi-spec theme; §2 records Item 1's specific impact |

---

## 1. Open Class C Escalations (Operator Decisions Required)

These items require explicit operator decisions before redline closure. Per `CONSOLIDATED_PLAN_v1.2_APPROVED.md` §3, Class C corrections involve architectural intent and have operator-only authority. Per template `_template.md` §10.3, "Class C corrections block the redline from closing" until the operator decides.

| ID | From | Issue | Conflicting D-XXX or Rule | Default Position | Status |
|----|------|-------|---------------------------|------------------|--------|
| C-AI-001-1 | AI-SPEC-001 §10.3 C1 | `size_multiplier_cap` channel (Spec §7 — paper-binding V0.2 + small-live post-graduation authority for an LLM-driven sizing reducer that composes `min` with `_RISK_PCT[phase]`). Does it require new D-023 (consolidated plan default), or fall inside D-014's existing "automatic regression" scope? | T-Rule 4 (Locked Decisions Are Final) + D-014 (Position Sizing); consolidated plan §5 reserves D-023 placeholder for "AI authority boundary" | Ratify D-023 with explicit scope: LLM-driven sizing reducer; cannot increase any cap; cannot override D-005 / D-010 / D-011 / D-022; promotion to live-binding requires V0.2 graduation criteria + 90-day A/B per `system-state.md` line 8 (`live_trading: blocked_until_90day_AB_test_passes`). | open |
| C-AI-001-2 | AI-SPEC-001 §10.3 C2 | Spec §12 V0.1 Advisory → V0.2 Paper-Binding gate AND Spec §13 Lean Live 0.25x → 0.5x gate. Both gates use a mix of statistical thresholds (≥200 cards, ≥30 actions, Wilson lower-95 ≥ 0.40) and operational SLOs (parse rate ≥99.5%, prompt frozen ≥10 days). They do not specify whether transitions are automated when criteria pass or require explicit operator approval per event; Spec §17 ("authority degradation requires explicit operator action") only addresses *demotion*, not promotion. | T-Rule 9 (Paper Phase Is Mandatory, 45 days minimum, 12 GLC criteria) + D-013 (Paper Phase) + `system-state.md` line 8 (`live_trading: blocked_until_90day_AB_test_passes`) | Per T-Rule 9 + `system-state.md`: any transition that affects live capital (V0.2 → small-live veto, lean live 0.25x → 0.5x) requires explicit operator approval per event; paper-binding-only promotions can be automated subject to GLC-001..012 cleanliness. Encode this distinction in D-023 alongside C1. | open |
| C-AI-001-3 | AI-SPEC-001 §10.3 C3 | Spec §4 ("Capped opportunity lean") + Spec §5 (Opportunity Lean Constraints). The opportunity-lean channel is the only Governor authority surface that *proposes* a trade rather than gating one (it is admissibility-of-a-new-strategy-class, not just a sizing-cap on an already-proposed trade). Even at ≤0.25x paper-only, this is in tension with Spec §27 ("AI controls admissibility and size ceilings, not trade execution") and with Spec §27's own self-flagged dangerous assumption about event-risk precision. | T-Rule 5 (Capital Preservation Is Absolute) — lean is reductive in dollar terms (small size, defined risk) but additive in *trade count*; T-Rule 9 satisfied by V0.1 paper-only constraint | Per consolidated plan §5 conservative-first principle: defer the lean channel to a separate spec (AI-SPEC-001b or AI-SPEC-014); ship core Item 1 V0.1 as veto-only. Re-introduce lean only after the core Governor passes graduation. | open |

---

## 2. Open Class B Corrections (Consolidated Operator Approval)

Class B corrections change implementation meaning but not architectural goal. Per `CONSOLIDATED_PLAN_v1.2_APPROVED.md` §3 + template `_template.md` §10.2, GPT or Claude proposes; Cursor verifies; **operator approves a consolidated list, not per-correction**. B1–B8 below are part of one consolidated approval set scoped to AI-SPEC-001.

| ID | From | Spec Section | Spec Says | Reality | Proposed Correction | Status |
|----|------|--------------|-----------|---------|---------------------|--------|
| B-AI-001-1 | AI-SPEC-001 §10.2 B1 | Spec §1 (Final Decision Stack — "Supabase pgvector case retrieval") + Spec §16 (Retrieval Quality Score) | Implies `pgvector` extension is enabled and a populated case-store with embeddings exists. | Zero `pgvector` references across all 68 migrations at HEAD; no embedding infrastructure in `backend/`. | Add Class B note to Spec §1 + §16: pgvector enablement + case-store schema with embedding columns is a **pre-V0.1 implementation prerequisite**, not an existing capability. Spec §28 V0.1 Ship Scope item 1 is the build target — clarify pgvector is part of "Item 1 V0.1 schema" specifically, not assumed-present. | open |
| B-AI-001-2 | AI-SPEC-001 §10.2 B2 | Spec §1 + Spec §24 ("refactored synthesis_agent") | Implies an in-place refactor of an existing module with similar surface area. | `backend_agents/synthesis_agent.py` (628 lines) produces a 5-field JSON `{direction, confidence, strategy, rationale, risk_level}`; Governor schema in Spec §3 has 18+ fields including event taxonomy, novelty/uncertainty/conflict scores, allowed/blocked strategy-class enums, opportunity-lean fields, freshness flags, retrieval case IDs. The schema delta is too large for "refactor". | Spec wording is **observability of architectural intent only** — implementation will be a full rewrite using `synthesis_agent.py`'s structured-output / provider-pluggable scaffolding as starting point. Set correct implementer expectation. | open |
| B-AI-001-3 | AI-SPEC-001 §10.2 B3 | Spec §14 (Versioning and Rollback — `ai_governor_versions` table DDL) | Provides full DDL as if the table is part of the spec deliverable. | Migration not present at HEAD; zero matches for `ai_governor_versions` in `supabase/`. | No Class B *correction* to spec wording; tag as "scheduled buildout" so the audit trail shows the migration is part of P-Phase 4+ implementation, not assumed-present. | open |
| B-AI-001-4 | AI-SPEC-001 §10.2 B4 | Spec §3.B (`GovernorDecisionRecord`) | Implies a `governor_decisions` (or equivalent) persistence target with the documented row shape exists. | No table at HEAD. | Spec defines the row shape; persistence target name should be set in TASK_REGISTER §14A.2. **Recommended canonical name:** `ai_governor_decisions` (matches the `ai_governor_versions` namespace). | open |
| B-AI-001-5 | AI-SPEC-001 §10.2 B5 | Spec §16 (`schema_quality_factor` formula referencing `calibration_eligible = true`) | Implies `calibration_eligible` is an attribute on retrievable cases at query time. | Zero matches for `calibration_eligible` in `backend/` and `supabase/migrations/` at HEAD; the label only lives in archived locked spec + audit infra docs. | Cross-spec sequencing: Item 1 cannot enforce `schema_quality_factor = 0.00 for contaminated rows` until Item 10 (Counterfactual P&L) extends `trading_prediction_outputs` (or its successor case store) with `calibration_eligible`. Add Class B note to Spec §16: depends on AI-SPEC-010 deliverable. | open |
| B-AI-001-6 | AI-SPEC-001 §10.2 B6 | Spec §3 LLM Output (`data_freshness_warning`, `data_freshness_flags`) + Spec §11 ("Data freshness fail") + Spec §16 ("data freshness penalty") | Treats data freshness as a working signal the Governor reads. | Carry-forward #4: `_safe_redis()` at `prediction_engine.py:100` is dead code (no callers). Carry-forward #1: `gex:updated_at` has no producer. Freshness substrate is **non-functional** at HEAD. | Spec §28 V0.1 Ship Scope must include "freshness substrate buildout" as a sub-item — wire a real caller of `_safe_redis()` (or replacement) AND stand up producers for `gex:updated_at` + any other staleness keys the Card reads. Alternatively, Spec §24 must explicitly mark `data_freshness_warning` as MVP-deferred. | open |
| B-AI-001-7 | AI-SPEC-001 §10.2 B7 | Spec §10 (Constitutional Gates — "Streak halt", "Phase sizing tiers") | Lists the gates as one-line bullet items. | "Streak halt" is split: 3-loss reduction at `risk_engine.py:234–235`, 5-loss session halt at `prediction_engine.py:688–691`. "Phase sizing tiers" `_RISK_PCT` lives at `risk_engine.py:79–84` and is **non-monotonic** at HEAD (Phase 1 0.010 > Phase 2 0.0075 — evidence pack §9.4) by paired-design with the 2026-04-20 SPX width widening. | Add implementer-facing Class B note: (a) D-022 enforcement is split between `risk_engine.py` and `prediction_engine.py`; the Governor's "Final Arbiter" composition rule must read from BOTH paths. (b) The Governor's `size_multiplier_cap` must NOT widen the non-monotonic regression; this is a hard constraint pending Item 12 / separate ladder fix. | open |
| B-AI-001-8 | AI-SPEC-001 §10.2 B8 | Spec §12 V0.2 Paper-Binding promotion gate ("≥ 200 replay/advisory decision cards") | Implies Item 4 (Replay Harness) is operational by the time the gate is evaluated. | Item 4 is itself V0.1 Cluster A future design (evidence pack §8 Item 4 — NOT YET IMPLEMENTED). | Add Class B note: gate eligibility requires Item 4 to ship first AND accumulate ≥200 cards. Operator should verify Item 4's expected card production rate before committing to Spec §12 thresholds, otherwise V0.2 paper-binding promotion is calendar-blocked on Item 4 throughput. | open |

---

## 3. Class A Mechanical Corrections (Batch-Clear At Gate 1)

Per `CONSOLIDATED_PLAN_v1.2_APPROVED.md` §3 + template `_template.md` §10.1, Class A corrections are mechanical (wrong file paths, stale line numbers, wrong counts, naming inconsistencies). **Any AI corrects; Cursor verifies; rubber-stamped at end of audit phase (Gate 1).** NOT per-finding operator approval.

This section is a count-and-summary table. Full per-correction detail lives in each per-item redline's §10.1.

| Spec | Class A Count | Summary | Status |
|------|---------------|---------|--------|
| AI-SPEC-001 | 2 | **A1** — `backend_agents/` count: spec §24 says "8 specialist agents", actual count is 7 non-`__init__` `.py` files at HEAD `b0cd6b3` (`economic_calendar.py`, `feedback_agent.py`, `flow_agent.py`, `macro_agent.py`, `sentiment_agent.py`, `surprise_detector.py`, `synthesis_agent.py`) — correct to 7 OR define an explicit 8th not-yet-built agent. **A2** — Strategy-class taxonomy naming inconsistency: `risk_engine.py:105–106` uses `debit_call_spread` / `debit_put_spread`; `synthesis_agent.py:40–41` and MASTER_PLAN feature-flag boilerplate use `bull_debit_spread` / `bear_debit_spread`. Recommended: keep spec wording as canonical Governor enum; flag separate cleanup pass. | open |

**Total Class A corrections in audit phase:** 2 (will grow as audits complete)

---

## 4. Resolved Findings

When the operator decides on a Class C item, when a Class B is approved-and-applied (Phase 2), or when a Class A is batch-cleared at Gate 1, **MOVE** the entry from sections 1–3 to here. Include `Resolution Date` (when), `Resolution` (operator-approved decision text or applied-correction reference), and `Notes` (link to the PR / commit / D-XXX entry that closes it).

| ID | From | Resolution Date | Resolution | Notes |
|----|------|-----------------|------------|-------|
| (none yet) | | | | |

---

## 5. Cross-Spec Themes

Findings that appear in multiple audits OR governance debt that affects multiple specs. Update as themes emerge across audits. Status `open — confirmed in N audit(s)` is incremented as subsequent audits confirm; status changes to `closed` only when the underlying debt is resolved (Phase 2 correction applied, governance change ratified, or theme superseded by a Phase 3 buildout).

| Theme | Affected Specs | Description | Status |
|-------|----------------|-------------|--------|
| Strategy-class taxonomy naming inconsistency | AI-SPEC-001 (confirmed); likely also AI-SPEC-007, AI-SPEC-011, AI-SPEC-012 (per `CROSS_CUTTING_EVIDENCE_MATRIX.md` §3 strategy-enum touchpoints) | `risk_engine.py:105–106` uses `debit_call_spread` / `debit_put_spread`; `synthesis_agent.py:40–41` + `MASTER_PLAN.md` feature-flag boilerplate use `bull_debit_spread` / `bear_debit_spread`. System-wide cleanup task; not Item 1's scope to fix. | open — confirmed in 1 audit |
| `_safe_redis()` dead code (carry-forward #4) | AI-SPEC-001 (confirmed high-impact, B-AI-001-6); potential AI-SPEC-005 (vol fair-value freshness), AI-SPEC-013 (drift-detection freshness) | Function defined at `prediction_engine.py:100` but never called at HEAD. Any spec relying on freshness gates must include freshness substrate buildout (caller wiring + `gex:updated_at` producer + `gex:atm_iv` producer). | open — confirmed in 1 audit |
| `calibration_eligible` flag missing — depends on Item 10 deliverable | AI-SPEC-001 (confirmed, B-AI-001-5); likely also AI-SPEC-005, AI-SPEC-006, AI-SPEC-009, AI-SPEC-012 (per matrix §3 calibration-input touchpoints) | `calibration_eligible` referenced by multiple specs as a queryable attribute on cases, but only Item 10 (Counterfactual P&L) is the producer. Cross-spec sequencing constraint: Items that depend on this flag are calendar-blocked on Item 10. | open — confirmed in 1 audit |
| `_RISK_PCT` non-monotonic ladder (evidence pack §9.4) | AI-SPEC-001 (must not worsen, B-AI-001-7); AI-SPEC-012 (Item 12 owns ladder fix); AI-SPEC-013 (drift-triggered demotion path interacts with ladder) | Phase 1 (0.010) > Phase 2 (0.0075) at HEAD `risk_engine.py:79–84`. Pre-existing governance debt re-introduced by 2026-04-20 SPX width widening. Matrix §4 proposed module-level merge order **1 → 13 → 12** for `risk_engine.py`. | open — pre-existing debt (predates audit phase) |
| `pgvector` / embedding infrastructure missing | AI-SPEC-001 (confirmed, B-AI-001-1); likely also AI-SPEC-003 (case retrieval), AI-SPEC-007 (any case-based reasoning) | `pgvector` extension not enabled in any of 68 migrations at HEAD. Several specs assume case-store with embeddings exists. Pre-V0.1 implementation prerequisite, not existing capability. | open — confirmed in 1 audit |

---

## 6. Governance Updates Required (Roll-Up From All Audits)

Aggregated checklist of what governance documents must change. Each per-item audit's §11 contributes to this section. Future audits **append** to the relevant subsection; do not modify existing items unless a later audit narrows or supersedes a prior proposal (in which case add a "see also" note rather than overwriting).

### `approved-decisions.md`
- [ ] **D-023 — AI Authority Boundary** (proposed in AI-SPEC-001 §11; covers C-AI-001-1, C-AI-001-2, C-AI-001-3 disposition). Wording must cover (a) Governor's `size_multiplier_cap` channel composing with `_RISK_PCT[phase]`, (b) explicit non-overridability of D-005 / D-010 / D-011 / D-014 / D-021 / D-022 with reductive-only constraint, (c) opportunity-lean channel disposition (folded into D-023 or deferred to separate spec), (d) promotion-gate authority handoff between automated criteria and operator approval.
- [ ] **No existing D-XXX modifications required by AI-SPEC-001** — Spec defers cleanly to D-005, D-010, D-011, D-014, D-021, D-022 without amendment.

### `MASTER_PLAN.md`
- [ ] **New phase entry: Phase 3A (or equivalent) — AI Risk Governor V0.1** (AI-SPEC-001 §11). Per Spec §28 V0.1 ship-scope: 4–6 weeks; 11 build items decomposed at `AI-SPEC-001.md` §12.2.

### `TASK_REGISTER.md`
- [ ] **New section: §14A — Risk Governor implementation** (AI-SPEC-001 §11). Sub-items per `AI-SPEC-001.md` §12.2 (14A.0 schema bootstrap, 14A.1 freshness substrate, 14A.2 Card generator, 14A.3 Governor LLM agent, 14A.4 Final Arbiter, 14A.5 caching, 14A.6 champion/challenger, 14A.7 cost circuit breaker, 14A.8 observability, 14A.9 replay calibration, 14A.10 promotion-gate machinery).

### `system-state.md`
- [ ] **Operational state addition: `ai_risk_governor` field** (AI-SPEC-001 §11). Tracks `{ phase: 'not_started' | 'v0.1_advisory' | 'v0.2_paper_binding' | 'v0.2_small_live' | 'production' | 'demoted', authority_promoted_at: timestamp | null, last_demotion_reason: text | null }` (or equivalent). Tracks promotion-gate progression per Spec §12 + §17.

### `constitution.md`
- [ ] **Pointer note only — no rule change** (AI-SPEC-001 §11). If D-023 is ratified, T-Rule 4 needs a one-line note that D-023 is the explicit AI-authority-boundary record. T-Rule 5 / T-Rule 6 / T-Rule 9 already cover D-005 / D-010 / D-011 / D-013 non-overridability and the Governor design respects all three.

---

## Update Log

| Date | Audit | Action |
|------|-------|--------|
| 2026-04-26 | P1.3.1b | Initial creation. Populated from AI-SPEC-001 audit (PR #60, merged at `f456922`). 3 open Class C escalations (C-AI-001-1, C-AI-001-2, C-AI-001-3); 8 open Class B corrections (B-AI-001-1 through B-AI-001-8); 2 Class A items (logged for Gate 1 batch-clear); 5 cross-spec themes identified; 5 governance update line items aggregated. |
| 2026-04-26 | P1.3.1b backfill | Added Section 0 (Pre-Audit Findings) covering Phase 0 PRs #54/#55, P1.1 PR #56, P1.2 PR #57, P1.3.0 PR #58, P1.3.0b PR #59. 13 pre-audit findings catalogued (4 Phase 0, 7 P1.1, 4 P1.2, 1 P1.3.0 [duplicate of PRE-P0-4], 2 P1.3.0b informational). §0.6 cross-reference table added linking pre-audit IDs to §5 cross-spec themes and §1–§3 per-audit entries where applicable. Sections 1–6 unchanged. |
