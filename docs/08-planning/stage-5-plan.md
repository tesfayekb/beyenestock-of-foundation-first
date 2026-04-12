# Stage 5 Plan — Operations & Reliability

> **Owner:** Project Lead | **Created:** 2026-04-12 | **Plan Version:** v10
> **Modules:** PLAN-HEALTH-001, PLAN-JOBS-001
> **Depends On:** Phase 4 complete (all modules), Phase 3.5 hardening complete

## Purpose

Implement health monitoring, job scheduling, and operational infrastructure. Includes DW-019 (User Session Revocation) as a Phase 4 carryover with no blocking dependency on health/jobs infrastructure.

## Decisions

| ID | Decision | Rationale |
|----|----------|-----------|
| D5-001 | Include DW-019 in Phase 5 | Self-contained; only needs list-sessions + revoke-session edge functions using Supabase admin session API. No dependency on health/jobs. |
| D5-002 | Defer DW-020 to Phase 6 | No backend infrastructure or schema exists for notification preferences. |
| D5-003 | Defer DW-023 to Phase 6 | Display formatting improvement with no operational impact. |
| D5-004 | Include job_idempotency_keys table in Stage 5C | Infrastructure must exist before any job can declare `exactly_once` semantics, even if no Phase 5 jobs require it. |

## Stages

---

### Stage 5A — Health Check Infrastructure

**Scope:**
- `system_health_snapshots` table with RLS (only `monitoring.view` holders can SELECT)
- `GET /health` public edge function — returns `{ status, timestamp }` only (no internals)
- `GET /health/detailed` authenticated edge function — requires `monitoring.view` permission, returns per-subsystem check results
- Health status model: `healthy | degraded | unhealthy`
- Subsystem checks: database connectivity, auth service, audit pipeline
- Audit events: `health.status_changed`

**Schema — `system_health_snapshots`:**

| Column | Type | Notes |
|--------|------|-------|
| id | uuid | PK, gen_random_uuid() |
| status | text | healthy / degraded / unhealthy |
| checks | jsonb | Per-subsystem results |
| created_at | timestamptz | now() |

**RLS:** SELECT for authenticated users with `monitoring.view`. No INSERT/UPDATE/DELETE via client — edge functions use service role.

**Edge Functions:**
- `health-check` — public, no auth required, returns minimal status
- `health-detailed` — requires Bearer JWT + `monitoring.view`

**Phase Gate 5A:**
- [ ] `GET /health` returns correct status without auth
- [ ] `GET /health/detailed` requires `monitoring.view` and returns subsystem details
- [ ] `system_health_snapshots` table created with correct RLS
- [ ] No sensitive internals in unauthenticated health response
- [ ] `health.status_changed` event emitted on status transition

---

### Stage 5B — Metrics & Alerting Infrastructure

**Scope:**
- `system_metrics` table — stores time-series metric snapshots
- `alert_configs` table — configurable alert thresholds
- `alert_history` table — triggered alert records
- Alert severity model: `info | warning | critical`
- Monitoring domains: API, auth, database, jobs, audit, integrations
- `GET /health/metrics` edge function — requires `monitoring.view`
- `GET /health/alerts` edge function — requires `monitoring.view`
- `POST /health/alert-config` edge function — requires `monitoring.configure`
- Audit events: `health.alert_triggered`, `health.monitoring_failed`

**Schema — `system_metrics`:**

| Column | Type | Notes |
|--------|------|-------|
| id | uuid | PK |
| metric_key | text | e.g., `api.error_rate_5xx`, `auth.failure_rate` |
| value | numeric | Metric value |
| metadata | jsonb | Optional context |
| recorded_at | timestamptz | now() |

**Schema — `alert_configs`:**

| Column | Type | Notes |
|--------|------|-------|
| id | uuid | PK |
| metric_key | text | Which metric this alert watches |
| severity | text | info / warning / critical |
| threshold_value | numeric | Trigger threshold |
| comparison | text | gt / lt / gte / lte / eq |
| enabled | boolean | Default true |
| cooldown_seconds | integer | Suppress re-fire within window |
| created_by | uuid | FK to auth.users |
| created_at | timestamptz | |
| updated_at | timestamptz | |

