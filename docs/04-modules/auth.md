# Auth Module

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-11

## Purpose

Handles all user authentication: sign up, sign in, sign out, password reset, social login, MFA.

## Scope

Authentication flows only. Authorization (permissions) is handled by the RBAC module.

## Enforcement Rules

- This module is the **sole source of authentication truth**
- No module may implement independent auth logic
- Identity must come only from approved Supabase Auth flows
- Authorization is delegated to RBAC and must not be hardcoded here
- Any violation results in an **INVALID** implementation

## Key Rules

- All auth flows use Supabase Auth
- No custom JWT generation
- MFA required for admin roles, optional for others
- Social login: Google and Apple
- Email verification required before full access
- CAPTCHA tokens must be omitted entirely when unavailable; placeholder or empty tokens must never be forwarded to Supabase Auth

## User Flows

| Flow | Description |
|------|-------------|
| Sign up | Email/password registration |
| Email verification | Confirm email before full access |
| Sign in | Email/password authentication |
| Sign out | End session, clear tokens |
| Password reset request | Send reset link to verified email |
| Password reset completion | Set new password via valid token |
| Social login callback | Handle OAuth return from Google/Apple |
| MFA enroll | Set up TOTP authenticator |
| MFA verify | Challenge during sign-in |
| MFA recovery | Use one-time recovery code |

## Auth State Rules

- Unauthenticated users may only access public routes
- Unverified email blocks access to protected features
- MFA challenge must be completed before session is fully active (admin roles)
- Expired or invalid sessions require re-authentication
- `onAuthStateChange` subscribers must never await other Supabase Auth APIs directly; defer follow-up auth reads outside the callback to avoid auth-lock deadlocks and post-login blank screens

## Shared Functions

| Function | Purpose | Used By |
|----------|---------|---------|
| `getCurrentUser()` | Returns authenticated user | All modules |
| `requireAuth()` | Guard — redirects if not authenticated | All protected routes |
| `requireVerifiedEmail()` | Guard — blocks access if email unverified | All protected routes |
| `requireRecentAuth()` | Guard — requires recent authentication for sensitive actions | user-panel, admin-panel |
| `getSessionContext()` | Returns current session metadata | All modules |
| `signOut()` | Ends session, clears tokens | Layout, user-panel |

## Failure Modes

| Failure | System Response |
|---------|-----------------|
| Invalid or expired session | Redirect to sign-in |
| Unverified email | Block protected access, prompt verification |
| MFA challenge required | Present MFA input before completing sign-in |
| Existing MFA factor or incomplete MFA setup | `/mfa-enroll` must detect verified vs incomplete factors, avoid blind duplicate enrollment, and route user to continue or recover |
| OAuth callback failure | Display error, allow retry |
| Password reset token invalid/expired | Display error, allow new request |
| Repeated failed attempts | Progressive throttling / account lockout |

## Events

| Event | Emitted When | Consumed By |
|-------|-------------|-------------|
| `auth.signed_up` | New user registers | audit-logging, user-management |
| `auth.signed_in` | User logs in | audit-logging |
| `auth.signed_out` | User logs out | audit-logging |
| `auth.password_reset` | Password reset completed | audit-logging |
| `auth.mfa_enrolled` | MFA setup completed | audit-logging |
| `auth.mfa_recovered` | MFA recovery code used | audit-logging |
| `auth.failed_attempt` | Login failure | audit-logging, health-monitoring |
| `auth.session_revoked` | Session manually revoked | audit-logging |

## Monitoring

- Track login success/failure rates
- Track password reset requests/completions
- Track MFA enrollment/disable events
- Alert on auth failure spikes or suspicious patterns
- Report metrics to health-monitoring module

## Jobs

None owned by this module.

## Permissions

| Permission | Description |
|-----------|-------------|
| — | Auth module does not define permissions; it provides identity. RBAC assigns permissions. |

## Dependencies

- [Auth Security](../02-security/auth-security.md)
- [Security Architecture](../02-security/security-architecture.md)
- [User Management](user-management.md)
- [Health Monitoring](health-monitoring.md)
- [API Module](api.md)

## Used By / Affects

- [RBAC](rbac.md) — consumes identity for role/permission checks
- [User Management](user-management.md) — creates profile on sign-up
- [Admin Panel](admin-panel.md) — enforces admin auth + MFA
- [User Panel](user-panel.md) — session context, sign-out, account settings
- [Audit Logging](audit-logging.md) — records all auth events
- [API Module](api.md) — authenticates all API requests
- [Jobs & Scheduler](jobs-and-scheduler.md) — service-level auth for background tasks

## Risks If Modified

HIGH — auth changes affect the entire security perimeter.

## Related Documents

- [Auth Security](../02-security/auth-security.md)
- [RBAC Module](rbac.md)
- [Audit Logging Module](audit-logging.md)
- [User Management Module](user-management.md)
- [Health Monitoring Module](health-monitoring.md)
