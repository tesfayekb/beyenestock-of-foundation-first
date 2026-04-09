# Health Monitoring Module

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-09

## Purpose

Monitors system health, tracks metrics, evaluates service status, and surfaces alerts for operational response.

## Scope

Health checks, metrics, alerting, uptime, degraded-state detection, and monitoring visibility.

## Enforcement Rule (CRITICAL)

- All critical subsystems **MUST** have monitoring coverage
- Missing health checks, metrics, or alerts for critical systems is an **INVALID** implementation
- Monitoring failures must themselves be detectable

## Key Rules

- Public health endpoint must return only minimal safe status data
- Internal metrics and detailed diagnostics require authorized access
- Alert thresholds are configurable and auditable
- Monitoring must cover API, auth, database, jobs, audit pipeline, and integrations

## Health Status Model

| Status | Meaning |
|--------|---------|
| `healthy` | All critical checks passing |
| `degraded` | Partial failure or threshold breach without full outage |
| `unhealthy` | Critical subsystem failure or severe degradation |

### Status Calculation Rules

- `healthy` if all critical checks pass
- `degraded` if one or more warning thresholds breach
- `unhealthy` if any critical subsystem fails or repeated severe thresholds are exceeded

## Health Check Endpoint

```
GET /health
Response: { status: "healthy" | "degraded" | "unhealthy", checks: {...minimal safe subset...} }
```

**Rule:** No sensitive internals exposed in unauthenticated health responses

## Monitoring Domains

- API health
- Authentication health
- Database health
- Jobs/scheduler health
- Audit logging health
- External integration health

## Alert Severity Model

| Severity | Meaning |
|----------|---------|
| `info` | Informational, no action needed |
| `warning` | Threshold approaching, investigation recommended |
| `critical` | Immediate action required |

### Alert Rules

- Alerts must support throttling or grouping to prevent alert flooding
- System should support **maintenance mode** to suppress non-critical alerts during planned operations

## Metrics Tracked

| Metric | Source | Alert Threshold | Severity |
|--------|--------|----------------|----------|
| Error rate (5xx) | API logs | > 1% in 5 min | warning |
| Auth failure rate | Auth events | > 10 in 1 min | warning |
| API response time (p95) | API logs | > 500ms | warning |
| Job failure rate | Job scheduler | > 3 consecutive | critical |
| Database connection pool | DB stats | > 80% utilized | warning |
| Audit write failure | Audit events | any sustained failure | critical |

## Shared Functions

| Function | Purpose | Used By | Defined In |
|----------|---------|---------|------------|
| `getSystemHealth()` | Returns current system status | admin-panel | [Function Index](../07-reference/function-index.md) |
| `getMetrics(timeRange)` | Returns metrics view | admin-panel | [Function Index](../07-reference/function-index.md) |
| `evaluateAlerts()` | Evaluates thresholds and alert state | health jobs (`alert_evaluation`) | [Function Index](../07-reference/function-index.md) |

## Events

| Event | Emitted When | Consumed By |
|-------|-------------|-------------|
| `health.alert_triggered` | Metric exceeds threshold | admin notification / on-call flow |
| `health.status_changed` | Overall status changes | audit-logging, admin-panel |
| `health.monitoring_failed` | Monitoring pipeline fails | admin alerts |

## Jobs

| Job | Schedule | Purpose |
|-----|----------|---------|
| `health_check` | Every 1 min | Run subsystem checks |
| `metrics_aggregate` | Every 5 min | Aggregate monitoring data |
| `alert_evaluation` | Every 1 min | Evaluate alert thresholds |

## Permissions

| Permission | Description |
|-----------|-------------|
| `monitoring.view` | Can view health dashboard |
| `monitoring.configure` | Can configure thresholds and alerts |

## Failure Handling Rules (CRITICAL)

- Monitoring failure must raise an alert via `health.monitoring_failed`
- Monitoring pipeline failure must degrade system health state to `degraded` or `unhealthy`
- Prolonged monitoring blindness (sustained failure) must create action tracker entry
- Critical alerting failure must surface in admin panel as a control failure
- Critical health degradation must surface prominently in admin panel
- Repeated failures must not be silently suppressed

## Dependencies

- [API Module](api.md)
- [Auth Module](auth.md)
- [Audit Logging Module](audit-logging.md)
- [Jobs and Scheduler](jobs-and-scheduler.md)

## Used By / Affects

admin-panel, operational visibility, incident response.

## Risks If Modified

HIGH — weak monitoring reduces visibility into outages, abuse, and security incidents.

## Related Documents

- [Audit Logging Module](audit-logging.md)
- [Admin Panel](admin-panel.md)
- [Performance Strategy](../03-performance/performance-strategy.md)
- [Security Architecture](../02-security/security-architecture.md)
