# Deferred Work Register

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-13

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
| **Future Owner Phase** | `unassigned` — deferred to v2 (provider credentials not yet available) |
| **Future Owner Module** | PLAN-AUTH-001 |
| **Required Plan Realignment** | v2 planning must include OAuth callback verification, provider config validation, OAuth E2E tests, and auth-security.md OAuth section validation |
| **Related Decisions** | DEC-020 (v1 OAuth limited to Google + Apple) |
| **Related Actions** | ACT-011 (Phase 1 auth verification) |
| **Required Tests for Closure** | OAuth sign-in E2E flow, OAuth account linking, OAuth error handling (denied consent, expired token), OAuth + MFA combined flow |
| **Status** | `deferred (v2)` |
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
| **Future Owner Phase** | `unassigned` — deferred to v2 (provider credentials not yet available) |
| **Future Owner Module** | PLAN-AUTH-001 |
| **Required Plan Realignment** | Same as DW-001 — OAuth callback verification, provider validation, E2E tests |
| **Related Decisions** | DEC-020 (v1 OAuth limited to Google + Apple) |
| **Related Actions** | ACT-011 (Phase 1 auth verification) |
| **Required Tests for Closure** | Apple Sign-In E2E flow, Apple account linking, Apple-specific email relay handling, Apple + MFA combined flow |
| **Status** | `deferred (v2)` |
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
| **Status** | `implemented` |
| **Implemented by Action** | ACT-020 |
| **Implemented in Plan Version** | v7 |

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
| **Related Actions** | ACT-017, ACT-019 |
| **Required Tests for Closure** | Anonymous/anon-key query returns zero rows on protected tables; regular user sees only own user_roles; admin sees role-gated rows; superadmin sees all; write attempts without policy denied |
| **Status** | `implemented` |
| **Implemented by Action** | ACT-019 |
| **Implemented in Plan Version** | v6 |

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
| **Related Decisions** | DEC-022 |
| **Related Actions** | ACT-017, ACT-019 |
| **Required Tests for Closure** | If multi-tenancy introduced: zero-rows cross-tenant queries, tenant-scoped RLS policies |
| **Status** | `cancelled` |
| **Implemented by Action** | ACT-019 (resolved via DEC-022: N/A for v1) |
| **Implemented in Plan Version** | v6 |

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
| **Status** | `implemented` |
| **Implemented by Action** | ACT-020 |
| **Implemented in Plan Version** | v7 |
| **Resolution Note** | No permission cache exists — architecture uses fresh DB queries via get_my_authorization_context() RPC on every check. Role changes are inherently immediate. Last-superadmin guard trigger fires instantly. |

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

### DW-008: MFA Recovery Codes

| Field | Value |
|-------|-------|
| **ID** | DW-008 |
| **Date Deferred** | 2026-04-09 |
| **Source Plan Section** | PLAN-AUTH-001-D |
| **Source Phase** | Phase 1 — Foundation (Auth) |
| **Title** | MFA recovery code generation, storage, and usage |
| **Reason Deferred** | Core MFA (TOTP enroll + verify) prioritized first; recovery codes are secondary safety net |
| **Blocking Dependencies** | MFA enrollment flow operational (done); hashed storage mechanism for recovery codes; UI for code display + regeneration |
| **Impact on Source Phase** | Phase 1 closed as `approved-partial` — MFA enrollment works but recovery path not yet available |
| **Future Owner Phase** | Phase 4 — Admin & User Interfaces (user-panel MFA configuration) |
| **Future Owner Module** | PLAN-AUTH-001, PLAN-USRPNL-001 |
| **Required Plan Realignment** | Phase 4 user-panel MFA configuration section must include recovery code generation, display, regeneration, and single-use consumption |
| **Related Decisions** | DEC-017 (MFA recovery code format: 10 codes, 8 alphanumeric, single-use, hashed storage) |
| **Related Actions** | ACT-010, ACT-011 |
| **Required Tests for Closure** | Recovery code generation (10 codes returned), code display + copy UX, single-use consumption (code works once then invalidated), full set regeneration (old codes invalidated), hashed storage verification (no plaintext in DB), recovery code + re-enrollment flow |
| **Status** | `implemented` |
| **Implemented by Action** | ACT-064 |
| **Implemented in Plan Version** | v11.0 |

---

### DW-009: requireRole() Shared Function

| Field | Value |
|-------|-------|
| **ID** | DW-009 |
| **Date Deferred** | 2026-04-10 |
| **Source Plan Section** | PLAN-RBAC-001 |
| **Source Phase** | Phase 2 — Access Control (RBAC) |
| **Title** | Server-side requireRole() guard function |
| **Reason Deferred** | Phase 2 focused on schema, helpers, and edge function foundation; requireRole() is a consumer-facing guard needed when modules start enforcing role checks |
| **Blocking Dependencies** | has_role() DB function operational (done); edge function auth pattern established (done) |
| **Impact on Source Phase** | No impact on Phase 2 gate — requireRole() is a downstream consumer utility, not a gate item |
| **Future Owner Phase** | Phase 3 — Core Services (needed before user-management and API modules enforce role checks) |
| **Future Owner Module** | PLAN-RBAC-001, PLAN-API-001 |
| **Required Plan Realignment** | Phase 3 must implement requireRole() before any edge function uses role-based access control |
| **Related Decisions** | — |
| **Related Actions** | ACT-015, ACT-017 |
| **Required Tests for Closure** | Correct role → access allowed; wrong role → 403; no role → 403; superadmin bypass verified; integration with edge function auth pattern |
| **Status** | `implemented` |
| **Implemented by Action** | ACT-023 |
| **Implemented in Plan Version** | Phase 3 Stage 3A |

---

### DW-010: requireSelfScope() Shared Function

