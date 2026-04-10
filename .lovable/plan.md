# Phase 3.5 — Security Hardening Plan

> **Scope:** DW-014 (Denial Audit Logging) + DW-015 (Superadmin Guardrails)  
> **Scope Lock:** No other work. No new features. No refactors beyond these two items.

---

## DW-014: Denial Audit Logging

### Goal

Every `PermissionDeniedError` produces an immutable audit log entry — making denied access attempts observable, forensic-traceable, and pattern-detectable.

### Design

**Interception point: `_shared/handler.ts` (centralized, zero duplication)**

The `createHandler` wrapper already catches `PermissionDeniedError` at line 59. This is the single interception point. No per-endpoint changes required.

**Flow:**
```
handler.ts catch (PermissionDeniedError)
  → logAuditEvent({ action: 'auth.permission_denied', ... })
  → return 403 (regardless of audit success)
```

**Audit entry fields:**

| Field | Source |
|-------|--------|
| `actor_id` | From `PermissionDeniedError.userId` (attached by `checkPermissionOrThrow`) |
| `action` | `'auth.permission_denied'` |
| `target_type` | `'permission'` |
| `target_id` | `null` |
| `metadata.permission_key` | From `PermissionDeniedError.permissionKey` |
| `metadata.endpoint` | `new URL(req.url).pathname` |
| `metadata.correlation_id` | From handler-generated correlationId |
| `ip_address` | From `x-forwarded-for` header |
| `user_agent` | From `user-agent` header |

**Actor ID extraction:**

`PermissionDeniedError` is thrown *after* authentication but the handler wrapper doesn't have the authenticated context. Solution: add optional `userId` field to `PermissionDeniedError`. `checkPermissionOrThrow` and `requireSelfScope` attach the userId when throwing. Handler reads it from the error.

```typescript
// errors.ts — add userId to PermissionDeniedError
export class PermissionDeniedError extends Error {
  permissionKey: string
  userId?: string  // ← NEW
  constructor(message: string, permissionKey: string, userId?: string) { ... }
}

// authorization.ts — pass userId when throwing
throw new PermissionDeniedError(msg, permissionKey, userId)

// handler.ts — read userId from error, fire-and-forget audit
if (err instanceof PermissionDeniedError) {
  if (err.userId) {
    logAuditEvent({ actorId: err.userId, action: 'auth.permission_denied', ... })
      .catch(() => {}) // non-blocking
  }
  return apiError(403, 'Permission denied', { correlationId: cid })
}
```

**Failure behavior (CRITICAL):**

- 403 response is ALWAYS returned, regardless of audit write outcome
- Audit is fire-and-forget (non-blocking `await` with no abort on failure)
- Audit write failure logs to console + emits `audit.write_failed`
- Rationale: denial enforcement must never be degraded by audit infrastructure
- This is intentionally different from high-risk mutation audit (fail-closed)

**Sensitive data protection:**
- No tokens, passwords, or request bodies in denial audit metadata
- Only: permission key, endpoint path, actor ID, IP, user agent

### Success Criteria

- [ ] Every `PermissionDeniedError` → audit_logs entry with all required fields
- [ ] No sensitive data in denial audit entries
- [ ] Audit write failure does NOT block 403 response
- [ ] `audit.write_failed` emitted on denial audit failure
- [ ] New event `auth.permission_denied` added to event-index.md
- [ ] Runtime verified: trigger denial → confirm audit_logs row exists

---

## DW-015: Superadmin Guardrails

### Goal

High-risk actions require secondary authentication guard even for superadmin — preventing silent misuse and enabling audit differentiation.

### High-Risk Actions List (explicit)

| Action | Endpoint | Permission |
|--------|----------|-----------|
| Role assignment | assign-role | `roles.assign` |
| Role revocation | revoke-role | `roles.revoke` |
| Permission assignment | assign-permission-to-role | `permissions.assign` |
| Permission revocation | revoke-permission-from-role | `permissions.revoke` |
| User deactivation | deactivate-user | `users.deactivate` |
| User reactivation | reactivate-user | `users.reactivate` |

### Design

