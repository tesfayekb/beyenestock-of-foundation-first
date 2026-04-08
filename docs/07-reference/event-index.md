# Event Index

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-08

## Purpose

Central registry of all events emitted and consumed across modules.

## Scope

All application events.

## Event Map

| Name | Module | Used By | Impact If Changed |
|------|--------|---------|-------------------|
| `auth.signed_up` | auth | audit-logging, user-management | HIGH — breaks user creation flow |
| `auth.signed_in` | auth | audit-logging | MEDIUM — breaks login audit |
| `auth.signed_out` | auth | audit-logging | LOW — audit only |
| `auth.password_reset` | auth | audit-logging | LOW — audit only |
| `auth.mfa_enrolled` | auth | audit-logging | LOW — audit only |
| `auth.failed_attempt` | auth | audit-logging, health-monitoring | MEDIUM — breaks security alerting |
| `rbac.role_assigned` | rbac | audit-logging | MEDIUM — breaks role audit |
| `rbac.role_revoked` | rbac | audit-logging | MEDIUM — breaks role audit |
| `rbac.permission_denied` | rbac | audit-logging, health-monitoring | MEDIUM — breaks security monitoring |
| `user.profile_updated` | user-management | audit-logging | LOW — audit only |
| `user.account_deactivated` | user-management | audit-logging, admin-panel | MEDIUM — affects admin visibility |
| `user.account_reactivated` | user-management | audit-logging, admin-panel | MEDIUM — affects admin visibility |
| `admin.config_changed` | admin-panel | audit-logging, health-monitoring | HIGH — affects system behavior |
| `admin.user_action` | admin-panel | audit-logging | MEDIUM — admin audit trail |
| `user_panel.settings_changed` | user-panel | audit-logging | LOW — audit only |
| `user_panel.session_revoked` | user-panel | audit-logging | MEDIUM — security event |
| `audit.logged` | audit-logging | health-monitoring | LOW — metrics only |
| `health.alert_triggered` | health-monitoring | admin notification | HIGH — affects alerting |
| `health.status_changed` | health-monitoring | audit-logging | MEDIUM — system status |
| `api.error` | api | health-monitoring | MEDIUM — affects error tracking |
| `api.rate_limited` | api | audit-logging | LOW — audit only |
| `job.started` | jobs-and-scheduler | audit-logging | LOW — audit only |
| `job.completed` | jobs-and-scheduler | audit-logging | LOW — audit only |
| `job.failed` | jobs-and-scheduler | audit-logging, health-monitoring | HIGH — affects alerting |
| `job.queued` | jobs-and-scheduler | health-monitoring | LOW — metrics only |
| `job.retry_scheduled` | jobs-and-scheduler | audit-logging, health-monitoring | MEDIUM — affects retry tracking |
| `job.dead_lettered` | jobs-and-scheduler | audit-logging, health-monitoring, admin-panel | HIGH — requires operator action |
| `job.paused` | jobs-and-scheduler | audit-logging | MEDIUM — affects scheduling |
| `job.cancelled` | jobs-and-scheduler | audit-logging | MEDIUM — affects scheduling |

## Dependencies

- [Dependency Map](../01-architecture/dependency-map.md)

## Used By / Affects

All modules that emit or consume events.

## Related Documents

- Module docs in `docs/04-modules/`
