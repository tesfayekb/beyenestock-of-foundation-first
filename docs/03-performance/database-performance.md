# Database Performance

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-08

## Purpose

Defines database performance governance, optimization rules, and operational controls for a permission-driven, RLS-enforced, audit-heavy, multi-tenant system.

## Scope

PostgreSQL database: schema design, query discipline, indexing, write paths, migrations, observability, capacity planning, and change control.

## Enforcement Rule (CRITICAL)

- All critical-path production queries **MUST** use efficient indexed access paths or documented alternatives
- No query may bypass RLS, permission checks, or audit requirements for performance
- Sequential scans on large production tables are **prohibited** unless explicitly justified and approved
- Integrity beats performance for security-sensitive writes — no exception
- Denormalization or caching must **never** weaken authorization or audit correctness
- Any violation of these rules is an **INVALID** implementation

---

## Schema Design

- Normalize to 3NF minimum; denormalize only with documented justification and integrity review
- Use appropriate column types (no `text` for booleans, no `varchar` without length)
- Timestamps on every table (`created_at`, `updated_at`)
- Soft delete where appropriate (`deleted_at`)
- All foreign keys indexed
- Tenant scope columns indexed
- Common sort keys indexed
- Policy filter columns indexed
- Join bridge tables indexed on both sides

---

## Workload and Query Classification

Not all queries are equal. Each class has distinct rules:

| Class | Latency Target | Indexing | Complexity | Async/Offload |
|-------|---------------|----------|------------|---------------|
| **Critical Reads** (auth, session, permission) | p95 < 50ms, p99 < 100ms | Mandatory, benchmarked | Minimal joins | No |
| **Critical Writes** (auth, role changes) | p95 < 100ms | Mandatory | Minimal lock scope | No |
| **Standard Reads** (user data, dashboards) | p95 < 150ms | Required | Moderate | No |
| **Admin Search/Filter** | p95 < 500ms | Required on search columns | Bounded result sets | Optional for large exports |
| **Analytics/Reporting** | p95 < 2s | Required | May use materialized views | Yes, for heavy reports |
| **Background/Maintenance** | Best effort | Required for access paths | Batched | Yes |
| **Reconciliation/Audit Queries** | p95 < 1s | Required | Read-only, append patterns | Yes, for exports |

**Rules:**
- Every new query must be classified before merge
- Classification determines allowed complexity and latency budget
- Queries exceeding class budget require optimization or reclassification

---

## RLS and Tenant-Scoped Performance Rules

This system depends on RLS for authorization. Database performance strategy must account for this.

**Mandatory Rules:**

- All tenant-scoped tables must be indexed for tenant isolation patterns
- RLS policies must be benchmarked on realistic tenant-sized datasets (small, medium, large)
- Queries must include tenant/account scoping in access pattern review
- Indexes must reflect actual RLS policy filters, not just application-level filters
- Permission-sensitive queries must **not** rely on post-filtering in application code — filtering must happen at DB level
- `has_role()` and equivalent security definer functions must be benchmarked for latency at scale
- No RLS policy may cause sequential scan on large tables

**Benchmarking Requirements:**

| Tenant Size | Expected Row Count | Must Meet Target |
|-------------|-------------------|-----------------|
| Small | < 1,000 rows | All class targets |
| Medium | 10,000–100,000 rows | All class targets |
| Large (realistic max) | 500,000+ rows | All class targets, no plan regression |

---

## Write Path and Transaction Rules

### Write Performance

- High-frequency writes must minimize lock duration
- Write paths must avoid unnecessary index churn (review index count on write-heavy tables)
- Bulk writes must batch safely with defined batch sizes
- Transactional scope must be minimal — only include what requires atomicity
- Critical writes must validate contention behavior under concurrent load testing
- Audit writes must use append-only patterns optimized for insert throughput

### Transaction Governance

- Transactions must be as short as possible
- No user-interactive waits inside a transaction
- Lock wait threshold: **5 seconds** (warning), **15 seconds** (critical)
- Deadlock detection and alerting required
- Retry policy required for transient serialization/deadlock failures (max 3 retries with backoff)
- High-contention tables must be identified and reviewed quarterly

