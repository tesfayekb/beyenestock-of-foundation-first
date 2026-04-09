# User Panel Module

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-09

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

## Module-Local Components

| Component | Purpose |
|-----------|---------|
| `UserLayout` | Layout wrapper with user navigation (module-local, not cross-module shared) |

## Shared Functions

| Function | Purpose | Used By | Defined In |
|----------|---------|---------|------------|
| `requireSelfScope(userId)` | Enforces self-only access | user-panel, user-management | [Function Index](../07-reference/function-index.md) |

## Events

| Event | Emitted When | Consumed By | Notes |
|-------|-------------|-------------|-------|
| `user_panel.settings_changed` | User updates settings | audit-logging | |
| `auth.session_revoked` | User revokes a session | audit-logging, health-monitoring | Owned by auth module; user panel triggers the action |
| `user_panel.mfa_updated` | MFA settings changed (enable/disable/reconfigure) | audit-logging | Self-service MFA management event |

## Jobs

None owned by this module.

## Permissions

| Permission | Description | Enforced By | Route(s) | Events |
|-----------|-------------|-------------|----------|--------|
| `profile.self_manage` | Manage own profile/settings | `requireSelfScope()`, `checkPermission()` | `/settings` | `user_panel.settings_changed` |
| `session.self_manage` | View/revoke own sessions | `requireSelfScope()`, `checkPermission()` | `/settings/security` | `auth.session_revoked` |
| `mfa.self_manage` | Manage own MFA settings | `requireSelfScope()`, `checkPermission()` | `/settings/security` | `user_panel.mfa_updated` |

**Note:** These are self-scope permissions defined in [permission-index.md](../07-reference/permission-index.md). Enforcement uses `requireSelfScope()` + `checkPermission()` — never role-based gating.

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
