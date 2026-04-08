# Config Index

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-08 | **Status:** Living Document

## Purpose

Central registry and **governance system** for all configuration values in the application. This document is the single source of truth for configuration — it defines what configs exist, how they behave, who may change them, and how changes are validated and audited.

## Scope

All configurable parameters across all modules, including runtime settings, feature flags, thresholds, and policy values.

---

## Enforcement Rule (CRITICAL)

| Rule | Description |
|------|-------------|
| **Completeness** | No runtime config may exist outside this index. Undocumented config = unauthorized config. |
| **Change governance** | No config may be changed without impact review. Security-sensitive config changes require explicit approval. |
| **Drift prohibition** | Config drift from documented baseline is **invalid**. Deployed config must match this index. |
| **No hidden defaults** | Hidden or implicit default behavior is **prohibited** for critical paths. All defaults must be documented. |
| **Secret boundary** | Secrets are **referenced**, never stored as plain values. Secret-bearing configs point to secret source only. |
| **Audit mandate** | All config changes to `security-sensitive` or `authorization-sensitive` configs must generate an audit event and action tracker entry. |

---

## Config Classification Model

Every config is assigned a classification that determines governance requirements:

| Classification | Description | Approval Required | Audit Required | Change Review |
|---------------|-------------|-------------------|----------------|---------------|
| **security-sensitive** | Affects authentication, encryption, token behavior | Yes — Lead + Security | Yes | Mandatory |
| **authorization-sensitive** | Affects RBAC, permissions, role enforcement | Yes — Lead | Yes | Mandatory |
| **operational** | Affects system behavior, jobs, scheduling | No — but review recommended | Yes | Recommended |
| **performance** | Affects latency, throughput, resource usage | No | Yes | Recommended |
| **ux-product** | Affects user-facing behavior, pagination, display | No | No | Optional |
| **infrastructure** | Affects runtime environment, intervals, connections | No — but review recommended | Yes | Recommended |
| **feature-flag** | Controls feature rollout, experiments | No | Yes | Recommended |
| **retention-compliance** | Affects data retention, legal compliance | Yes — Lead | Yes | Mandatory |

---

## Config Entry Schema

Every config entry in the registry must include the following fields:

| Field | Description | Required |
|-------|-------------|----------|
| `name` | Fully qualified config name | Yes |
| `type` | Data type (`integer`, `boolean`, `string`, `enum`, `duration`, `float`) | Yes |
| `module` | Owning module | Yes |
| `classification` | From classification model above | Yes |
| `default` | Default value if not explicitly set | Yes |
| `allowed_values` | Valid range, enum values, or constraints | Yes |
| `invalid_value_behavior` | What happens if invalid value is set (`fail-secure`, `fail-fast`, `use-default`) | Yes |
| `unit` | Unit of measurement (seconds, minutes, count, etc.) | If applicable |
| `source` | Where the config lives (see Source Model below) | Yes |
| `mutability` | `build-time`, `deploy-time`, `runtime-mutable` | Yes |
| `reload_behavior` | `restart-required`, `hot-reload`, `next-request`, `scheduled-refresh` | Yes |
| `blast_radius` | `small`, `medium`, `large`, `system-wide` | Yes |
| `approval_required` | Whether change requires approval | Yes |
| `audit_required` | Whether change generates audit event | Yes |
| `used_by` | Modules/flows consuming this config | Yes |
| `related_routes` | Routes affected by this config | If applicable |
| `related_permissions` | Permissions affected | If applicable |
| `related_jobs` | Jobs affected | If applicable |
| `related_tests` | Tests validating this config | If applicable |
| `related_risks` | Risk register items | If applicable |
| `related_watchlist` | Regression watchlist items | If applicable |
| `related_env_vars` | Environment variables | If applicable |
| `lifecycle` | `active`, `deprecated`, `pending-removal`, `experimental`, `emergency-override` | Yes |

---

## Source / Mutability / Reload Model

| Source Type | Description | Example |
|------------|-------------|---------|
| **Code constant** | Hardcoded in source, requires deploy to change | Pagination defaults |
| **Environment variable** | Set at deploy time via env config | Token TTLs |
| **Database config** | Stored in config table, runtime mutable | Feature flags |
| **Secret manager** | Stored in secret vault, never in code or config index | API keys, encryption keys |
| **Feature flag service** | Managed via feature flag system | Rollout percentages |

