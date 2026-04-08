# Auth Security

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-08

## Purpose

Defines enforced authentication security requirements and implementation rules.

## Scope

All authentication flows:

- Email/password
- Social login
- MFA
- Session management
- Recovery and reset flows

## Enforcement Rule (CRITICAL)

- All authentication controls defined here are **mandatory**
- Any violation results in an **INVALID** implementation
- Authentication rules override convenience

## Authentication Methods

| Method | Priority | Status |
|--------|----------|--------|
| Email + Password | Required | Not started |
| Google OAuth | Required | Not started |
| Apple Sign-In | Required | Not started |
| MFA (TOTP) | Required | Not started |

## Password Policy

- Minimum 12 characters
- Allow password manager-generated passwords
- Reject known weak/common passwords if supported
- No password reuse for last 5
- Password hashing handled by trusted auth provider

## Session Management

- JWT/session tokens via trusted auth provider
- Access tokens short-lived
- Refresh token rotation enforced
- Secure, HttpOnly, SameSite cookies where applicable
- Session revocation required on password reset/change
- Ability to revoke all active sessions required
- Suspicious session activity must be auditable

## MFA

- TOTP-based authenticator app
- Required for admin roles
- Optional but encouraged for regular users
- Recovery codes generated on enrollment
- Recovery codes are **one-time use**
- Regenerating recovery codes invalidates previous set
- MFA disable/reset is a high-risk action requiring re-authentication

## Sensitive Auth Flows

The following require enhanced controls:

- Password reset
- Email verification
- Email change
- Password change
- MFA enrollment / disable / recovery
- Logout all sessions
- Account deletion

**Requirements:**

- Re-authentication where appropriate
- Audit logging required
- Rate limiting required

## Re-Authentication Rules

Recent authentication is required for:

- Password change
- Email change
- MFA disable
- Role-sensitive account changes
- Account deletion

## Rate Limiting

- Login attempts: max 5 per minute per IP
- Password reset: max 3 per hour per email
- MFA verification attempts rate limited
- Account lockout / progressive throttling after repeated failures

## Social Login Security

- Validate OAuth tokens server-side
- Never trust client-provided OAuth data
- Only link accounts using verified identity data
- Prevent unsafe account merging or takeover on ambiguous identity claims

## Audit Requirements

Log all authentication-sensitive events:

- Login success/failure
- Password reset requested/completed
- MFA enrolled/disabled/recovered
- Email change
- Session revoked
- Suspicious auth activity

## Dependencies

- [Security Architecture](security-architecture.md)
- [Auth Module](../04-modules/auth.md)

## Used By / Affects

Every authenticated feature and all session-protected flows.

## Risks If Changed

HIGH — authentication is the primary entry boundary to the system.

## Related Documents

- [Security Architecture](security-architecture.md)
- [Authorization Security](authorization-security.md)
- [Auth Module](../04-modules/auth.md)
- [RBAC Module](../04-modules/rbac.md)
- [Audit Logging](../04-modules/audit-logging.md)
