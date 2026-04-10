# Phase 3.5 — Security Hardening Plan (A+ Revision)

> **Scope:** DW-014 (Denial Audit Logging) + DW-015 (Superadmin Guardrails)  
> **Scope Lock:** No other work. No new features. No refactors beyond these two items.  
> **Revision:** v2 — addresses all A+ gaps from review feedback.

---

## DW-014: Denial Audit Logging

### Goal

Every authorization denial produces an immutable audit log entry — making denied access attempts observable, forensic-traceable, and pattern-detectable.

### Architectural Rule: Single Denial Path (CRITICAL)

**Rule: ALL authorization denials MUST throw `PermissionDeniedError`. No manual 403 returns from authorization logic are permitted.**

Current state (verified):
- `checkPermissionOrThrow()` → throws `PermissionDeniedError` ✅
- `requireSelfScope()` → throws `PermissionDeniedError` ✅
- `requireRecentAuth()` → throws `PermissionDeniedError` ✅
- No manual `apiError(403, ...)` returns exist for authorization decisions ✅

This rule MUST be enforced for all future guards. Any new authorization primitive MUST throw `PermissionDeniedError` — never return a manual 403.

**Centralization rule:** ALL denial audit logging occurs ONLY in `handler.ts` catch block. No endpoint-level denial logging permitted. This prevents duplication and ensures consistency.

### Design

**Interception point: `_shared/handler.ts` — single catch block, zero duplication**

**Flow:**
```
handler.ts catch (PermissionDeniedError)
  → extract actor ID (multi-source fallback)
  → logAuditEvent({ action: 'auth.permission_denied', ... })  [fire-and-forget]
  → return 403 (ALWAYS, regardless of audit outcome)
```

### Actor ID Extraction — Multi-Source Fallback (A+ requirement)

The handler wrapper doesn't have the authenticated context directly. Actor ID is resolved via cascading fallback:

```
1. err.userId           — attached by checkPermissionOrThrow / requireSelfScope / requireRecentAuth
2. JWT fallback         — extract from Authorization header (lightweight parse, no full validation)
3. null                 — still log the denial (unknown actor is still valuable forensic data)
```

**Implementation:**

```typescript
// handler.ts — actor extraction helper
function extractActorId(err: PermissionDeniedError, req: Request): string | null {
  // Source 1: error-attached userId (most reliable)
  if (err.userId) return err.userId

  // Source 2: JWT fallback (base64 decode, no validation — already validated upstream)
  try {
    const token = req.headers.get('Authorization')?.replace('Bearer ', '')
    if (token) {
      const payload = JSON.parse(atob(token.split('.')[1]))
      return payload.sub ?? null
    }
  } catch { /* ignore parse failures */ }

  // Source 3: unknown actor — still log
  return null
}
```

**Why this is A+:** No silent gaps. Even if a future developer forgets to pass `userId` on a new error throw site, the JWT fallback catches it. If the JWT is malformed, we still log with `null` actor — the denial event itself is valuable.

### Audit Entry Schema

| Field | Source | Required |
|-------|--------|----------|
| `actor_id` | `extractActorId()` multi-source | No (null = unknown actor) |
| `action` | `'auth.permission_denied'` | Yes |
| `target_type` | `'permission'` | Yes |
| `target_id` | `null` | — |
| `metadata.permission_key` | `err.permissionKey` | Yes |
| `metadata.endpoint` | `new URL(req.url).pathname` | Yes |
| `metadata.correlation_id` | Handler-generated `correlationId` | Yes |
| `ip_address` | `x-forwarded-for` header | Best-effort |
| `user_agent` | `user-agent` header | Best-effort |

**Event schema enforcement:** `auth.permission_denied` MUST follow the exact schema above. It MUST be added to `event-index.md` with this field contract. All fields match existing audit event conventions.

### Failure Behavior (CRITICAL)

- **403 response is ALWAYS returned**, regardless of audit write outcome
- Audit is **fire-and-forget**: `logAuditEvent(...).catch(...)` — non-blocking
- Audit write failure → console error + `audit.write_failed` event emitted
- Rationale: denial enforcement must NEVER be degraded by audit infrastructure
- This is intentionally different from high-risk mutation audit (fail-closed)

### Sensitive Data Protection

- No tokens, passwords, or request bodies in denial audit metadata
- Only: permission key, endpoint path, correlation ID
- `sanitizeMetadata()` denylist applies automatically

### Volume Consideration

Denial logs can spike under attack. Current design:
- Writes are bounded by rate limiter (standard/strict classes already in handler)
- No additional throttling in Phase 3.5 — rate limiter is the first line of defense
- **Deferred (Phase 6):** Denial log aggregation/sampling for sustained high-volume attacks (DW-016)

