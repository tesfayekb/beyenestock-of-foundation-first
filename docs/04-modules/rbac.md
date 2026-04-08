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

Permissions are resource-based and dynamically generated.

### Permission Format

```
{resource}.{action}
```

Examples:

- `user.read`
- `user.create`
- `user.update`
- `user.delete`
- `audit.view`
- `config.update`

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
- Permissions must be centrally indexed (`permission-index.md`)
- Permission changes are HIGH impact

## Permission Enforcement

### Application Layer

- Use `checkPermission(permission)` for feature access
- Use `requireRole(role)` only for high-level gating (e.g., admin panel)

### Database Layer (RLS)

- Use `has_role()` or equivalent helper functions
- Avoid direct joins in RLS if recursion risk exists
- Policies must reflect permission model

## Shared Functions

| Function | Purpose | Used By |
|----------|---------|---------|
| `has_role(user_id, role)` | SQL security definer function | RLS policies |
| `checkPermission(permission)` | Checks permission dynamically | All modules |
| `requireRole(role)` | High-level role guard | Admin routes |
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
- Restricted to `superadmin` or equivalent permissions

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
