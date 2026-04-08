# Jobs and Scheduler Module

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-08

## Purpose

Manages background jobs, scheduled tasks, execution lifecycle, failure handling, retry logic, concurrency control, and operational governance.

## Scope

Job definitions, scheduling, execution, state management, retry logic, dead-letter handling, concurrency protection, observability, manual trigger governance, and recovery operations.

## Enforcement Rule (CRITICAL)

- No production job may exist outside the **job registry**
- Every job must declare concurrency policy, idempotency strategy, and failure classification
- All job runs must be auditable and observable
- Manual triggers must be permission-checked, audited, and input-validated
- Terminal failures must enter dead-letter state
- Any unregistered, unmonitored, or ungoverned job is an **INVALID** implementation

## Key Rules

- All jobs must be idempotent
- All jobs must declare concurrency policy and idempotency strategy
- All jobs must log start, completion, and failure
- Failed jobs retry with configurable exponential backoff + jitter
- Jobs must not exceed configured timeout (default: 30s edge function limit)
- Long-running tasks must use orchestration/chaining, not oversized single functions
- No job may run outside the registered job registry
- Every job run must emit metrics and correlation metadata
- Manual triggers must be permission-checked, audited, and validated
- Terminal failures must enter dead-letter state
- Jobs must fail secure and isolate downstream impact

## Job Lifecycle State Model

Every job run passes through a defined state machine:

| State | Description |
|-------|-------------|
| `registered` | Job defined in registry but not yet scheduled |
| `scheduled` | Job has a pending scheduled execution |
| `queued` | Job awaiting execution slot |
| `running` | Job actively executing |
| `succeeded` | Job completed successfully |
| `retry_pending` | Job failed, awaiting retry |
| `failed` | Job exhausted retries but not yet dead-lettered |
| `dead_lettered` | Terminal failure — requires operator action |
| `paused` | Job execution suspended by operator |
| `cancelled` | Job cancelled by operator or system |

## Job Classification and Priority

| Class | Priority | Retry Behavior | Alert Threshold | Audit Level | Example |
|-------|----------|---------------|-----------------|-------------|---------|
| `system_critical` | Highest | Aggressive retry, immediate alert on failure | First failure | Full | `health_check` |
| `operational` | High | Standard retry with backoff | 2 consecutive failures | Full | `metrics_aggregate` |
| `maintenance` | Normal | Standard retry, tolerant | 3 consecutive failures | Standard | `audit_cleanup` |
| `analytics` | Low | Best-effort, limited retries | Degraded only | Minimal | Future analytics jobs |
| `user_triggered` | Normal | Standard retry | Per-job | Full | Manual admin triggers |

## Concurrency and Idempotency Rules

- Every job **must** declare a `concurrency_policy`:
  - `forbid` — reject if already running (default)
  - `replace` — cancel current and start new
  - `allow` — permit parallel execution
- Every job run **must** have a unique `execution_id`
- Every idempotent job **must** have an `idempotency_key`
- Distributed lock required for critical singleton jobs
- `health_check` and `metrics_aggregate` must use `forbid` (singleton/non-overlapping)

## Failure Classification and Dead-Letter Policy

### Error Classification

| Error Type | Retry? | Action |
|-----------|--------|--------|
| Transient (network, timeout) | Yes | Exponential backoff + jitter |
| Dependency failure | Yes | Backoff, notify if persistent |
| Validation / configuration | No | Fail fast, alert admin |
| Authorization / security | No | Fail fast, security alert |
| Permanent logic error | No | Fail fast, require fix |

### Retry Strategy

- Retry policy must be **configurable per job**
- Exponential backoff must include **jitter** to prevent retry storms
- Only transient and dependency failures should retry automatically
- Permanent failures must fail fast, not consume retries

| Attempt | Base Delay | With Jitter |
|---------|-----------|-------------|
| 1 | 30 seconds | 30s ± random |
| 2 | 2 minutes | 2m ± random |
| 3 | 10 minutes | 10m ± random |
| Final | Dead-letter, alert admin | — |

### Dead-Letter Handling

