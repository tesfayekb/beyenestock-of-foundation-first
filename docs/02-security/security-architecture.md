# Security Architecture

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-08

## Purpose

Defines the overall security architecture and threat model for the application.

## Scope

All layers: frontend, API, database, infrastructure.

## Security Layers

```
┌────────────────────────────────────┐
│  Layer 1: Input Validation         │
│  - Schema validation (Zod)         │
│  - Sanitization                    │
│  - Rate limiting                   │
├────────────────────────────────────┤
│  Layer 2: Authentication           │
│  - Email/password + social + MFA   │
│  - Session management              │
│  - Token validation                │
├────────────────────────────────────┤
│  Layer 3: Authorization            │
│  - RBAC with dynamic permissions   │
│  - RLS policies on every table     │
│  - Security definer functions      │
├────────────────────────────────────┤
│  Layer 4: Data Protection          │
│  - Encryption at rest              │
│  - Encryption in transit (TLS)     │
│  - No sensitive data in client     │
├────────────────────────────────────┤
│  Layer 5: Audit & Monitoring       │
│  - All write operations logged     │
│  - Failed auth attempts tracked    │
│  - Health monitoring               │
└────────────────────────────────────┘
```

## Key Principles

1. **Deny by default** — No access unless explicitly granted
2. **Never trust the client** — All validation server-side
3. **Roles in separate table** — Never store roles on user/profile table (prevents privilege escalation)
4. **Security definer functions** — For role checks to avoid RLS recursion
5. **No secrets in code** — All secrets in environment variables
6. **Audit everything** — Every state change is logged with actor, action, timestamp

## Threat Model (High-Level)

| Threat | Mitigation |
|--------|-----------|
| Privilege escalation | Roles in separate table + security definer functions |
| SQL injection | Parameterized queries via Supabase client |
| XSS | React auto-escaping + input sanitization |
| CSRF | SameSite cookies + token validation |
| Unauthorized data access | RLS on every table |
| Credential stuffing | Rate limiting + MFA |
| Session hijacking | Secure cookie settings + rotation |

## Dependencies

- [System Design Principles](../01-architecture/system-design-principles.md) — Security First, Least Privilege, Defense in Depth

## Used By / Affects

All modules, especially auth, rbac, api.

## Risks If Changed

HIGH — security architecture changes affect the entire threat model.

## Related Documents

- [Auth Security](auth-security.md)
- [Authorization Security](authorization-security.md)
- [Input Validation](input-validation-and-sanitization.md)