### Lock/Contention Controls

- Tables with known contention patterns must document mitigation strategy
- Advisory locks preferred over row locks for coordination patterns
- No table-level locks in application code without explicit approval

---

## Index Governance

### Rules

- Every nontrivial index must map to a known query pattern
- Composite index column order must match filter/sort access path
- Partial indexes allowed where justified (document the filter condition)
- Duplicate/redundant indexes must be reviewed and removed
- Write-cost of indexes must be considered, not just read speed
- Index review must be tied to slow query findings

### Required Index Coverage

| Column Type | Indexing Requirement |
|-------------|---------------------|
| Primary keys | Automatic |
| Foreign keys | Always indexed |
| Tenant/account scope columns | Always indexed |
| RLS policy filter columns | Always indexed |
| Columns in WHERE/ORDER BY on large tables | Indexed |
| Common sort keys | Indexed |
| Join bridge table columns (both sides) | Indexed |
| Full-text search columns | GIN/GiST index or dedicated search |

### Index Lifecycle

- New indexes require query plan justification
- Unused indexes reviewed monthly and dropped
- Index effectiveness tracked via observability

---

## Search and Pagination Rules

- Cursor-based pagination required for large or high-churn datasets
- Offset pagination prohibited for large datasets unless explicitly justified
- Stable sort keys required for cursor pagination (e.g., `created_at` + `id`)
- Admin search endpoints must define searchable columns explicitly — no open-ended column search
- Wildcard / full-table search on large tables prohibited without dedicated search design (e.g., GIN index, search index)
- Exports and reporting beyond interactive page limits must move to async jobs
- Maximum result set: **100 rows per page** (configurable per endpoint, never unlimited)
- No `SELECT *` — always specify columns

---

## Migration Safety

**Mandatory Rules:**

- Migrations must be safe for production-sized datasets
- Avoid blocking table rewrites unless explicitly approved
- Index creation must use `CONCURRENTLY` where supported
- Backfills must be chunked and observable (log progress, allow pause/resume)
- Rollback path required for high-risk migrations
- Schema changes on critical tables (users, roles, permissions, audit_logs) require impact review

**Migration Review Checklist:**

| Check | Required For |
|-------|-------------|
| Lock duration estimate | All DDL on large tables |
| Concurrent index build | All new indexes on production tables |
| Chunked backfill plan | Any data migration > 10,000 rows |
| Rollback script | All high-risk migrations |
| RLS policy re-benchmark | Any schema change on RLS-protected tables |
| Performance baseline comparison | Critical path tables |

---

## Connection Management

- Use connection pooling (Supabase default pgBouncer)
- Close connections properly in edge functions
- No long-running transactions holding connections
- Connection pool saturation monitored and alerted
- Edge function cold starts must not exhaust connection pool

---

## Caching Relationship

Database load must be managed through safe caching where appropriate:

- Repeated permission reads may use scoped cache with bounded TTL (≤ 60s) and invalidation on role/permission change
- Reference/lookup data (feature flags, config) may be cached
- No cache may bypass authorization boundaries or leak cross-tenant data
- Cache invalidation strategy must be documented before reducing DB load through caching
- Hot-read endpoints must be reviewed for DB offload opportunities

---

## Hot Tables and Hot Paths

### Identified Hot Tables

| Table | Access Pattern | Review Frequency |
|-------|---------------|-----------------|
| `users` / `profiles` | Auth, session, permission lookup | Quarterly |
| `user_roles` / `role_permissions` | Every permission check | Quarterly |
| `audit_logs` | Every privileged action (append) | Monthly (growth) |
| `health_metrics` | Continuous monitoring writes | Monthly (growth) |
| `job_executions` | Job system reads/writes | Monthly |
| `permissions` | Permission evaluation | Quarterly |

### Rules

- Hot tables require explicit query and index review
- Operational (hot) and historical (cold) workloads should be separated where practical
- Write-heavy hot tables must be monitored for bloat, vacuum health, and index overhead
- Hot-path queries must have the strictest latency budgets (see Query Classification)

