# Config Index

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-08

## Purpose

Central registry of all configuration values in the application.

## Scope

All configurable parameters.

## Config Map

| Name | Module | Used By | Impact If Changed |
|------|--------|---------|-------------------|
| `auth.password_min_length` | auth | auth flows | MEDIUM — affects password policy |
| `auth.max_login_attempts` | auth | auth, health-monitoring | MEDIUM — affects security |
| `auth.lockout_duration` | auth | auth | MEDIUM — affects user access |
| `auth.mfa_required_roles` | auth, rbac | auth flows | HIGH — affects access requirements |
| `session.access_token_ttl` | auth | all authenticated flows | HIGH — affects session behavior |
| `session.refresh_token_rotation` | auth | all authenticated flows | HIGH — affects session security |
| `api.rate_limit_per_minute` | api | all API calls | MEDIUM — affects availability |
| `audit.retention_days` | audit-logging | audit cleanup job | LOW — affects storage |
| `monitoring.error_rate_threshold` | health-monitoring | alerting | MEDIUM — affects alert sensitivity |
| `monitoring.health_check_interval` | health-monitoring | health check job | LOW — affects monitoring frequency |
| `jobs.max_retries` | jobs-and-scheduler | all jobs | MEDIUM — affects reliability |
| `jobs.retry_backoff_base` | jobs-and-scheduler | all jobs | LOW — affects retry timing |
| `pagination.default_page_size` | api | all list endpoints | LOW — affects UX |
| `pagination.max_page_size` | api | all list endpoints | LOW — affects performance |

## Dependencies

None — this is a reference document.

## Used By / Affects

All modules that use configurable values.

## Related Documents

- [Env Var Index](env-var-index.md)
