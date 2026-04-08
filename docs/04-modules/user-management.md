# User Management Module

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-08

## Purpose

Manages user profiles, account settings, and user lifecycle.

## Scope

Profile CRUD, account settings, user search/listing, account deactivation.

## Key Rules

- Profile data is separate from auth data
- Users can only edit their own profile (enforced by RLS)
- Admins can view/edit all profiles
- Profile changes are audited
- Soft delete for account deactivation

## Shared Functions

| Function | Purpose | Used By |
|----------|---------|---------|
| `getUserProfile(userId)` | Fetches user profile | admin-panel, user-panel |
| `updateUserProfile(userId, data)` | Updates profile data | admin-panel, user-panel |
| `listUsers(filters, pagination)` | Lists users with filtering | admin-panel |

## Events

| Event | Emitted When | Consumed By |
|-------|-------------|-------------|
| `user.profile_updated` | Profile data changed | audit-logging |
| `user.account_deactivated` | Account soft-deleted | audit-logging, admin-panel |
| `user.account_reactivated` | Account restored | audit-logging, admin-panel |

## Jobs

None owned by this module.

## Permissions

| Permission | Description |
|-----------|-------------|
| `users.view_all` | Can view all user profiles |
| `users.edit_any` | Can edit any user profile |
| `users.deactivate` | Can deactivate user accounts |

## Dependencies

- [Auth Module](auth.md)
- [RBAC Module](rbac.md)

## Used By / Affects

admin-panel, user-panel.

## Risks If Modified

MEDIUM — affects user data access patterns.

## Related Documents

- [Auth Module](auth.md)
- [RBAC Module](rbac.md)
- [Admin Panel](admin-panel.md)
- [User Panel](user-panel.md)
