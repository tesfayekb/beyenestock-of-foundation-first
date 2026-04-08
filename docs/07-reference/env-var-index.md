# Environment Variable Index

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-08 | **Status:** Living Document | **Env Version:** `env-v1.0`

## Purpose

Central registry and **governance system** for all environment variables required by the application. This document is the single source of truth for environment configuration — it defines what variables exist, their classification, validation rules, rotation policies, and audit requirements.

## Scope

All environment variables across all environments (local, CI, staging, production).

---

## Enforcement Rule (CRITICAL)

| Rule | Description |
|------|-------------|
| **Completeness** | No environment variable may exist outside this index. Undocumented env var = unauthorized. |
| **Ownership** | Every env var must have a defined purpose and owning module. |
| **Secret boundary** | Secrets must only exist in approved secret manager (Lovable Cloud). Plain-text secrets in code, env files, or client bundles are **prohibited**. |
| **Drift prohibition** | Env drift from documented baseline is **invalid**. Deployed env must match this index. |
| **Exposure enforcement** | Server-only env vars must **never** appear in frontend bundles, client code, or logs. Build process must enforce exposure boundaries. |
| **Startup gate** | Application must validate all `required` env vars at startup. Missing critical vars = fail-fast (do not start). |

---

## Env Var Classification Model

| Classification | Description | Exposure | Governance Level |
|---------------|-------------|----------|-----------------|
| **secret** | API keys, signing keys, service credentials | Server-only, never logged | Highest — rotation required, audit mandatory |
| **infrastructure-critical** | Database URLs, auth endpoints | Server-only | High — change requires approval |
| **internal** | Backend-only non-secret config | Server-only | Medium — review recommended |
| **public** | Safe for frontend exposure (publishable keys) | Client-safe | Standard — documented |
| **feature-control** | Feature flags, toggles via env | Varies | Standard — tracked |

---

## Env Var Entry Schema

Every env var entry must include:

| Field | Description | Required |
|-------|-------------|----------|
| `name` | Variable name | Yes |
| `type` | Data type (`string`, `url`, `key`, `boolean`, `integer`, `duration`) | Yes |
| `classification` | From classification model above | Yes |
| `module` | Owning module | Yes |
| `description` | What this variable does | Yes |
| `source` | Where the value comes from (`secret-manager`, `CI-config`, `deploy-config`, `platform-provided`) | Yes |
| `required` | Whether app fails without it | Yes |
| `default` | Default value if not set (secrets have no default) | If applicable |
| `format_validation` | Expected format (URL pattern, key length, regex) | Yes |
| `exposure` | `server-only` or `client-safe` | Yes |
| `environments` | Which environments use this var | Yes |
| `rotation_policy` | Rotation schedule for secrets | If secret |
| `blast_radius` | `small`, `medium`, `large`, `system-wide` | Yes |
| `startup_behavior` | `fail-fast`, `warn`, `use-default` | Yes |
| `related_configs` | Config index entries that depend on this var | If applicable |
| `related_routes` | Routes affected | If applicable |
| `related_risks` | Risk register items | If applicable |
| `related_tests` | Tests validating this var | If applicable |
| `lifecycle` | `active`, `deprecated`, `pending-removal`, `experimental` | Yes |

---

## Validation Rules

### Startup Validation (CRITICAL)

| Severity | Behavior | Applies To |
|----------|----------|------------|
| **Critical** | `fail-fast` — application must NOT start | All `required` secrets and infrastructure-critical vars |
| **Warning** | Log warning, continue with degraded functionality | Optional internal/feature-control vars |
| **Default** | Use documented default silently | Vars with safe defaults |

### Format Validation

| Validation | Rule |
|-----------|------|
| **URL vars** | Must match valid URL pattern (`https://...`) |
| **Key vars** | Must meet minimum length requirement |
| **Boolean vars** | Must be `true` or `false` (case-insensitive) |
| **Integer vars** | Must be valid integer within allowed range |

**Rule:** Invalid format on a `required` var = startup failure. No silent acceptance of malformed values.

---

## Exposure Control Rules

| Rule | Description |
|------|-------------|
| **Server-only enforcement** | Vars classified as `secret` or `infrastructure-critical` must NEVER be: exposed to frontend, appear in client bundles, logged in any output, included in error messages |
| **Build-time verification** | Build process must verify no server-only vars leak into client bundle |
| **Public marking** | Only vars explicitly classified as `public` may be exposed client-side |
| **Log sanitization** | All logging must sanitize env var values — secrets must be masked |
| **Error messages** | Error outputs must never contain env var values |

---

## Secret Rotation Policy

