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

## Query Plan Stability and Regression Control

### Plan Baseline Enforcement

- Critical-path queries must have **baseline query plans stored** (captured via `EXPLAIN (ANALYZE, BUFFERS)`)
- Baselines must be refreshed after major schema changes, index additions, or PostgreSQL upgrades
- Periodic plan comparison required (minimum: weekly for critical queries)

### Regression Detection

Auto-detect and flag the following plan changes:

- Index scan → sequential scan regression
- Join strategy changes (nested loop ↔ hash join ↔ merge join)
- Row estimate drift > 10x from actual
- Cost estimate increase > 2x from baseline

**Rules:**

- Plan regression on a critical query = **release blocker** until reviewed
- Regressions caused by statistics drift must trigger immediate `ANALYZE`
- Regressions caused by data growth must trigger index or partitioning review

---

## Statistics and Vacuum Governance

### Statistics Management

- `ANALYZE` must run regularly on high-change tables (at minimum after bulk operations)
- Stale statistics (> 24h on hot tables) must trigger alert
- Custom statistics targets may be set for columns with skewed distributions
- Statistics health must be monitored as part of DB observability

### Vacuum Governance

- Auto-vacuum thresholds must be monitored and tuned for hot tables
- Tables with high write churn must have aggressive vacuum settings:
  - Lower `autovacuum_vacuum_threshold`
  - Lower `autovacuum_vacuum_scale_factor`
- Vacuum lag (dead tuple accumulation) must be monitored

### Required Signals

| Signal | Warning | Critical |
|--------|---------|----------|
| Statistics staleness (hot tables) | > 12h | > 24h |
| Vacuum lag (dead tuples) | > 100,000 | > 1,000,000 |
| Autovacuum frequency (hot tables) | < 1/hour | < 1/day |
| Transaction ID wraparound proximity | > 50% | > 75% |

---

## Partitioning Strategy

High-growth tables must be evaluated for partitioning:

| Table | Growth Pattern | Partitioning Trigger | Strategy |
|-------|---------------|---------------------|----------|
| `audit_logs` | Continuous append | > 10M rows or > 10GB | Time-based (monthly) |
| `health_metrics` | Continuous append | > 5M rows or > 5GB | Time-based (weekly/monthly) |
| `job_executions` | High churn | > 5M rows | Time-based + status |

**Rules:**

- Tables expected to exceed thresholds must have partitioning plan documented before reaching trigger
- Partition pruning must be verified in query plans (queries must include partition key in WHERE)
- Archive partitions may be detached rather than deleted
- Partitioning changes require migration safety review

---

## Query Timeout and Kill Policy

### Execution Time Limits

| Context | Warning | Hard Kill |
|---------|---------|-----------|
| Hot-path queries (auth, permission, session) | 500ms | 2s |
| Standard API queries | 1s | 5s |
| Admin/search queries | 3s | 10s |
| Background/job queries | 10s | 60s |
| Reporting/export queries | 30s | 300s (async only) |

**Rules:**

- `statement_timeout` must be configured per connection context where possible
- Queries exceeding warning threshold must be logged and flagged
- Queries exceeding hard kill threshold must be terminated
- Repeatedly killed queries must create Action Tracker entries
- Long-running analytical queries must be routed to async job system

---

## Materialization Strategy

### When to Materialize

- Queries that compute aggregates across > 100,000 rows and run frequently (> 1/min)
- Dashboard summary data that doesn't require real-time freshness
- Permission/role resolution caches for complex hierarchies

### Refresh Strategies

| Strategy | Use When | Freshness |
|----------|----------|-----------|
| **Scheduled** | Predictable staleness acceptable | Minutes to hours |
| **Event-driven** | On relevant data change | Near real-time |
| **On-demand** | Infrequent access, expensive computation | Variable |

**Rules:**

- Every materialized view must have a defined refresh strategy and owner
- Refresh must not block hot-path queries
- Staleness must be tracked and surfaced in observability
- Materialized views must not bypass RLS — downstream access must still be permission-scoped

---

## Data Access Layer Consistency

- All database access must follow standardized query patterns through a shared data access layer
- No raw/unreviewed SQL queries in critical paths
- Query builders/ORM patterns must be consistent across modules
- Direct DB access bypassing the access layer is prohibited unless explicitly justified (e.g., migrations, one-time scripts)
- Access layer must enforce: parameterized queries, column selection (no `SELECT *`), and result set limits

---

## Cross-Table Join Complexity Limits

| Path Type | Max Join Depth | Rule |
|-----------|---------------|------|
| Hot path (auth, session, permission) | 2 tables | No exceptions |
| Standard API | 3 tables | Must use indexed join keys |
| Admin/search | 4 tables | Must be justified |
| Reporting/analytics | Unlimited | Must use precomputed structures or async |

**Rules:**

- All joins must use indexed join keys
- Join fan-out must be estimated and bounded
- Queries exceeding complexity limits must be refactored or moved to materialized views
- Self-joins on large tables require explicit justification

---

## Hot vs Cold Data Separation

### Enforcement Rules

- Hot operational tables must **not** scan historical/archived data in normal operation
- Historical data must be logically or physically separated:
  - Partition detachment
  - Archive tables
  - Separate schemas
- Queries on hot tables must include time-bounding or status filtering to exclude cold data
- Cold data access must use dedicated query paths with relaxed latency budgets
- Mixed hot/cold queries are prohibited on critical paths

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

## Global Query Cost Budgeting

Beyond latency, queries must be evaluated for resource cost:

- **CPU cost**: queries with high computational overhead must be optimized or offloaded
- **IO cost**: queries causing excessive disk reads must use indexes or caching
- **Row processing cost**: queries processing > 100,000 rows on hot paths must be refactored

**Rules:**

- High-cost queries (by `EXPLAIN` cost estimate) must be flagged even if they meet latency targets
- Repeatedly expensive queries must be reviewed for materialization or caching
- Cost budgets must consider concurrent load — a "fast" query at 1 QPS may be expensive at 1000 QPS

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
| Statistics staleness (hot tables) | > 12h | > 24h |
| Vacuum lag (dead tuples) | > 100K | > 1M |
| Query plan regressions | Any on critical path | Sustained regression |

### Rules

- All signals must be collected and available in dashboards
- Threshold breaches create alerts
- Sustained warning-level signals (> 24h) must create Action Tracker entries
- Critical signals must trigger immediate investigation

---

## Action Tracker Integration

The following **MUST** create Action Tracker entries:

| Trigger | Severity | Target Resolution |
|---------|----------|-------------------|
| Slow query spike (sustained) | HIGH | 24h |
| Query plan regression on critical path | HIGH | 24h |
| Vacuum/statistics issues on hot tables | MEDIUM | 48h |
| Index inefficiency detected | MEDIUM | 1 week |
| Sustained lock contention | HIGH | 24h |
| Connection pool saturation (critical) | CRITICAL | 4h |
| Deadlock pattern detected | HIGH | 24h |
| Table growth exceeding forecast | MEDIUM | 1 week |
| Query timeout kills (repeated) | HIGH | 24h |

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
