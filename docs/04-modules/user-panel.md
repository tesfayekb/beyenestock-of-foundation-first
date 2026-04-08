# User Panel Module

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-08

## Purpose

End-user interface for managing their own profile, settings, and account.

## Scope

User-facing UI: profile editing, password change, MFA settings, session management, notification preferences.

## Key Rules

- Users can only see and edit their own data
- RLS enforced on all queries
- MFA enrollment UI included
- Session listing with ability to revoke sessions

## Shared Functions

| Function | Purpose | Used By |
|----------|---------|---------|
| `UserLayout` | Layout wrapper with user nav | User pages only |

## Events

| Event | Emitted When | Consumed By |
|-------|-------------|-------------|
| `user_panel.settings_changed` | User updates settings | audit-logging |
| `user_panel.session_revoked` | User revokes a session | audit-logging |

## Jobs

None owned by this module.

## Permissions

| Permission | Description |
|-----------|-------------|
| — | No special permissions. All users have access to their own panel. |

## Dependencies

- [Auth Module](auth.md)
- [RBAC Module](rbac.md)
- [User Management Module](user-management.md)

## Used By / Affects

End-point module — no other modules depend on it.

## Risks If Modified

LOW — changes are isolated to user self-service.

## Related Documents

- [Admin Panel](admin-panel.md)
- [Auth Module](auth.md)