| Mutability | When changeable | Risk Level |
|-----------|----------------|------------|
| **Build-time** | Only at build/compile | Lowest |
| **Deploy-time** | At deployment via env/config | Medium |
| **Runtime-mutable** | Live without redeploy | Highest — requires strongest governance |

| Reload Behavior | Effect Timing |
|-----------------|---------------|
| **Restart required** | Change takes effect after service restart |
| **Hot reload** | Change takes effect immediately |
| **Next request** | Change applies to next incoming request |
| **Scheduled refresh** | Change applies at next refresh interval |

---

## Validation and Default Rules

### Validation Requirements

Every config must define:
- **Type constraint** — enforced at load time
- **Range/enum constraint** — enforced at load time
- **Invalid value behavior** — one of:
  - `fail-secure` — revert to safe default (REQUIRED for security-sensitive configs)
  - `fail-fast` — reject startup / raise error
  - `use-default` — silently use documented default

### Fail-Secure Defaults (CRITICAL)

| Scenario | Required Behavior |
|----------|-------------------|
| MFA config missing or invalid | Fail secure — enforce MFA for all roles |
| Rate limit config missing | Default safe limit (e.g., 60/min), **never** unlimited |
| Token TTL config missing | Default short TTL, **never** infinite |
| Retention config missing | Conservative default (e.g., 90 days), **never** unlimited |
| Max retries missing | Safe bounded default, **never** infinite |

**Rule:** Security-sensitive configs **must** fail secure. No config absence may weaken the security posture.

---

## Environment-Specific Rules

| Rule | Description |
|------|-------------|
| **Production strictness** | Production values must be equal to or stricter than non-prod |
| **Override policy** | Non-prod environments may use relaxed settings; prod may NOT relax below baseline |
| **Environment documentation** | Config entries must note if value differs by environment |
| **Secret isolation** | Secrets must not be shared across environments |

| Environment | Override Allowed | Relaxation Allowed | Notes |
|-------------|-----------------|-------------------|-------|
| **Local** | Yes | Yes | Developer flexibility |
| **CI** | Limited | Yes | Must match prod structure |
| **Staging** | Limited | Limited | Should mirror prod closely |
| **Production** | No (without approval) | No | Strictest values enforced |

---

## Secret Boundary Rules

| Rule | Description |
|------|-------------|
| **No plain values** | Secret values are **never** stored in this index |
| **Reference only** | Secret-bearing configs reference the secret source (e.g., `source: secret-manager/auth-signing-key`) |
| **Classification** | Config index distinguishes: regular config, secret reference, derived runtime setting |
| **Access control** | Secret configs require highest approval tier for any change |

---

## Config Lifecycle

| State | Description | Action Required |
|-------|-------------|-----------------|
| **Active** | In use, governed by this index | Standard governance |
| **Deprecated** | Scheduled for removal, still functional | Migration plan required |
| **Pending removal** | Will be removed in next release | Removal action tracker entry |
| **Experimental** | Under evaluation, may change without notice | Flag in monitoring |
| **Emergency override** | Temporarily set for incident mitigation | Must expire, be audited, and have rollback plan |

**Rule:** Deprecated configs must have a target removal date and migration path documented.

---

## Drift Detection and Audit Rules

| Rule | Description |
|------|-------------|
| **Audit event** | All changes to `security-sensitive` or `authorization-sensitive` configs must emit `CONFIG_CHANGED` audit event |
| **Drift detection** | Periodic comparison between this index and deployed config is required |
| **Config checksum** | Config version/checksum must be visible in admin health panel |
| **Unauthorized mutation** | Unauthorized config mutation must trigger alert |
| **Action tracker** | Critical config changes must create action tracker entries |
| **Change log** | All config changes must be traceable to a change request or action entry |

---

## Emergency Override Governance

