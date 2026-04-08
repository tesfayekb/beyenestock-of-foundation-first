# Environment Variable Index

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-08

## Purpose

Central registry of all environment variables required by the application.

## Scope

All environment variables across all environments.

## Env Var Map

| Name | Module | Used By | Impact If Changed |
|------|--------|---------|-------------------|
| `SUPABASE_URL` | infrastructure | All Supabase client calls | HIGH — breaks all API access |
| `SUPABASE_ANON_KEY` | infrastructure | Frontend Supabase client | HIGH — breaks frontend API |
| `SUPABASE_SERVICE_ROLE_KEY` | infrastructure | Edge functions (server-side) | HIGH — breaks server operations |
| `SUPABASE_JWT_SECRET` | infrastructure | Token validation | HIGH — breaks authentication |

> Additional environment variables will be added as modules are implemented (e.g., OAuth client IDs, SMTP configuration, external API keys).

## Rules

- Never expose service role key to the client
- Anon key is safe for client-side (publishable)
- All secrets managed through Lovable Cloud secrets management
- No secrets in code, environment files committed to git, or client bundles

## Dependencies

- [Security Architecture](../02-security/security-architecture.md)

## Used By / Affects

All modules that access external services.

## Related Documents

- [Config Index](config-index.md)
- [Security Architecture](../02-security/security-architecture.md)
