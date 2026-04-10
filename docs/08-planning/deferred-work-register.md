# Deferred Work Register

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-10

## Purpose

Authoritative registry for postponed items that were originally part of an approved plan section. Ensures deferred work is not lost, is formally tracked with blocking dependencies, and is explicitly reassigned to a future phase before that phase begins.

**This is NOT for new feature proposals** — those belong in [feature-proposals.md](feature-proposals.md).
This document is for work that was **already approved** in the master plan but could not be completed in its original phase.

## Scope

All deferred subsections, gate items, or deliverables from approved plan sections that were not completed in their original phase.

## Enforcement Rules (CRITICAL)

- When any approved plan subsection is marked `deferred`, a corresponding entry **MUST** be created here
- When any phase gate item is deferred or marked N/A, a corresponding entry **MUST** be created here
- No phase may be formally closed with deferred items unless all deferred items have entries in this register
- Deferred items **MUST** be assigned to a future phase before that phase's planning begins
- Unassigned deferred items must be reviewed at every phase boundary
- Items may only be `cancelled` via change control with a decision record (DEC-NNN)

## Entry Schema (MANDATORY)

Each deferred item MUST include all of the following fields:

| Field | Description |
|-------|-------------|
| `id` | Unique ID: `DW-NNN` |
| `date_deferred` | Date the item was deferred |
| `source_plan_section` | Original plan section ID (e.g., PLAN-AUTH-001-B) |
| `source_phase` | Phase where work was originally planned |
| `title` | Short descriptive title |
| `reason_deferred` | Why it could not be completed |
| `blocking_dependencies` | What must be resolved before resuming |
| `impact_on_source_phase` | How deferral affected the source phase's completion |
| `future_owner_phase` | Target phase for resumption (or `unassigned`) |
| `future_owner_module` | Module that will own this work |
| `required_plan_realignment` | What plan changes are needed when this work resumes |
| `related_decisions` | DEC-NNN references |
| `related_actions` | ACT-NNN references |
| `required_tests_for_closure` | Tests/gates that must pass when implemented |
| `status` | See status legend below |
| `implemented_by_action` | ACT-NNN when eventually implemented |
| `implemented_in_plan_version` | Plan version when implemented |

## Status Legend

| Status | Meaning |
|--------|---------|
| `deferred` | Postponed, not yet assigned to a future phase |
| `assigned` | Assigned to a specific future phase |
| `in-progress` | Actively being implemented in the assigned phase |
| `implemented` | Completed and verified |
| `cancelled` | Permanently dropped via change control |

## Phase Boundary Review Rule

At each phase boundary (before advancing to the next phase):

1. Review ALL open deferred items (status = `deferred` or `assigned`)
2. Confirm blocking dependencies are still accurate
3. Confirm future phase assignment is still appropriate
4. If a deferred item's future phase is the upcoming phase → it **MUST** be included in that phase's scope
5. Document review outcome in action tracker

---

## Registry

### DW-001: Google OAuth

| Field | Value |
|-------|-------|
| **ID** | DW-001 |
| **Date Deferred** | 2026-04-09 |
| **Source Plan Section** | PLAN-AUTH-001-B |
| **Source Phase** | Phase 1 — Foundation (Auth) |
| **Title** | Google OAuth sign-in |
| **Reason Deferred** | External Google OAuth client credentials not yet configured |
| **Blocking Dependencies** | Google Cloud Console OAuth client ID/secret configured; Supabase Auth Google provider enabled with redirect URIs |
| **Impact on Source Phase** | Phase 1 closed as `approved-partial` — auth foundation complete but OAuth providers deferred |
| **Future Owner Phase** | Phase 6 — Hardening & System Validation (or dedicated Auth Completion mini-phase before release) |
| **Future Owner Module** | PLAN-AUTH-001 |
| **Required Plan Realignment** | Phase 6 scope must include OAuth callback verification, provider config validation, OAuth E2E tests, and auth-security.md OAuth section validation |
| **Related Decisions** | DEC-020 (v1 OAuth limited to Google + Apple) |
| **Related Actions** | ACT-011 (Phase 1 auth verification) |
| **Required Tests for Closure** | OAuth sign-in E2E flow, OAuth account linking, OAuth error handling (denied consent, expired token), OAuth + MFA combined flow |
| **Status** | `deferred` |
| **Implemented by Action** | — |
| **Implemented in Plan Version** | — |

---

### DW-002: Apple Sign-In