- After max retries, move to `dead_lettered` state
- Preserve full failure metadata (error, stack, input, timing)
- Require admin visibility in admin panel
- Operator action paths:
  - **Inspect** — view full failure context
  - **Replay** — re-execute with original or modified input
  - **Cancel** — mark as permanently abandoned
  - **Mark resolved** — close without replay

## Job Registry (SSOT)

| Field | `audit_cleanup` | `health_check` | `metrics_aggregate` |
|-------|----------------|----------------|---------------------|
| **Job ID** | `audit_cleanup` | `health_check` | `metrics_aggregate` |
| **Owner Module** | audit-logging | health-monitoring | health-monitoring |
| **Purpose** | Archive old audit logs | Run health checks | Aggregate metrics |
| **Schedule** | Weekly | Every 1 min | Every 5 min |
| **Trigger Type** | scheduled | scheduled | scheduled |
| **Class** | maintenance | system_critical | operational |
| **Priority** | Normal | Highest | High |
| **Timeout (seconds)** | 25 | 10 | 20 |
| **Max Retries** | 3 | 3 | 3 |
| **Retry Policy** | Standard backoff | Aggressive | Standard backoff |
| **Concurrency Policy** | forbid | forbid | forbid |
| **Idempotency Strategy** | Time-window dedup | Execution-id based | Time-window dedup |
| **Failure Classification** | Transient/dependency | Transient | Transient/dependency |
| **Alert Severity** | Low | Critical | High |
| **Health Impact** | None | System health degrades | Metrics staleness |
| **Audit Required** | Yes | Yes | Yes |
| **Run Principal** | `svc:audit-cleanup` | `svc:health-check` | `svc:metrics-aggregate` |
| **Status** | Not started | Not started | Not started |

### Recovery and Reconciliation Jobs (Planned)

| Job ID | Purpose | Class | Status |
|--------|---------|-------|--------|
| `job_reconcile_stuck_runs` | Detect and recover jobs stuck in `running` beyond timeout | system_critical | Planned |
| `job_dead_letter_scan` | Scan and surface unresolved dead-lettered jobs | operational | Planned |
| `job_health_backfill` | Backfill missing health metrics after outage | maintenance | Planned |
| `job_audit_integrity_check` | Verify audit log completeness and consistency | maintenance | Planned |

## Manual Trigger Governance

- All manual job inputs must be **schema-validated**
- All inputs must be **sanitized**
- Only **allowlisted parameter sets** permitted — no freeform execution
- **Dry-run** support required for high-impact jobs
- Destructive maintenance jobs require **approval path**
- All manual triggers must be audited with:
  - Actor identity
  - Reason / justification
  - Input parameters
  - Execution result

## Service Identity and Permission Model

- Every job runs under a defined **service principal** (least-privilege)
- No broad admin bypass permitted
- Manual trigger requires:
  - `jobs.trigger` permission
  - Plus permission to affect underlying resource if applicable
- Sensitive jobs may require **re-auth** in admin UI
- All manual triggers audited with actor identity and reason

## Job Observability and Health Metrics

### Required Telemetry Per Run

| Field | Description |
|-------|-------------|
| `job_id` | Job identifier |
| `execution_id` | Unique run identifier |
| `scheduled_time` | When the run was scheduled |
| `actual_start_time` | When execution began |
| `end_time` | When execution completed |
| `duration_ms` | Total execution time |
| `queue_delay_ms` | Time between scheduled and actual start |
| `retry_count` | Number of retries for this run |
| `final_state` | Terminal state of this run |
| `failure_type` | Error classification if failed |
| `affected_records` | Count of records processed |
| `correlation_id` | Trace ID for cross-system correlation |

### Health Monitoring Metrics

| Metric | Purpose |
|--------|---------|
| Success rate | Job reliability |
| p95 runtime | Performance tracking |
| Retry rate | Stability indicator |
| Dead-letter count | Unresolved failure volume |
| Consecutive failures | Degradation detection |
| Missed schedule count | Scheduler reliability |
| Stale-last-success age | Freshness tracking |

