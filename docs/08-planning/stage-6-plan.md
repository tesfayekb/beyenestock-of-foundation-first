# Stage 6 Plan — Hardening & System Validation

> **Owner:** Project Lead | **Created:** 2026-04-12 | **Plan Version:** v11.0 (extends v10.1)  
> **Phase:** 6  
> **Depends On:** Phase 5 CLOSED  
> **Gate Target:** Release readiness (master-plan Phase 6 gate)

---

## Overview

Phase 6 closes remaining deferred work items (10 open after v2 deferrals), establishes the regression test suite, and passes the release readiness gate from the master plan.

### Scope Summary

| Category | DW Items | Count |
|----------|----------|-------|
| Auth hardening | DW-008 (completed) | 1 |
| Test infrastructure | DW-012, DW-013 | 2 |
| Performance hardening | DW-021, DW-022, DW-024 | 3 |
| Reliability hardening | DW-028, DW-029 | 2 |
| Scalability & UX | DW-011, DW-023 | 2 |
| **Total in scope** | | **10** |

### Explicitly Excluded (v2)

| ID | Title | Reason |
|----|-------|--------|
| DW-001 | Google OAuth | Provider credentials not configured. Deferred to v2. |
| DW-002 | Apple Sign-In | Provider credentials not configured. Deferred to v2. |
| DW-007 | Moderator Role | Feature addition, not hardening. Requires new permission set, role seeding, RBAC testing. DEC-018. |
| DW-020 | User Notification Preferences | No notification backend exists. New module, not hardening. |

---

## Stage Plan

### Stage 6A — Auth Hardening (DW-008) ✅ COMPLETE

**Scope:**

1. **MFA recovery codes** (DW-008): Per DEC-017 spec. ✅ Implemented (ACT-064).
   - 10 recovery codes (8 alphanumeric each) generated on MFA enrollment
   - Stored hashed (bcrypt) in `mfa_recovery_codes` table (service-role only, no RLS read)
   - Display codes once on enrollment, allow regeneration on SecurityPage
   - Single-use consumption with recovery code entry on MfaChallenge page
   - Audit event: `auth.mfa_recovery_used`

2. **OAuth providers** (DW-001, DW-002): Deferred to v2. UI buttons present but providers require Supabase Dashboard configuration with external credentials.

**Migrations:**
- MIG-033: `mfa_recovery_codes` table ✅

**Gate:** ✅ All applicable items passed (OAuth items deferred to v2)

---

### Stage 6B — Test Infrastructure & Regression Suite (DW-012, DW-013)

**Scope:**

1. **Authenticated test harness** (DW-012):
   - Admin token provisioning for edge function integration tests
   - Mockable `supabaseAdmin.auth.admin` wrapper for failure injection
   - Test cases for lifecycle edge cases:
     - Deactivate already-deactivated user → 409
     - Reactivate already-active user → 409
     - Invalid UUID → 400
     - Missing body → 400
   - Rollback-path tests:
     - Unban failure → no profile status change
     - Profile update failure after unban → re-ban

2. **Test user cleanup** (DW-013):
   - Auto-cleanup mechanism on test success and failure paths
   - Handle Supabase auth deletion trigger chain

3. **Regression test suite** (mapped to watchlist items):

   **Vitest unit/integration tests (RW-001 through RW-005):**

   | RW Item | Test Scope | Test Type |
   |---------|-----------|-----------|
   | RW-001: Permission cache invalidation | Assign role → immediate API access; revoke → immediate denial | Edge function integration |
   | RW-002: RLS policy visibility | Tenant A cannot see tenant B rows; policy changes take effect | DB-level test via service role |
   | RW-003: Shared function contracts | Function signature stability; consumer compatibility | Unit test with snapshot |
   | RW-004: Job retry misconfiguration | Retry count matches config; no duplicate execution; DLQ after max retries | Edge function integration |
   | RW-005: Audit event completeness | Every critical mutation produces audit entry with required fields | Edge function integration |

   **Playwright E2E tests (RW-006 through RW-010):**

   | RW Item | Test Scope | Test Type |
   |---------|-----------|-----------|
   | RW-006: Health monitoring blind spot | Health endpoint returns correct status; alert thresholds trigger at boundaries | E2E + edge function |
   | RW-007: User lifecycle deactivation/reactivation | Full lifecycle: create → deactivate → blocked → reactivate → restored | E2E with admin token |
   | RW-008: PERMISSION_DEPS drift | All 3 copies identical; new permission added to all 3 | Automated hash comparison |
   | RW-009: Admin UI component compliance | No raw colors, semantic tokens only, all pages render | E2E visual |
   | RW-010: MFA enrollment redirect | Admin without MFA → redirect to /mfa-enroll → return to /admin | E2E auth flow |