**Approach: `requireRecentAuth()` as the superadmin guardrail**

The `has_permission()` SQL function's superadmin bypass is architecturally correct and must NOT be changed — it's the RBAC foundation. Changing it risks regression across the entire system.

The guardrail is: **all high-risk endpoints must enforce `requireRecentAuth()`**. This means:

1. Superadmin still passes permission checks (correct)
2. But high-risk actions require recent authentication (5-minute window)
3. All high-risk actions already have fail-closed audit logging
4. With DW-014, denied attempts are also logged

**Verification needed:** Confirm all 6 endpoints have `requireRecentAuth()`. Currently known:
- `deactivate-user` ✅ has `requireRecentAuth(ctx.user.lastSignInAt)`
- `reactivate-user` — verify
- `assign-role` — verify
- `revoke-role` — verify
- `assign-permission-to-role` — verify
- `revoke-permission-from-role` — verify

If any are missing → add `requireRecentAuth(ctx.user.lastSignInAt)` after auth + permission check.

**Additional guardrail: superadmin self-role-revocation prevention**

In `revoke-role`: if the actor is revoking the superadmin role from themselves → deny. DB trigger `prevent_last_superadmin_delete` handles the *last* superadmin case, but doesn't prevent a superadmin removing *their own* role when others exist.

### Success Criteria

- [ ] All 6 high-risk endpoints enforce `requireRecentAuth()`
- [ ] Superadmin cannot revoke own superadmin role
- [ ] No regression in existing RBAC behavior
- [ ] No regression in success response shapes
- [ ] No regression in existing audit events
- [ ] Runtime verified: superadmin with stale session → 403 on high-risk action
- [ ] Runtime verified: superadmin self-role-revocation → denied

---

## Files Impacted

| File | DW-014 | DW-015 | Change |
|------|--------|--------|--------|
| `_shared/errors.ts` | ✅ | — | Add `userId` to `PermissionDeniedError` |
| `_shared/handler.ts` | ✅ | — | Denial audit in catch block |
| `_shared/authorization.ts` | ✅ | — | Pass `userId` to error constructor |
| `reactivate-user/index.ts` | — | maybe | Add `requireRecentAuth` if missing |
| `assign-role/index.ts` | — | maybe | Add `requireRecentAuth` if missing |
| `revoke-role/index.ts` | — | ✅ | `requireRecentAuth` + self-revocation guard |
| `assign-permission-to-role/index.ts` | — | maybe | Add `requireRecentAuth` if missing |
| `revoke-permission-from-role/index.ts` | — | maybe | Add `requireRecentAuth` if missing |
| `docs/07-reference/event-index.md` | ✅ | — | Add `auth.permission_denied` |
| `docs/08-planning/deferred-work-register.md` | ✅ | ✅ | Mark resolved |
| `docs/08-planning/master-plan.md` | ✅ | ✅ | Phase gate update |
| `docs/00-governance/system-state.md` | ✅ | ✅ | Phase 3.5 status |

---

## Runtime Verification Plan

### DW-014 Verification
1. Call protected endpoint with regular-user token → 403
2. Query `audit_logs` for `action = 'auth.permission_denied'` → entry exists with correct fields
3. Inspect metadata → no sensitive data, only permission_key + endpoint + correlation_id

### DW-015 Verification
1. All 6 high-risk endpoints: superadmin with stale session → 403
2. `revoke-role` with superadmin targeting own superadmin role → denied
3. Superadmin with fresh session → all high-risk actions succeed (no regression)

---

## Regression Protection

No changes to:
- ✅ Success response shapes
- ✅ Existing audit event names/metadata
- ✅ `has_permission()` / `is_superadmin()` SQL functions
- ✅ 401/400 error paths
- ✅ Rate limiting
- ✅ CORS

---

## Execution Stages

| Stage | Scope |
|-------|-------|
| 3.5A | DW-014: errors.ts + handler.ts + authorization.ts + event-index.md |
| 3.5B | DW-015: requireRecentAuth verification/addition + revoke-role self-guard |
| 3.5C | Runtime verification + closure artifacts |
