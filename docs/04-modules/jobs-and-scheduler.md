# Jobs and Scheduler Module

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-09

## Purpose

Manages background jobs, scheduled tasks, execution lifecycle, failure handling, retry logic, concurrency control, and operational governance.

## Scope

Job definitions, scheduling, execution, state management, retry logic, dead-letter handling, concurrency protection, observability, manual trigger governance, versioning, backpressure, recovery operations, deterministic scheduling, resource budgeting, security isolation, and emergency controls.

## Enforcement Rule (CRITICAL)

- No production job may exist outside the **job registry**
- Every job must declare concurrency policy, idempotency strategy, execution guarantee, and failure classification
- All job runs must be auditable and observable
- Manual triggers must be permission-checked, audited, and input-validated
- Terminal failures must enter dead-letter state
- Every job execution must have a matching start and terminal audit event — missing events flag system as unhealthy
- All scheduling and telemetry timestamps must use **UTC from a consistent time source** — no local/system time usage allowed
- Any unregistered, unmonitored, or ungoverned job is an **INVALID** implementation

## Key Rules

- All jobs must be idempotent
- All jobs must declare concurrency policy, idempotency strategy, and execution guarantee
- All jobs must log start, completion, and failure
- Failed jobs retry with configurable exponential backoff + jitter
- Jobs must not exceed configured timeout (default: 30s edge function limit)
- Long-running tasks must use orchestration/chaining, not oversized single functions
- No job may run outside the registered job registry
- Every job run must emit metrics and correlation metadata
- Manual triggers must be permission-checked, audited, and validated
- Terminal failures must enter dead-letter state
- Jobs must fail secure and isolate downstream impact
- Poison jobs must be auto-detected and paused
- Critical jobs must validate pre-conditions and post-conditions

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
| `paused` | Job execution suspended by operator or system |
| `cancelled` | Job cancelled by operator or system |
| `poison` | Job auto-paused due to repeated systematic failure |

## Job Classification and Priority

| Class | Priority | Retry Behavior | Alert Threshold | Audit Level | Example |
|-------|----------|---------------|-----------------|-------------|---------|
| `system_critical` | Highest | Aggressive retry, immediate alert on failure | First failure | Full | `health_check` |
| `operational` | High | Standard retry with backoff | 2 consecutive failures | Full | `metrics_aggregate` |
| `maintenance` | Normal | Standard retry, tolerant | 3 consecutive failures | Standard | `audit_cleanup` |
| `analytics` | Low | Best-effort, limited retries | Degraded only | Minimal | Future analytics jobs |
| `user_triggered` | Normal | Standard retry | Per-job | Full | Manual admin triggers |

## Deterministic Scheduling Model

Scheduler must guarantee:
- **No duplicate execution** for the same schedule window
- **No missed execution** without detection and compensating action

Rules:
- Each scheduled run must have a `schedule_window_id` (e.g., minute bucket, hour bucket)
- Before execution: check if window already executed → **skip** (dedup at schedule level)
- If a scheduled window is missed:
  - Enqueue **compensating run** for the missed window
  - Log missed window in telemetry
  - Flag in health monitoring if repeated
- Scheduler must handle **clock drift** — all scheduling decisions use the authoritative UTC time source
- Scheduler must handle **duplicate trigger** (e.g., multi-node race) via `schedule_window_id` dedup

## Time Source Standardization

- All scheduling, telemetry, SLO measurement, and retry timing must use **UTC from a single authoritative time source**
- No local system time or non-UTC timestamps allowed in any job-related operation
- Time source must be consistent across all execution nodes/functions

## Execution Guarantee Model

Each job **must** declare its execution guarantee:

| Guarantee | Description | Requirements |
|-----------|-------------|-------------|
| `at_least_once` | Job may execute more than once; consumer handles duplicates (default) | Idempotency key recommended |
| `exactly_once` | Job executes exactly once; no duplicate side effects | **Mandatory:** idempotency key persisted at DB level, atomic write + dedup check, distributed lock OR transactional guard |

Rules:
- Default is `at_least_once`
- Jobs with financial, ledger, or billing side effects **must** use `exactly_once`
- `exactly_once` jobs must verify dedup before committing side effects
- Execution guarantee must be stored in job registry and telemetry

