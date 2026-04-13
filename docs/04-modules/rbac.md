# RBAC Module

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-13

## Purpose

Manages role-based access control, including dynamic roles, permission assignment, and enforcement across API and database layers.

## Scope

Role management, permission system, access control gates, and RLS integration.

## Enforcement Rules (CRITICAL)

- Authorization must be enforced **server-side** and at the **database level**
- No client-side checks may determine access
- Roles and permissions must not be hardcoded in business logic
- Any bypass of RBAC or RLS is an **INVALID** implementation

## RBAC Model

Authorization consists of:

1. **User → Roles**
2. **Roles → Permissions**
3. **Permissions → Resources/Actions**

## Base Roles (IMMUTABLE)

| Role | Description |
|------|-------------|
| `superadmin` | Full access to all current and future permissions (logical inheritance — no seeded permission rows) |
| `admin` | Administrative access — provisioned as a seed role during initial setup |
| `user` | Default role with baseline access |

**Rules:**

- Base roles cannot be deleted (enforced by DB trigger on `is_immutable`)
- Base roles' `key`, `is_base`, `is_immutable`, and `is_permission_locked` columns cannot be modified (enforced by DB trigger)
- `superadmin` automatically has all permissions via logical inheritance in `has_permission()` — no individual permission rows can be assigned or revoked from superadmin
- `admin` permissions can only be modified by a superadmin with 5-minute reauth window
- `user` role permissions are locked (`is_permission_locked = true`) and cannot be modified by any actor
- Last superadmin assignment cannot be deleted (enforced by DB trigger + application layer)
- A superadmin cannot revoke their own superadmin role (enforced by application layer + API)

## Superadmin Governance

Superadmin is the apex role. Its assignment and management follow stricter rules than all other roles.

### Bootstrap
The first user to sign up is automatically assigned both `superadmin` and `user` roles via a DB trigger (`handle_new_user_role`). This is protected with `pg_advisory_xact_lock(42)` to prevent race conditions. The event is recorded in audit logs as `rbac.first_superadmin_bootstrapped`.

### Assignment
- Only an existing superadmin can assign the `superadmin` role to another user
- Requires 5-minute reauth window (vs 30-minute standard)
- Enforced at API layer in `assign-role` edge function
- Any admin with `roles.assign` is blocked from assigning superadmin (403)

### Revocation
- A superadmin cannot revoke their own superadmin role (UI shows lock icon; API returns 409)
- The last superadmin cannot be removed under any circumstances (DB trigger enforces)
- Standard hierarchy: only superadmin can revoke the `admin` or `superadmin` role from others

### Permission scope
- Superadmin inherits all permissions logically — no individual `role_permissions` rows exist for superadmin
- Individual permission assignment to superadmin is blocked (409 from assign-permission-to-role)

## User Role Governance

- The `user` role is automatically assigned to every new user on signup (DB trigger `handle_new_user_role`)
- The `user` role cannot be manually assigned via API — blocked with `USER_ROLE_AUTO_ASSIGNED` (409)
- The `user` role cannot be revoked from any user — blocked at API layer and shown as locked in UI
- User role is removed only when the user account is deleted (cascade via `ON DELETE CASCADE`)
- The `user` role has `is_permission_locked = true` — its permissions cannot be modified by any actor
- The 5 user-role permissions (`users.view_self`, `users.edit_self`, `profile.self_manage`, `mfa.self_manage`, `session.self_manage`) are universally held by all users and shown as "all users" in the RoleDetailPage UI

## Dynamic Roles

- The schema and backend are **dynamic-role-capable**: roles can be created, updated, and deleted at runtime via the `roles` table
- **Phase 2** delivers the dynamic-role-capable foundation (schema, helpers, RPCs)
- **Operational creation/deletion of dynamic roles** via admin UI is deferred to Phase 4
- Roles are assigned permissions dynamically via privileged server-side RPCs (not direct client writes)
- Role changes are HIGH impact and must be audited

## Permission Model

Permissions are centrally defined in [permission-index.md](../07-reference/permission-index.md) and provisioned dynamically into the RBAC system from that index. No permission may exist at runtime unless it is registered in the Permission Index with an immutable key.

### Permission Format

```
{resource}.{action}
```

Examples:

- `users.view_all`
- `users.create`
- `users.edit_self`
- `audit.view`
- `config.update`

### Permission Scope

Permission scope is governed by [permission-index.md](../07-reference/permission-index.md) and must be enforced consistently across application layer, API layer, and RLS.

| Scope | Description | Example |
|-------|-------------|---------|
| **self** | User can only act on own resources | `users.view_self`, `profile.self_manage` |
| **resource-scoped** | Access to specific resource instances | `audit.view` |
| **tenant-scoped** | Access within tenant boundary | Future implementation |
| **system-wide** | Unrestricted scope | `system.kill_switch` |

### Schema

