# Performance Strategy

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-09

## Purpose

Defines performance targets, optimization strategies, governance, degradation policies, observability requirements, and capacity planning for all system layers.

## Scope

Frontend rendering, API response times, database queries, asset loading, authorization/RLS performance, caching safety, degradation behavior, load testing, performance change control, trace-level budget enforcement, multi-tenant scale guarantees, and incident classification.

## Enforcement Rule (CRITICAL)

- Performance targets are **mandatory**, not aspirational
- No feature may merge if it materially regresses critical-path performance without an approved exception
- Performance budgets are enforced at CI, load test, and runtime monitoring layers
- Breach of critical thresholds must trigger alerts and block release where applicable
- Every request on a critical path must emit per-layer trace data for budget enforcement
- Any unmonitored critical path is an **INVALID** implementation

## Performance Governance

Every performance metric must have:

| Attribute | Description |
|-----------|-------------|
| **Owner** | Module or team responsible |
| **Warning threshold** | Triggers investigation |
| **Critical threshold** | Triggers alert + blocks release |
| **Enforcement point** | CI, runtime monitoring, load test, or synthetic probe |
| **Breach action** | Investigate, rollback, or hotfix |

Metrics that block release:
- Core Web Vitals (LCP, CLS, INP)
- Critical API p95 latency
- Bundle size budget
- Database p95 query latency

## Workload Classification

Not all paths require the same targets. Performance targets are classified by workload:

| Workload Class | Examples | Latency Sensitivity | Optimization Priority |
|---------------|---------|--------------------|-----------------------|
| **Auth / Session** | Login, MFA, session restore, token refresh | Critical | Highest |
| **Public pages** | Landing, marketing, public content | High (SEO-impacting) | High |
| **Authenticated user flows** | Dashboard, profile, settings | High | High |
| **Admin panel** | User management, role assignment, config | Medium | Medium |
| **Background jobs** | Health checks, audit cleanup, metrics | Low (latency), High (reliability) | Medium |
| **Reporting / Export** | Audit export, analytics views | Tolerant | Lower |
| **Real-time features** | Live health dashboard, notifications | Medium | Medium |

## Hot Path vs Cold Path Separation

### Hot Paths (Strictest Budgets)

- Login + MFA verification
- Session restore / token refresh
- Dashboard initial load
- Permission evaluation
- Health check endpoints

Rules for hot paths:
- **Zero unnecessary dependencies** in execution chain
- **Minimal abstraction layers** — direct, optimized code
- **No lazy initialization** in request path
- **Pre-warmed** where applicable (see Cold Start Strategy)

### Cold Paths (Relaxed Budgets)

- Audit export
- Admin batch operations
- Analytics / reporting views
- Bulk data operations

Cold paths may use higher latency budgets but must still respect timeout and degradation policies.

## Critical User Journeys

The following flows receive **highest optimization priority**:

1. Login + MFA verification
2. Session restore / token refresh
3. Dashboard initial load
4. Permission-based navigation resolution
5. Admin role/permission changes
6. Health dashboard load + freshness
7. Audit log search and filter

## p99-First Optimization Philosophy

For **critical flows** (auth, dashboard, admin actions):
- Optimization priority is **p99, not p95**
- p99 regressions are treated as **critical** even if p95 is within target
- Load tests must validate p99 under realistic concurrency
- p99 outlier analysis required: identify and eliminate tail latency causes

## Performance Targets

### Frontend

| Metric | Target | Warning | Critical | Enforcement |
|--------|--------|---------|----------|-------------|
| First Contentful Paint (FCP) | < 1.5s | > 1.5s | > 2.5s | CI + synthetic monitoring |
| Largest Contentful Paint (LCP) | < 2.5s | > 2.5s | > 4.0s | CI + synthetic monitoring |
| Cumulative Layout Shift (CLS) | < 0.1 | > 0.1 | > 0.25 | CI + synthetic monitoring |
| Interaction to Next Paint (INP) | < 200ms | > 200ms | > 500ms | Runtime monitoring |
| Route transition time (SPA) | < 300ms | > 300ms | > 800ms | Runtime monitoring |
| Bundle size (initial) | < 200KB gzipped | > 200KB | > 300KB | CI (blocks merge) |
| Route chunk budget | < 50KB gzipped | > 50KB | > 100KB | CI |
| JS errors (rate) | < 0.1% | > 0.1% | > 1% | Runtime monitoring |

### API

| Endpoint Class | p50 | p95 | p99 | Enforcement |
|---------------|-----|-----|-----|-------------|
| Auth / session (critical) | < 100ms | < 300ms | < 500ms | Load test + runtime |
| Standard reads | < 150ms | < 400ms | < 700ms | Runtime monitoring |
| Writes | < 200ms | < 500ms | < 800ms | Runtime monitoring |
| Search / filter | < 250ms | < 600ms | < 1000ms | Runtime monitoring |
| Admin / audit endpoints | < 300ms | < 800ms | < 1500ms | Runtime monitoring |
| Health / internal | < 50ms | < 100ms | < 200ms | Synthetic probe |