| Field | Value |
|-------|-------|
| **ID** | DW-010 |
| **Date Deferred** | 2026-04-10 |
| **Source Plan Section** | PLAN-RBAC-001 |
| **Source Phase** | Phase 2 — Access Control (RBAC) |
| **Title** | Server-side requireSelfScope() guard function |
| **Reason Deferred** | Phase 2 focused on schema, helpers, and edge function foundation; requireSelfScope() is needed when user-owned resource endpoints are built |
| **Blocking Dependencies** | getSessionContext() operational (done); user-owned resource endpoints exist (Phase 3/4) |
| **Impact on Source Phase** | No impact on Phase 2 gate — requireSelfScope() is a downstream consumer utility |
| **Future Owner Phase** | Phase 3 — Core Services (needed before user-management self-scope endpoints) |
| **Future Owner Module** | PLAN-RBAC-001, PLAN-USRMGMT-001 |
| **Required Plan Realignment** | Phase 3 must implement requireSelfScope() before user-management self-edit/self-view endpoints |
| **Related Decisions** | — |
| **Related Actions** | ACT-015, ACT-017 |
| **Required Tests for Closure** | Own resource → access allowed; other user's resource → 403; admin override if applicable; null/missing userId → 403 |
| **Status** | `implemented` |
| **Implemented by Action** | ACT-023 |
| **Implemented in Plan Version** | Phase 3 Stage 3A |

---

## Summary Dashboard

| ID | Title | Source Phase | Future Phase | Status |
|----|-------|-------------|--------------|--------|
| DW-001 | Google OAuth | Phase 1 | `unassigned` (v2) | `deferred (v2)` |
| DW-002 | Apple Sign-In | Phase 1 | `unassigned` (v2) | `deferred (v2)` |
| DW-003 | Permission Allow/Deny Tests | Phase 2 | Phase 3 | `implemented` |
| DW-004 | DB-Level RLS Verification | Phase 2 | Phase 3 | `implemented` |
| DW-005 | Cross-Tenant Isolation Scope | Phase 2 | N/A (DEC-022) | `cancelled` |
| DW-006 | Cache Invalidation Verification | Phase 2 | Phase 3 | `implemented` |
| DW-007 | Moderator Role | Phase 2 | `unassigned` (v2) | `deferred (v2)` |
| DW-008 | MFA Recovery Codes | Phase 1 | Phase 6 | `implemented` |
| DW-009 | requireRole() Shared Function | Phase 2 | Phase 3 | `implemented` |
| DW-010 | requireSelfScope() Shared Function | Phase 2 | Phase 3 | `implemented` |
| DW-011 | Distributed Rate Limiting | Phase 3 | Phase 6 | `deferred (v2)` |
| DW-012 | Authenticated lifecycle test infrastructure | Phase 3 | Phase 6 | `implemented` |
| DW-013 | Orphaned test-user cleanup automation | Phase 3 | Phase 6 | `implemented` |
| DW-014 | Denial audit logging | Phase 3 | Phase 3.5 | `implemented` |
| DW-015 | Superadmin guardrails | Phase 3 | Phase 3.5 | `implemented` |
| DW-016 | Admin Monitoring/Health UI | Phase 4 | Phase 5 | `implemented` |
| DW-017 | Admin Jobs/Config UI | Phase 4 | Phase 5 | `implemented` |
| DW-018 | User Password Change Flow | Phase 4 | Phase 4 (Stage 4J) | `implemented` |
| DW-019 | User Session Revocation | Phase 4 | Phase 5 | `implemented` |
| DW-020 | User Notification Preferences | Phase 4 | `unassigned` (v2) | `deferred (v2)` |
| DW-021 | DB-level admin user search (replace auth.admin.listUsers) | Phase 4 | Phase 6 | `implemented` |
| DW-022 | Server-shaped admin user DTO/view | Phase 4 | Phase 6 | `implemented` |
| DW-023 | Audit actor-scope display shaping | Phase 4 | Phase 6 | `implemented` |
| DW-024 | Admin panel unbounded client-side aggregation queries | Phase 4 | Phase 6 | `implemented` |
| DW-025 | Role creation (create-role edge function + UI) | Phase 4 | Phase 6 | `implemented` |
| DW-026 | Role deletion (delete-role edge function + UI) | Phase 4 | Phase 6 | `implemented` |
| DW-027 | Admin Edit User Profile | Phase 4 | Phase 4 (Stage 4K) | `implemented` |
| DW-028 | True fail-closed audit rollback (alert config) | Phase 5 | Phase 6 | `deferred` |
| DW-029 | Batched audit cleanup DELETE | Phase 5 | Phase 6 | `deferred` |
| DW-030 | TypeScript strict mode | Phase 6 | `unassigned` (v2) | `deferred` |
| DW-031 | Service worker (Workbox) | Phase 6 | `unassigned` (v2) | `deferred` |
| DW-032 | CDN security headers (X-Frame-Options, early hints) | Phase 6 | `unassigned` (v2) | `deferred` |
| DW-033 | Auth page label/input association | Phase 6 | Phase 7 | `deferred` |
| DW-034 | Superadmin Assignment Notification Email | Post-Phase 6 | `unassigned` (v2) | `deferred (v2)` |
| DW-035 | Invite-Only Signup Flow | Post-Phase 6 | `unassigned` (v2) | `deferred (v2)` |


### DW-011: Distributed Rate Limiting