---

## Data Lifecycle and Retention

High-growth tables require lifecycle management:

- `audit_logs`: minimum 90-day retention, then archive (batched, non-blocking)
- `health_metrics`: configurable retention, summary/rollup for historical data
- `job_executions`: retain recent (30 days active), archive completed
- Event/metrics tables require growth forecasting (monthly projection)

**Rules:**

- Purge/archive operations must be batched and non-blocking
- No silent data removal — all retention actions audited
- Historical data access patterns must be separated from hot-path operational queries
- Archive jobs must follow Job Module governance (observable, retry-safe, kill-switch aware)

---

## Observability and Telemetry

### Required Database Signals

| Signal | Warning Threshold | Critical Threshold |
|--------|------------------|-------------------|
| p95 query latency | > 200ms | > 500ms |
| p99 query latency | > 500ms | > 1s |
| Slow query count (> 1s) | > 5/min | > 20/min |
| Lock wait time | > 5s | > 15s |
| Deadlock count | > 0/hour | > 3/hour |
| Connection pool saturation | > 70% | > 90% |
| Sequential scan rate (large tables) | > 5% of queries | > 15% of queries |
| Table bloat | > 30% | > 50% |
| Replication lag (if applicable) | > 1s | > 5s |
| Index usage effectiveness | < 90% used | < 70% used |

### Rules

- All signals must be collected and available in dashboards
- Threshold breaches create alerts
- Sustained warning-level signals (> 24h) must create Action Tracker entries
- Critical signals must trigger immediate investigation

---

## Capacity Planning

### Scaling Triggers

| Condition | Action |
|-----------|--------|
| Sustained connection saturation > 80% | Evaluate pooler config or read replicas |
| Slow query growth trend > 20% month-over-month | Query optimization sprint |
| Table growth exceeding retention forecasts | Implement archival or partitioning |
| p99 query latency exceeding targets for 7+ days | Architectural review |
| Hot table bloat > 40% | Vacuum tuning or table maintenance |

### Growth Assumptions

- Define expected user/tenant growth rate (reviewed quarterly)
- Define expected data volume growth per hot table
- Capacity thresholds must be defined for: read replicas, partitioning, archival, materialized views, and specialized search

---

## Integrity vs Performance Policy

- **Integrity always beats performance** for critical and security-sensitive writes
- Denormalization must not weaken authorization, audit correctness, or data consistency
- Performance shortcuts cannot bypass RLS, permission checks, or audit requirements
- Any optimization that trades correctness for speed requires explicit approval and documented risk acceptance

---

## Database Change Control

**Mandatory Rules:**

- Any new table, index, or query pattern on critical paths requires performance review
- Any RLS policy change requires benchmark review on realistic datasets
- Any migration affecting large tables requires operational impact review
- No merge if critical query plans regress beyond approved latency budget
- Query plan baselines must be maintained for critical-path queries
- Plan regressions must be reviewed before release

**Performance Review Required For:**

- New RLS policies or policy changes
- New indexes on hot tables
- Schema changes on tables > 100,000 rows
- New join patterns involving permission or audit tables
- Introduction of new recurring/scheduled queries

---

## Dependencies

- [Performance Strategy](performance-strategy.md)
- [Caching Strategy](caching-strategy.md)
- [Architecture Overview](../01-architecture/architecture-overview.md)
- [Authorization Security](../02-security/authorization-security.md)

## Used By / Affects

All modules that interact with the database: auth, RBAC, user-management, admin-panel, user-panel, audit-logging, health-monitoring, jobs-and-scheduler, API.

## Risks If Changed

HIGH — database performance rules affect every module, authorization enforcement, audit integrity, and system stability.

## Related Documents

- [Performance Strategy](performance-strategy.md)
- [Caching Strategy](caching-strategy.md)
- [Jobs and Scheduler](../04-modules/jobs-and-scheduler.md)
- [Audit Logging](../04-modules/audit-logging.md)
- [RBAC Module](../04-modules/rbac.md)
- [Security Architecture](../02-security/security-architecture.md)