| Meta-Metric | Target | Warning | Critical |
|-------------|--------|---------|----------|
| Error rate (per endpoint) | < 0.5% | > 0.5% | > 2% |
| Error budget (critical services) | ≥ 99.5% success/month | < 99.5% | < 99.0% |

### Database

| Metric | Target | Warning | Critical | Enforcement |
|--------|--------|---------|----------|-------------|
| Query latency (p95) | < 100ms | > 100ms | > 250ms | Runtime + load test |
| Query latency (p99) | < 200ms | > 200ms | > 500ms | Runtime monitoring |
| Slow query threshold | > 200ms | — | — | Runtime alert |
| Lock wait time | < 50ms | > 50ms | > 200ms | Runtime monitoring |
| Connection saturation | < 70% pool | > 70% | > 90% | Runtime monitoring |

### Authorization / RLS

| Metric | Target | Warning | Critical |
|--------|--------|---------|----------|
| Permission evaluation latency | < 10ms | > 10ms | > 50ms |
| RLS overhead per query | < 20ms | > 20ms | > 50ms |
| Admin dashboard load | < 2s | > 2s | > 4s |
| Health dashboard freshness | ≤ 3 min | > 3 min | > 5 min |

## Layered Performance Budgets

For a 500ms API budget, time allocation by layer:

| Layer | Budget | Notes |
|-------|--------|-------|
| Network / TLS | 50ms | CDN + edge proximity |
| Auth / validation / authorization | 50ms | Token verify + permission check |
| Service logic | 100ms | Business rules, orchestration |
| Database (query + RLS) | 150ms | Including RLS evaluation |
| Audit emission | 30ms | Async where possible |
| Serialization / response | 20ms | JSON encoding |
| Buffer | 100ms | Headroom for variance |

For frontend render budget (LCP < 2.5s):

| Layer | Budget |
|-------|--------|
| DNS + TLS + TTFB | 500ms |
| HTML parse + critical CSS | 300ms |
| JS download + parse | 400ms |
| Hydration / mount | 500ms |
| Data fetch + render | 500ms |
| Buffer | 300ms |

## End-to-End Trace Budget Enforcement

Every request on a critical path **must** emit a structured trace with per-layer timing:

| Trace Span | Required |
|-----------|----------|
| `network` | Time in transit / TLS |
| `auth` | Token verification |
| `authorization` | Permission evaluation |
| `service_logic` | Business rules |
| `database` | Query execution (including RLS) |
| `audit` | Audit event emission |
| `serialization` | Response encoding |

Rules:
- If **any layer exceeds its budget** → automatically flagged in monitoring
- Trace data feeds into p95/p99 per-layer dashboards
- Budget violations aggregated for trend analysis
- Persistent per-layer violations create action tracker items

## Cold Start vs Warm Path Strategy

Relevant for edge functions, serverless, and Supabase functions:

| Path | Latency Budget | Strategy |
|------|---------------|----------|
| **Cold start** | ≤ 1s additional | Acceptable only for non-critical paths |
| **Warm path** | Standard targets apply | Must meet published p95/p99 targets |

Rules:
- Critical endpoints (auth, health) must use **pre-warming** where platform supports it
- Heavy initialization **must not** occur in request path — use lazy singleton or boot-time init
- Cache initialization data where safe (DB connection pools, permission caches)
- Cold-start frequency tracked in telemetry — repeated cold starts on hot paths = critical issue
- If cold starts cause p99 violations on critical paths → architectural mitigation required

## Multi-Tenant Scale Guarantees

All performance benchmarks **must** be validated at multiple tenant sizes:

| Tenant Profile | Data Volume | Required |
|---------------|-------------|----------|
| Small | < 100 users, < 10K records | Baseline |
| Medium | 100–1,000 users, 10K–100K records | Standard load test |
| Large (realistic max) | 1,000+ users, 100K+ records | Stress test |

Rules:
- **No query may degrade beyond target** as tenant size grows
- RLS performance must be tested at large-tenant scale
- Index effectiveness validated at each tier
- Pagination and filter performance validated at large scale
- If any target is breached at large-tenant scale → must be resolved before release

## Database and Query Performance Rules

- All queries **must** be indexed to access pattern — no full table scans on production data
- **No N+1 queries** — batch or join at query level
- Every new endpoint requires **query plan review** for critical paths
- p95 and p99 query latency tracked per endpoint
- Slow queries (> 200ms) logged and alerted
- Query plans reviewed for critical paths before release
- RLS performance **must** be benchmarked on realistic tenant-sized datasets
- Tenant scoping / RLS queries must not degrade beyond target as data grows