**Gate:**
- [ ] Authenticated admin tests pass for deactivate/reactivate edge cases
- [ ] Rollback-path tests pass (failure injection)
- [ ] Test user cleanup works on success and failure
- [ ] All 10 RW items have corresponding regression tests
- [ ] All regression tests pass

---

### Stage 6C — Performance Hardening (DW-021, DW-022, DW-024)

**Scope:**

1. **DB-level admin user search** (DW-021):
   - Option A: Materialized `email` column on `profiles` synced via trigger on auth.users changes
   - Option B: `SECURITY DEFINER` DB function joining profiles + auth.users
   - Remove `auth.admin.listUsers()` from search path entirely
   - Design decision needed before implementation (security review for auth.users access)

2. **Server-shaped admin user DTO** (DW-022):
   - Single DB query/view returning user + email + roles
   - Replace multi-query enrichment in `list-users`
   - Target: < 200ms response at current scale

3. **Unbounded aggregation fix** (DW-024):
   - Replace client-side `user_roles` full-table fetch in AdminDashboard/AdminRolesPage
   - Extend `get-user-stats` or create server-side aggregation endpoint
   - No unbounded `.select('role_id')` without limit

**Migrations:**
- MIG-034: Email sync mechanism (trigger or function, depending on design decision)
- MIG-035: Admin user view/function if using DB view approach

**Gate:**
- [ ] Email search works without `auth.admin.listUsers()` in search path
- [ ] Single-query admin user DTO returns user + email + roles
- [ ] Admin user list query < 200ms at current scale
- [ ] No unbounded client-side fetches in admin dashboard or role list
- [ ] All existing admin UI functionality preserved (no regression)

---

### Stage 6D — Reliability Hardening (DW-028, DW-029)

**Scope:**

1. **Audit rollback for alert config** (DW-028):
   - Pre-fetch old values before `health-alert-config` update
   - On `logAuditEvent()` failure: restore original values
   - Caller receives appropriate error (not silent success)
   - True fail-closed behavior: no config change without audit record

2. **Batched audit cleanup** (DW-029):
   - Create `rpc_batch_delete_audit_logs(cutoff timestamptz, batch_size int)` DB function
   - Returns count of deleted records per batch
   - Update `job-audit-cleanup` to call RPC in loop until 0 remaining
   - Respects 30-second edge function timeout budget

**Migrations:**
- MIG-036: `rpc_batch_delete_audit_logs` function (SECURITY DEFINER, delete in batches)

**Gate:**
- [ ] Alert config update with simulated audit failure restores original values
- [ ] Caller receives error on audit failure (not 200)
- [ ] Batch delete removes correct records (≥ 90 days only)
- [ ] Batch loop completes within 30s timeout at scale
- [ ] No records newer than cutoff deleted
- [ ] Existing audit cleanup job still works at current scale

---

### Stage 6E — Scalability & UX (DW-011, DW-023)

**Scope:**

1. **Distributed rate limiting** (DW-011):
   - Evaluate Upstash Redis (serverless, compatible with Deno/edge functions)
   - Replace in-memory per-isolate rate limiter in `_shared/rate-limit.ts`
   - Durable counters across cold starts and isolate restarts
   - Requires: Upstash account, `UPSTASH_REDIS_REST_URL` + `UPSTASH_REDIS_REST_TOKEN` secrets
   - Redeployment of all edge functions (rate limiter is in shared handler)
   - **Fallback**: If Upstash not viable, document limitation and close with operational mitigation (current in-memory limiter as defense-in-depth, not institutional-grade)

