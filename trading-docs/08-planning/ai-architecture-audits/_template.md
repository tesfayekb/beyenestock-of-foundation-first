# Spec Verification Audit — AI-SPEC-NNN

> **Status:** Template — fill in for each per-item audit (P1.3.1 through P1.3.13).
> **Binding format:** This is THE format every per-item audit must follow. Do not vary.
> **Created:** Phase 1 P1.3.0 of CONSOLIDATED_PLAN_v1.2_APPROVED.md.

---

## 1. Audit Header

| Field | Value |
|-------|-------|
| Spec ID | AI-SPEC-NNN |
| Spec name | [item name, e.g., "AI Risk Governor"] |
| Stable ID | PLAN-{MODULE}-001 (e.g., PLAN-AIGOV-001) |
| Tier | V0.1 / V0.2 / V0.3 / V0.4 |
| Cluster | A (foundational) / B (alpha-generation) / C (governance/maturation) |
| Audit date | YYYY-MM-DD |
| Repo HEAD at audit time | [full SHA] |
| Primary auditor | Cursor |
| Cross-check auditor | Claude |
| Architectural validator | GPT-5.5 Pro |
| Cross-cutting matrix reference | CROSS_CUTTING_EVIDENCE_MATRIX.md §3 (AI-SPEC-NNN block) |
| Evidence pack reference | AI_ARCH_EVIDENCE_PACK.md §[relevant sections] |

---

## 2. Spec Intent Summary (verified by GPT)

[2-4 sentences. The architectural intent of the locked spec, in plain language. NOT what the code does. NOT what the audit found. ONLY what the spec was designed to do.

Example: "AI-SPEC-001 introduces an AI Risk Governor that sits above existing rules-based risk_engine.py. The Governor has paper-binding authority over halt decisions and sizing multipliers. Authority promotion to production-binding requires drift-clean status from AI-SPEC-013 plus 100 closed paper trades. The Governor cannot override D-005 (-3% halt) or D-022 (consecutive-loss halt) — those remain hardcoded."]

If during audit you discover the spec's intent is unclear or contradicts itself, document that ambiguity here and escalate as Class C in §10.

---

## 3. Repo Evidence (verified by Cursor)

Verify the spec's claimed file/line/migration/Redis-key references against actual repo state at HEAD.

### 3.1 File/Module References

For every `backend/<file>.py:NN` reference in the spec, verify:

| Spec Reference | Verification | Status |
|---------------|--------------|--------|
| `backend/foo.py:123 (function bar)` | [does file exist? does line exist? is it the function claimed?] | verified / wrong-file / wrong-line / wrong-symbol / not-found |

### 3.2 Supabase Schema References

For every table/column the spec references, verify against `supabase/migrations/`:

| Spec Reference | Verification | Status |
|---------------|--------------|--------|
| `trading_positions.exit_reason` | [exists per migration YYYYMMDD_X.sql] | verified / column-missing / table-missing / wrong-type |

If the spec references a table that doesn't exist yet (e.g., `item_promotion_records`), mark as `not-yet-created` and reference evidence pack §7.2.

### 3.3 Redis Key References

For every Redis key the spec references, verify against evidence pack §10:

| Spec Reference | Producer | Consumer | Status |
|---------------|----------|----------|--------|
| `gex:net` | [from §10.2] | [from §10.2] | verified / consumer-only / producer-only / not-found |

If the spec assumes a freshness or staleness gate, cross-check against the `_safe_redis()` finding in matrix §1 carry-forward #4.

### 3.4 Commit Hash References

For every commit hash claimed in the spec (e.g., "scaffold shipped at 2400e98"), verify via `git show <hash> --stat`:

| Spec Reference | Verification | Status |
|---------------|--------------|--------|
| `commit 2400e98 (12E counterfactual scaffold)` | [verify SHA exists; verify commit message matches; verify files-touched matches spec claim] | verified / wrong-sha / wrong-files |

---

## 4. Existing Partial Implementation (verified by Cursor)

What already exists in the codebase that overlaps with this spec's scope. Reference evidence pack §8.

