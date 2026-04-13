# RBAC Governance Hardening — Closure Report

> **Date:** 2026-04-13 | **Owner:** Project Lead | **Status:** Complete

## Summary

Comprehensive hardening pass on RBAC enforcement across server (edge functions) and UI (admin panel) layers. This work **supersedes and expands** DW-015 (Superadmin Guardrails), which covered only `requireRecentAuth()` and self-revocation prevention. This session added permanent structural restrictions, inheritance visibility, and button-level permission gating.

## Scope

### Phase 1A/1B — Migration & Schema Foundation

- `is_permission_locked` and `is_immutable` column separation already in schema
- Superadmin role: `is_immutable = true`, `is_permission_locked = false` (inherits all logically — locking unnecessary)
- Admin role: `is_immutable = true`, `is_permission_locked = false`
- User role: `is_immutable = true`, `is_permission_locked = true`

### Phase 2A — assign-permission-to-role Hardening

- Added `SUPERADMIN_ONLY_PERMISSIONS` set (9 keys):
  - `permissions.assign` — governs the RBAC system itself
  - `permissions.revoke` — governs the RBAC system itself
  - `roles.create` — structural change to authorization model
  - `roles.edit` — structural change to authorization model
  - `roles.delete` — structural change to authorization model
  - `jobs.emergency` — system-wide kill switch
  - `admin.config` — system configuration; privilege escalation vector (NIST AC-6, SOC 2 CC6.3)
  - `monitoring.configure` — alert threshold modification enables audit evasion (PCI-DSS Req 10, SOC 2 CC7)
  - `audit.export` — bulk compliance data exfiltration risk (HIPAA, GDPR, SOC 2, ISO 27001 A.9.2.3)
- Server rejects any attempt to assign these permissions to a non-superadmin role with `403 SUPERADMIN_ONLY_PERMISSION`
- Validates `role.key !== 'superadmin'` before blocking — superadmin itself retains full assignment capability

### Phase 2B — revoke-permission-from-role Hardening

- Mirrors Phase 2A enforcement on the revoke path
- Prevents revocation of superadmin-only permissions from the superadmin role (structural integrity)

### Phase 2C — list-roles Effective Count

- `list-roles` edge function now returns effective permission count as union of direct + inherited user-role permissions
- Non-user, non-superadmin roles include inherited base permissions in their count

### Phase 3A — RoleDetailPage UI: Permission Inheritance

- Base user-role permissions (5 keys): `users.view_self`, `users.edit_self`, `profile.self_manage`, `mfa.self_manage`, `session.self_manage`
- On non-user roles: these permissions display as checked, disabled, with "inherited from user role" badge
- On user role itself: permissions are directly manageable (no inheritance badge)
- `effectivePermissionCount` computed via `useMemo` — union of direct + inherited

### Phase 3B — RoleDetailPage UI: Superadmin-Only Restrictions

- 6 superadmin-only permissions display as disabled with "superadmin only" badge on ALL non-superadmin roles
- Toggle is permanently disabled — not just hidden — with clear visual explanation
- Combined with inheritance: a permission can be both "inherited" and visible, or "superadmin only" and locked

### Phase 4A — get-role-detail Effective Count

- `get-role-detail` edge function includes inherited permissions in the effective count
- Consistent with `list-roles` count logic

## 8 Button-Level Gaps Closed

All admin action buttons now enforce granular permissions via `checkPermission()`:

| # | Button | Page | Permission Required |
|---|--------|------|-------------------|
| 1 | Deactivate User | UserDetailPage | `users.deactivate` |
| 2 | Reactivate User | UserDetailPage | `users.reactivate` |
| 3 | Export CSV | AdminAuditPage | `audit.export` |
| 4 | Kill Switch | AdminJobsPage | `jobs.emergency` |
| 5 | Pause Job | AdminJobsPage | `jobs.pause` |
| 6 | Resume Job | AdminJobsPage | `jobs.resume` |
| 7 | Replay Dead Letter | AdminJobsPage | `jobs.deadletter.manage` |
| 8 | jobs-resume edge function | jobs-resume/index.ts | Fixed: was checking `jobs.pause` instead of `jobs.resume` |

Buttons are hidden when the user lacks the required permission. Server-side enforcement is the primary gate; UI hiding is defense-in-depth.

## Reauth Dialog Architecture Fix

**Problem:** TanStack Query v5 changed `onError` ordering — global mutation `onError` fires before per-call `onError`. The global handler in `useAssignPermission`/`useRevokePermission` silently returned for `RECENT_AUTH_REQUIRED`, but the per-call handler in `performToggle` never received the error.

**Fix:**
- Moved `RECENT_AUTH_REQUIRED` detection to the **global** mutation `onError` handler (where TanStack Query v5 routes it first)
- `onReauthRequired` callback called synchronously within `onError`, setting React state and opening the dialog
- Moved `refetch()` from `onSuccess` to `onSettled` (runs on both success and error — correct placement)
- Eliminated unhandled-rejection surface: error is consumed in the mutation's own `onError`

## Regression Test Updates

- `rw008-permission-deps-drift.test.ts`: Updated to verify edge functions import from `_shared/permission-deps.ts` (not raw JSON). Added sync check ensuring `_shared/permission-deps.ts` matches `permission-deps.json` SSOT.

## Files Modified

### Edge Functions
- `supabase/functions/assign-permission-to-role/index.ts`
- `supabase/functions/revoke-permission-from-role/index.ts`
- `supabase/functions/list-roles/index.ts`
- `supabase/functions/get-role-detail/index.ts`

### UI Components
- `src/pages/admin/RoleDetailPage.tsx`
- `src/pages/admin/UserDetailPage.tsx`
- `src/hooks/useRoleActions.ts`

### Tests
- `src/test/rw008-permission-deps-drift.test.ts`

## Deferred Items from This Session

| Item | Deferred To | Reason |
|------|-------------|--------|
| DW-034: Superadmin Assignment Notification Email | v2 | Requires email/notification infrastructure |
| DW-035: Invite-Only Signup Flow | v2 | Requires invitation token system |

## Evidence

- All 83 tests pass (83/83)
- Edge functions deployed and verified
- Server-side 403 enforcement verified for superadmin-only permissions
- UI inheritance badges render correctly on non-user roles
- Reauth dialog opens correctly on `RECENT_AUTH_REQUIRED`

## Related Documents

- [Deferred Work Register — DW-015 supersession note](../deferred-work-register.md)
- [System State — RBAC Governance Hardening section](../../00-governance/system-state.md)
- [RBAC Module Documentation](../../04-modules/rbac.md)
- [Security Architecture](../../02-security/security-architecture.md)
