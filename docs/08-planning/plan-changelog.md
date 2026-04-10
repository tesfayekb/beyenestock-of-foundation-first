# Plan Changelog

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-09

## Purpose

Tracks every plan revision with full traceability across:
- Plan sections
- Approved decisions
- Supersession chains

This document is the authoritative history of all plan changes.

## Scope

All changes to:
- `master-plan.md`
- `approved-decisions.md`

## Enforcement Rule (CRITICAL)

- Every plan change MUST create a changelog entry
- No change may occur without being recorded here
- If an entry is missing or incomplete → the change is **INVALID**
- History must **NEVER** be overwritten — only appended

## Versioning Rules

- Each plan revision increments version: `vN` → `vN+1`
- Versions are immutable once recorded
- No version may be edited after creation

## Changelog Format (MANDATORY)

Each entry MUST include:

- **Plan Version** (e.g., v1 → v2)
- **Date**
- **Section IDs Changed**
- **Decision IDs Affected** (DEC-NNN)
- **What Changed**
- **Why It Changed**
- **What Stayed Unchanged**
- **What Was Added**
- **What Was Removed**
- **Approval Status**
- **Supersession Links** (if applicable)

If any field is missing → entry is **INVALID**.

## Diff Requirement

Each entry MUST align with the required plan diff:
- Sections unchanged (by ID)
- Sections modified (with reason)
- Sections added (new IDs)
- Sections removed (with justification)
- Conflicts with approved decisions (DEC-NNN)

## Entries

### v0 → v1 (2026-04-08)

**Type:** Initial creation

| Field | Value |
|-------|-------|
| Plan Version | v0 → v1 |
| Section IDs Created | PLAN-GOV-001, PLAN-AUTH-001, PLAN-RBAC-001, PLAN-USRMGMT-001, PLAN-ADMIN-001, PLAN-USRPNL-001, PLAN-AUDIT-001, PLAN-HEALTH-001, PLAN-API-001, PLAN-JOBS-001 |
| Decision IDs Affected | DEC-001, DEC-002, DEC-003, DEC-005 |
| What Changed | Initial plan created |
| Why | Project initialization |
| What Stayed | N/A |
| What Was Added | All plan sections |
| What Was Removed | None |
| Approval Status | PLAN-GOV-001: implemented; others: proposed |
| Supersession Links | None |

### v1 → v2 (2026-04-08)

**Type:** Corrective alignment — audit issue fixes

| Field | Value |
|-------|-------|
| Plan Version | v1 → v2 |
| Section IDs Changed | None |
| Decision IDs Affected | DEC-002 (superseded by DEC-006), DEC-006 (new), DEC-007 (new) |
| What Changed | DEC-002 superseded — Constitution has 11 rules, not 10. OQ-003 formally resolved with DEC-007 (audit retention 90 days). Added `normalizeRequest()` to Function Index. Added `roles.create` and `roles.delete` to Permission Index. Added provisional moderator disclaimers. Fixed permission matrix to permission-driven model. Fixed `app_role` vs `TEXT` type mismatch. |
| Why | Final audit identified 7 consistency gaps (score 98.5/100). All fixes are corrective alignment — no structural changes. |
| What Stayed | All plan sections, all other decisions, all module definitions, all existing index entries |
| What Was Added | DEC-006, DEC-007, `normalizeRequest()` function entry, `roles.create` + `roles.delete` permission entries, provisional disclaimers |
| What Was Removed | None |
| Approval Status | Approved |
| Supersession Links | DEC-002 → DEC-006 |

### v2 → v3 (2026-04-09)

**Type:** Governance transition — plan approval (Review Round 2)

| Field | Value |
|-------|-------|
| Plan Version | v2 → v3 |
| Section IDs Changed | PLAN-AUTH-001, PLAN-RBAC-001, PLAN-USRMGMT-001, PLAN-ADMIN-001, PLAN-USRPNL-001, PLAN-AUDIT-001, PLAN-HEALTH-001, PLAN-API-001, PLAN-JOBS-001 |
| Decision IDs Affected | DEC-008, DEC-009, DEC-010, DEC-011, DEC-012, DEC-013, DEC-014, DEC-015, DEC-016 |
| What Changed | Execution status only — all 9 sections moved from `proposed` to `approved` |
| Why | All module documentation scored 100/100; governance system complete; OQ-002 and OQ-005 remain open (resolved in v4) |
| What Stayed | All module definitions, dependencies, acceptance criteria, subsections unchanged |
| What Was Added | DEC-008 through DEC-016 (implementation approvals) |
| What Was Removed | None |
| Approval Status | Approved (Review Round 2) |
| Supersession Links | None |