| Rule | Description |
|------|-------------|
| **Schedule** | All secret-classified vars must be rotated every 90 days or on security event |
| **Event-based rotation** | Immediate rotation required on: suspected compromise, team member departure, security incident |
| **Session continuity** | Rotation must not break active sessions where applicable (graceful transition) |
| **Audit** | Every rotation must generate audit event and action tracker entry |
| **Cross-environment** | Secrets must differ across all environments — no shared secrets between staging and production |
| **Tracking** | Last rotation date and next rotation due date tracked per secret |

---

## Environment-Specific Mapping

| Env Var | Local | CI | Staging | Production |
|---------|-------|-----|---------|------------|
| `SUPABASE_URL` | Local instance | Test instance | Staging instance | Production instance |
| `SUPABASE_ANON_KEY` | Local key | Test key | Staging key | Production key |
| `SUPABASE_SERVICE_ROLE_KEY` | Local key | Test key | Staging key | Production key |
| `SUPABASE_JWT_SECRET` | Local secret | Test secret | Staging secret | Production secret |

### Environment Rules

| Rule | Description |
|------|-------------|
| **Production strictness** | Production values must be equal to or stricter than non-prod |
| **Secret isolation** | Secrets must differ across ALL environments |
| **No prod sharing** | Production secrets must NEVER be used in non-prod environments |
| **Override policy** | Local/CI may use relaxed values; production may NOT relax below baseline |

---

## Drift Detection and Audit Rules

| Rule | Description |
|------|-------------|
| **Drift detection** | Runtime env must match documented values in this index |
| **Mismatch response** | Undocumented or mismatched env var → alert |
| **Env checksum** | Env version/checksum visible in admin health panel |
| **Unauthorized change** | Unauthorized env mutation → alert + action tracker entry |
| **Audit events** | Changes to `secret` or `infrastructure-critical` vars must generate `ENV_VAR_CHANGED` audit event |
| **Action tracker** | Critical env changes must create action tracker entries |

### Drift Severity

| Severity | Applies To | Response Time |
|----------|-----------|---------------|
| **Critical** | `secret`, `infrastructure-critical` | Immediate (< 15 min) |
| **High** | `internal` with large blast radius | Rapid (< 4 hours) |
| **Medium** | `feature-control`, `internal` | Standard (< 24 hours) |
| **Low** | `public` | Tracked |

---

## Emergency Override Governance

| Rule | Description |
|------|-------------|
| **Allowed scope** | Emergency override permitted for `internal` and `feature-control` vars only |
| **Secret overrides** | Secret vars may NOT be emergency-overridden without Lead + Security approval |
| **Audit** | All overrides must be audited with justification |
| **Expiration** | Overrides must expire within 72 hours |
| **Rollback** | Rollback plan required before override |
| **Action tracker** | Override must create action tracker entry with `type: emergency-override` |

---

## Testing Requirements

| Test Type | Applies To | Description |
|-----------|-----------|-------------|
| **Startup validation tests** | All required vars | Verify app fails-fast when critical vars missing |
| **Fail-fast tests** | Infrastructure-critical | Verify system refuses to start with invalid values |
| **Secret exposure tests** | All secrets | Verify secrets never appear in client bundle, logs, or error output |
| **Environment mismatch tests** | All vars | Verify correct behavior when env differs from expected |
| **Rotation tests** | Secrets | Verify rotation doesn't break active sessions |
| **Format validation tests** | All vars | Verify invalid formats are rejected |

**Rule:** Every `secret` and `infrastructure-critical` var must have at least one dedicated test.

---

## Env Var Lifecycle

| State | Description | Action Required |
|-------|-------------|-----------------|
| **Active** | In use, governed by this index | Standard governance |
| **Deprecated** | Scheduled for removal, still functional | Migration plan + target removal date |
| **Pending removal** | Will be removed in next release | Removal action tracker entry |
| **Experimental** | Under evaluation, may change | Flag in monitoring |

---

## Env Var Registry

### `SUPABASE_URL`

| Field | Value |
|-------|-------|
| **Type** | `url` |
| **Classification** | infrastructure-critical |
| **Module** | infrastructure |
| **Description** | Base URL for Supabase project API |
| **Source** | platform-provided (Lovable Cloud) |
| **Required** | Yes |
| **Default** | None |
| **Format validation** | Valid HTTPS URL (`https://*.supabase.co`) |
| **Exposure** | client-safe (URL only, not a secret) |
| **Environments** | All |
| **Blast radius** | system-wide |
| **Startup behavior** | `fail-fast` |
| **Related configs** | All Supabase-dependent configs |
| **Related routes** | All API routes |
| **Related risks** | RSK-004 (infrastructure failure) |
| **Related tests** | Startup validation, connectivity tests |
| **Lifecycle** | active |

### `SUPABASE_ANON_KEY`