### Global Idempotency Registry

For `exactly_once` jobs:
- Idempotency keys must be stored in a **central idempotency store** (dedicated DB table)
- Must enforce **unique constraint** on idempotency key
- Must use **atomic insert-or-ignore** (no race conditions)
- Idempotency records must include: `idempotency_key`, `job_id`, `execution_id`, `created_at`, `result_hash`
- Retention policy: idempotency records retained for configurable window (minimum: 7 days)

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
- Retries must respect system load (backpressure-aware)

| Attempt | Base Delay | With Jitter |
|---------|-----------|-------------|
| 1 | 30 seconds | 30s ± random |
| 2 | 2 minutes | 2m ± random |
| 3 | 10 minutes | 10m ± random |
| Final | Dead-letter, alert admin | — |

### Dead-Letter Handling

- After max retries, move to `dead_lettered` state
- Preserve full failure metadata (error, stack, input, timing, job version)
- Require admin visibility in admin panel
- Operator action paths:
  - **Inspect** — view full failure context
  - **Replay** — re-execute with original or modified input (see Replay Safety)
  - **Cancel** — mark as permanently abandoned
  - **Mark resolved** — close without replay

### Poison Job Detection

- If the **same job** fails repeatedly across **distinct executions** (not retries of one run):
  - Mark as `poison` state
  - Auto-pause the job
  - Escalate to admin with full failure history
- Poison threshold: configurable per job class (default: 5 consecutive cross-execution failures)
- Poison jobs require explicit operator resolution before resuming

## Job Versioning and Safe Deployment

- Every job in the registry must declare a `job_version`
- Every execution must store the version used at runtime
- Retries **must** use the same version as the original attempt (or be explicitly upgraded by operator)
- Dead-letter replay must support:
  - **Replay with original version** — default, safe reprocessing
  - **Replay with current version** — explicit operator decision, requires confirmation
- Version changes require change-control entry

## Replay Safety

Each job must declare `replay_safe: true | false`:

- `replay_safe: true` — replay permitted without additional confirmation
- `replay_safe: false` — replay requires:
  - Operator confirmation
  - Impact preview (if available)
  - Explicit acknowledgment of potential side effects

All replays must log:
- Original `execution_id`
- Replay `execution_id`
- Operator identity
- Reason / justification
- Version used (original or current)

## Backpressure and Rate Limiting

- Define **max concurrent jobs globally**
- Define **max concurrent jobs per type**
- Define **queue depth threshold** — reject or defer new submissions beyond limit
- **Adaptive throttling**: under system degradation:
  - Non-critical jobs slowed or paused automatically
  - Retries respect system load — no retry storms
  - `system_critical` jobs maintain priority execution
- Circuit breaker integration: repeated failures from external dependencies trigger automatic pause

## Priority Queue Execution Model

Scheduler must execute based on:

| Factor | Behavior |
|--------|----------|
| **Priority** | Higher priority jobs preempt lower priority in queue |
| **Aging** | Jobs waiting beyond threshold get priority boost (prevent starvation) |
| **System load** | Under degradation, only `system_critical` and `operational` execute; lower classes deferred |

- `system_critical` always preempts all other classes
- Lower priority jobs delayed if system under load
- Priority is **enforced at execution time**, not just documentation

## Cross-System Dependency Declaration

Each job must declare its **runtime dependencies**:

| Dependency Type | Examples |
|----------------|---------|
| Database | Primary DB, read replicas |
| External APIs | Third-party services, webhooks |
| Internal services | Auth, audit logging |
| Other jobs | Upstream data producers |

Behavior:
- If a declared dependency is **degraded**: job auto-paused or downgraded
- Dependency status integrates with health monitoring
- Dependency failure triggers appropriate error classification

## SLO Definitions

Each job must declare service-level objectives:

| Job | SLO Success Rate | SLO Latency | SLO Freshness |
|-----|-----------------|-------------|---------------|
| `health_check` | ≥ 99.9% | ≤ 2s | ≤ 3 min |
| `metrics_aggregate` | ≥ 99.5% | ≤ 15s | ≤ 10 min |
| `audit_cleanup` | ≥ 99.0% | ≤ 25s | ≤ 8 days |