## Stale / Missed Run Detection

- Detect when a scheduled run **did not execute**
- Detect when a job has **not succeeded** within expected freshness window
- Detect jobs **stuck in `running`** state beyond timeout
- Detect **repeated partial successes**

Freshness thresholds:

| Job | Expected Freshness | Staleness Action |
|-----|-------------------|-----------------|
| `health_check` | 2–3 minutes | Degrade system health status |
| `metrics_aggregate` | 10 minutes | Raise warning alert |
| `audit_cleanup` | 8 days | Raise info alert |

## Partial Failure and Resumability

For tasks split into smaller jobs:

- Define **chunking strategy** (batch size, partition key)
- Support **checkpointing** (last processed marker)
- Define **replay boundary** (from checkpoint, not from start)
- Declare **delivery guarantee**: exactly-once vs at-least-once
- Support **resume-from-last-checkpoint** behavior

## Downstream Failure Isolation

- Job failures **must not cascade** into core request path
- Non-critical jobs degrade gracefully
- Audit failure must not corrupt business execution
- Dependency outage must trip **circuit breaker** where applicable
- Repeated external dependency failure should **pause affected job** automatically after threshold

## Timeout Policy

- **Soft timeout**: warning threshold (e.g., 80% of hard limit)
- **Hard timeout**: forced termination
- Jobs repeatedly approaching timeout must be refactored
- Timeout budget must account for retries and chunk sizes
- Long-running workflows must use orchestration/chaining

## Registry Governance

- No production job may exist outside this registry
- Every job must have a **stable ID** (never reassigned)
- Schedule changes require **change-control entry**
- New jobs require **dependency and health impact review**
- Removed jobs require **decommission note**
- Registry is the **single source of truth** for all job definitions

## Shared Functions

| Function | Purpose | Used By |
|----------|---------|---------|
| `scheduleJob(jobId, schedule)` | Registers a job schedule | Module-specific setup |
| `executeWithRetry(fn, config)` | Wraps job with configurable retry logic | All jobs |
| `acquireJobLock(jobId, executionId)` | Distributed lock for singleton jobs | Concurrent job protection |
| `classifyError(error)` | Categorize error for retry/dead-letter routing | All jobs |
| `emitJobTelemetry(runContext)` | Emit standardized observability data | All jobs |

## Events

| Event | Emitted When | Consumed By |
|-------|-------------|-------------|
| `job.started` | Job execution begins | audit-logging |
| `job.completed` | Job finishes successfully | audit-logging |
| `job.failed` | Job fails after all retries | audit-logging, health-monitoring |
| `job.queued` | Job enters execution queue | health-monitoring |
| `job.retry_scheduled` | Retry scheduled after failure | audit-logging, health-monitoring |
| `job.dead_lettered` | Job enters terminal failure | audit-logging, health-monitoring, admin-panel |
| `job.paused` | Job execution suspended | audit-logging |
| `job.cancelled` | Job execution cancelled | audit-logging |

## Permissions

| Permission | Description |
|-----------|-------------|
| `jobs.view` | View job status and history |
| `jobs.trigger` | Manually trigger a job |
| `jobs.pause` | Pause a scheduled job |
| `jobs.resume` | Resume a paused job |
| `jobs.retry` | Retry a failed job |
| `jobs.deadletter.manage` | Inspect, replay, cancel, or resolve dead-lettered jobs |

## Dependencies

- [Auth Module](auth.md) — for service-level auth and service principals
- [Audit Logging Module](audit-logging.md) — for job event logging
- [Input Validation](../02-security/input-validation-and-sanitization.md) — for manual trigger input governance

## Used By / Affects

health-monitoring, admin-panel, audit-logging, operational visibility, incident response.

## Risks If Modified

HIGH — job changes can affect data consistency, monitoring reliability, system health visibility, and operational trust.

## Related Documents

- [Health Monitoring](health-monitoring.md)
- [Audit Logging](audit-logging.md)
- [Admin Panel](admin-panel.md)
- [Permission Index](../07-reference/permission-index.md)
- [Event Index](../07-reference/event-index.md)
