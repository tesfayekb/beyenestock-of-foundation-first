# Master Plan

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-10

## Purpose

The canonical plan for this project.
Every section has a stable ID, defined scope, dependencies, and execution criteria.

This document is the approved baseline for execution.

## Plan Status Legend

| Status | Meaning |
|--------|---------|
| `proposed` | Under consideration |
| `approved` | Ready for execution |
| `approved-partial` | Subsections approved |
| `approved-with-modifications` | Approved with changes |
| `deferred` | Postponed |
| `rejected` | Not accepted |
| `implemented` | Completed and verified |

## Plan Sections

---

### PLAN-GOV-001: SSOT Documentation System
**Status:** `implemented`
**Risk Level:** HIGH

**Purpose:**
Create full SSOT documentation system.

**Dependencies:** None
**Used By / Affects:** All modules

**Acceptance Criteria:**
- All governance, architecture, module, tracking, and planning docs exist
- Governance layer fully enforced

---

### PLAN-AUTH-001: Authentication Module
**Status:** `approved-partial`
**Risk Level:** HIGH
**Module Doc:** [auth.md](../04-modules/auth.md)

**Purpose:**
Implement authentication system.

**Dependencies:**
- PLAN-GOV-001

**Used By / Affects:**
- RBAC
- User Management
- Admin Panel
- User Panel