SLO enforcement:
- Automated health scoring based on SLO compliance
- SLO breach triggers alert at severity defined by job class
- Persistent SLO breach escalates to operator action

## Resource Budgeting

Each job must define resource limits:

| Resource | Constraint |
|----------|-----------|
| Max DB operations | Per-execution cap on queries/writes |
| Max API calls | Per-execution cap on external calls |
| Max execution time | Timeout budget (soft + hard) |
| Max memory / payload size | Where applicable |

Behavior:
- If resource budget exceeded: job fails gracefully or degrades
- Repeated budget overuse → flagged in health system
- Resource consumption included in telemetry for trend analysis

## Data Integrity Safeguards

Critical jobs **must** implement:

- **Pre-condition validation**: verify expected data state before execution
- **Post-condition validation**: verify data consistency after execution
- If post-condition fails:
  - Log integrity violation
  - Flag in health monitoring
  - Do **not** silently proceed

Examples:
- `audit_cleanup`: verify record count matches expected archival window
- `metrics_aggregate`: verify aggregated totals are consistent with source data

## Security Boundary and Isolation

- Jobs must **only** access resources via the permission system
- Jobs must **never** bypass the API layer unless explicitly documented and approved
- DB access must respect **RLS** and **scoped service identity** — no direct unrestricted DB access
- A compromised job must not be able to:
  - Escalate privileges
  - Access data outside its declared scope
  - Affect other jobs' execution
- Job execution environment must enforce least-privilege at every layer

## Emergency Controls

### Global Kill Switch

- Immediately stops **all** new job executions and retries system-wide
- Preserves audit trail of activation
- Requires `jobs.emergency` permission

### Per-Job Kill Switch

- Immediately stops new executions and retries for a specific job
- Job moves to `paused` state
- Requires `jobs.pause` permission

### Class-Level Pause

- Pause all jobs of a given class (e.g., all `analytics` or `maintenance` jobs)
- `system_critical` class can only be paused via global kill switch
- Requires `jobs.pause` permission

All emergency controls must:
- Take effect **instantly** (no queue drain delay)
- Be audited with actor identity, reason, and timestamp
- Be surfaceable in admin panel

## Job Lineage and Causality Tracking

Required telemetry fields for chained/triggered jobs:

| Field | Description |
|-------|-------------|
| `parent_execution_id` | Execution ID of the job that triggered this one |
| `root_execution_id` | Original execution ID at the start of the chain |

Rules:
- Chained jobs **must** propagate lineage fields
- Lineage must be queryable for debugging and audit trails
- Root-to-leaf execution chains must be reconstructible

## Multi-Region and Failover Awareness

> Note: Deferred for future implementation, but architecture must not preclude.

- Scheduler must support **single-leader execution** model
- Failover must not produce **duplicate execution** for the same schedule window
- `schedule_window_id` dedup provides the foundation for safe failover
- When multi-region is activated, leader election and fencing must be documented

## Action Tracker Integration

The following job events **must** automatically create action tracker items:

| Trigger Event | Severity | Follow-Up Window | Owner |
|--------------|----------|-----------------|-------|
| `job.dead_lettered` | High | 4 hours | Module owner |
| `job.poison_detected` | Critical | 1 hour | Module owner + platform lead |
| `job.slo_breach` | Per job class | 8 hours | Module owner |
| Repeated retries (≥ 3 consecutive) | Medium | 24 hours | Module owner |
| Dependency failure (persistent) | High | 4 hours | Module owner + dependency owner |

Rules:
- Action items must include: job ID, execution ID, failure context, and recommended action
- Unresolved action items must escalate per the action tracker escalation policy
- Resolution must be logged

## Job Registry (SSOT)