**Schema — `alert_history`:**

| Column | Type | Notes |
|--------|------|-------|
| id | uuid | PK |
| alert_config_id | uuid | FK to alert_configs |
| metric_key | text | Denormalized for query speed |
| severity | text | |
| metric_value | numeric | Value that triggered the alert |
| threshold_value | numeric | Threshold at trigger time |
| resolved_at | timestamptz | Null until resolved |
| created_at | timestamptz | |

**RLS:** All tables SELECT-only for `monitoring.view`. Mutations via edge functions with service role.

**Phase Gate 5B:**
- [ ] `system_metrics`, `alert_configs`, `alert_history` tables created with RLS
- [ ] Alert thresholds configurable via `POST /health/alert-config`
- [ ] Alert evaluation produces correct `alert_history` entries
- [ ] `health.alert_triggered` event fires when threshold breached
- [ ] Alert cooldown prevents duplicate firing within window
- [ ] Metrics endpoint returns time-series data for dashboard consumption

---

### Stage 5C — Job Scheduler Infrastructure

**Scope:**
- `job_registry` table — SSOT for all registered jobs
- `job_executions` table — execution history with full lifecycle tracking
- `job_idempotency_keys` table — for `exactly_once` guarantee (unique constraint, 7-day retention)
- 11-state lifecycle model: registered → scheduled → queued → running → succeeded/retry_pending/failed/dead_lettered/paused/cancelled/poison
- Concurrency policies: forbid / replace / allow
- Error classification: transient, dependency, validation, authorization, permanent
- Retry backoff: 30s → 2m → 10m → dead-letter
- Shared `executeWithRetry()` utility function
- Dead-letter handling with operator action paths
- Poison job detection (threshold: 5 consecutive cross-execution failures)
- Job versioning — execution stores version used at runtime

**Schema — `job_registry`:**

| Column | Type | Notes |
|--------|------|-------|
| id | text | PK, job identifier (e.g., `health_check`) |
| version | text | Semantic version |
| owner_module | text | Module that owns this job |
| description | text | |
| schedule | text | Cron expression or `manual` |
| trigger_type | text | scheduled / manual / event |
| class | text | system_critical / operational / maintenance / analytics / user_triggered |
| priority | text | highest / high / normal / low |
| execution_guarantee | text | at_least_once / exactly_once |
| timeout_seconds | integer | |
| max_retries | integer | |
| retry_policy | text | aggressive / standard / none |
| concurrency_policy | text | forbid / replace / allow |
| replay_safe | boolean | |
| enabled | boolean | Default true |
| status | text | registered / paused / poison |
| created_at | timestamptz | |
| updated_at | timestamptz | |

**Schema — `job_executions`:**

| Column | Type | Notes |
|--------|------|-------|
| id | uuid | PK |
| job_id | text | FK to job_registry |
| execution_id | uuid | Unique per run |
| schedule_window_id | text | For dedup |
| state | text | 11-state lifecycle |
| job_version | text | Version at execution time |
| attempt | integer | Current attempt number |
| started_at | timestamptz | |
| completed_at | timestamptz | |
| error | jsonb | Error details on failure |
| metadata | jsonb | Execution context |
| parent_execution_id | uuid | For chained jobs |
| root_execution_id | uuid | Chain root |
| correlation_id | text | |
| created_at | timestamptz | |

**Schema — `job_idempotency_keys`:**

| Column | Type | Notes |
|--------|------|-------|
| id | uuid | PK |
| idempotency_key | text | UNIQUE constraint |
| job_id | text | FK to job_registry |
| execution_id | uuid | FK to job_executions |
| result_hash | text | Hash of execution result |
| created_at | timestamptz | |
| expires_at | timestamptz | 7-day retention window |

**RLS:** All tables SELECT-only for `jobs.view`. Mutations via edge functions with service role.

**Shared Functions:**
- `executeWithRetry(jobId, handler, options)` — retry wrapper with backoff, jitter, error classification
- `classifyError(error)` — returns transient/dependency/validation/authorization/permanent
- `detectPoisonJob(jobId)` — checks consecutive cross-execution failure count

