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

**Self access (enforced via `requireSelfScope()` + RLS):**

- `users.view_self`
- `users.edit_self`

**Elevated access (admin permissions):**

- `users.view_all`
- `users.edit_any`
- `users.deactivate`
- `users.reactivate`

No access is granted based on role name alone. Self-scope access must be enforced through `requireSelfScope()` plus RLS.

## Lifecycle Rules

User lifecycle uses two stable states:

- `active` — user can authenticate and use the system
- `deactivated` — user cannot authenticate or use existing sessions

State transitions are recorded as events (`user.account_deactivated`, `user.account_reactivated`). Reactivation restores the user to `active` state.

**Deactivation effects (CRITICAL):**

- Active sessions must be revoked (`auth.session_revoked`)
- Tokens must be invalidated
- Login must be blocked while deactivated
- Audit history must be preserved
- Reactivation restores authentication eligibility but does not restore previously revoked sessions

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

| Permission | Description | Enforced By |
|-----------|-------------|-------------|
| `users.view_self` | View own profile | `requireSelfScope()`, RLS |
| `users.edit_self` | Edit own profile | `requireSelfScope()`, RLS |
| `users.view_all` | View all user profiles | `checkPermission()` |
| `users.edit_any` | Edit any user profile | `checkPermission()` |
| `users.deactivate` | Deactivate user accounts | `checkPermission()`, `requireRecentAuth()` |
| `users.reactivate` | Reactivate deactivated accounts | `checkPermission()`, `requireRecentAuth()` |

## Dependencies

- [Auth Module](auth.md)
- [RBAC Module](rbac.md)
- [Input Validation](../02-security/input-validation-and-sanitization.md)
- [Audit Logging Module](audit-logging.md)

## Used By / Affects

admin-panel, user-panel, auth module (deactivation triggers session/token invalidation).

## Risks If Modified

HIGH — affects user data access, lifecycle control, and administrative operations.

## Related Documents

- [Auth Module](auth.md)
- [RBAC Module](rbac.md)
- [Admin Panel](admin-panel.md)
- [User Panel](user-panel.md)
- [Authorization Security](../02-security/authorization-security.md)