| Rule | Description |
|------|-------------|
| **Allowed classes** | Emergency overrides only permitted for configs classified as `operational`, `performance`, or `infrastructure` |
| **Security configs** | Security-sensitive configs may NOT be emergency-overridden without Lead + Security approval |
| **Audit** | All emergency overrides must be audited with justification |
| **Expiration** | Emergency overrides must have a defined expiration (max 72 hours) |
| **Rollback** | Rollback plan required before override is applied |
| **Action tracker** | Override must create action tracker entry with `type: emergency-override` |
| **Review** | Override must be reviewed within expiration window |

---

## Testing Requirements

| Test Type | Applies To | Description |
|-----------|-----------|-------------|
| **Boundary tests** | Numeric configs | Test min, max, edge values |
| **Fail-secure tests** | Security-sensitive configs | Verify system fails secure when config missing/invalid |
| **Regression tests** | All classified configs | Verify config-driven behavior doesn't break on change |
| **Integration tests** | Critical configs | End-to-end validation of config change impact |
| **Config-change tests** | Authorization-sensitive | Verify immediate enforcement after config change |

**Rule:** Every `security-sensitive` or `authorization-sensitive` config must have at least one dedicated test.

---

## Config Registry

### Authentication Configs

#### `auth.password_min_length`

| Field | Value |
|-------|-------|
| **Type** | `integer` |
| **Module** | auth |
| **Classification** | security-sensitive |
| **Default** | `12` |
| **Allowed values** | `8–128` |
| **Invalid value behavior** | `fail-secure` — use default `12` |
| **Unit** | characters |
| **Source** | code constant |
| **Mutability** | build-time |
| **Reload behavior** | restart-required |
| **Blast radius** | medium |
| **Approval required** | Yes |
| **Audit required** | Yes |
| **Used by** | auth flows, user registration |
| **Related tests** | Password validation boundary tests |
| **Related risks** | RSK-001 (credential compromise) |
| **Lifecycle** | active |

#### `auth.max_login_attempts`

| Field | Value |
|-------|-------|
| **Type** | `integer` |
| **Module** | auth |
| **Classification** | security-sensitive |
| **Default** | `5` |
| **Allowed values** | `3–10` |
| **Invalid value behavior** | `fail-secure` — use default `5` |
| **Unit** | attempts |
| **Source** | code constant |
| **Mutability** | build-time |
| **Reload behavior** | restart-required |
| **Blast radius** | medium |
| **Approval required** | Yes |
| **Audit required** | Yes |
| **Used by** | auth flows, health-monitoring |
| **Related tests** | Lockout threshold tests |
| **Related risks** | RSK-001, RSK-002 |
| **Lifecycle** | active |

#### `auth.lockout_duration`

| Field | Value |
|-------|-------|
| **Type** | `duration` |
| **Module** | auth |
| **Classification** | security-sensitive |
| **Default** | `15 minutes` |
| **Allowed values** | `5m–60m` |
| **Invalid value behavior** | `fail-secure` — use default `15m` |
| **Unit** | minutes |
| **Source** | code constant |
| **Mutability** | build-time |
| **Reload behavior** | restart-required |
| **Blast radius** | medium |
| **Approval required** | Yes |
| **Audit required** | Yes |
| **Used by** | auth flows |
| **Related tests** | Lockout duration enforcement tests |
| **Related risks** | RSK-001 |
| **Lifecycle** | active |

#### `auth.mfa_required_roles`

| Field | Value |
|-------|-------|
| **Type** | `enum[]` |
| **Module** | auth, rbac |
| **Classification** | authorization-sensitive |
| **Default** | `["admin"]` |
| **Allowed values** | Valid `app_role` enum values |
| **Invalid value behavior** | `fail-secure` — enforce MFA for all roles |
| **Source** | code constant |
| **Mutability** | build-time |
| **Reload behavior** | restart-required |
| **Blast radius** | large |
| **Approval required** | Yes — Lead |
| **Audit required** | Yes |
| **Used by** | auth flows, RBAC enforcement |
| **Related permissions** | All role-gated permissions |
| **Related tests** | MFA enforcement tests |
| **Related risks** | RSK-002 (privilege escalation) |
| **Related watchlist** | RW-001 |
| **Lifecycle** | active |

### Session Configs

#### `session.access_token_ttl`