### Files Changed (DW-014)

| File | Change |
|------|--------|
| `_shared/errors.ts` | Add optional `userId` field to `PermissionDeniedError` constructor |
| `_shared/handler.ts` | Add denial audit logging in `PermissionDeniedError` catch block + `extractActorId()` helper |
| `_shared/authorization.ts` | Pass `userId` as 3rd arg in all `PermissionDeniedError` throws |
| `docs/07-reference/event-index.md` | Add `auth.permission_denied` with field contract |

### Success Criteria

- [ ] Every `PermissionDeniedError` → audit_logs entry with all required fields
- [ ] Actor ID extracted via multi-source fallback (error → JWT → null)
- [ ] No sensitive data in denial audit entries
- [ ] Audit write failure does NOT block 403 response
- [ ] `audit.write_failed` emitted on denial audit failure
- [ ] `auth.permission_denied` added to event-index.md with exact schema
- [ ] Centralization enforced: no endpoint-level denial logging exists
- [ ] Runtime verified: trigger denial → confirm audit_logs row exists with correct fields

---

## DW-015: Superadmin Guardrails

### Goal

High-risk actions require BOTH explicit permission AND recent authentication — even for superadmin. No silent bypass.

### Design Choice: Option A — Explicit Permission Required (A+ standard)

**The `is_superadmin()` bypass in `has_permission()` SQL remains unchanged** — it is the RBAC foundation for standard operations.

**For high-risk actions only:** endpoints call a NEW authorization helper `checkHighRiskPermission()` that:
1. Checks the permission **without superadmin bypass** (direct role_permissions lookup)
2. Enforces `requireRecentAuth()`

This means superadmin must have the permission explicitly assigned via role_permissions — the logical bypass is NOT used for high-risk actions.

**Implementation:**

```typescript
// authorization.ts — NEW function
export async function checkHighRiskPermission(
  userId: string,
  permissionKey: string,
  lastSignInAt: string | undefined
): Promise<void> {
  // Step 1: Recent auth required
  requireRecentAuth(lastSignInAt)

  // Step 2: Explicit permission check (NO superadmin bypass)
  const { data, error } = await supabaseAdmin.rpc('has_explicit_permission', {
    _user_id: userId,
    _permission_key: permissionKey,
  })

  if (error || data !== true) {
    throw new PermissionDeniedError(
      `Explicit permission required: ${permissionKey}`,
      permissionKey,
      userId
    )
  }
}
```

**New SQL function required:**

```sql
CREATE OR REPLACE FUNCTION public.has_explicit_permission(_user_id UUID, _permission_key TEXT)
RETURNS BOOLEAN
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  IF _user_id IS NULL OR _permission_key IS NULL THEN
    RETURN false;
  END IF;
  -- NO is_superadmin() bypass — explicit check only
  RETURN EXISTS (
    SELECT 1
    FROM public.user_roles ur
    JOIN public.role_permissions rp ON rp.role_id = ur.role_id
    JOIN public.permissions p ON p.id = rp.permission_id
    WHERE ur.user_id = _user_id
      AND p.key = _permission_key
  );
END;
$$;
```

**Why this works for superadmin:** Superadmin role already has all permissions explicitly seeded via role_permissions (admin gets all except `jobs.emergency`; superadmin gets all via seed). The bypass is only a **convenience shortcut** — the explicit mappings exist. So `has_explicit_permission()` will return `true` for superadmin for all seeded permissions.

**Wait — correction:** Reviewing seed data (Step 6 of Phase 2 plan): "superadmin: NO seeded rows (logical inheritance via `has_permission()`)". This means superadmin does NOT have explicit role_permissions rows.

**Revised approach:** We need to seed explicit role_permissions for superadmin for the 6 high-risk permissions. This is a data-only change (INSERT), not a schema change.

**High-risk permissions to seed for superadmin:**
- `roles.assign`
- `roles.revoke`
- `permissions.assign`
- `permissions.revoke`
- `users.deactivate`
- `users.reactivate`

### High-Risk Actions List

| Action | Endpoint | Permission | Current `requireRecentAuth` |
|--------|----------|-----------|---------------------------|
| Role assignment | assign-role | `roles.assign` | ❌ MISSING |
| Role revocation | revoke-role | `roles.revoke` | ❌ MISSING |
| Permission assignment | assign-permission-to-role | `permissions.assign` | ❌ MISSING |
| Permission revocation | revoke-permission-from-role | `permissions.revoke` | ❌ MISSING |
| User deactivation | deactivate-user | `users.deactivate` | ✅ present |
| User reactivation | reactivate-user | `users.reactivate` | ✅ present |