| Field | `audit_cleanup` | `health_check` | `metrics_aggregate` | `alert_evaluation` |
|-------|----------------|----------------|---------------------|-------------------|
| **Job ID** | `audit_cleanup` | `health_check` | `metrics_aggregate` | `alert_evaluation` |
| **Version** | `1.0.0` | `1.0.0` | `1.0.0` | `1.0.0` |
| **Owner Module** | audit-logging | health-monitoring | health-monitoring | health-monitoring |
| **Purpose** | Archive old audit logs | Run health checks | Aggregate metrics | Evaluate alert thresholds |
| **Schedule** | Weekly | Every 1 min | Every 5 min | Every 1 min |
| **Trigger Type** | scheduled | scheduled | scheduled | scheduled |
| **Class** | maintenance | system_critical | operational | system_critical |
| **Priority** | Normal | Highest | High | Highest |
| **Execution Guarantee** | at_least_once | at_least_once | at_least_once | at_least_once |
| **Timeout (seconds)** | 25 | 10 | 20 | 10 |
| **Max Retries** | 3 | 3 | 3 | 3 |
| **Retry Policy** | Standard backoff | Aggressive | Standard backoff | Aggressive |
| **Concurrency Policy** | forbid | forbid | forbid | forbid |
| **Idempotency Strategy** | Time-window dedup | Execution-id based | Time-window dedup | Time-window dedup |
| **Failure Classification** | Transient/dependency | Transient | Transient/dependency | Transient |
| **Replay Safe** | true | true | true | true |
| **Alert Severity** | Low | Critical | High | Critical |
| **Health Impact** | None | System health degrades | Metrics staleness | Alert blindness — missed threshold breaches |
| **Audit Required** | Yes | Yes | Yes | Yes |
| **Run Principal** | `svc:audit-cleanup` | `svc:health-check` | `svc:metrics-aggregate` | `svc:alert-evaluation` |
| **Dependencies** | DB | DB, monitored services | DB, metrics sources | DB, metrics data, alert config |
| **Resource Budget** | ≤ 1000 DB ops | ≤ 50 DB ops | ≤ 500 DB ops | ≤ 100 DB ops |
| **SLO Success Rate** | ≥ 99.0% | ≥ 99.9% | ≥ 99.5% | ≥ 99.9% |
| **SLO Latency** | ≤ 25s | ≤ 2s | ≤ 15s | ≤ 5s |
| **SLO Freshness** | ≤ 8 days | ≤ 3 min | ≤ 10 min | ≤ 3 min |
| **Event Outputs** | — | `health.alert_triggered`, `health.status_changed` | — | `health.alert_triggered`, `health.status_changed` |
| **Status** | Not started | Not started | Not started | Not started |

### Recovery and Reconciliation Jobs (Planned)

| Job ID | Purpose | Class | Status |
|--------|---------|-------|--------|
| `job_reconcile_stuck_runs` | Detect and recover jobs stuck in `running` beyond timeout | system_critical | Planned |
| `job_dead_letter_scan` | Scan and surface unresolved dead-lettered jobs | operational | Planned |
| `job_health_backfill` | Backfill missing health metrics after outage | maintenance | Planned |
| `job_audit_integrity_check` | Verify audit log completeness and consistency | maintenance | Planned |
| `job_poison_scan` | Detect and flag poison jobs across the registry | system_critical | Planned |
| `job_idempotency_cleanup` | Prune expired idempotency records | maintenance | Planned |

## Formal Job Execution Contract

Every job **must** implement the following interface:

```typescript
interface JobContract {
  jobId: string;
  version: string;
  executionId: string;
  idempotencyKey?: string;
  executionGuarantee: 'at_least_once' | 'exactly_once';
  parentExecutionId?: string;
  rootExecutionId?: string;

  validatePreConditions(context: JobContext): Promise<boolean>;
  execute(context: JobContext): Promise<JobResult>;
  validatePostConditions(context: JobContext, result: JobResult): Promise<boolean>;
}
```

Every job **must** use the following shared functions:
- `executeWithRetry` — retry wrapper
- `classifyError` — error categorization
- `emitJobTelemetry` — observability emission
- `acquireJobLock` — if concurrency policy requires it

Zero deviation between jobs is required — consistent observability, retry, and audit behavior.

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
| `job_version` | Version executed |
| `execution_id` | Unique run identifier |
| `execution_guarantee` | at_least_once or exactly_once |
| `schedule_window_id` | Schedule dedup window identifier |
| `parent_execution_id` | Parent job execution (if chained) |
| `root_execution_id` | Root of execution chain |
| `scheduled_time` | When the run was scheduled (UTC) |
| `actual_start_time` | When execution began (UTC) |
| `end_time` | When execution completed (UTC) |
| `duration_ms` | Total execution time |
| `queue_delay_ms` | Time between scheduled and actual start |
| `retry_count` | Number of retries for this run |
| `final_state` | Terminal state of this run |
| `failure_type` | Error classification if failed |
| `affected_records` | Count of records processed |
| `resource_usage` | DB ops, API calls consumed |
| `correlation_id` | Trace ID for cross-system correlation |

