# Jobs and Scheduler Module

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-08

## Purpose

Manages background jobs and scheduled tasks.

## Scope

Job definitions, scheduling, execution, failure handling, retry logic.

## Key Rules

- All jobs must be idempotent
- All jobs must log start, completion, and failure
- Failed jobs retry with exponential backoff (max 3 retries)
- Jobs must not exceed 30-second execution time (edge function limit)
- Long-running tasks must be broken into smaller jobs

## Job Registry

| Job ID | Module | Schedule | Purpose | Status |
|--------|--------|----------|---------|--------|
| `audit_cleanup` | audit-logging | Weekly | Archive old audit logs | Not started |
| `health_check` | health-monitoring | Every 1 min | Run health checks | Not started |
| `metrics_aggregate` | health-monitoring | Every 5 min | Aggregate metrics | Not started |

## Job Execution Pattern

```typescript
// Standard job structure
async function executeJob(jobId: string) {
  // 1. Log job start
  // 2. Execute task (idempotent)
  // 3. Log job completion or failure
  // 4. On failure: schedule retry with backoff
}
```

## Retry Strategy

| Attempt | Delay |
|---------|-------|
| 1 | 30 seconds |
| 2 | 2 minutes |
| 3 | 10 minutes |
| Final | Mark as failed, alert admin |

## Shared Functions

| Function | Purpose | Used By |
|----------|---------|---------|
| `scheduleJob(jobId, schedule)` | Registers a job schedule | Module-specific setup |
| `executeWithRetry(fn, config)` | Wraps job with retry logic | All jobs |

## Events

| Event | Emitted When | Consumed By |
|-------|-------------|-------------|
| `job.started` | Job execution begins | audit-logging |
| `job.completed` | Job finishes successfully | audit-logging |
| `job.failed` | Job fails after all retries | audit-logging, health-monitoring |

## Permissions

| Permission | Description |
|-----------|-------------|
| `jobs.view` | Can view job status |
| `jobs.trigger` | Can manually trigger a job |

## Dependencies

- [Auth Module](auth.md) — for service-level auth
- [Audit Logging Module](audit-logging.md) — for logging

## Used By / Affects

health-monitoring.

## Risks If Modified

MEDIUM — job changes can affect data consistency and monitoring.

## Related Documents

- [Health Monitoring](health-monitoring.md)
- [Audit Logging](audit-logging.md)
