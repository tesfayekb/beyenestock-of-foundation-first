# Stage 3.5 — Security Hardening Plan (v3)

> **Status:** PROPOSED — awaiting approval  
> **Owner:** AI  
> **Created:** 2026-04-10  
> **Scope:** DW-014 (Denial Audit Logging) + DW-015 (Superadmin Guardrails)  
> **Baseline:** Executes against approved plan baseline v4

---

## Objective

Harden existing security enforcement with observability (DW-014) and friction controls (DW-015) — without altering the RBAC foundation.

---

## Stage 3.5A — DW-014: Denial Audit Logging

### Problem

Authorization denials are enforced but invisible. No forensic trail, no intrusion detection, no abuse pattern visibility.

### Design

**Unified denial path rule:**  
All authorization failures MUST throw `PermissionDeniedError`. Manual `403` returns are prohibited in handler-wrapped functions.

**Centralized interception (handler.ts only):**  
The `catch` block in `createHandler()` intercepts `PermissionDeniedError` and fires a non-blocking audit write before returning the `403` response.

**Actor extraction (multi-source, trust-ranked):**

| Priority | Source | Trust Level |
|----------|--------|-------------|
| 1 | `err.userId` | **Authoritative** — set at throw site with validated identity |
| 2 | JWT payload decode | **Best-effort enrichment only** — must never affect authorization logic, only audit metadata. If decode fails → `null` |
| 3 | `null` | Logged with `actor_id = null` — event still recorded |

**Event schema:**

```
action: "auth.permission_denied"
actor_id: <userId | null>
target_type: "permission"
target_id: null
metadata: {
  permission_key: string,
  endpoint: string,
  correlation_id: string,
  reason: string   // e.g. "missing_permission", "self_scope_violation", "recent_auth_required"
}
```

**Failure behavior:** Fire-and-forget. Audit write failure must NOT block the `403` response. Failure is logged to `console.error` only.

**Centralization rule:** All denial logging MUST occur only in `handler.ts`. No endpoint-level denial logging permitted.

**Enforcement rule:** Any new authorization helper or guard introduced in the future MUST throw `PermissionDeniedError`. Returning `apiError(403, ...)` from authorization logic is considered a governance violation.

**Volume note:** Denial audit events may spike under attack. Acceptable for current scale. If volume becomes a concern, throttling/aggregation is a future optimization (not in scope for 3.5).

### Files Impacted

| File | Change |
|------|--------|
| `supabase/functions/_shared/errors.ts` | Add optional `userId` property to `PermissionDeniedError` |
| `supabase/functions/_shared/authorization.ts` | Pass `userId` into `PermissionDeniedError` in `checkPermissionOrThrow()` and `requireSelfScope()` |
| `supabase/functions/_shared/handler.ts` | Add denial audit logging in `PermissionDeniedError` catch branch |
| `docs/07-reference/event-index.md` | Add `auth.permission_denied` event definition |

### Success Criteria

- [ ] Every `PermissionDeniedError` produces an `auth.permission_denied` audit entry
- [ ] Actor ID extracted from `err.userId` (authoritative) with JWT best-effort fallback
- [ ] No manual `403` returns exist in handler-wrapped functions
- [ ] Audit write failure does not block `403` response
- [ ] No endpoint-level denial logging exists (centralized only)
- [ ] `auth.permission_denied` added to event-index.md with correct schema
- [ ] No change to success flow response shapes

---

## Stage 3.5B — DW-015: Superadmin Guardrails

### Problem

Superadmin bypasses permission checks via `is_superadmin()`. High-risk actions lack friction controls, allowing silent privileged mutations.

### Design

**Principle:** Harden without changing the RBAC foundation. No new SQL functions, no new permission seeding, no split permission model.

**Three surgical additions:**

#### 1. Add `requireRecentAuth()` to 4 RBAC endpoints missing it

Currently only `deactivate-user` and `reactivate-user` enforce recent auth. The following 4 endpoints perform high-risk RBAC mutations without it:

| Endpoint | Current Guards | Addition |
|----------|---------------|----------|
| `assign-role` | `checkPermissionOrThrow` | + `requireRecentAuth()` |
| `revoke-role` | `checkPermissionOrThrow` | + `requireRecentAuth()` |
| `assign-permission-to-role` | `checkPermissionOrThrow` | + `requireRecentAuth()` |
| `revoke-permission-from-role` | `checkPermissionOrThrow` | + `requireRecentAuth()` |

#### 2. Self-superadmin-role-revocation prevention

In `revoke-role/index.ts`: if the target user is the acting user AND the role being revoked is `superadmin`, return `409 Conflict`.

This prevents a superadmin from accidentally or maliciously removing their own superadmin role (the last-superadmin guard only covers the final assignment, not self-revocation when multiple superadmins exist).

#### 3. No new SQL authorization primitives

- `has_permission()` remains the single authorization RPC
- `is_superadmin()` bypass remains unchanged for non-high-risk paths
- No `has_explicit_permission()` function introduced
- No new seed data required

### Files Impacted

| File | Change |
|------|--------|
| `supabase/functions/assign-role/index.ts` | Add `requireRecentAuth(ctx.user.lastSignInAt)` |
| `supabase/functions/revoke-role/index.ts` | Add `requireRecentAuth()` + self-superadmin-revocation guard |
| `supabase/functions/assign-permission-to-role/index.ts` | Add `requireRecentAuth(ctx.user.lastSignInAt)` |
| `supabase/functions/revoke-permission-from-role/index.ts` | Add `requireRecentAuth(ctx.user.lastSignInAt)` |

### Success Criteria

- [ ] All 6 high-risk endpoints enforce `requireRecentAuth()`
- [ ] Self-superadmin-revocation blocked with `409`
- [ ] No new SQL functions introduced
- [ ] No new permission seed data required
- [ ] Existing `has_permission()` / `is_superadmin()` behavior unchanged
- [ ] No change to success flow response shapes
- [ ] No change to existing audit events

---

## Regression Protection

**Explicitly preserved (no changes permitted):**

- SQL functions: `has_permission()`, `has_role()`, `is_superadmin()`
- Success-path response shapes for all endpoints
- Existing audit event schemas and action names
- RLS policies
- `checkPermissionOrThrow()` authorization logic (only enriches error, does not change flow)

---

## Runtime Verification Plan

| Test | Method | Expected |
|------|--------|----------|
| Permission denied → audit log written | Invoke endpoint without required permission | `auth.permission_denied` row in `audit_logs` |
| Self-scope denial → audit log written | Call `get-profile` with mismatched user | `auth.permission_denied` row |
| Actor ID present in denial log | Check `actor_id` column | Non-null UUID matching caller |
| Audit failure → 403 still returned | Simulate audit write failure | 403 response, console error logged |
| Recent auth enforced on RBAC endpoints | Call `assign-role` with stale session | 403 with `recent_auth` message |
| Self-superadmin revocation blocked | Superadmin revokes own superadmin role | 409 Conflict |
| Success flows unchanged | Normal authorized calls | Same response shapes as before |

---

## Closure Outputs (post-execution)

After execution and verification, the following will be updated:

- `docs/08-planning/deferred-work-register.md` — mark DW-014, DW-015 as resolved
- `docs/08-planning/master-plan.md` — update phase gate checkboxes
- `docs/06-tracking/system-state.md` — reflect hardening completion
