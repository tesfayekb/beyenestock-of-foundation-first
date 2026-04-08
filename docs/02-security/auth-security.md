# Auth Security

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-08

## Purpose

Defines authentication security requirements and implementation rules.

## Scope

User authentication: email/password, social login (Google, Apple), MFA.

## Authentication Methods

| Method | Priority | Status |
|--------|----------|--------|
| Email + Password | Required | Not started |
| Google OAuth | Required | Not started |
| Apple Sign-In | Required | Not started |
| MFA (TOTP) | Required | Not started |

## Security Rules

### Password Policy
- Minimum 12 characters
- Must include uppercase, lowercase, number, special character
- Bcrypt hashing (handled by Supabase Auth)
- No password reuse (last 5)

### Session Management
- JWT tokens via Supabase Auth
- Access token: short-lived (1 hour max)
- Refresh token: rotation on use
- Secure, HttpOnly, SameSite cookies where applicable

### MFA
- TOTP-based (authenticator app)
- Required for admin roles
- Optional for regular users (strongly encouraged)
- Recovery codes generated on MFA enrollment

### Rate Limiting
- Login attempts: max 5 per minute per IP
- Password reset: max 3 per hour per email
- Account lockout after 10 consecutive failures

### Social Login Security
- Validate OAuth tokens server-side
- Link social accounts to existing users by verified email
- Never trust client-provided OAuth data

## Dependencies

- [Security Architecture](security-architecture.md)
- [Auth Module](../04-modules/auth.md)

## Used By / Affects

Every authenticated feature in the application.

## Risks If Changed

HIGH — authentication is the security perimeter.

## Related Documents

- [Security Architecture](security-architecture.md)
- [Authorization Security](authorization-security.md)
- [Auth Module](../04-modules/auth.md)
- [RBAC Module](../04-modules/rbac.md)