## Authorization and RLS Performance Rules

- Permission evaluation **must** be centralized and cacheable where safe
- No repeated permission recalculation within a single request
- RLS queries benchmarked on realistic data volumes
- Audit writes must not materially degrade core request latency (async emission preferred)
- RBAC permission resolution caching must have:
  - Bounded TTL
  - Invalidation on permission change
  - Scoped cache keys (no cross-user leakage)

## Caching Safety and Invalidation Rules

- Cache **only** non-sensitive or properly scoped data
- Permission-sensitive responses require **scoped cache keys** (user + permission set)
- No cache that can leak tenant or user data across boundaries
- Cache invalidation rules **must** be defined before any cache is introduced
- RBAC permission cache:
  - TTL ≤ 60 seconds
  - Invalidated on role/permission change events
- Static asset caching: aggressive (content-hash based)
- API response caching: conservative, opt-in per endpoint

## Frontend Optimization Strategies

- Code splitting by route (`React.lazy`)
- Tree shaking (Vite default)
- Image optimization (lazy loading, WebP, responsive sizes)
- Minimize re-renders (`React.memo`, `useMemo`, `useCallback` where measured)
- Skeleton/loader states for async data (layout shift controlled)
- Low-priority widgets defer loading
- Charts, editors, and heavy tools lazy-loaded only
- Admin-only code excluded from public bundle

## Frontend Degradation Policy

Under stress or slow connections:
- Skeletons/loaders allowed, but CLS must stay within budget
- Dashboards may load summary first, details second (progressive)
- Real-time features can downgrade to polling under stress
- Non-critical charts and widgets must not block core interaction
- Low-priority analytics/tracking deferred under degradation
- Error boundaries must prevent single-component failure from breaking page

## API Optimization Strategies

- Minimize round trips (batch queries, compound responses)
- Use real-time subscriptions only where justified
- Paginate all list endpoints
- Streaming / chunked responses for large exports

## Backend Degradation and Resilience Policy

Under load or dependency stress:
- **Overload protection**: request rate limiting per endpoint class
- **Request timeouts**: enforced at API layer (no unbounded waits)
- **Queue / backpressure handling**: heavy operations offloaded to job system
- **Concurrency caps**: heavy endpoints (export, search) limited
- **Circuit breakers**: external service failures trip breaker after threshold
- **Fail-fast**: saturated dependencies return fast error, not slow timeout
- **Non-critical work**: offloaded to background jobs, not blocking request path
- **Graceful degradation order**: analytics → reporting → admin features → user features → auth (last to degrade)

## Observability and Telemetry

### Monitoring Model

Two monitoring modes are **both required**:

| Mode | Purpose | Characteristics |
|------|---------|----------------|
| **Synthetic monitoring** | Controlled probes against known endpoints | Consistent baseline, detects infrastructure issues |
| **Real User Monitoring (RUM)** | Captures real-world user experience | Real variability, geographic spread, device diversity |

Rules:
- Both must be active for critical paths
- Discrepancies between synthetic and RUM must be **investigated** (indicates environmental or geographic issues)

### Frontend (Required)

| Signal | Purpose |
|--------|---------|
| FCP, LCP, CLS, INP | Core Web Vitals |
| JS error rate | Client stability |
| Route transition time | SPA navigation performance |
| Bundle size per route | Asset governance |

### API (Required)

| Signal | Purpose |
|--------|---------|
| p50 / p95 / p99 latency (per endpoint) | Response time tracking |
| Error rate (per endpoint) | Reliability |
| Request volume | Capacity tracking |
| Timeout rate | Saturation indicator |
| Per-layer trace spans | Budget enforcement |

### Database (Required)

| Signal | Purpose |
|--------|---------|
| Query latency (p50/p95/p99) | Query performance |
| Slow query count | Degradation detection |
| Lock wait time | Contention indicator |
| Connection pool utilization | Saturation |

### Authorization (Required)

| Signal | Purpose |
|--------|---------|
| Permission evaluation latency | RBAC overhead |
| Cache hit rate | Caching effectiveness |

### Jobs (Required)

| Signal | Purpose |
|--------|---------|
| Queue delay | Backpressure indicator |
| Execution time | Job performance |
| (Refer to [Jobs Module](../04-modules/jobs-and-scheduler.md) for full telemetry) | |

## Cross-Region and Network Variability

> Note: Even if not multi-region today, targets must account for network reality.

- Performance targets must be validated from **representative geographic regions**
- CDN edge behavior must be verified for static assets
- Network variability (latency jitter, packet loss) must be factored into p99 analysis
- Synthetic probes should run from multiple locations
- If multi-region is activated: per-region targets and monitoring required

## Performance Incident Classification