| Field | Value |
|-------|-------|
| **ID** | DW-011 |
| **Date Deferred** | 2026-04-10 |
| **Source Plan Section** | PLAN-API-001 |
| **Source Phase** | Phase 3 — Core Services (API) |
| **Title** | Distributed/shared rate limiting for privileged endpoints |
| **Reason Deferred** | Current in-memory per-isolate rate limiting is adequate defense-in-depth for development but not institutional-grade for production — cold starts reset counters, no cross-isolate coordination |
| **Blocking Dependencies** | Redis/Upstash or equivalent distributed store; production traffic patterns for tuning |
| **Impact on Source Phase** | No impact — current limiter is functional and deployed; this is a hardening improvement |
| **Future Owner Phase** | Phase 6 — Hardening & System Validation |
| **Future Owner Module** | PLAN-API-001 |
| **Required Plan Realignment** | Phase 6 must include: centralized rate limit backing store, durable counters, abuse telemetry, admin monitoring dashboard integration |
| **Related Decisions** | — |
| **Related Actions** | ACT-027 (rate limiting introduced), ACT-028 (rate limiter hardened) |
| **Required Tests for Closure** | Cross-isolate rate limit enforcement, cold-start counter persistence, abuse pattern detection, admin dashboard rate limit visibility |
| **Status** | `deferred (v2)` |
| **Implemented by Action** | N/A — deferred to v2. In-memory per-isolate limiter retained as defense-in-depth. Requires Upstash Redis for institutional-grade enforcement. |
| **Implemented in Plan Version** | v11.0 (closure decision) |

---

### DW-012: Authenticated lifecycle test infrastructure (409, rollback-path coverage)

| Field | Value |
|-------|-------|
| **ID** | DW-012 |
| **Source Plan Section** | PLAN-USRMGMT-001 |
| **Source Phase** | Phase 3 — Core Services (User Management) |
| **Title** | Authenticated lifecycle test infrastructure for 409 + rollback-path coverage |
| **Reason Deferred** | Tests for already-deactivated (409), already-active (409), invalid UUID (400), missing body (400) require authenticated admin tokens. Rollback-path tests (unban failure → no status change, profile update failure → re-ban) require mockable wrappers around `supabaseAdmin.auth.admin` calls for failure injection. Neither infrastructure exists yet. |
| **Blocking Dependencies** | Test harness for admin token provisioning; mockable auth admin client wrapper; non-production failure injection mechanism |
| **Impact on Source Phase** | Moderate — current unauthenticated boundary tests provide basic coverage; auth-required paths are the higher-value regression surface |
| **Future Owner Phase** | Phase 6 — Hardening & System Validation |
| **Future Owner Module** | PLAN-USRMGMT-001 |
| **Required Plan Realignment** | Phase 6 must include: test admin user provisioning, auth admin mock wrapper, failure injection for deactivate/reactivate rollback paths, auto-cleanup of test artifacts |
| **Related Decisions** | — |
| **Related Actions** | ACT-030 (regression tests created), ACT-031 (evidence corrected) |
| **Required Tests for Closure** | deactivate already-deactivated → 409; reactivate already-active → 409; invalid UUID → 400; missing body → 400; unban failure → no profile change; profile update failure after unban → re-ban; ban failure on deactivation → rollback to active; audit write failure → no mutation |
| **Status** | `assigned` |
| **Implemented by Action** | — |
| **Implemented in Plan Version** | — |

---

### DW-013: Orphaned test-user cleanup automation

| Field | Value |
|-------|-------|
| **ID** | DW-013 |
| **Source Plan Section** | PLAN-USRMGMT-001 |
| **Source Phase** | Phase 3 — Core Services (User Management) |
| **Title** | Automated test-user cleanup after lifecycle verification |
| **Reason Deferred** | Supabase `auth.admin.deleteUser()` fails when profile triggers have FK or validation dependencies. Manual dashboard deletion is required. Future test harnesses must auto-clean on both success and failure paths. |
| **Blocking Dependencies** | Understanding of Supabase auth deletion trigger chain; test harness design |
| **Impact on Source Phase** | Low — only 3 orphaned users; operational not security risk |
| **Future Owner Phase** | Phase 6 — Hardening & System Validation |
| **Future Owner Module** | PLAN-USRMGMT-001 |
| **Required Plan Realignment** | Test harness must include cleanup-on-exit for all test users |
| **Related Decisions** | — |
| **Related Actions** | ACT-031 (orphan documented) |
| **Required Tests for Closure** | Verify test-user creation and deletion both succeed programmatically |
| **Status** | `assigned` |
| **Implemented by Action** | — |
| **Implemented in Plan Version** | — |

---

### DW-014: Denial Audit Logging

| Field | Value |
|-------|-------|
| **ID** | DW-014 |
| **Date Deferred** | 2026-04-10 |
| **Source Plan Section** | PLAN-AUDIT-001 |
| **Source Phase** | Phase 3 — Core Services (Audit) |
| **Title** | Audit log entries for permission denials |
| **Reason Deferred** | Gate 1 reviewer noted denied actions are enforced but not logged to audit trail. Current behavior is fail-secure (403 returned) but denials are not auditable. |
| **Blocking Dependencies** | None — logAuditEvent infrastructure exists; requires adding calls on PermissionDeniedError catch paths |
| **Impact on Source Phase** | No impact — Phase 3 gates passed. This is a hardening improvement. |
| **Future Owner Phase** | Phase 3.5 — Security Hardening |
| **Future Owner Module** | PLAN-AUDIT-001, PLAN-API-001 |
| **Required Plan Realignment** | Phase 6 must add denial logging to handler.ts PermissionDeniedError catch path with user_id, permission, resource, correlation_id |
| **Related Decisions** | — |
| **Related Actions** | ACT-035 (Gate 1 reviewer note) |
| **Required Tests for Closure** | Denied request → audit_logs entry with action='auth.permission_denied'; log contains actor_id, permission_key, correlation_id; no sensitive data in denial metadata |
| **Status** | `implemented` |
| **Implemented by Action** | Phase 3.5A — Stage 3.5 plan execution |
| **Implemented in Plan Version** | v9 |
| **Resolution Note** | Centralized denial interception in handler.ts. PermissionDeniedError enriched with userId (authoritative) and reason. JWT fallback as best-effort enrichment only. actor_id nullable (no fake sentinels). Event: auth.permission_denied with metadata including permission_key, reason, endpoint, actor_known, correlation_id. Runtime-verified: permission denial + cross-user access both produce correct audit rows. |