**All 6 endpoints** will be migrated from `checkPermissionOrThrow()` to `checkHighRiskPermission()`, which enforces both explicit permission AND recent auth in a single call.

### Additional Guardrail: Superadmin Self-Role-Revocation Prevention

In `revoke-role`: if actor is revoking the `superadmin` role from themselves → deny with 400. DB trigger `prevent_last_superadmin_delete` handles the last-superadmin case, but does not prevent self-revocation when other superadmins exist.

### Files Changed (DW-015)

| File | Change |
|------|--------|
| `_shared/authorization.ts` | Add `checkHighRiskPermission()` using `has_explicit_permission` RPC |
| `sql/05_high_risk_helpers.sql` | New SQL file: `has_explicit_permission()` function |
| `assign-role/index.ts` | Replace `checkPermissionOrThrow` → `checkHighRiskPermission` |
| `revoke-role/index.ts` | Replace `checkPermissionOrThrow` → `checkHighRiskPermission` + self-revocation guard |
| `assign-permission-to-role/index.ts` | Replace `checkPermissionOrThrow` → `checkHighRiskPermission` |
| `revoke-permission-from-role/index.ts` | Replace `checkPermissionOrThrow` → `checkHighRiskPermission` |
| `deactivate-user/index.ts` | Replace `checkPermissionOrThrow` + `requireRecentAuth` → single `checkHighRiskPermission` |
| `reactivate-user/index.ts` | Replace `checkPermissionOrThrow` + `requireRecentAuth` → single `checkHighRiskPermission` |
| `docs/07-reference/function-index.md` | Add `has_explicit_permission()` entry |

**Data change (INSERT, not migration):**
- Seed 6 explicit role_permissions rows for superadmin role → high-risk permissions

### Success Criteria

- [ ] All 6 high-risk endpoints use `checkHighRiskPermission()` (explicit + recent auth)
- [ ] `has_explicit_permission()` SQL function deployed — no superadmin bypass
- [ ] Superadmin has explicit role_permissions for all 6 high-risk permissions
- [ ] Superadmin cannot revoke own superadmin role
- [ ] No regression: superadmin with fresh session + explicit permissions → all actions succeed
- [ ] No regression: success response shapes unchanged
- [ ] No regression: existing audit events unchanged
- [ ] Runtime verified: superadmin without explicit permission → 403 (if we temporarily remove seed)
- [ ] Runtime verified: superadmin with stale session → 403
- [ ] Runtime verified: superadmin self-role-revocation → denied

---

## Regression Protection (explicit)

No changes to:
- ✅ `has_permission()` SQL function (superadmin bypass preserved for non-high-risk)
- ✅ `is_superadmin()` SQL function
- ✅ Success response shapes on all endpoints
- ✅ Existing audit event names or metadata schemas
- ✅ 401/400 error handling paths
- ✅ Rate limiting behavior
- ✅ CORS handling
- ✅ Non-high-risk permission checks (still use `checkPermissionOrThrow`)

---

## Runtime Verification Plan

### DW-014 Verification
1. Call `list-users` with regular-user token → 403
2. Query `audit_logs WHERE action = 'auth.permission_denied'` → entry exists
3. Verify fields: `actor_id` matches user, `metadata.permission_key = 'users.view_all'`, `metadata.endpoint` present, `metadata.correlation_id` present
4. Verify: no sensitive data in metadata
5. Call endpoint with no auth → 401 (no denial audit — this is auth failure, not authorization)

### DW-015 Verification
1. All 4 RBAC endpoints: call with superadmin (fresh session) → 200 ✅
2. All 4 RBAC endpoints: call with superadmin (stale session >5min) → 403
3. `deactivate-user` + `reactivate-user`: already have requireRecentAuth, verify still works
4. `revoke-role` with superadmin targeting own superadmin role → denied (400)
5. Temporarily remove superadmin's explicit `roles.assign` permission → call `assign-role` → 403
6. Restore permission → call `assign-role` → 200

---

## Execution Stages

| Stage | Scope |
|-------|-------|
| 3.5A | DW-014: errors.ts + handler.ts + authorization.ts + event-index.md |
| 3.5B | DW-015: SQL function + authorization.ts + 6 endpoint files + seed data + self-revocation guard |
| 3.5C | Runtime verification + closure artifacts (master-plan, system-state, deferred-work-register) |

---

## Deferred from Phase 3.5

| ID | Item | Phase |
|----|------|-------|
| DW-016 (new) | Denial log aggregation/sampling for high-volume attack scenarios | Phase 6 |