| Field | Value |
|-------|-------|
| **Type** | `duration` |
| **Module** | auth |
| **Classification** | security-sensitive |
| **Default** | `15 minutes` |
| **Allowed values** | `5m–60m` |
| **Invalid value behavior** | `fail-secure` — use default `15m` |
| **Unit** | minutes |
| **Source** | environment variable |
| **Mutability** | deploy-time |
| **Reload behavior** | next-request |
| **Blast radius** | system-wide |
| **Approval required** | Yes — Lead + Security |
| **Audit required** | Yes |
| **Used by** | all authenticated flows |
| **Related routes** | All authenticated routes |
| **Related tests** | Token expiration tests |
| **Related risks** | RSK-003 (session hijacking) |
| **Lifecycle** | active |

#### `session.refresh_token_rotation`

| Field | Value |
|-------|-------|
| **Type** | `boolean` |
| **Module** | auth |
| **Classification** | security-sensitive |
| **Default** | `true` |
| **Allowed values** | `true`, `false` |
| **Invalid value behavior** | `fail-secure` — default `true` (rotation enabled) |
| **Source** | code constant |
| **Mutability** | build-time |
| **Reload behavior** | restart-required |
| **Blast radius** | system-wide |
| **Approval required** | Yes — Lead + Security |
| **Audit required** | Yes |
| **Used by** | all authenticated flows |
| **Related tests** | Token rotation tests |
| **Related risks** | RSK-003 |
| **Lifecycle** | active |

### API Configs

#### `api.rate_limit_per_minute`

| Field | Value |
|-------|-------|
| **Type** | `integer` |
| **Module** | api |
| **Classification** | operational |
| **Default** | `60` |
| **Allowed values** | `10–1000` |
| **Invalid value behavior** | `fail-secure` — use default `60` |
| **Unit** | requests/minute |
| **Source** | environment variable |
| **Mutability** | deploy-time |
| **Reload behavior** | next-request |
| **Blast radius** | system-wide |
| **Approval required** | No |
| **Audit required** | Yes |
| **Used by** | all API calls |
| **Related tests** | Rate limit enforcement tests |
| **Related risks** | RSK-005 (DoS) |
| **Lifecycle** | active |

### Audit Configs

#### `audit.retention_days`

| Field | Value |
|-------|-------|
| **Type** | `integer` |
| **Module** | audit-logging |
| **Classification** | retention-compliance |
| **Default** | `90` |
| **Allowed values** | `30–365` |
| **Invalid value behavior** | `fail-secure` — use default `90` |
| **Unit** | days |
| **Source** | environment variable |
| **Mutability** | deploy-time |
| **Reload behavior** | scheduled-refresh |
| **Blast radius** | medium |
| **Approval required** | Yes — Lead |
| **Audit required** | Yes |
| **Used by** | audit cleanup job |
| **Related jobs** | Audit log cleanup job |
| **Related tests** | Retention policy tests |
| **Lifecycle** | active |

### Monitoring Configs

#### `monitoring.error_rate_threshold`

| Field | Value |
|-------|-------|
| **Type** | `float` |
| **Module** | health-monitoring |
| **Classification** | operational |
| **Default** | `0.05` (5%) |
| **Allowed values** | `0.01–0.50` |
| **Invalid value behavior** | `fail-secure` — use default `0.05` |
| **Unit** | ratio (0–1) |
| **Source** | environment variable |
| **Mutability** | deploy-time |
| **Reload behavior** | next-request |
| **Blast radius** | medium |
| **Approval required** | No |
| **Audit required** | Yes |
| **Used by** | alerting, health dashboard |
| **Related tests** | Alert threshold tests |
| **Lifecycle** | active |

#### `monitoring.health_check_interval`

| Field | Value |
|-------|-------|
| **Type** | `duration` |
| **Module** | health-monitoring |
| **Classification** | infrastructure |
| **Default** | `60 seconds` |
| **Allowed values** | `10s–300s` |
| **Invalid value behavior** | `use-default` |
| **Unit** | seconds |
| **Source** | environment variable |
| **Mutability** | deploy-time |
| **Reload behavior** | scheduled-refresh |
| **Blast radius** | small |
| **Approval required** | No |
| **Audit required** | No |
| **Used by** | health check job |
| **Related jobs** | Health check job |
| **Lifecycle** | active |