**Phase Gate 5C:**
- [ ] `job_registry`, `job_executions`, `job_idempotency_keys` tables created with RLS
- [ ] `executeWithRetry()` correctly implements backoff with jitter
- [ ] Error classification routes errors to correct retry/fail-fast paths
- [ ] `schedule_window_id` dedup prevents duplicate execution
- [ ] Poison detection triggers at configured threshold (default: 5)
- [ ] Job versioning stored on every execution record
- [ ] Idempotency key unique constraint enforced

---

### Stage 5D — Core Jobs Implementation

**Scope:** Implement the 4 jobs defined in the module doc job registry:

| Job | Schedule | Class | Owner Module |
|-----|----------|-------|-------------|
| `health_check` | Every 1 min | system_critical | health-monitoring |
| `metrics_aggregate` | Every 5 min | operational | health-monitoring |
| `alert_evaluation` | Every 1 min | system_critical | health-monitoring |
| `audit_cleanup` | Weekly | maintenance | audit-logging |

**Implementation:**
- Each job is an edge function invoked via `pg_cron` + `pg_net`
- Each job uses `executeWithRetry()` wrapper
- Each job emits start/complete/fail audit events
- `health_check` checks: DB ping, auth service, audit write test
- `metrics_aggregate` aggregates from `system_health_snapshots` into `system_metrics`
- `alert_evaluation` reads `system_metrics` + `alert_configs`, writes to `alert_history`
- `audit_cleanup` archives records older than 90 days (per DEC-007)

**Formal Job Execution Contract (per module doc):**
- Every job declares: concurrency_policy, idempotency_strategy, execution_guarantee, failure_classification
- Every execution has matching start + terminal audit event
- All timestamps UTC
- Resource budgets enforced per job registry

**Phase Gate 5D:**
- [ ] All 4 jobs registered in `job_registry`
- [ ] Each job executes on schedule via `pg_cron`
- [ ] Start and terminal audit events for every execution
- [ ] `health_check` correctly detects DB/auth/audit subsystem status
- [ ] `audit_cleanup` respects 90-day retention (DEC-007)
- [ ] `alert_evaluation` fires `health.alert_triggered` on threshold breach
- [ ] All jobs use `executeWithRetry()` with correct retry policies

---

### Stage 5E — Emergency Controls & Operational Governance

**Scope:**
- Global kill switch — stops all job execution immediately
- Per-job kill switch — pauses individual jobs
- Class-level pause — pause all jobs of a given class
- `POST /jobs/kill-switch` edge function — requires `jobs.emergency`
- `POST /jobs/pause` edge function — requires `jobs.pause`
- `POST /jobs/resume` edge function — requires `jobs.pause`
- All emergency actions audited with actor, reason, timestamp
- Circuit breaker: repeated dependency failures auto-pause affected jobs

**Permissions (new):**

| Permission | Description |
|-----------|-------------|
| `jobs.view` | View job registry and execution history |
| `jobs.trigger` | Manually trigger job execution |
| `jobs.pause` | Pause/resume individual jobs or job classes |
| `jobs.emergency` | Activate global kill switch |

**Phase Gate 5E:**
- [ ] Kill switch immediately stops all new executions
- [ ] Per-job pause moves job to `paused` state
- [ ] Class-level pause affects all jobs of that class
- [ ] `system_critical` only pausable via global kill switch
- [ ] All emergency actions produce audit entries
- [ ] Circuit breaker auto-pauses on repeated dependency failures

---

### Stage 5F — Admin UI & DW-019

**Scope:**
- Health monitoring dashboard in admin panel (requires `monitoring.view`)
- Job management dashboard in admin panel (requires `jobs.view`)
- Job detail view with execution history
- Dead-letter management: inspect, replay, cancel, mark resolved
- Emergency controls UI: kill switch, pause/resume
- Alert configuration UI (requires `monitoring.configure`)
- **DW-019: User Self-Service Session Revocation** — revoke-sessions edge function, user panel SecurityPage UI