### v3 → v4 (2026-04-09)

**Type:** Corrective alignment — pre-implementation audit fixes

| Field | Value |
|-------|-------|
| Plan Version | v3 → v4 |
| Section IDs Changed | None (no plan section definitions changed) |
| Decision IDs Affected | DEC-017 (new), DEC-018 (new), DEC-019 (new) |
| What Changed | Resolved OQ-002 (MFA recovery codes → DEC-017), OQ-004 (moderator deferred to v2 → DEC-018), OQ-005 (pg_cron → DEC-019). Fixed RSK→RISK ID mismatch across 6 reference indexes. Added missing permission entries (self-scope permissions). Added missing Permission UUID placeholders. Added RW-006 (health monitoring watchlist item). Updated Last Reviewed dates. Fixed v2→v3 changelog wording. |
| Why | Pre-implementation audit identified 10 issues (2 critical blockers, 5 medium, 3 low). All resolved. |
| What Stayed | All plan section definitions, dependencies, acceptance criteria, module docs unchanged |
| What Was Added | DEC-017, DEC-018, DEC-019, RW-006, 3 self-scope permission entries, Permission UUID placeholders |
| What Was Removed | Provisional moderator references (per DEC-018) |
| Approval Status | Approved |
| Supersession Links | None |

### v4 → v5 (2026-04-10)

**Type:** Governance enhancement — Deferred Work Register + carried-forward gate item protocol

| Field | Value |
|-------|-------|
| Plan Version | v4 → v5 |
| Section IDs Changed | Phase Gate Rules (new subsection: Carried-Forward Gate Item Rule) |
| Decision IDs Affected | DEC-021 (new) |
| What Changed | Added Deferred Work Register as SSOT governance document. Added Carried-Forward Gate Item Rule to Phase Gate Rules. Linked deferred items (DW-001 through DW-007) from master-plan gate items and subsections. Updated system-state with deferred_work_open field. Fixed DW-001/DW-002 status from `deferred` to `assigned` (had explicit future phase). Bumped plan version to v5. |
| Why | Deferred approved work had no formal carry-forward mechanism. Phase-boundary review, future-phase reassignment, and gate-item lifecycle were not governed. Carried-forward gate items had no explicit interaction rule with phase advancement. |
| What Stayed | All plan section definitions, dependencies, acceptance criteria, module docs, existing decisions unchanged |
| What Was Added | deferred-work-register.md (7 seed entries), DEC-021, Carried-Forward Gate Item Rule, DW-NNN links in Phase 1/2 gate sections |
| What Was Removed | None |
| Approval Status | Approved |
| Supersession Links | None |

### v5 → v6 (2026-04-10)

**Type:** Gate closure — runtime verification + change control resolution

| Field | Value |
|-------|-------|
| Plan Version | v5 → v6 |
| Section IDs Changed | PLAN-RBAC-001 (Phase 2 gate items 10, 11 updated) |
| Decision IDs Affected | DEC-022 (new) |
| What Changed | Phase 2 gate item 10 (RLS DB-level testing) checked with ACT-019 evidence. Phase 2 gate item 11 (cross-tenant isolation) marked N/A via DEC-022 (v1 single-tenant). DW-004 status → implemented. DW-005 status → cancelled. Permission deny matrix verified (29/29). System-state updated to reflect 10/12 gate items checked. |
| Why | Runtime verification tests executed against deployed Supabase confirmed RLS enforcement, write denial, and security helper fail-secure behavior. Cross-tenant gate item formally resolved as architecturally inapplicable for v1. |
| What Stayed | All plan section definitions, acceptance criteria, Phase Gate Rules, Carried-Forward Gate Item Rule unchanged |
| What Was Added | DEC-022, ACT-019, runtime verification evidence |
| What Was Removed | None |
| Approval Status | Approved |
| Supersession Links | None |

## Supersession Chain Requirement

For any modification to an approved section:

Must include:
- `prior_section_id`
- `new_section_id`
- `decision_id`
- `reason`
- `date`

Must maintain full traceability:
- plan → decision → changelog → updated plan

## No Silent Change Rule

No modification to `master-plan.md` or `approved-decisions.md` may occur without:
- Corresponding changelog entry
- Proper version increment
- Recorded diff

Violations = **INVALID** change.

## Dependencies

- [Master Plan](master-plan.md)
- [Approved Decisions](approved-decisions.md)

## Used By / Affects

- Plan governance
- Decision traceability
- Historical auditing

## Risks If Changed

HIGH — loss of traceability breaks system integrity and decision history.

## Related Documents

- [Master Plan](master-plan.md)
- [Approved Decisions](approved-decisions.md)
- [Plan Review Log](plan-review-log.md)