| Severity | Definition | Example | Response |
|----------|-----------|---------|----------|
| **P0** | System unusable | Auth failure, major latency spike (> 5x target) | Immediate response, rollback if needed |
| **P1** | Critical degradation | Dashboard unusable, p99 > critical for auth | 1-hour response, hotfix path |
| **P2** | Partial degradation | Admin panel slow, export timeouts | 4-hour response, investigation |
| **P3** | Minor regression | p95 slightly above warning, non-critical path | Next sprint, tracked |

Rules:
- Every P0/P1 incident must:
  - Create action tracker item
  - Include root cause analysis
  - Include prevention steps
- P2 incidents tracked in action tracker with standard follow-up
- P3 incidents tracked in backlog

## Action Tracker Integration

The following performance events **must** automatically create action tracker entries:

| Trigger | Severity | Owner | Target Resolution |
|---------|----------|-------|-------------------|
| SLO breach (critical service) | High | Service owner | 4 hours |
| p99 regression on critical flow | High | Module owner | 4 hours |
| DB slow query spike | Medium | Backend owner | 24 hours |
| Bundle size violation | Medium | Frontend owner | Next sprint |
| Error rate > critical threshold | High | Service owner | 4 hours |
| Sustained warning-level degradation (> 7 days) | Medium | Module owner | Next sprint |
| Per-layer trace budget violation (persistent) | Medium | Layer owner | 24 hours |
| Cold start causing p99 violation | High | Platform owner | 24 hours |

## Cost vs Performance Tradeoff Policy

Performance improvements must be evaluated against:

| Factor | Consideration |
|--------|--------------|
| **Infrastructure cost** | Additional compute, storage, CDN, caching layers |
| **Complexity cost** | Code complexity, operational burden, debugging difficulty |
| **Operational risk** | New failure modes, monitoring gaps |

Rules:
- Performance optimizations that increase infra cost > 20% require explicit approval
- Complexity-adding optimizations must demonstrate measurable user impact
- Premature optimization remains forbidden — measure first, optimize where it matters
- Cost-performance tradeoff decisions documented in approved decisions log

## Load Testing and Capacity Planning

### Load Test Policy

- Load test **required** before major releases
- Stress test **required** for critical API endpoints (auth, admin actions)
- Realistic tenant/user-size test datasets mandatory (see Multi-Tenant Scale Guarantees)
- Concurrency scenarios for admin and user panels
- Recovery test after induced degradation (verify system returns to healthy state)
- Performance regression test: compare against previous baseline

### Capacity Planning

- Define expected user growth assumptions (document in planning docs)
- Define expected tenant data size assumptions
- Thresholds for architectural escalation:

| Trigger | Action |
|---------|--------|
| DB p95 > warning for 7 days | Add read replicas or optimize queries |
| Connection pool > 80% sustained | Scale pool or add connection pooler |
| Bundle size approaching critical | Audit dependencies, split routes |
| API error rate > 1% sustained | Investigate, scale, or circuit-break |
| Cache miss rate > 50% | Review cache strategy and TTLs |
| Queue depth growing unbounded | Scale workers or add backpressure |

## Dependency and Bundle Governance

- No large dependency added without **justification and size impact review**
- Third-party scripts reviewed for **performance cost and security**
- Route-level chunk budget enforced (< 50KB gzipped)
- Admin-only code **must not** be included in public bundle
- Charts, rich editors, and heavy tools: **lazy-loaded only**
- Dependency additions require performance-impact assessment

## Performance Change Control

Performance-impact assessment **required** for:
- New dependencies (bundle size + runtime cost)
- New polling or real-time subscriptions
- New global context or state providers
- New database joins or complex queries
- New audit-heavy workflows
- New background job schedules

No merge allowed if:
- Critical-path performance regresses beyond warning threshold
- Bundle size exceeds budget
- No approved exception documented

## Dependencies

- [Architecture Overview](../01-architecture/architecture-overview.md)
- [Database Performance](database-performance.md)
- [Caching Strategy](caching-strategy.md)
- [Jobs and Scheduler](../04-modules/jobs-and-scheduler.md) — job performance telemetry
- [Authorization Security](../02-security/authorization-security.md) — permission evaluation performance
- [Action Tracker](../06-tracking/action-tracker.md) — performance incident follow-up

## Used By / Affects

All modules with UI, API, data operations, or background processing.

## Risks If Changed

HIGH — loosening targets degrades user experience, reliability, and operational trust. Incorrect caching rules can cause security breaches. Removing trace enforcement eliminates budget accountability.

## Related Documents

- [Database Performance](database-performance.md)
- [Caching Strategy](caching-strategy.md)
- [Health Monitoring](../04-modules/health-monitoring.md)
- [Jobs and Scheduler](../04-modules/jobs-and-scheduler.md)
- [System Design Principles](../01-architecture/system-design-principles.md)
- [Action Tracker](../06-tracking/action-tracker.md)