2. **Audit actor display** (DW-023):
   - Actor display name resolution in audit query response (batch lookup from profiles)
   - Actor-as-subject scope toggle on UserDetailPage audit trail
   - No N+1 for actor resolution — batch profile lookup for unique actor_ids in response
   - UI: toggle button on UserDetailPage audit section

**Gate:**
- [x] Rate limit: DW-011 deferred to v2. In-memory limiter documented as defense-in-depth. Upstash Redis required for distributed enforcement.
- [x] No regression in existing rate-limited endpoints
- [x] Audit entries show actor display name (not raw UUID)
- [ ] Actor-scope toggle works on UserDetailPage
- [x] No N+1 queries for actor resolution

---

### Stage 6F — Security Validation & Release Gate

**Scope:**

1. **Security adversarial tests:**
   - Privilege escalation: non-admin attempts admin endpoints, role self-assignment, permission bypass
   - Injection: SQL injection via edge function inputs (all Zod-validated, verify)
   - Replay: reuse expired/revoked JWT, replay MFA challenge
   - CSRF: verify SameSite cookie policy, no state-changing GET endpoints

2. **Performance baselines:**
   - Establish p95/p99 latency for all critical endpoints (health-check, list-users, list-roles, get-profile)
   - Verify LCP < 2.5s, CLS < 0.1 for admin and user panels
   - Bundle size audit

3. **Reference index reconciliation:**
   - route-index.md vs actual routes in App.tsx + edge functions
   - function-index.md vs actual shared functions
   - event-index.md vs actual logAuditEvent() calls
   - permission-index.md vs actual permission checks

4. **Observability verification:**
   - All critical paths emit events with `correlation_id`
   - All audit events have required fields
   - Health monitoring covers all subsystems

5. **SSOT accuracy check:**
   - system-state.md reflects final module status
   - master-plan.md gate checkboxes filled with evidence
   - All module docs accurate

**Gate (master-plan Phase 6 gate — all items mandatory):**
- [ ] All E2E critical flows pass
- [ ] Security adversarial tests pass (privilege escalation, injection, replay)
- [ ] Performance within budget (LCP < 2.5s, CLS < 0.1)
- [ ] All regression watchlist items have regression tests
- [ ] All reference indexes verified against implementation
- [ ] System-state.md reflects accurate module status
- [ ] Full observability coverage — all critical paths emit events and logs with traceability (correlation_id)

---

## Execution Order & Dependencies

```
6A (Auth) ──────────┐
6B (Testing) ───────┤
6C (Performance) ───┼──→ 6F (Security & Release Gate)
6D (Reliability) ───┤
6E (Scalability) ───┘
```

Stages 6A–6E are independent and can execute in any order. Stage 6F is the final gate and depends on all prior stages being complete.

---

## New Events Summary

| Event | Classification | Severity | Owner | Stage |
|-------|---------------|----------|-------|-------|
| `auth.oauth_linked` | security | HIGH | auth | 6A |
| `auth.oauth_unlinked` | security | HIGH | auth | 6A |
| `auth.mfa_recovery_used` | security | CRITICAL | auth | 6A |

---

## New Permissions Summary

No new permissions required. All Phase 6 work uses existing permission set.

---

## Estimated Migrations

| ID | Description | Stage |
|----|-------------|-------|
| MIG-033 | mfa_recovery_codes table | 6A |
| MIG-034 | Email sync mechanism for profiles | 6C |
| MIG-035 | Admin user view/function (if DB view approach) | 6C |
| MIG-036 | rpc_batch_delete_audit_logs function | 6D |

---

## Risk Notes

1. **DW-011 (distributed rate limiting)** depends on external service (Upstash Redis). If not viable, close with operational mitigation + documented limitation.
2. **DW-001/002 (OAuth)** requires Supabase Dashboard configuration — cannot be fully automated via migrations. Manual setup step documented.
3. **DW-021/022 (DB user search/DTO)** may require `SECURITY DEFINER` function accessing `auth.users` — security review required before implementation.
4. **DW-008 (MFA recovery codes)** requires secure hashing — bcrypt via Deno standard library. Recovery codes are security-critical: single-use, hashed, no plaintext storage.
5. **Stage 6B** is the largest stage due to 10 regression test scenarios. May need sub-staging if scope exceeds a single implementation pass.