### Health Monitoring Metrics

| Metric | Purpose |
|--------|---------|
| Success rate | Job reliability (SLO tracking) |
| p95 runtime | Performance tracking (SLO tracking) |
| Retry rate | Stability indicator |
| Dead-letter count | Unresolved failure volume |
| Consecutive failures | Degradation detection |
| Missed schedule count | Scheduler reliability |
| Stale-last-success age | Freshness tracking (SLO tracking) |
| Poison job count | Systematic failure detection |
| Queue depth | Backpressure indicator |
| SLO compliance % | Per-job health scoring |
| Resource budget utilization | Cost/capacity tracking |

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

## Audit Integrity Verification

- Every job execution **must** have:
  - A `job.started` event
  - A terminal event (`job.completed`, `job.failed`, or `job.dead_lettered`)
- If a terminal event is missing for a completed execution → flag system as unhealthy
- `job_audit_integrity_check` reconciliation job verifies completeness
- Missing audit events must be surfaced in health monitoring and admin panel

## Partial Failure and Resumability

For tasks split into smaller jobs:

- Define **chunking strategy** (batch size, partition key)
- Support **checkpointing** (last processed marker)
- Define **replay boundary** (from checkpoint, not from start)
- Declare **execution guarantee**: exactly-once vs at-least-once
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
- Every job must declare a **version**
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
| `detectPoisonJob(jobId)` | Check cross-execution failure pattern | Scheduler, reconciliation |
| `enforceBackpressure(queue)` | Apply rate limiting and adaptive throttling | Scheduler |
| `checkScheduleWindow(jobId, windowId)` | Dedup check for deterministic scheduling | Scheduler |
| `checkIdempotencyKey(key)` | Central idempotency registry lookup | exactly_once jobs |
| `activateKillSwitch(scope)` | Emergency stop for global/job/class | Admin panel, emergency ops |

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
| `job.poison_detected` | Job flagged as poison | audit-logging, health-monitoring, admin-panel |
| `job.replayed` | Dead-lettered job replayed | audit-logging |
| `job.slo_breach` | Job SLO threshold violated | health-monitoring, admin-panel |
| `job.kill_switch_activated` | Emergency stop triggered | audit-logging, health-monitoring, admin-panel |
| `job.schedule_missed` | Scheduled window missed | health-monitoring |
| `job.resource_budget_exceeded` | Resource limit breached | health-monitoring |

## Permissions

| Permission | Description |
|-----------|-------------|
| `jobs.view` | View job status and history |
| `jobs.trigger` | Manually trigger a job |
| `jobs.pause` | Pause a scheduled job |
| `jobs.resume` | Resume a paused job |
| `jobs.retry` | Retry a failed job |
| `jobs.deadletter.manage` | Inspect, replay, cancel, or resolve dead-lettered jobs |
| `jobs.emergency` | Activate global kill switch |

## Dependencies

- [Auth Module](auth.md) — for service-level auth and service principals
- [Audit Logging Module](audit-logging.md) — for job event logging
- [Input Validation](../02-security/input-validation-and-sanitization.md) — for manual trigger input governance
- [Health Monitoring](health-monitoring.md) — for dependency status and SLO alerting
- [Action Tracker](../06-tracking/action-tracker.md) — for operational follow-up on failures

## Used By / Affects

health-monitoring, admin-panel, audit-logging, action-tracker, operational visibility, incident response.

## Risks If Modified

HIGH — job changes can affect data consistency, monitoring reliability, system health visibility, and operational trust.

## Related Documents

- [Health Monitoring](health-monitoring.md)
- [Audit Logging](audit-logging.md)
- [Admin Panel](admin-panel.md)
- [Permission Index](../07-reference/permission-index.md)
- [Event Index](../07-reference/event-index.md)
- [Action Tracker](../06-tracking/action-tracker.md)