---

### DW-015: Superadmin Guardrails

| Field | Value |
|-------|-------|
| **ID** | DW-015 |
| **Date Deferred** | 2026-04-10 |
| **Source Plan Section** | PLAN-RBAC-001 |
| **Source Phase** | Phase 3 — Core Services (RBAC) |
| **Title** | Superadmin guardrails for high-risk RBAC actions |
| **Reason Deferred** | Gate 1 reviewer noted superadmin bypasses all permission checks via is_superadmin(). High-risk actions (role changes, user deletion) have no additional gate even for superadmin. Design note, not a security vulnerability. |
| **Blocking Dependencies** | Design decision on which actions require explicit permission even for superadmin |
| **Impact on Source Phase** | No impact — Phase 3 gates passed. This is an A+ hardening recommendation. |
| **Future Owner Phase** | Phase 3.5 — Security Hardening |
| **Future Owner Module** | PLAN-RBAC-001 |
| **Required Plan Realignment** | No RBAC redesign. Surgical hardening only: requireRecentAuth on RBAC endpoints + self-superadmin-revocation prevention. |
| **Related Decisions** | — |
| **Related Actions** | ACT-035 (Gate 1 reviewer note) |
| **Required Tests for Closure** | All 6 high-risk endpoints enforce requireRecentAuth(); self-superadmin-revocation blocked with 403; no new SQL functions; no RBAC model drift |
| **Status** | `implemented` |
| **Implemented by Action** | Phase 3.5B — Stage 3.5 plan execution |
| **Implemented in Plan Version** | v9 |
| **Resolution Note** | Added requireRecentAuth() to assign-role, revoke-role, assign-permission-to-role, revoke-permission-from-role (4 endpoints that were missing it). Self-superadmin-revocation prevention added to revoke-role (403 if actor revokes own superadmin role). No new SQL functions, no new seed data, no RBAC model changes. Existing has_permission()/is_superadmin() behavior unchanged. |

---

- [Master Plan](master-plan.md)
- [Approved Decisions](approved-decisions.md)
- [Action Tracker](../06-tracking/action-tracker.md)
- [Change Control Policy](../00-governance/change-control-policy.md)

### DW-016: Admin Monitoring/Health UI

| Field | Value |
|-------|-------|
| **ID** | DW-016 |
| **Date Deferred** | 2026-04-10 |
| **Source Plan Section** | PLAN-ADMIN-001 (monitoring & health scope) |
| **Source Phase** | Phase 4 — Admin & User Interfaces |
| **Title** | Admin health dashboard, alert configuration, and monitoring UI |
| **Reason Deferred** | No health-check endpoint, monitoring backend, or alert system exists yet |
| **Blocking Dependencies** | Health monitoring module backend implementation |
| **Impact on Source Phase** | Phase 4 delivers user/role/audit admin surfaces; monitoring UI deferred |
| **Future Owner Phase** | Phase 5 — Health & Monitoring |
| **Future Owner Module** | PLAN-ADMIN-001, PLAN-HEALTH-001 |
| **Required Plan Realignment** | Phase 5 must include monitoring UI as part of health module delivery |
| **Related Decisions** | — |
| **Related Actions** | — |
| **Required Tests for Closure** | Health dashboard renders, alert config CRUD, monitoring permission enforcement |
| **Status** | `implemented` |
| **Implemented by Action** | ACT-063 |
| **Implemented in Plan Version** | v10.1 |
| **Resolution Note** | AdminHealthPage created with system snapshots, metrics, alert history. Permission-gated by monitoring.view. |

---

### DW-017: Admin Jobs/Config UI

| Field | Value |
|-------|-------|
| **ID** | DW-017 |
| **Date Deferred** | 2026-04-10 |
| **Source Plan Section** | PLAN-ADMIN-001 (jobs & config scope) |
| **Source Phase** | Phase 4 — Admin & User Interfaces |
| **Title** | Admin jobs dashboard, job trigger, dead-letter management, kill switch, and system config UI |
| **Reason Deferred** | No job/scheduler backend or config management backend exists yet |
| **Blocking Dependencies** | Jobs & scheduler module backend, config management backend |
| **Impact on Source Phase** | Phase 4 delivers user/role/audit admin surfaces; jobs/config UI deferred |
| **Future Owner Phase** | Phase 5 — Jobs & Scheduler |
| **Future Owner Module** | PLAN-ADMIN-001, PLAN-JOBS-001 |
| **Required Plan Realignment** | Phase 5 must include jobs/config UI as part of module delivery |
| **Related Decisions** | — |
| **Related Actions** | — |
| **Required Tests for Closure** | Jobs dashboard renders, trigger/deadletter/kill-switch flows, config CRUD, permission enforcement |
| **Status** | `implemented` |
| **Implemented by Action** | ACT-063 |
| **Implemented in Plan Version** | v10.1 |
| **Resolution Note** | AdminJobsPage created with job registry, execution logs, dead-letter management, kill switch + pause/resume controls. Permission-gated by jobs.view / jobs.manage / jobs.emergency. |

---

### DW-018: User Password Change Flow

