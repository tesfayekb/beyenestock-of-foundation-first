# RBAC Module

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-08

## Purpose

Manages role-based access control: role assignment, permission checking, and RLS policy enforcement.

## Scope

Role management, permission resolution, access control gates.

## Key Rules

- Roles stored in `user_roles` table (NEVER on profile table)
- Use `has_role()` security definer function for all permission checks
- No client-side role checks for security decisions
- Default role for new users: `user`
- Role changes are audited

## Shared Functions

| Function | Purpose | Used By |
|----------|---------|---------|
| `has_role(user_id, role)` | SQL security definer function | All RLS policies |
| `useUserRole()` | React hook — fetches current user's role | admin-panel, user-panel, layout |
| `requireRole(role)` | Guard — denies access if role not matched | Protected routes |
| `checkPermission(permission)` | Checks specific permission for current user | All feature modules |

## Events

| Event | Emitted When | Consumed By |
|-------|-------------|-------------|
| `rbac.role_assigned` | Role given to user | audit-logging |
| `rbac.role_revoked` | Role removed from user | audit-logging |
| `rbac.permission_denied` | Access denied | audit-logging, health-monitoring |

## Jobs

None owned by this module.

## Permissions

| Permission | Description |
|-----------|-------------|
| `roles.assign` | Can assign roles to users |
| `roles.revoke` | Can revoke roles from users |
| `roles.view` | Can view role assignments |

## Dependencies

- [Auth Module](auth.md)
- [Authorization Security](../02-security/authorization-security.md)

## Used By / Affects

admin-panel, user-panel, api, user-management.

## Risks If Modified

HIGH — RBAC changes can cause privilege escalation or denial of service.

## Related Documents

- [Authorization Security](../02-security/authorization-security.md)
- [Permission Index](../07-reference/permission-index.md)
- [Auth Module](auth.md)
