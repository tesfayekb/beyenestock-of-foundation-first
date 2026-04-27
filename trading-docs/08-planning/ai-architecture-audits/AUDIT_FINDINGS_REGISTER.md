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

> **ID convention:** Open findings use `<class>-<spec-id>-<n>` (e.g., `C-AI-001-1` = Class C, AI-SPEC-001, item 1; `B-AI-002-3` = Class B, AI-SPEC-002, item 3). Class A items roll up by spec rather than per-item to avoid noise (Class A is mechanical and batch-cleared at Gate 1).

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