| Field | Value |
|-------|-------|
| **ID** | DW-002 |
| **Date Deferred** | 2026-04-09 |
| **Source Plan Section** | PLAN-AUTH-001-C |
| **Source Phase** | Phase 1 — Foundation (Auth) |
| **Title** | Apple Sign-In |
| **Reason Deferred** | Apple Developer account configuration and Supabase provider setup not yet completed |
| **Blocking Dependencies** | Apple Developer account with Sign-In with Apple capability; Services ID configured; Supabase Auth Apple provider enabled |
| **Impact on Source Phase** | Phase 1 closed as `approved-partial` — auth foundation complete but OAuth providers deferred |
| **Future Owner Phase** | Phase 6 — Hardening & System Validation (or dedicated Auth Completion mini-phase before release) |
| **Future Owner Module** | PLAN-AUTH-001 |
| **Required Plan Realignment** | Same as DW-001 — OAuth callback verification, provider validation, E2E tests |
| **Related Decisions** | DEC-020 (v1 OAuth limited to Google + Apple) |
| **Related Actions** | ACT-011 (Phase 1 auth verification) |
| **Required Tests for Closure** | Apple Sign-In E2E flow, Apple account linking, Apple-specific email relay handling, Apple + MFA combined flow |
| **Status** | `deferred` |
| **Implemented by Action** | — |
| **Implemented in Plan Version** | — |

---

### DW-003: RBAC Permission Allow/Deny Tests

| Field | Value |
|-------|-------|
| **ID** | DW-003 |
| **Date Deferred** | 2026-04-10 |
| **Source Plan Section** | PLAN-RBAC-001 (Phase 2 gate item 9) |
| **Source Phase** | Phase 2 — Access Control (RBAC) |
| **Title** | Every permission has allow + deny test |
| **Reason Deferred** | Deferred to Phase 3 integration testing per ACT-015/ACT-017 |
| **Blocking Dependencies** | Edge functions deployed and runtime-verified; test infrastructure for permission matrix |
| **Impact on Source Phase** | Phase 2 gate remains open — foundation implemented but not fully gate-closed |
| **Future Owner Phase** | Phase 3 — Core Services (integration testing) |
| **Future Owner Module** | PLAN-RBAC-001 |
| **Required Plan Realignment** | Phase 3 scope must include RBAC permission test matrix as prerequisite before user management builds on RBAC |
| **Related Decisions** | — |
| **Related Actions** | ACT-015, ACT-016, ACT-017 |
| **Required Tests for Closure** | Allow test for each of 29 permissions with correct role; deny test for each with wrong role; revoked-permission-denied test |
| **Status** | `assigned` |
| **Implemented by Action** | — |
| **Implemented in Plan Version** | — |

---

### DW-004: DB-Level RLS Verification

| Field | Value |
|-------|-------|
| **ID** | DW-004 |
| **Date Deferred** | 2026-04-10 |
| **Source Plan Section** | PLAN-RBAC-001 (Phase 2 gate item 10) |
| **Source Phase** | Phase 2 — Access Control (RBAC) |
| **Title** | RLS tested at database level (not just API) |
| **Reason Deferred** | Requires manual DB-level testing with test users in different role contexts |
| **Blocking Dependencies** | Deployed schema; test users with assigned roles; ability to execute queries as different Postgres roles |
| **Impact on Source Phase** | Phase 2 gate remains open |
| **Future Owner Phase** | Phase 3 — Core Services (pre-integration) |
| **Future Owner Module** | PLAN-RBAC-001 |
| **Required Plan Realignment** | Must be completed before any Phase 3 module writes RLS-dependent queries |
| **Related Decisions** | — |
| **Related Actions** | ACT-017 |
| **Required Tests for Closure** | Anonymous/anon-key query returns zero rows on protected tables; regular user sees only own user_roles; admin sees role-gated rows; superadmin sees all; write attempts without policy denied |
| **Status** | `assigned` |
| **Implemented by Action** | — |
| **Implemented in Plan Version** | — |

---

### DW-005: Cross-Tenant Isolation Gate Scope Resolution

| Field | Value |
|-------|-------|
| **ID** | DW-005 |
| **Date Deferred** | 2026-04-10 |
| **Source Plan Section** | PLAN-RBAC-001 (Phase 2 gate item 11) |
| **Source Phase** | Phase 2 — Access Control (RBAC) |
| **Title** | Cross-tenant isolation verification |
| **Reason Deferred** | System is single-tenant for v1 — gate item is mis-scoped for current architecture |
| **Blocking Dependencies** | Change control decision to either mark N/A for v1 or defer to multi-tenancy introduction |
| **Impact on Source Phase** | Phase 2 gate technically open; requires plan amendment to resolve |
| **Future Owner Phase** | `unassigned` — pending plan amendment via change control |
| **Future Owner Module** | PLAN-RBAC-001 |
| **Required Plan Realignment** | Amend Phase 2 gate item 11 via change control to reflect v1 single-tenant scope |
| **Related Decisions** | — (requires new DEC-NNN) |
| **Related Actions** | ACT-017 |
| **Required Tests for Closure** | If multi-tenancy introduced: zero-rows cross-tenant queries, tenant-scoped RLS policies |
| **Status** | `deferred` |
| **Implemented by Action** | — |
| **Implemented in Plan Version** | — |

