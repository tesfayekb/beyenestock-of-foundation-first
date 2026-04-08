# User Panel Module

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-08

## Purpose

Provides a secure self-service interface for users to manage their own profile, settings, authentication settings, and active sessions.

## Scope

User-facing UI for:

- Profile editing
- Password change
- MFA enrollment and management
- Session visibility and revocation
- Notification/preferences management

## Enforcement Rule (CRITICAL)

- User panel is **self-service only**
- Users may access **only their own** data and sessions
- Any cross-user access is an **INVALID** implementation
- RLS and API-level checks are mandatory

## Access Control

- Authenticated access required
- Self-scope enforced by RLS and backend authorization
- No access to other users' records, sessions, or settings

## Key Rules

- Users can only view and edit their own data
- RLS enforced on all queries
- MFA enrollment and management UI included
- Session listing available with revocation controls
- Sensitive changes require secure validation and audit logging

## Sensitive User Actions

The following require enhanced controls:

- Password change
- MFA enrollment / disable
- Session revocation
- Email change (if supported)

**Requirements:**

- Recent authentication where appropriate
- Audit logging required
- Validation and sanitization required

## Shared Functions

| Function | Purpose | Used By |
|----------|---------|---------|
| `UserLayout` | Layout wrapper with user navigation | User pages |
| `requireSelfScope()` | Enforces self-only access | User panel routes / handlers |

## Events

| Event | Emitted When | Consumed By |
|-------|-------------|-------------|
| `user_panel.settings_changed` | User updates settings | audit-logging |
| `user_panel.session_revoked` | User revokes a session | audit-logging |
| `user_panel.mfa_updated` | MFA settings changed | audit-logging |

## Jobs

None owned by this module.

## Permissions

| Permission | Description |
|-----------|-------------|
| `profile.self_manage` | Manage own profile/settings |
| `session.self_manage` | View/revoke own sessions |
| `mfa.self_manage` | Manage own MFA settings |

**Note:** These are self-scope permissions, not broad administrative permissions.

## Dependencies

- [Auth Module](auth.md)
- [RBAC Module](rbac.md)
- [User Management Module](user-management.md)
- [Input Validation](../02-security/input-validation-and-sanitization.md)

## Used By / Affects

End-user self-service flows and account security operations.

## Risks If Modified

MEDIUM — incorrect changes can expose user data, weaken session security, or compromise MFA flows.

## Related Documents

- [Admin Panel](admin-panel.md)
- [Auth Module](auth.md)
- [Auth Security](../02-security/auth-security.md)
- [Input Validation](../02-security/input-validation-and-sanitization.md)