| Field | Value |
|-------|-------|
| **ID** | DW-018 |
| **Date Deferred** | 2026-04-10 |
| **Source Plan Section** | PLAN-USRPNL-001 (password change scope) |
| **Source Phase** | Phase 4 — Admin & User Interfaces |
| **Title** | User self-service password change within user panel |
| **Reason Deferred** | Requires Supabase `updateUser()` password integration + re-auth flow not yet built |
| **Blocking Dependencies** | Re-auth UI pattern, Supabase password update integration |
| **Impact on Source Phase** | Phase 4 delivers profile editing, MFA, and session info; password change deferred |
| **Future Owner Phase** | Phase 4 follow-up or Phase 5 |
| **Future Owner Module** | PLAN-USRPNL-001 |
| **Required Plan Realignment** | Must be included in SecurityPage when re-auth pattern is available |
| **Related Decisions** | — |
| **Related Actions** | ACT-042 |
| **Required Tests for Closure** | Password change E2E, re-auth required, old password validation, audit logging |
| **Status** | `implemented` |
| **Implemented by Action** | ACT-042 |
| **Implemented in Plan Version** | v9 |

---

### DW-019: User Session Revocation

| Field | Value |
|-------|-------|
| **ID** | DW-019 |
| **Date Deferred** | 2026-04-10 |
| **Source Plan Section** | PLAN-USRPNL-001 (session revocation scope) |
| **Source Phase** | Phase 4 — Admin & User Interfaces |
| **Title** | User self-service session listing and revocation |
| **Reason Deferred** | Supabase session revocation API integration not yet built |
| **Blocking Dependencies** | Supabase session management API integration, session listing endpoint |
| **Impact on Source Phase** | Phase 4 delivers read-only session info; revocation controls deferred |
| **Future Owner Phase** | Phase 4 follow-up or Phase 5 |
| **Future Owner Module** | PLAN-USRPNL-001 |
| **Required Plan Realignment** | Must be added to SecurityPage when session API is integrated |
| **Related Decisions** | — |
| **Related Actions** | — |
| **Required Tests for Closure** | Session list renders, revoke session E2E, audit logging, self-scope enforcement |
| **Status** | `implemented` |
| **Implemented by Action** | ACT-063 |
| **Implemented in Plan Version** | v10.1 |
| **Resolution Note** | revoke-sessions edge function + SecurityPage UI. Self-scope enforced (ctx.user.id). Supports 'others' and 'global' scopes. Requires requireRecentAuth(30min). Audit: user.sessions_revoked. |

---

### DW-020: User Notification Preferences

| Field | Value |
|-------|-------|
| **ID** | DW-020 |
| **Date Deferred** | 2026-04-10 |
| **Source Plan Section** | PLAN-USRPNL-001 (notification/preferences scope) |
| **Source Phase** | Phase 4 — Admin & User Interfaces |
| **Title** | User notification and preference management |
| **Reason Deferred** | No notification system backend exists |
| **Blocking Dependencies** | Notification system backend, preference storage schema |
| **Impact on Source Phase** | Phase 4 delivers core user panel; notification preferences deferred |
| **Future Owner Phase** | `unassigned` — v2 scope |
| **Future Owner Module** | PLAN-USRPNL-001 |
| **Required Plan Realignment** | Requires new notification module or extension to user-management |
| **Related Decisions** | — |
| **Related Actions** | — |
| **Required Tests for Closure** | Preference CRUD, notification delivery based on preferences |
| **Status** | `deferred (v2)` |
| **Implemented by Action** | — |
| **Implemented in Plan Version** | — |
| **Resolution Note** | Deferred to v2 — no notification backend exists. Implementing from scratch is beyond Phase 6 hardening scope. |

---

### DW-021: DB-Level Admin User Search

| Field | Value |
|-------|-------|
| **ID** | DW-021 |
| **Date Deferred** | 2026-04-11 |
| **Source Plan Section** | PLAN-ADMIN-001 (user management) |
| **Source Phase** | Phase 4 — Admin & User Interfaces (Stage 4B) |
| **Title** | Replace auth.admin.listUsers() email search with DB-level mechanism |
| **Reason Deferred** | Current list-users email search uses auth.admin.listUsers(perPage:1000) + in-memory filter + ID injection. Works at small scale with caching and 500-ID cap, but not institution-grade for large tenants. |
| **Blocking Dependencies** | DB view or function joining profiles + auth email, or materialized email column synced to profiles |
| **Impact on Source Phase** | No impact — Stage 4B functionally complete; this is a scalability hardening item |
| **Future Owner Phase** | Phase 6 — Hardening & System Validation |
| **Future Owner Module** | PLAN-ADMIN-001, PLAN-USRMGMT-001 |
| **Required Plan Realignment** | Phase 6 must include admin search scalability review |
| **Related Decisions** | — |
| **Related Actions** | — |
| **Required Tests for Closure** | Email search works beyond 1000 users; no auth.admin.listUsers() in search path; query performance < 500ms at 10K users |
| **Status** | `assigned` |
| **Implemented by Action** | — |
| **Implemented in Plan Version** | — |

---

### DW-022: Server-Shaped Admin User DTO/View

| Field | Value |
|-------|-------|
| **ID** | DW-022 |
| **Date Deferred** | 2026-04-11 |
| **Source Plan Section** | PLAN-ADMIN-001 (user management) |
| **Source Phase** | Phase 4 — Admin & User Interfaces (Stage 4B) |
| **Title** | Single DB-level query/view returning fully shaped admin user objects |
| **Reason Deferred** | Current list-users enriches profiles with email + roles via separate queries in app layer. Functionally correct with batch approach, but not optimally server-shaped. |
| **Blocking Dependencies** | DB view or function combining profiles + email + roles into single result set |
| **Impact on Source Phase** | No impact — current batch approach is correct, not N+1 |
| **Future Owner Phase** | Phase 6 — Hardening & System Validation |
| **Future Owner Module** | PLAN-ADMIN-001 |
| **Required Plan Realignment** | Phase 6 must evaluate admin user DTO design |
| **Related Decisions** | — |
| **Related Actions** | — |
| **Required Tests for Closure** | Single query returns user + email + roles; response time < 200ms at 10K users |
| **Status** | `assigned` |
| **Implemented by Action** | — |
| **Implemented in Plan Version** | — |

---

