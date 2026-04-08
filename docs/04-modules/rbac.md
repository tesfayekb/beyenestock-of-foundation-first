# RBAC Module

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-08

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
| `superadmin` | Full access to all current and future permissions |
| `user` | Default role with baseline access |

**Rules:**

- Base roles cannot be deleted
- Base roles cannot be modified
- `superadmin` automatically has all permissions (including newly created ones)

## Dynamic Roles

- Roles can be created, updated, and deleted at runtime
- Roles are assigned permissions dynamically
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

### Permission Tables (Conceptual)

```sql
permissions (
  id UUID PRIMARY KEY,
  key TEXT UNIQUE NOT NULL,
  description TEXT
)

role_permissions (
  id UUID PRIMARY KEY,
  role app_role NOT NULL,
  permission_id UUID REFERENCES permissions(id) ON DELETE CASCADE,
  UNIQUE (role, permission_id)
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
| `has_role(user_id, role)` | SQL security definer function | RLS policies |
| `checkPermission(permission)` | Default permission enforcement | All modules |
| `requireRole(role)` | Base-role bootstrap gating only | Admin panel initial access |
| `requireSelfScope(userId)` | Self-scope resource enforcement | user-panel, user-management |
| `useUserRole()` | Fetch current user role | UI components |

## Events

| Event | Emitted When | Consumed By |
|-------|-------------|-------------|
| `rbac.role_assigned` | Role assigned | audit-logging |
| `rbac.role_revoked` | Role removed | audit-logging |
| `rbac.permission_assigned` | Permission added to role | audit-logging |
| `rbac.permission_revoked` | Permission removed from role | audit-logging |
| `rbac.permission_denied` | Access denied | audit-logging, health-monitoring |

## Privileged RBAC Actions

The following are HIGH impact:

- Assigning roles
- Revoking roles
- Creating roles
- Deleting roles
- Assigning permissions
- Revoking permissions

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
