# Auth Module

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-08

## Purpose

Handles all user authentication: sign up, sign in, sign out, password reset, social login, MFA.

## Scope

Authentication flows only. Authorization (permissions) is handled by the RBAC module.

## Key Rules

- All auth flows use Supabase Auth
- No custom JWT generation
- MFA required for admin roles, optional for others
- Social login: Google and Apple
- Email verification required before full access

## Shared Functions

| Function | Purpose | Used By |
|----------|---------|---------|
| `getCurrentUser()` | Returns authenticated user | All modules |
| `requireAuth()` | Guard — redirects if not authenticated | All protected routes |
| `signOut()` | Ends session, clears tokens | Layout, user-panel |

## Events

| Event | Emitted When | Consumed By |
|-------|-------------|-------------|
| `auth.signed_up` | New user registers | audit-logging, user-management |
| `auth.signed_in` | User logs in | audit-logging |
| `auth.signed_out` | User logs out | audit-logging |
| `auth.password_reset` | Password reset completed | audit-logging |
| `auth.mfa_enrolled` | MFA setup completed | audit-logging |
| `auth.failed_attempt` | Login failure | audit-logging, health-monitoring |

## Jobs

None owned by this module.

## Permissions

| Permission | Description |
|-----------|-------------|
| — | Auth module does not define permissions; it provides identity. RBAC assigns permissions. |

## Dependencies

- [Auth Security](../02-security/auth-security.md)
- [Security Architecture](../02-security/security-architecture.md)

## Used By / Affects

All modules depend on auth for user identity.

## Risks If Modified

HIGH — auth changes affect the entire security perimeter.

## Related Documents

- [Auth Security](../02-security/auth-security.md)
- [RBAC Module](rbac.md)
- [Audit Logging Module](audit-logging.md)