### Job Configs

#### `jobs.max_retries`

| Field | Value |
|-------|-------|
| **Type** | `integer` |
| **Module** | jobs-and-scheduler |
| **Classification** | operational |
| **Default** | `3` |
| **Allowed values** | `1–10` |
| **Invalid value behavior** | `fail-secure` — use default `3` |
| **Unit** | count |
| **Source** | code constant |
| **Mutability** | build-time |
| **Reload behavior** | restart-required |
| **Blast radius** | medium |
| **Approval required** | No |
| **Audit required** | Yes |
| **Used by** | all jobs |
| **Related tests** | Retry contract tests |
| **Related risks** | RSK-007 (job failure cascade) |
| **Lifecycle** | active |

#### `jobs.retry_backoff_base`

| Field | Value |
|-------|-------|
| **Type** | `integer` |
| **Module** | jobs-and-scheduler |
| **Classification** | performance |
| **Default** | `2` |
| **Allowed values** | `1–10` |
| **Invalid value behavior** | `use-default` |
| **Unit** | seconds (base for exponential) |
| **Source** | code constant |
| **Mutability** | build-time |
| **Reload behavior** | restart-required |
| **Blast radius** | small |
| **Approval required** | No |
| **Audit required** | No |
| **Used by** | all jobs |
| **Lifecycle** | active |

### Pagination Configs

#### `pagination.default_page_size`

| Field | Value |
|-------|-------|
| **Type** | `integer` |
| **Module** | api |
| **Classification** | ux-product |
| **Default** | `20` |
| **Allowed values** | `5–100` |
| **Invalid value behavior** | `use-default` |
| **Unit** | items |
| **Source** | code constant |
| **Mutability** | build-time |
| **Reload behavior** | restart-required |
| **Blast radius** | small |
| **Approval required** | No |
| **Audit required** | No |
| **Used by** | all list endpoints |
| **Lifecycle** | active |

#### `pagination.max_page_size`

| Field | Value |
|-------|-------|
| **Type** | `integer` |
| **Module** | api |
| **Classification** | performance |
| **Default** | `100` |
| **Allowed values** | `50–500` |
| **Invalid value behavior** | `fail-fast` — reject request |
| **Unit** | items |
| **Source** | code constant |
| **Mutability** | build-time |
| **Reload behavior** | restart-required |
| **Blast radius** | medium |
| **Approval required** | No |
| **Audit required** | No |
| **Used by** | all list endpoints |
| **Related tests** | Pagination boundary tests |
| **Lifecycle** | active |

---

## Critical Config Summary

### Top Critical Configs (Require Strongest Governance)

| Config | Classification | Blast Radius | Why Critical |
|--------|---------------|--------------|--------------|
| `session.access_token_ttl` | security-sensitive | system-wide | Controls all session durations |
| `session.refresh_token_rotation` | security-sensitive | system-wide | Disabling weakens replay protection |
| `auth.mfa_required_roles` | authorization-sensitive | large | Weakening exposes privileged roles |
| `api.rate_limit_per_minute` | operational | system-wide | Misconfiguration enables DoS |
| `audit.retention_days` | retention-compliance | medium | Compliance violation risk |

### Quarterly Review Required

All configs with classification `security-sensitive`, `authorization-sensitive`, or `retention-compliance` must be reviewed quarterly to confirm:
- Values still appropriate
- No drift from baseline
- Related tests still passing
- No deprecated configs lingering

---

## Dependencies

- [Change Control Policy](../00-governance/change-control-policy.md) — config changes follow change control
- [Action Tracker](../06-tracking/action-tracker.md) — critical config changes create entries
- [Risk Register](../06-tracking/risk-register.md) — config-related risks tracked
- [Regression Watchlist](../06-tracking/regression-watchlist.md) — config-sensitive items monitored

## Related Documents

- [Env Var Index](env-var-index.md)
- [Permission Index](permission-index.md)
- [Route Index](route-index.md)
- [Function Index](function-index.md)
- [Event Index](event-index.md)