### DW-023: Audit Actor-Scope Display Shaping

| Field | Value |
|-------|-------|
| **ID** | DW-023 |
| **Date Deferred** | 2026-04-11 |
| **Source Plan Section** | PLAN-ADMIN-001 (user detail) |
| **Source Phase** | Phase 4 — Admin & User Interfaces (Stage 4B) |
| **Title** | Audit trail actor display name resolution and actor-as-subject scope |
| **Reason Deferred** | Current user detail audit trail shows events where user is target only, not actor. Actor IDs are raw UUIDs without display name resolution. Both are UX improvements, not plan violations. |
| **Blocking Dependencies** | Actor display name enrichment in audit query response; design decision on actor-scope inclusion |
| **Impact on Source Phase** | No impact — target-scope audit is correct for Stage 4B |
| **Future Owner Phase** | Phase 5+ (deeper audit UX work) |
| **Future Owner Module** | PLAN-ADMIN-001, PLAN-AUDIT-001 |
| **Required Plan Realignment** | Future audit UX phase must include actor enrichment |
| **Related Decisions** | — |
| **Related Actions** | — |
| **Required Tests for Closure** | Audit entries show actor display name; optional actor-scope toggle works; no N+1 for actor resolution |
| **Status** | `assigned` |
| **Implemented by Action** | — |
| **Implemented in Plan Version** | — |

---

### DW-024: Admin Panel Unbounded Client-Side Aggregation Queries

| Field | Value |
|-------|-------|
| **ID** | DW-024 |
| **Date Deferred** | 2026-04-11 |
| **Source Plan Section** | PLAN-ADMIN-001 (admin dashboard + role list) |
| **Source Phase** | Phase 4 — Admin & User Interfaces (Stage 4B + 4C) |
| **Title** | AdminDashboard useRolesBreakdown and AdminRolesPage fetchRoles fetch unbounded tables client-side |
| **Reason Deferred** | (1) useRolesBreakdown fetches entire user_roles table with .select('role_id') and no limit. (2) fetchRoles fetches all role_permissions and all user_roles to compute per-role permission/user counts. Both are RLS-enforced and correct at current scale, but unbounded for large tenants. |
| **Blocking Dependencies** | DB functions for role assignment counts / permission counts, or server-side aggregation endpoint |
| **Impact on Source Phase** | No impact — correct at current scale |
| **Future Owner Phase** | Phase 6 — Hardening & System Validation |
| **Future Owner Module** | PLAN-ADMIN-001 |
| **Required Plan Realignment** | Phase 6 must include dashboard + role list query optimization |
| **Related Decisions** | — |
| **Related Actions** | — |
| **Required Tests for Closure** | Dashboard and role list load in < 1s at 10K users; no unbounded client-side fetches |
| **Status** | `assigned` |
| **Implemented by Action** | — |
| **Implemented in Plan Version** | — |

---

---

### DW-025: Role Creation (create-role Edge Function + UI)

| Field | Value |
|-------|-------|
| **ID** | DW-025 |
| **Date Deferred** | 2026-04-11 |
| **Source Plan Section** | PLAN-ADMIN-001 (admin-panel.md documents role CRUD as planned capability) |
| **Original Description** | Allow admins with `roles.create` permission to create new custom roles via edge function and admin UI form. Permission `roles.create` already exists in the database. |
| **Why Deferred** | Stage 4C scope was explicitly limited to role list/detail and assign/revoke operations. Role creation was documented in admin-panel.md but never scheduled into any stage plan. |
| **Blocking Dependencies** | None — `roles.create` permission already seeded. Requires new `create-role` edge function + UI form. |
| **Target Phase** | Phase 6 (hardening) |
| **Risk If Forgotten** | Medium — admins cannot create custom roles, limiting RBAC flexibility. All roles must be seeded via SQL. |
| **Status** | `implemented` |
| **Implemented by Action** | ACT-050 |
| **Implemented in Plan Version** | v9 |

---

### DW-026: Role Deletion (delete-role Edge Function + UI)

| Field | Value |
|-------|-------|
| **ID** | DW-026 |
| **Date Deferred** | 2026-04-11 |
| **Source Plan Section** | PLAN-ADMIN-001 (admin-panel.md documents role CRUD as planned capability) |
| **Original Description** | Allow admins with `roles.delete` permission to delete non-immutable, non-base roles. Permission `roles.delete` already exists in the database. DB trigger `prevent_immutable_role_delete` already protects immutable roles. |
| **Why Deferred** | Stage 4C scope was explicitly limited to role list/detail and assign/revoke. Role deletion was never scheduled. |
| **Blocking Dependencies** | DW-025 (role creation should land first so there are deletable roles). Must handle cascade: reassign or block if users are assigned to the role. |
| **Target Phase** | Phase 6 (hardening) |
| **Risk If Forgotten** | Low — immutable roles cannot be deleted anyway; custom roles (once DW-025 lands) would accumulate without cleanup. |
| **Status** | `implemented` |
| **Implemented by Action** | ACT-050 |
| **Implemented in Plan Version** | v9 |

---

### DW-027: Admin Edit User Profile (users.edit_any UI)

| Field | Value |
|-------|-------|
| **ID** | DW-027 |
| **Date Deferred** | 2026-04-11 |
| **Source Plan Section** | PLAN-ADMIN-001 (admin-panel.md documents admin user editing as planned capability) |
| **Original Description** | Allow admins with `users.edit_any` permission to edit another user's display name and avatar via the admin UI. The `update-profile` edge function already partially supports admin edits (it accepts `user_id` param). The `users.edit_any` permission is seeded in the DB. Only the admin-side UI form on UserDetailPage is missing. |
| **Why Deferred** | Stage 4B scope covered view/deactivate/reactivate only. Admin profile editing was not scheduled into any stage. |
| **Blocking Dependencies** | Stage 4E (user self-service profile edit) should land first to establish the profile editing pattern. |
| **Target Phase** | Phase 4 (Stage 4K) |
| **Risk If Forgotten** | Medium — `users.edit_any` permission exists but is non-functional from UI; admins must use direct DB access to edit user profiles. |
| **Related Actions** | ACT-043 |
| **Status** | `implemented` |
| **Implemented by Action** | ACT-043 |
| **Implemented in Plan Version** | v9 |