| Aspect | Existing State | Source |
|--------|---------------|--------|
| Functional scaffold | [yes/no — name files, line counts] | Evidence pack §8 |
| Schema in place | [yes/partial/no — name migrations] | Evidence pack §7 |
| Feature flag wiring | [yes/no — name flag] | Evidence pack §10 |
| Tests covering scope | [yes/no — name test files] | Direct file inspection |
| Documentation references | [TASK_REGISTER section, MASTER_PLAN phase] | TASK_REGISTER, MASTER_PLAN |

If the existing implementation is observability-only when the spec assumes calibration-grade, that's a Class B correction (logged in §10).

---

## 5. The Ten Audit Dimensions

Per CONSOLIDATED_PLAN_v1.2_APPROVED.md §2 Layer B, every spec is evaluated against these 10 dimensions. The cross-cutting matrix gave a summary view; this section gives per-item depth.

| # | Dimension | Finding | Source / Evidence |
|---|-----------|---------|-------------------|
| 1 | File/module exists | [yes / no / partial — what does exist] | [path, line count from §3.1] |
| 2 | DB table/column exists | [yes / no / partial — what exists, what doesn't] | [migration ref from §3.2] |
| 3 | Redis keys | [list relevant keys with status] | [§3.3 entries] |
| 4 | Current behavior matches spec | exact / partial / no | [explanation with file:line] |
| 5 | Spec is future design | yes / no — partially built ≠ no | [explanation] |
| 6 | Governance conflict | yes / no — and what D-XXX, MASTER_PLAN section, or TASK_REGISTER section is touched | [reference] |
| 7 | Authority level proposed | advisory / paper-binding / production-binding / disabled | [from spec, plus current actual authority if scaffold exists] |
| 8 | Calibration dependencies | [list — historical data, labels, replay, archived chains needed] | [explanation, with quantities if known] |
| 9 | Training contamination risk | low / medium / high — and what would contaminate | [explanation referencing strategy_attribution.calibration_eligible if relevant] |
| 10 | Implementation owner | Cursor | (constant) |

---

## 6. Missing Pieces

What the spec assumes exists but doesn't. Be specific:

- Files referenced in spec but absent: [list with paths]
- Tables referenced but not yet created: [list]
- Redis keys with no producer: [list, cross-ref §3.3]
- Functions called by spec but not yet defined: [list]
- Feature flags assumed but not in code: [list]

If the spec is a future design entirely, this section captures the buildout list. If the spec extends an existing scaffold, this section captures the gap between scaffold and spec target.

---

## 7. Contradictions

Places where the spec contradicts itself, contradicts another spec, or contradicts existing governance.

### 7.1 Internal Contradictions
[Spec says A in §X but B in §Y — list with quotes]

### 7.2 Cross-Spec Contradictions
[Spec touches AI-SPEC-NNN — see CROSS_CUTTING_EVIDENCE_MATRIX.md §3 / §4 / §6]

### 7.3 Governance Contradictions
[Spec proposes change that conflicts with D-001 through D-022, MASTER_PLAN, TASK_REGISTER, or constitution T-Rule. List with specific D-XXX or rule reference.]

If a contradiction with a D-XXX requires a NEW D-XXX entry to resolve, that's Class C (logged in §10).

---

## 8. Carry-Forward Findings From P1.1 / P1.2

Cross-reference the 5 priority findings from P1.1 + P1.2 carry-forward list. For this spec, indicate which findings apply and how.

| Finding | Applies to this spec? | Implication |
|---------|----------------------|-------------|
| #1: `gex:updated_at` consumer-only orphan | yes / no | [if yes: how it affects this audit] |
| #2: `gex:atm_iv` consumer-only | yes / no | [...] |
| #3: MASTER_PLAN debit-spread feature flag debt | yes / no | [...] |
| #4: `_safe_redis()` is dead code at HEAD | yes / no | [...] |
| #5: `counterfactual_pnl` is column triple, not table | yes / no | [...] |

If any of these findings makes the spec require revision, that's Class B or Class C (logged in §10).

---

## 9. Risk Rating

Single-line summary of audit risk findings.

**Rating:** LOW / MEDIUM / HIGH / CRITICAL

**Rationale:** [1-3 sentences explaining the rating]

**Categories:**
- Spec-vs-code drift severity: [low/medium/high]
- Number of Class A corrections: [count]
- Number of Class B corrections: [count]
- Number of Class C corrections: [count]
- Cross-cutting impact (specs affected): [count from matrix §4-§7]

---

## 10. Spec Corrections Required

Per CONSOLIDATED_PLAN_v1.2_APPROVED.md §3, three correction classes:

### 10.1 Class A — Mechanical Errors

Wrong file paths, stale line numbers, mistyped names, wrong counts. Any AI corrects; Cursor verifies. Rubber-stamped at end.

| # | Spec Section | Spec Says | Correct Value | Source of Truth |
|---|--------------|-----------|---------------|----------------|
| A1 | [§N of spec] | "backend/foo.py:123" | "backend/foo.py:145" | grep + read |
| A2 | [...] | [...] | [...] | [...] |

### 10.2 Class B — Implementation Status / Content Omissions

"Exists" should be "planned"; "live" should be "observability-only"; spec assumes data being captured that isn't. GPT or Claude proposes; Cursor verifies. Operator approves consolidated list.

| # | Spec Section | Spec Says | Reality | Proposed Correction |
|---|--------------|-----------|---------|--------------------|
| B1 | [§N] | "Counterfactual P&L is captured per-trade" | "counterfactual_pnl is 3 columns; only populated for skipped cycles per 12E" | "spec is observability-only, NOT calibration-grade" |
| B2 | [...] | [...] | [...] | [...] |

If a Class B correction is large enough to change architectural meaning, escalate to Class C.

### 10.3 Class C — Architectural Intent Corrections

Operator-only authority. Default: reject unless clear reason. Resolution requires NEW D-XXX or spec revision to comply with existing D-XXX.

| # | Spec Section | Issue | Conflicting D-XXX or Rule | Resolution Required |
|---|--------------|-------|--------------------------|--------------------|
| C1 | [§N] | "Spec proposes drift detector auto-promotes authority" | T-Rule 4 + constitutional principle | "Operator decision: revise spec to require manual promotion, OR add new D-XXX explicitly authorizing auto-promotion under specific conditions" |
| C2 | [...] | [...] | [...] | [...] |

---

## 11. Governance Updates Required

What governance documents must change for this spec to integrate cleanly. List all that apply:

- [ ] approved-decisions.md — new D-XXX needed (specify): [D-NNN | not needed]
- [ ] approved-decisions.md — existing D-XXX modified (specify): [D-NNN | not needed]
- [ ] MASTER_PLAN.md — new phase entry: [yes/no]
- [ ] MASTER_PLAN.md — Phase update needed: [section | not needed]
- [ ] TASK_REGISTER.md — new section needed: [Section 14.X | not needed]
- [ ] system-state.md — operational state change: [yes/no]
- [ ] constitution.md — T-Rule clarification needed: [yes/no — flag only, do not propose]

Cross-cutting matrix §3 dimension 6 should already have flagged most of these.

---

## 12. TASK_REGISTER Implications

What concrete tasks does P1.3 audit imply for downstream work?

### 12.1 Pre-implementation tasks (must complete before P1.3 audit can close)

[List blocking items the operator must resolve. Examples:
- Operator decision on Class C item C1
- New D-XXX wording approved
- Cross-spec conflict with AI-SPEC-NNN resolved]

### 12.2 Implementation tasks (Cursor work after Phase 4 doc integration)

[High-level task list for when the spec is built — NOT a full task spec, just enough that TASK_REGISTER §14 can capture it. Examples:
- 14A: Build risk_engine.py extension for Risk Governor authority hooks
- 14A.1: Add new exit reasons to position_monitor.py taxonomy
- 14A.2: Migration for governor_decisions table]

### 12.3 Calibration / Data dependencies

[What labeled data must exist before spec is calibration-grade. Cross-ref dimension 8.]

---

## 13. Recommended Status

Pick exactly one. (One of these checkboxes must be checked.)

- [ ] **spec_accurate_repo_missing** — Spec is correct as written; nothing exists in repo yet; ready for clean buildout.
- [ ] **spec_accurate_repo_partial** — Spec is correct; partial scaffold exists (cite); spec describes the full target.
- [ ] **spec_needs_factual_correction_only** — Spec has Class A errors only; intent is sound; mechanical fixes will land in Phase 2.
- [ ] **spec_has_semantic_drift_from_locked_intent** — Spec has Class B corrections that change implementation meaning but not architectural goal. Phase 2 corrections + operator approval.
- [ ] **spec_conflicts_with_existing_governance** — Spec contains Class C item(s) requiring new D-XXX or revision before integration.
- [ ] **spec_should_be_split_into_separate_proposal** — Spec scope is too broad and should be decomposed before integration. Operator decision.

---

## 14. Sign-Off

| Auditor | Sign-off Status | Date | Notes |
|---------|----------------|------|-------|
| Primary (Cursor) | [pending / approved / blocked-by-Class-C] | YYYY-MM-DD | [notes] |
| Cross-check (Claude) | [pending / approved / dispute] | YYYY-MM-DD | [notes] |
| Validator (GPT-5.5 Pro) | [pending / approved / dispute] | YYYY-MM-DD | [notes] |
| Operator | [pending / approved / requires-revision] | YYYY-MM-DD | [notes] |

If all four sign-offs are "approved", the redline is closed and the spec moves to Phase 2 correction application.

If any auditor signs "dispute", the redline returns to whoever first claimed verified for re-verification.

If operator signs "requires-revision", redline reopens with operator's notes.

---

## Redline File Location

`trading-docs/08-planning/ai-architecture-audits/AI-SPEC-NNN.md`

(Where NNN matches the spec being audited; e.g., `AI-SPEC-001.md`.)

---

## Process Notes

1. **Single binding format:** Every per-item audit (P1.3.1 through P1.3.13) uses this template verbatim. No deviation.

2. **Three-AI authority split (per consolidated plan §2 audit roles):**
   - Cursor = primary auditor (verifies repo evidence, fills §3 + §4)
   - Claude = cross-check auditor (verifies cross-spec implications, fills §7 + §8)
   - GPT-5.5 Pro = architectural validator (verifies §2 spec intent + §10.3 Class C escalations)

3. **Workflow per audit:**
   - Step 1: Cursor receives the locked spec + this template + evidence pack + matrix
   - Step 2: Cursor fills §1 through §6 from repo evidence
   - Step 3: Claude reviews §1-§6, fills §7-§9 from cross-cutting matrix
   - Step 4: GPT validates §2 spec intent and reviews any Class C escalations in §10
   - Step 5: Cursor commits redline to `trading-docs/08-planning/ai-architecture-audits/AI-SPEC-NNN.md`
   - Step 6: Operator reviews; signs §14 or returns for revision

4. **Class A corrections do NOT need operator approval per-item.** They batch-clear at end of Phase 1 (Gate 1).

5. **Class B corrections need operator approval as a consolidated list,** not per-correction.

6. **Class C corrections block the redline from closing** until operator either approves a new D-XXX or rejects the spec change.

7. **No code changes during audit.** Phase 1 is read-only. Code changes happen in Phase 2 + downstream.

---

## Out of Scope For The Per-Item Audit

The following are NOT done during a single per-item audit:

- Modifying the locked spec document itself (Phase 2)
- Writing new D-XXX entries to approved-decisions.md (Phase 5)
- Updating MASTER_PLAN.md (Phase 5)
- Creating tables/migrations (downstream implementation)
- Writing test cases (downstream implementation)
- Auditing OTHER specs (each redline is one spec only)

If during a per-item audit you find a contradiction with another spec, document it in §7.2 and let the cross-cutting matrix track it. Do NOT open the other spec's audit early.
