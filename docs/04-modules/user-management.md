# User Management Module

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-08

## Purpose

Manages user profiles, account settings data, and user lifecycle state.

## Scope

Profile CRUD, account settings data, user search/listing, account deactivation/reactivation.

## Enforcement Rule (CRITICAL)

- Profile and lifecycle access must be enforced by **permissions** and **self-scope rules**
- RLS and backend authorization checks are mandatory
- Any unauthorized cross-user access is an **INVALID** implementation

## Key Rules

- Profile data is separate from auth data
- Self-service access is limited to the authenticated user's own profile
- Elevated access requires explicit permissions
- Profile and lifecycle changes are audited
- Deactivation uses soft delete / reversible lifecycle state

## Access Model

**Self access:**

- `users.view_self`
- `users.edit_self`

**Elevated access:**

- `users.view_all`
- `users.edit_any`
- `users.deactivate`

No access is granted based on role name alone.

## Lifecycle Rules

User lifecycle states must be explicitly defined and enforced:

- `active`
- `deactivated`
- `reactivated`

**Deactivation rules:**

- Must be auditable
- Must revoke active access as defined by auth/security policy
- Must preserve retained data per policy

## Shared Functions

| Function | Purpose | Used By |
|----------|---------|---------|
| `getUserProfile(userId)` | Fetch profile data | admin-panel, user-panel |
| `updateUserProfile(userId, data)` | Update profile data | admin-panel, user-panel |
| `listUsers(filters, pagination)` | List/filter users | admin-panel |
| `deactivateUser(userId)` | Deactivate account | admin-panel |
| `reactivateUser(userId)` | Restore account | admin-panel |

## Events

| Event | Emitted When | Consumed By |
|-------|-------------|-------------|
| `user.profile_updated` | Profile changed | audit-logging |
| `user.account_deactivated` | Account deactivated | audit-logging, admin-panel |
| `user.account_reactivated` | Account restored | audit-logging, admin-panel |

## Jobs

None owned by this module.

## Permissions

| Permission | Description |
|-----------|-------------|
| `users.view_self` | View own profile |
| `users.edit_self` | Edit own profile |
| `users.view_all` | View all user profiles |
| `users.edit_any` | Edit any user profile |
| `users.deactivate` | Deactivate user accounts |

## Dependencies

- [Auth Module](auth.md)
- [RBAC Module](rbac.md)
- [Input Validation](../02-security/input-validation-and-sanitization.md)
- [Audit Logging Module](audit-logging.md)

## Used By / Affects

admin-panel, user-panel, auth-related account lifecycle flows.

## Risks If Modified

HIGH — affects user data access, lifecycle control, and administrative operations.

## Related Documents

- [Auth Module](auth.md)
- [RBAC Module](rbac.md)
- [Admin Panel](admin-panel.md)
- [User Panel](user-panel.md)
- [Authorization Security](../02-security/authorization-security.md)