---

### DW-028: True Fail-Closed Audit Rollback for health-alert-config Update Path

| Field | Value |
|-------|-------|
| **ID** | DW-028 |
| **Date Deferred** | 2026-04-12 |
| **Source Plan Section** | PLAN-HEALTH-001 (Stage 5B — health-alert-config endpoint) |
| **Source Phase** | Phase 5 — Operations & Reliability |
| **Title** | True fail-closed audit rollback for alert config update |
| **Reason Deferred** | The update path persists the DB change before calling `logAuditEvent()`. If audit fails, the change remains in DB but the caller receives 500. True rollback requires pre-fetching old values before the update statement, which adds complexity for a low-frequency operation. Practical risk is acceptable: config changes are rare, the 500 surfaces the error, and missing audit records are detectable via monitoring gap analysis. |
| **Blocking Dependencies** | None — implementation is straightforward (pre-fetch + restore on audit failure) |
| **Impact on Source Phase** | Minimal — alert config updates still work; only the audit trail is incomplete on failure |
| **Future Owner Phase** | Phase 6 |
| **Future Owner Module** | health-monitoring |
| **Required Plan Realignment** | Add pre-fetch + restore logic to `health-alert-config` update path |
| **Related Decisions** | — |
| **Related Actions** | ACT-058 |
| **Required Tests for Closure** | (1) Update with simulated audit failure restores original values. (2) Caller receives appropriate error. (3) No orphaned config changes without audit records. |
| **Status** | `deferred` |
| **Implemented by Action** | — |
| **Implemented in Plan Version** | — |

---

### DW-029: Batched Audit Cleanup DELETE

| Field | Value |
|-------|-------|
| **ID** | DW-029 |
| **Date Deferred** | 2026-04-12 |
| **Source Plan Section** | PLAN-JOBS-001 (Stage 5D — audit_cleanup job) |
| **Source Phase** | Phase 5 — Operations & Reliability |
| **Title** | Batched DELETE for audit_cleanup job |
| **Reason Deferred** | The current implementation does a single unbounded `DELETE FROM audit_logs WHERE created_at < cutoff`. The Supabase REST API does not support LIMIT on DELETE. At current scale (near-zero records) this is fine, but at millions of rows over 90 days the single DELETE will exceed the 30-second edge function timeout. The correct fix is a PostgreSQL function (via RPC) that deletes in batches of N rows and returns the count. |
| **Blocking Dependencies** | None — requires creating an RPC function for batched delete |
| **Impact on Source Phase** | Minimal — audit cleanup works correctly at current scale |
| **Future Owner Phase** | Phase 6 |
| **Future Owner Module** | jobs-and-scheduler |
| **Required Plan Realignment** | Add `rpc_batch_delete_audit_logs(cutoff, batch_size)` DB function and update `job-audit-cleanup` to call it in a loop |
| **Related Decisions** | DEC-007 (90-day retention) |
| **Related Actions** | ACT-060 |
| **Required Tests for Closure** | (1) Batch delete removes correct records. (2) Multiple batches complete within timeout. (3) No records newer than cutoff are deleted. |
| **Status** | `deferred` |
| **Implemented by Action** | — |
| **Implemented in Plan Version** | — |

---

### DW-030: TypeScript Strict Mode

| Field | Value |
|-------|-------|
| **ID** | DW-030 |
| **Date Deferred** | 2026-04-12 |
| **Source Plan Section** | Performance & Quality Audit Round 2 — Build & Configuration |
| **Source Phase** | Phase 6 — Performance Optimization |
| **Title** | Enable TypeScript strict mode (strict: true in tsconfig.app.json) |
| **Reason Deferred** | Enabling strict mode surfaces ~50+ type errors requiring a dedicated refactoring pass. Current codebase compiles cleanly with strict: false. Worth +5 audit points but requires significant effort. |
| **Blocking Dependencies** | None — purely a code quality improvement |
| **Impact on Source Phase** | Build & Config score remains 97/100 instead of 100/100 |
| **Future Owner Phase** | `unassigned` (v2) |
| **Future Owner Module** | All modules |
| **Required Plan Realignment** | Dedicated strict-mode migration sprint; fix all `as any` casts, add null checks, resolve implicit-any imports |
| **Related Decisions** | — |
| **Related Actions** | — |
| **Required Tests for Closure** | `npx tsc --noEmit` passes with strict: true; zero `as any` casts remain; all 82+ tests still pass |
| **Status** | `deferred` |
| **Implemented by Action** | — |
| **Implemented in Plan Version** | — |

---

### DW-031: Service Worker (Workbox)

| Field | Value |
|-------|-------|
| **ID** | DW-031 |
| **Date Deferred** | 2026-04-12 |
| **Source Plan Section** | Performance & Quality Audit Round 2 — Load Strategy |
| **Source Phase** | Phase 6 — Performance Optimization |
| **Title** | Add Workbox-based service worker for offline asset caching |
| **Reason Deferred** | Architectural decision needed on caching strategy, cache invalidation, and offline behavior for an admin panel. Lower priority — admin panels rarely need offline support. Worth +3 audit points. |
| **Blocking Dependencies** | Decision on cache-first vs network-first strategy; Workbox configuration design |
| **Impact on Source Phase** | Load Strategy score remains 88/100 instead of 91/100 |
| **Future Owner Phase** | `unassigned` (v2) |
| **Future Owner Module** | Frontend infrastructure |
| **Required Plan Realignment** | Add service worker registration to main.tsx; configure Workbox precache manifest; test cache invalidation on deploy |
| **Related Decisions** | — |
| **Related Actions** | — |
| **Required Tests for Closure** | Service worker registers successfully; vendor chunks served from cache on repeat visits; cache invalidates on new deploy; no stale content served |
| **Status** | `deferred` |
| **Implemented by Action** | — |
| **Implemented in Plan Version** | — |

