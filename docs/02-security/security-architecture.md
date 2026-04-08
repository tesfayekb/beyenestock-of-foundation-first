# Security Architecture

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-08

## Purpose

Defines the enforced security architecture and threat model for the application.

This document establishes **mandatory security controls** across all layers.

## Scope

All layers:

- Frontend
- API / edge functions
- Backend services
- Database
- Infrastructure

## Enforcement Rule (CRITICAL)

- All security controls defined here are **mandatory**
- Any violation results in an **INVALID** implementation
- No shortcuts or bypasses are allowed
- Security rules override convenience and performance trade-offs

## Trust Boundaries

| Zone | Trust Level | Rules |
|------|------------|-------|
| Client (browser) | **Untrusted** | Never rely on for security decisions |
| Frontend runtime | **Untrusted** for authorization | May render UI hints but must not enforce access |
| API / edge functions | **Trusted** execution layer | All business logic and authorization enforced here |
| Database with RLS | **Protected** data layer | All access governed by RLS policies |
| Service-role context | **Highly privileged** | Server-side only, never exposed to client |
| External integrations | **Conditionally trusted** | Must be validated at boundary |

## Security Layers

```
┌────────────────────────────────────┐
│  Layer 1: Input Validation &       │
│           Sanitization             │
├────────────────────────────────────┤
│  Layer 2: Authentication           │
├────────────────────────────────────┤
│  Layer 3: Authorization            │
├────────────────────────────────────┤
│  Layer 4: Data Protection          │
├────────────────────────────────────┤
│  Layer 5: Audit & Monitoring       │
└────────────────────────────────────┘
```

### Layer 1: Input Validation & Sanitization

- All inputs validated against schema (Zod)
- Sanitization applied to prevent XSS and injection
- Output encoding enforced where applicable
- Rate limiting applied at API boundary (per IP, per user, per endpoint)

### Layer 2: Authentication

- Email/password + OAuth (Google, Apple)
- MFA required for sensitive roles/actions
- Secure session management
- Token validation on every request
- Token rotation and expiration enforced
- Token storage: prefer httpOnly cookies over localStorage

### Layer 3: Authorization

- RBAC with dynamic permissions
- Roles stored in **separate table** (never on user/profile table)
- Security definer functions for permission checks
- RLS enforced on every table
- No authorization logic in client

### Layer 4: Data Protection

- Encryption at rest (database/storage)
- Encryption in transit (TLS)
- Sensitive data never exposed to client
- Secrets stored in environment variables only
- Secret rotation required

### Layer 5: Audit & Monitoring

- All significant actions logged (actor, action, timestamp)
- Failed authentication attempts tracked
- Audit logs are **immutable**, **append-only**, **tamper-resistant**, and **access-controlled**
- Health monitoring and alerting enabled

## Sensitive Operation Rules

The following MUST be protected with enhanced controls:

- Login / logout
- Password reset
- MFA enrollment / recovery
- Role or permission changes
- Account creation / deletion
- Token issuance / refresh

**Requirements:**

- Re-authentication where necessary
- Audit logging required
- RBAC enforcement mandatory

## Service Role Rules

- Service-role access is **server-side only**
- Must be minimized and explicitly justified
- Must be audited
- Must never be exposed to client code

## Security Boundary Rules

- No direct database access from client
- No bypass of RLS or RBAC
- No client-side-only authorization
- No hidden privileged paths
- All sensitive operations must pass through audited backend logic

## Threat Model (Expanded)

| Threat | Mitigation |
|--------|-----------|
| Privilege escalation | RBAC + RLS + role isolation |
| SQL injection | Parameterized queries + validation |
| XSS | Sanitization + output encoding |
| CSRF | SameSite cookies + token validation |
| Unauthorized data access | RLS enforcement |
| Credential stuffing | Rate limiting + MFA |
| Session hijacking | Secure cookies + token rotation |
| Abuse / API flooding | Rate limiting + monitoring |
| Insider misuse | Audit logging + least privilege |

## Key Principles

1. **Deny by default** — No access unless explicitly granted
2. **Never trust the client** — All validation server-side
3. **Roles in separate table** — Never store roles on user/profile table (prevents privilege escalation)
4. **Security definer functions** — For role checks to avoid RLS recursion
5. **No secrets in code** — All secrets in environment variables
6. **Audit everything** — Every state change is logged with actor, action, timestamp

## Dependencies

- [System Design Principles](../01-architecture/system-design-principles.md)
- [Architecture Overview](../01-architecture/architecture-overview.md)

## Used By / Affects

All modules, especially auth, rbac, api, audit.

## Risks If Changed

HIGH — weak security design compromises the entire system.

## Related Documents

- [Auth Security](auth-security.md)
- [Authorization Security](authorization-security.md)
- [Input Validation](input-validation-and-sanitization.md)