```sql
roles (
  id UUID PRIMARY KEY,
  key TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  description TEXT,
  is_base BOOLEAN NOT NULL DEFAULT false,
  is_immutable BOOLEAN NOT NULL DEFAULT false,
  is_permission_locked BOOLEAN NOT NULL DEFAULT false,  -- protects permission assignments; separate from identity immutability
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ
)

permissions (
  id UUID PRIMARY KEY,
  key TEXT UNIQUE NOT NULL,
  description TEXT,
  created_at TIMESTAMPTZ
)

user_roles (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  role_id UUID REFERENCES roles(id) ON DELETE CASCADE,
  assigned_at TIMESTAMPTZ,
  assigned_by UUID REFERENCES auth.users(id),
  UNIQUE (user_id, role_id)
)

role_permissions (
  id UUID PRIMARY KEY,
  role_id UUID REFERENCES roles(id) ON DELETE CASCADE,
  permission_id UUID REFERENCES permissions(id) ON DELETE CASCADE,
  UNIQUE (role_id, permission_id)
)
```

### Permission Rules

- Every resource must define permissions at creation
- No resource may exist without permissions
- Permissions must be centrally indexed in [permission-index.md](../07-reference/permission-index.md) — the Permission Index is the SSOT
- RBAC permission records must reconcile with permission-index.md; undocumented or missing permissions are invalid
- Permission drift detection and DB reconciliation are governed by the Permission Index
- Permission changes are HIGH impact

## Permission Enforcement

### Application Layer

- `checkPermission(permission)` is the **default enforcement mechanism** for routes, APIs, and features
- `requireRole(role)` is reserved for narrowly approved base-role or bootstrap gating only (e.g., initial admin panel access) — it must NOT be used for general authorization
- `requireSelfScope(userId)` enforces self-scope permissions — ensures user can only act on own resources

### Database Layer (RLS)

- Use `has_role()` or equivalent helper functions
- Avoid direct joins in RLS if recursion risk exists
- Policies must reflect the permission model defined in [permission-index.md](../07-reference/permission-index.md)

## Shared Functions

| Function | Purpose | Used By |
|----------|---------|---------|
| `is_superadmin(user_id)` | SQL security definer — fast-path superadmin check | RLS policies, `has_permission()` |
| `has_role(user_id, role_key)` | SQL security definer — check role by key | RLS policies |
| `has_permission(user_id, permission_key)` | SQL security definer — logical superadmin inheritance, else explicit mapping | RLS policies, edge functions |
| `get_my_authorization_context()` | SQL security definer — returns caller's effective roles + permissions | `useUserRoles()` hook |
| `checkPermission(permission)` | Default permission enforcement (client-side UX) | All modules |
| `requireRole(role)` | Base-role bootstrap gating only | Admin panel initial access |
| `requireSelfScope(userId)` | Self-scope resource enforcement | user-panel, user-management |
| `useUserRoles()` | Fetch current user's roles, permissions, superadmin status | UI components |
| `assign_role(target_user_id, role_id)` | Privileged RPC — assign role to user | Edge function |
| `revoke_role(target_user_id, role_id)` | Privileged RPC — revoke role from user | Edge function |
| `assign_permission_to_role(role_id, permission_id)` | Privileged RPC — assign permission to role | Edge function |
| `revoke_permission_from_role(role_id, permission_id)` | Privileged RPC — revoke permission from role | Edge function |

## Events

| Event | Emitted When | Consumed By |
|-------|-------------|-------------|
| `rbac.role_assigned` | Role assigned | audit-logging |
| `rbac.role_revoked` | Role removed | audit-logging |
| `rbac.permission_assigned` | Permission added to role | audit-logging |
| `rbac.permission_revoked` | Permission removed from role | audit-logging |
| `rbac.permission_denied` | Access denied | audit-logging, health-monitoring |
| `rbac.first_superadmin_bootstrapped` | First user signup triggers superadmin auto-assignment | audit-logging |

## Privileged RBAC Actions

| Action | Required Permission | Additional Guard | Reauth Window |
|--------|-------------------|-----------------|---------------|
| Assign any role | `roles.assign` | — | 30 min |
| Assign superadmin role | `roles.assign` | `is_superadmin()` check | 5 min |
| Revoke any role | `roles.revoke` | Hierarchy check (superadmin only for admin/superadmin) | 30 min |
| Create role | `roles.create` | `is_superadmin()` required | 5 min |
| Delete role | `roles.delete` | `is_superadmin()` required | 5 min |
| Assign permission to any role | `permissions.assign` | — | 30 min |
| Assign/revoke permission on admin role | `permissions.assign/revoke` | `is_superadmin()` required | 5 min |
| Assign/revoke permission on superadmin role | — | Blocked entirely (409) | — |
| Assign/revoke permission on user role | — | Blocked by `is_permission_locked` (409) | — |

**Requirements:**

- Server-side enforcement
- Audit logging required
- Restricted to the explicit permissions defined in [permission-index.md](../07-reference/permission-index.md) (e.g., `roles.assign`, `roles.revoke`); `superadmin` inherits these automatically

## Dependencies

- [Auth Module](auth.md)
- [Authorization Security](../02-security/authorization-security.md)

## Used By / Affects

- admin-panel
- user-panel
- api
- user-management
- audit-logging

## Risks If Modified

HIGH — incorrect RBAC logic can cause privilege escalation or system-wide access failures.

## Related Documents

- [Authorization Security](../02-security/authorization-security.md)
- [Permission Index](../07-reference/permission-index.md)
- [Auth Module](auth.md)
- [Audit Logging Module](audit-logging.md)
