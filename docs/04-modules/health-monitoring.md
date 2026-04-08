# Health Monitoring Module

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-08

## Purpose

Monitors system health, tracks metrics, and surfaces alerts.

## Scope

Health checks, error rate tracking, performance metrics, uptime monitoring.

## Key Rules

- Health endpoint must be unauthenticated (for external monitors)
- Internal metrics require admin access
- Alert thresholds are configurable
- Monitor: error rates, response times, auth failures, job failures

## Health Check Endpoint

```
GET /health
Response: { status: "healthy" | "degraded" | "unhealthy", checks: {...} }
```

## Metrics Tracked

| Metric | Source | Alert Threshold |
|--------|--------|----------------|
| Error rate (5xx) | API logs | > 1% in 5 min |
| Auth failure rate | Auth events | > 10 in 1 min |
| API response time (p95) | API logs | > 500ms |
| Job failure rate | Job scheduler | > 3 consecutive |
| Database connection pool | DB stats | > 80% utilized |

## Shared Functions

| Function | Purpose | Used By |
|----------|---------|---------|
| `getSystemHealth()` | Returns current health status | admin-panel |
| `getMetrics(timeRange)` | Returns metrics for time range | admin-panel |

## Events

| Event | Emitted When | Consumed By |
|-------|-------------|-------------|
| `health.alert_triggered` | Metric exceeds threshold | admin notification |
| `health.status_changed` | System status changes | audit-logging |

## Jobs

| Job | Schedule | Purpose |
|-----|----------|---------|
| `health_check` | Every 1 min | Run health checks |
| `metrics_aggregate` | Every 5 min | Aggregate metrics |

## Permissions

| Permission | Description |
|-----------|-------------|
| `monitoring.view` | Can view health dashboard |
| `monitoring.configure` | Can configure alert thresholds |

## Dependencies

- [Audit Logging Module](audit-logging.md) — for event data

## Used By / Affects

admin-panel.

## Risks If Modified

MEDIUM — monitoring changes affect visibility into system health.

## Related Documents

- [Audit Logging Module](audit-logging.md)
- [Admin Panel](admin-panel.md)
- [Performance Strategy](../03-performance/performance-strategy.md)