| Field | Value |
|-------|-------|
| **Type** | `key` |
| **Classification** | public |
| **Module** | infrastructure |
| **Description** | Publishable anonymous key for frontend Supabase client |
| **Source** | platform-provided (Lovable Cloud) |
| **Required** | Yes |
| **Default** | None |
| **Format validation** | JWT format, minimum 100 characters |
| **Exposure** | client-safe (publishable by design) |
| **Environments** | All |
| **Blast radius** | system-wide |
| **Startup behavior** | `fail-fast` |
| **Related configs** | All frontend API configs |
| **Related routes** | All frontend routes |
| **Related risks** | RSK-004 |
| **Related tests** | Startup validation, API connectivity tests |
| **Lifecycle** | active |

### `SUPABASE_SERVICE_ROLE_KEY`

| Field | Value |
|-------|-------|
| **Type** | `key` |
| **Classification** | secret, infrastructure-critical |
| **Module** | infrastructure |
| **Description** | Service role key for server-side Supabase operations — bypasses RLS |
| **Source** | secret-manager (Lovable Cloud) |
| **Required** | Yes |
| **Default** | None |
| **Format validation** | JWT format, minimum 100 characters |
| **Exposure** | **server-only** — NEVER expose to frontend, logs, or error output |
| **Environments** | All (must differ per environment) |
| **Rotation policy** | Every 90 days or on security event |
| **Blast radius** | system-wide |
| **Startup behavior** | `fail-fast` |
| **Related configs** | All server-side configs |
| **Related routes** | All edge function routes |
| **Related risks** | RSK-001 (credential compromise), RSK-002 (privilege escalation) |
| **Related tests** | Startup validation, exposure prevention tests |
| **Lifecycle** | active |

### `SUPABASE_JWT_SECRET`

| Field | Value |
|-------|-------|
| **Type** | `key` |
| **Classification** | secret, infrastructure-critical |
| **Module** | infrastructure (auth) |
| **Description** | JWT signing/verification secret for token validation |
| **Source** | secret-manager (Lovable Cloud) |
| **Required** | Yes |
| **Default** | None |
| **Format validation** | Minimum 32 characters, high entropy |
| **Exposure** | **server-only** — NEVER expose to frontend, logs, or error output |
| **Environments** | All (must differ per environment) |
| **Rotation policy** | Every 90 days or on security event; must not invalidate active sessions abruptly |
| **Blast radius** | system-wide |
| **Startup behavior** | `fail-fast` |
| **Related configs** | `session.access_token_ttl`, `session.refresh_token_rotation` |
| **Related routes** | All authenticated routes |
| **Related risks** | RSK-001, RSK-003 (session hijacking) |
| **Related tests** | Startup validation, token verification tests, exposure prevention tests |
| **Lifecycle** | active |

> Additional environment variables will be added as modules are implemented (e.g., OAuth client IDs, SMTP configuration, external API keys). Each must follow the full schema above.

---

## Critical Env Summary

### Top Critical Env Vars (Require Strongest Governance)

| Env Var | Classification | Blast Radius | Why Critical |
|---------|---------------|--------------|--------------|
| `SUPABASE_SERVICE_ROLE_KEY` | secret + infrastructure-critical | system-wide | Bypasses RLS — exposure = full data breach |
| `SUPABASE_JWT_SECRET` | secret + infrastructure-critical | system-wide | Controls all token validation — compromise = auth bypass |
| `SUPABASE_URL` | infrastructure-critical | system-wide | All API calls depend on this |
| `SUPABASE_ANON_KEY` | public | system-wide | Frontend inoperable without it |

### Rotation Schedule

| Env Var | Last Rotated | Next Due | Status |
|---------|-------------|----------|--------|
| `SUPABASE_SERVICE_ROLE_KEY` | — | Pre-production | Pending |
| `SUPABASE_JWT_SECRET` | — | Pre-production | Pending |

### Quarterly Review Required

All `secret` and `infrastructure-critical` vars must be reviewed quarterly to confirm:
- Values still valid and not compromised
- Rotation schedule on track
- No drift from baseline
- Exposure controls verified
- Related tests still passing

---

## Dependencies

- [Config Index](config-index.md) — env vars feed config values
- [Security Architecture](../02-security/security-architecture.md) — secret governance
- [Change Control Policy](../00-governance/change-control-policy.md) — env changes follow change control
- [Action Tracker](../06-tracking/action-tracker.md) — critical env changes create entries
- [Risk Register](../06-tracking/risk-register.md) — env-related risks tracked

## Related Documents

- [Config Index](config-index.md)
- [Permission Index](permission-index.md)
- [Function Index](function-index.md)
- [Route Index](route-index.md)
- [Event Index](event-index.md)