---

### DW-032: CDN Security Headers

| Field | Value |
|-------|-------|
| **ID** | DW-032 |
| **Date Deferred** | 2026-04-12 |
| **Source Plan Section** | Performance & Quality Audit Round 2 — Security Headers |
| **Source Phase** | Phase 6 — Performance Optimization |
| **Title** | HTTP response headers (X-Frame-Options, X-Content-Type-Options, HTTP/2 early hints) |
| **Reason Deferred** | These headers must be configured at the CDN/hosting layer, not in application code. Meta tags are advisory only. Worth +4 audit points total. |
| **Blocking Dependencies** | CDN/hosting access for response header configuration |
| **Impact on Source Phase** | Security Headers score remains 96/100 instead of 100/100 |
| **Future Owner Phase** | `unassigned` (v2) |
| **Future Owner Module** | Infrastructure/DevOps |
| **Required Plan Realignment** | Configure hosting provider to add X-Frame-Options: DENY, X-Content-Type-Options: nosniff, and Link preload headers |
| **Related Decisions** | — |
| **Related Actions** | — |
| **Required Tests for Closure** | curl -I shows correct response headers; security scanner confirms headers present |
| **Status** | `deferred` |
| **Implemented by Action** | — |
| **Implemented in Plan Version** | — |

---

### DW-033: Auth Page Input/Label Association

| Field | Value |
|-------|-------|
| **ID** | DW-033 |
| **Date Deferred** | 2026-04-12 |
| **Source Plan Section** | Performance & Quality Audit Round 2 — Accessibility |
| **Source Phase** | Phase 6 — Performance Optimization |
| **Title** | Add id attributes to SignIn/SignUp/ForgotPassword/ResetPassword inputs for label htmlFor association |
| **Reason Deferred** | Minor accessibility gap — auth page inputs have visible labels but lack programmatic id/htmlFor binding. Worth +1 audit point. |
| **Blocking Dependencies** | None |
| **Impact on Source Phase** | Accessibility score remains 98/100 instead of 99/100 |
| **Future Owner Phase** | Phase 7 (next minor release) |
| **Future Owner Module** | Auth module UI |
| **Required Plan Realignment** | Add matching id to each Input and htmlFor to each Label on auth pages |
| **Related Decisions** | — |
| **Related Actions** | — |
| **Required Tests for Closure** | Screen reader announces correct label for every auth form input; axe-core scan shows zero label-association violations |
| **Status** | `deferred` |
| **Implemented by Action** | — |
| **Implemented in Plan Version** | — |

---

### DW-034: Superadmin Assignment Notification Email

| Field | Value |
|-------|-------|
| **ID** | DW-034 |
| **Date Deferred** | 2026-04-13 |
| **Source Plan Section** | RBAC Governance Hardening |
| **Source Phase** | Post-Phase 6 |
| **Title** | Out-of-band email notification when superadmin is assigned |
| **Reason Deferred** | No transactional email service configured for v1. The event is fully audited in audit_logs (rbac.role_assigned with assigned_by_is_superadmin: true) but no email notification fires. |
| **Blocking Dependencies** | Transactional email provider integration (SendGrid, Resend, or similar) |
| **Impact on Source Phase** | None — audit trail is complete; email is defense-in-depth |
| **Future Owner Phase** | `unassigned` (v2) |
| **Future Owner Module** | RBAC, Auth |
| **Required Plan Realignment** | v2 must include email notification service and template for superadmin assignment events |
| **Related Decisions** | — |
| **Related Actions** | — |
| **Required Tests for Closure** | Superadmin assignment triggers email to both assignor and assignee; email contains actor, target, timestamp, correlation ID; no sensitive data in email body |
| **Status** | `deferred (v2)` |
| **Implemented by Action** | — |
| **Implemented in Plan Version** | — |

---

### DW-035: Invite-Only Signup Flow

| Field | Value |
|-------|-------|
| **ID** | DW-035 |
| **Date Deferred** | 2026-04-13 |
| **Source Plan Section** | RBAC Governance Hardening |
| **Source Phase** | Post-Phase 6 |
| **Title** | Admin-controlled invite-only user signup (disable open registration) |
| **Reason Deferred** | Currently any person can register at the sign-up URL. All RBAC protections mean registered users have no admin access without explicit role assignment, but the open signup surface exists. Full invite flow requires email token generation, invite management UI, and Supabase signup restriction. |
| **Blocking Dependencies** | Transactional email provider; invite token edge function; invite management admin UI; Supabase "Allow new users to sign up" dashboard setting coordination |
| **Impact on Source Phase** | None — all registered users are properly RBAC-gated; open signup is a governance preference not a security vulnerability |
| **Future Owner Phase** | `unassigned` (v2) |
| **Future Owner Module** | Auth, Admin Panel |
| **Required Plan Realignment** | v2 must include: invite token generation endpoint, invite list admin UI, email delivery of invite links, Supabase signup restriction toggle, first-signup bootstrap compatibility (first invite = superadmin) |
| **Related Decisions** | — |
| **Related Actions** | — |
| **Required Tests for Closure** | Non-invited email cannot create account; invited email can create account via token; expired invite rejected; invite revocation works; first invite creates superadmin correctly |
| **Status** | `deferred (v2)` |
| **Implemented by Action** | — |
| **Implemented in Plan Version** | — |

---

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