**Subsections:**
- PLAN-AUTH-001-A: Email/Password — `implemented`
- PLAN-AUTH-001-B: Google OAuth — `deferred` (awaiting credentials) → [DW-001](deferred-work-register.md#dw-001-google-oauth)
- PLAN-AUTH-001-C: Apple Sign-In — `deferred` (awaiting credentials) → [DW-002](deferred-work-register.md#dw-002-apple-sign-in)
- PLAN-AUTH-001-D: MFA (Authenticator) — `implemented`

**Acceptance Criteria:**
- Secure login/logout
- MFA enforced for admin roles
- Session management implemented

---

### PLAN-RBAC-001: RBAC Module
**Status:** `approved-partial`
**Risk Level:** HIGH
**Module Doc:** [rbac.md](../04-modules/rbac.md)

**Purpose:**
Implement role-based access control.

**Dependencies:**
- PLAN-AUTH-001

**Used By / Affects:**
- Admin Panel
- API
- User Management

**Acceptance Criteria:**
- Dynamic roles and permissions
- Secure enforcement at backend
- No UI-only authorization

---

### PLAN-USRMGMT-001: User Management Module
**Status:** `approved`
**Risk Level:** MEDIUM
**Module Doc:** [user-management.md](../04-modules/user-management.md)

**Dependencies:**
- PLAN-AUTH-001
- PLAN-RBAC-001

**Used By / Affects:**
- Admin Panel
- User Panel

**Acceptance Criteria:**
- User CRUD
- Account lifecycle management

---

### PLAN-ADMIN-001: Admin Panel
**Status:** `approved`
**Risk Level:** MEDIUM
**Module Doc:** [admin-panel.md](../04-modules/admin-panel.md)

**Dependencies:**
- PLAN-AUTH-001
- PLAN-RBAC-001

**Used By / Affects:**
- All modules

**Acceptance Criteria:**
- User management interface
- Role management interface
- Audit log viewing
- System health dashboard

---

### PLAN-USRPNL-001: User Panel
**Status:** `approved`
**Risk Level:** MEDIUM
**Module Doc:** [user-panel.md](../04-modules/user-panel.md)

**Dependencies:**
- PLAN-AUTH-001

**Acceptance Criteria:**
- Profile management
- Settings and MFA configuration
- Session management

---

### PLAN-AUDIT-001: Audit Logging
**Status:** `approved`
**Risk Level:** HIGH
**Module Doc:** [audit-logging.md](../04-modules/audit-logging.md)

**Dependencies:**
- PLAN-AUTH-001
- PLAN-RBAC-001

**Acceptance Criteria:**
- Immutable audit trail
- All significant actions logged
- Admin-viewable logs

---

### PLAN-HEALTH-001: Health Monitoring
**Status:** `approved`
**Risk Level:** MEDIUM
**Module Doc:** [health-monitoring.md](../04-modules/health-monitoring.md)

**Dependencies:** None

**Acceptance Criteria:**
- Health checks operational
- Metrics tracking active
- Alerting configured

---

### PLAN-API-001: API Layer
**Status:** `approved`
**Risk Level:** HIGH
**Module Doc:** [api.md](../04-modules/api.md)

**Dependencies:**
- PLAN-AUTH-001
- PLAN-RBAC-001

**Acceptance Criteria:**
- Consistent API conventions
- Error handling standardized
- Input validation enforced

---

### PLAN-JOBS-001: Jobs and Scheduler
**Status:** `approved`
**Risk Level:** MEDIUM
**Module Doc:** [jobs-and-scheduler.md](../04-modules/jobs-and-scheduler.md)

**Dependencies:** None

**Acceptance Criteria:**
- Job scheduling operational
- Retry logic implemented
- Failure handling defined

---

## Development Phases

### Phase 1 — Foundation (Auth + Infrastructure)

**Modules:** PLAN-AUTH-001
**Depends On:** PLAN-GOV-001 (implemented)

**Milestones:**
- Lovable Cloud enabled with database, auth, and storage
- Email/password sign-up, sign-in, sign-out functional
- Google OAuth and Apple Sign-In functional
- MFA enrollment and verification operational
- Password reset flow complete
- Session management and token lifecycle working
- Auth shared functions available (`getCurrentUser`, `requireAuth`, etc.)
- All auth events emitting correctly

**Phase Gate — must ALL pass before advancing:**
- [x] All auth user flows pass E2E tests — *ACT-011: Browser E2E 2026-04-09 (sign-in, sign-up, forgot-password, MFA-challenge, MFA-enroll tested)*
- [x] Auth failure modes tested (invalid session, expired token, failed MFA) — *ACT-014: (1) Invalid credentials → error toast + auth.failed_attempt event emitted, (2) Expired/invalid reset token → "Invalid reset link" page with recovery CTA, (3) MFA challenge without enrollment → error toast + disabled verify button. All fail-secure.*
- [x] Auth events verified against event-index.md — *ACT-011: `auth.failed_attempt` emission runtime-verified via console*
- [x] Auth shared functions verified against function-index.md — *ACT-013: Full cross-reference audit — all functions reconciled with code*
- [x] Auth security validated per auth-security.md — *ACT-014: Systematic validation: password policy (min 12 chars ✓), session management (Supabase JWT + refresh rotation ✓), MFA TOTP (enrollment + challenge ✓), sensitive flow protection (re-auth utility ✓), rate limiting (Supabase-managed ✓), audit events (all 8 auth events defined + emitting ✓). Status table updated. OAuth deferred per PLAN-AUTH-001-B/C.*
- [x] No security scan findings on auth module — *Security scan 2026-04-09: zero findings*

---

### Phase 2 — Access Control (RBAC)

**Modules:** PLAN-RBAC-001
**Depends On:** Phase 1 complete

**Milestones:**
- `user_roles` table created with RLS
- `has_role()` security definer function operational
- Role assignment and revocation working
- Permission enforcement at API/edge function level
- RLS policies enforced on all protected tables
- Permission cache with tenant-scoped invalidation
- V1 roles active: `superadmin`, `admin`, `user`

**Phase Gate — must ALL pass before advancing:**
- [x] Schema deployed: roles, permissions, user_roles, role_permissions, audit_logs — *ACT-015: 4 SQL migrations applied 2026-04-09*
- [x] Security helpers operational: is_superadmin, has_role, has_permission (with superadmin logical inheritance), get_my_authorization_context — *ACT-015: SECURITY DEFINER functions deployed*
- [x] RLS policies active on all RBAC tables — *ACT-015: 5 RLS policies deployed (roles, permissions, user_roles, role_permissions, audit_logs)*
- [x] Seed data: 3 base roles (superadmin, admin, user), 29 permissions, role-permission mappings, auto-assign trigger — *ACT-015: Seed applied*
- [x] Edge functions verified: assign-role, revoke-role, assign-permission-to-role, revoke-permission-from-role — *ACT-015: All 4 edge functions verified against schema (permission checks, audit logging, rollback, correlation_id, last-superadmin guard)*
- [x] Client-side helpers operational: useUserRoles, RequirePermission, checkPermission, checkRole — *ACT-015: All verified fail-secure*
- [x] Permission index matches implementation — *ACT-015: 29 seeded permissions match permission-index.md*
- [x] No privilege escalation paths found — *ACT-015: Security scan zero findings; superadmin inheritance server-enforced; immutability triggers protect base roles*
- [ ] Every permission has allow + deny test — *Deny matrix verified (ACT-019): all 29 permissions denied for non-existent/null user, invalid key denied, all roles denied. Allow matrix blocked pending edge function deployment + superadmin assignment.* → [DW-003](deferred-work-register.md#dw-003-rbac-permission-allowdeny-tests)
- [x] RLS tested at database level (not just API) — *ACT-019: Anonymous RLS verified (zero rows all 5 tables), write denial verified (INSERT blocked HTTP 401 all 5 tables, DELETE/UPDATE no effect), security helpers fail-secure (null/non-existent user → false)*
- [x] Cross-tenant isolation verified (zero rows, not errors) — *N/A for v1 single-tenant architecture per DEC-022. Gate item formally resolved via change control.*
- [ ] Role change immediately reflected (cache invalidation verified) — *Requires runtime E2E testing with role change scenario; blocked pending edge function deployment* → [DW-006](deferred-work-register.md#dw-006-role-change-cache-invalidation-verification)

---

### Phase 3 — Core Services (User Management, Audit, API)

**Modules:** PLAN-USRMGMT-001, PLAN-AUDIT-001, PLAN-API-001 (parallel)
**Depends On:** Phase 2 complete

**Milestones:**
- User CRUD with account lifecycle management
- Immutable audit trail recording all significant actions
- Standardized API layer with consistent error handling and input validation
- Audit log viewable by authorized roles
- API versioning and response conventions established

**Phase Gate — must ALL pass before advancing:**
- [ ] User management flows pass E2E tests with RBAC enforcement
- [ ] Audit entries verified for all auditable actions (reconciliation)
- [ ] No sensitive data in audit logs (passwords, tokens, MFA secrets)
- [ ] API input validation covers all endpoints
- [ ] API error responses standardized
- [ ] Route index matches all implemented routes

---

### Phase 4 — Admin & User Interfaces

**Modules:** PLAN-ADMIN-001, PLAN-USRPNL-001
**Depends On:** Phase 3 complete (Admin); Phase 1 complete (User Panel)

**Milestones:**
- Admin panel: user management, role management, audit log viewer, system health dashboard
- User panel: profile management, settings, MFA configuration, session management
- Admin actions enforced by RBAC (not UI-only)
- All admin-privileged operations audited

**Phase Gate — must ALL pass before advancing:**
- [ ] Admin actions verified with correct and incorrect roles (allow + deny)
- [ ] User panel flows pass E2E tests
- [ ] No admin capability accessible without proper role
- [ ] UI loading/error states for all async operations
- [ ] Accessibility baseline met

---

### Phase 5 — Operations & Reliability (Health Monitoring, Jobs)

**Modules:** PLAN-HEALTH-001, PLAN-JOBS-001
**Depends On:** Phase 1 complete (minimum); Phase 3 recommended for full integration (audit events, API execution layer)

**Milestones:**
- Health checks operational for all critical subsystems
- Metrics tracking and alerting configured
- Job scheduling via pg_cron operational
- Retry logic, failure handling, and dead-letter queue functional
- Kill switch and circuit breakers active

**Phase Gate — must ALL pass before advancing:**
- [ ] Health dashboard reflects real system state
- [ ] Job idempotency and retry behavior tested
- [ ] Poison job detection and isolation verified
- [ ] Kill switch stops execution immediately
- [ ] Health and job events emitting correctly

---

### Phase 6 — Hardening & System Validation

**Modules:** All
**Depends On:** Phases 1–5 complete

**Milestones:**
- Full security scan — zero critical/high findings
- Performance baselines established (p95/p99 latency, bundle size)
- Regression test suite complete for all critical paths
- Cross-module integration verified end-to-end
- All SSOT indexes accurate and complete

**Phase Gate — release readiness:**
- [ ] All E2E critical flows pass
- [ ] Security adversarial tests pass (privilege escalation, injection, replay)
- [ ] Performance within budget (LCP < 2.5s, CLS < 0.1)
- [ ] All regression watchlist items have regression tests
- [ ] All reference indexes verified against implementation
- [ ] System-state.md reflects accurate module status
- [ ] Full observability coverage — all critical paths emit events and logs with traceability (correlation_id)

---

## Phase Gate Rules

- No phase may advance without ALL gate conditions satisfied
- Gate verification must be **explicit and documented** — not assumed
- Failed gate conditions must be fixed and retested before advancing — no partial progression with known failures
- If a phase gate fails, changes must be **rolled back or corrected** before re-validation
- Gate verification must include **evidence** (test results, logs, screenshots, or metrics) — evidence must be traceable in action-tracker.md or linked artifacts
- Phase gate results logged in action-tracker.md
- Auth, RBAC, and Security gates are **never waivable**
- Schema changes after Phase 3 require **HIGH-impact change control** with rollback plan

### Carried-Forward Gate Item Rule

When a gate item is deferred from its source phase to a future phase via the [Deferred Work Register](deferred-work-register.md):

- The deferred item becomes a **prerequisite sub-gate** of the receiving phase
- Carried-forward sub-gates **MUST be completed before dependent implementation begins** in the receiving phase (e.g., DW-003/DW-004/DW-006 must be completed before Phase 3 builds user management on top of RBAC)
- The source phase may be marked `approved-partial` (not `implemented`) while carried-forward items remain open
- Receiving phase planning **MUST explicitly include** all carried-forward items in its scope
- Carried-forward items do not permit unrestricted phase advancement — they constrain the receiving phase's execution order

**Example:** Phase 3 may begin (e.g., audit logging infrastructure has no RBAC dependency), but RBAC-dependent modules (user-management, API) cannot proceed until DW-003/DW-004/DW-006 are completed as prerequisite sub-gates.

## Execution Order

Based on dependency chains and phases:

1. ~~PLAN-GOV-001~~ (implemented)
2. **Phase 1:** PLAN-AUTH-001
3. **Phase 2:** PLAN-RBAC-001
4. **Phase 3:** PLAN-USRMGMT-001, PLAN-AUDIT-001, PLAN-API-001 (parallel)
5. **Phase 4:** PLAN-ADMIN-001, PLAN-USRPNL-001
6. **Phase 5:** PLAN-HEALTH-001, PLAN-JOBS-001 (can overlap with Phase 3/4)
7. **Phase 6:** System-wide hardening and validation

## Execution Rules

- Only `approved` or `approved-partial` sections may be executed
- Execution must follow phase order and dependency chain
- No execution outside approved baseline
- All changes must follow [change-control-policy.md](../00-governance/change-control-policy.md)
- Phase gates are mandatory — no skipping

## Dependencies

- [Constitution](../00-governance/constitution.md)
- [System State](../00-governance/system-state.md)
- [Deferred Work Register](deferred-work-register.md)

## Used By / Affects

All implementation and execution decisions.

## Related Documents

- [Approved Decisions](approved-decisions.md)
- [Plan Changelog](plan-changelog.md)
- [Plan Review Log](plan-review-log.md)
- [Feature Proposals](feature-proposals.md)
- [Deferred Work Register](deferred-work-register.md)