**DW-019 Implementation:**
- Location: `SecurityPage.tsx` (user panel), NOT admin panel
- `POST /revoke-sessions` edge function — requires `session.self_manage` (self-scope: `requireSelfScope(ctx, targetUserId)`), accepts `{ scope: 'others' | 'global' }`, calls `supabaseAdmin.auth.admin.signOut(userId, scope)`, applies `requireRecentAuth()`, audits `user.sessions_revoked` with scope in metadata
- No session listing in Phase 5 — Supabase admin SDK returns no useful session metadata; listing is only meaningful with per-session revocation (Phase 6)
- UI: Two distinct actions on SecurityPage:
  - **"Sign out other devices"** — scope: `others`, standard action, keeps current session active
  - **"Sign out everywhere"** — scope: `global`, destructive action with confirmation dialog, invalidates all sessions including current
- Phase 6 DW item: Per-session revocation with session list view — revisit when Supabase stabilizes auth.sessions API or adds individual session revocation to admin SDK
- Audit event: `user.sessions_revoked` (with `{ scope }` in metadata)

**Phase Gate 5F:**
- [ ] Health dashboard reflects real system state
- [ ] Job dashboard shows registry, executions, dead-letter queue
- [ ] Dead-letter actions (replay, cancel, resolve) function correctly
- [ ] Kill switch and pause controls accessible and functional
- [ ] Alert configuration UI creates/updates alert_configs
- [ ] DW-019: "Sign out other devices" revokes other sessions, user stays logged in
- [ ] DW-019: "Sign out everywhere" terminates all sessions with confirmation dialog
- [ ] DW-019: Both actions require reauth and produce audit trail
- [ ] All new pages use DashboardLayout shell and design system tokens

---

## Deferred to Phase 6

| ID | Item | Reason |
|----|------|--------|
| DW-020 | User Notification Preferences | No schema or backend infrastructure exists |
| DW-023 | Audit actor-scope display shaping | Display-only improvement, no operational impact |
| DW-024 | Per-session revocation with list view | Requires stable auth.sessions API or individual session revocation in Supabase admin SDK |

## New Permissions Summary

| Permission | Stage | Description |
|-----------|-------|-------------|
| `monitoring.view` | 5A | View health dashboard and metrics |
| `monitoring.configure` | 5B | Configure alert thresholds |
| `jobs.view` | 5C | View job registry and execution history |
| `jobs.trigger` | 5E | Manually trigger job execution |
| `jobs.pause` | 5E | Pause/resume jobs or job classes |
| `jobs.emergency` | 5E | Global kill switch |

## New Events Summary

| Event | Stage | Emitted When |
|-------|-------|-------------|
| `health.status_changed` | 5A | System health status transitions |
| `health.alert_triggered` | 5B | Metric threshold breached |
| `health.monitoring_failed` | 5B | Monitoring pipeline failure |
| `job.started` | 5D | Job execution begins |
| `job.completed` | 5D | Job execution succeeds |
| `job.failed` | 5D | Job execution fails (after retries) |
| `job.dead_lettered` | 5D | Job enters dead-letter state |
| `job.poison_detected` | 5D | Poison job auto-paused |
| `job.kill_switch_activated` | 5E | Global kill switch triggered |
| `job.paused` | 5E | Job paused by operator or system |
| `job.resumed` | 5E | Job resumed |
| `user.sessions_revoked` | 5F | User revokes own sessions (self-service, scope in metadata) |

## Execution Order

Stages MUST execute sequentially: 5A → 5B → 5C → 5D → 5E → 5F

- 5B depends on 5A (metrics reference health snapshots)
- 5C is independent but sequenced for review cadence
- 5D depends on 5C (jobs use job infrastructure)
- 5E depends on 5C (emergency controls target job registry)
- 5F depends on all prior stages (UI surfaces everything)
- DW-019 in 5F has no dependency on 5A-5E but is sequenced to avoid context-switching

## Dependencies

- [Master Plan](master-plan.md) — Phase 5 section
- [Health Monitoring Module](../04-modules/health-monitoring.md)
- [Jobs and Scheduler Module](../04-modules/jobs-and-scheduler.md)
- [Deferred Work Register](deferred-work-register.md) — DW-019

## Related Documents

- [Action Tracker](../06-tracking/action-tracker.md)
- [Route Index](../07-reference/route-index.md)
- [Function Index](../07-reference/function-index.md)
- [Permission Index](../07-reference/permission-index.md)
- [Event Index](../07-reference/event-index.md)