---

### DW-006: Role Change Cache Invalidation Verification

| Field | Value |
|-------|-------|
| **ID** | DW-006 |
| **Date Deferred** | 2026-04-10 |
| **Source Plan Section** | PLAN-RBAC-001 (Phase 2 gate item 12) |
| **Source Phase** | Phase 2 — Access Control (RBAC) |
| **Title** | Role change immediately reflected (cache invalidation verified) |
| **Reason Deferred** | No permission cache exists; fresh RPC fetches used. Runtime E2E verification of role-change propagation to UI not yet performed |
| **Blocking Dependencies** | Deployed edge functions; test user with assignable roles; runtime E2E test capability |
| **Impact on Source Phase** | Phase 2 gate remains open |
| **Future Owner Phase** | Phase 3 — Core Services (pre-integration) |
| **Future Owner Module** | PLAN-RBAC-001 |
| **Required Plan Realignment** | Must verify before admin panel role management UI is built in Phase 4 |
| **Related Decisions** | — |
| **Related Actions** | ACT-017 |
| **Required Tests for Closure** | Assign role → verify UI reflects new permissions without page reload; revoke role → verify UI removes permissions; verify no stale authorization state |
| **Status** | `assigned` |
| **Implemented by Action** | — |
| **Implemented in Plan Version** | — |

---

### DW-007: Moderator Role

| Field | Value |
|-------|-------|
| **ID** | DW-007 |
| **Date Deferred** | 2026-04-09 |
| **Source Plan Section** | PLAN-RBAC-001 |
| **Source Phase** | Phase 2 — Access Control (RBAC) |
| **Title** | Moderator role deferred to v2 |
| **Reason Deferred** | Decided to limit v1 to superadmin/admin/user only |
| **Blocking Dependencies** | v2 planning and scope definition |
| **Impact on Source Phase** | None — v1 RBAC schema supports dynamic roles; moderator can be added without schema change |
| **Future Owner Phase** | `unassigned` — v2 scope |
| **Future Owner Module** | PLAN-RBAC-001 |
| **Required Plan Realignment** | v2 planning must include moderator role definition, permission mapping, and UI integration |
| **Related Decisions** | DEC-018 (moderator deferred to v2) |
| **Related Actions** | — |
| **Required Tests for Closure** | Moderator role CRUD, permission matrix, admin panel integration, E2E tests |
| **Status** | `deferred` |
| **Implemented by Action** | — |
| **Implemented in Plan Version** | — |

---

## Summary Dashboard

| ID | Title | Source Phase | Future Phase | Status |
|----|-------|-------------|--------------|--------|
| DW-001 | Google OAuth | Phase 1 | Phase 6 | `deferred` |
| DW-002 | Apple Sign-In | Phase 1 | Phase 6 | `deferred` |
| DW-003 | Permission Allow/Deny Tests | Phase 2 | Phase 3 | `assigned` |
| DW-004 | DB-Level RLS Verification | Phase 2 | Phase 3 | `assigned` |
| DW-005 | Cross-Tenant Isolation Scope | Phase 2 | `unassigned` | `deferred` |
| DW-006 | Cache Invalidation Verification | Phase 2 | Phase 3 | `assigned` |
| DW-007 | Moderator Role | Phase 2 | `unassigned` (v2) | `deferred` |

## Dependencies

- [Master Plan](master-plan.md)
- [Approved Decisions](approved-decisions.md)
- [Action Tracker](../06-tracking/action-tracker.md)
- [Change Control Policy](../00-governance/change-control-policy.md)

## Used By / Affects

- Phase gate closure decisions
- Future phase scoping and planning
- Action tracker (deferred items linked to actions)
- System state (open deferred items listed)

## Risks If Changed

HIGH — lost deferred items cause permanent scope gaps and untested security paths.

## Related Documents

- [Master Plan](master-plan.md)
- [Feature Proposals](feature-proposals.md)
- [Plan Changelog](plan-changelog.md)
- [System State](../00-governance/system-state.md)
