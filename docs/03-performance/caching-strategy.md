# Caching Strategy

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-08

## Purpose

Defines caching governance, safety boundaries, invalidation rules, and operational controls for a permission-driven, RLS-enforced, audit-heavy, multi-tenant system.

## Scope

All caching layers: CDN/edge, API response, application state (TanStack Query), service worker, and precomputed/materialized data.

## Enforcement Rule (CRITICAL)

- No cache may weaken authorization, tenant isolation, audit correctness, or freshness requirements
- Any cache without documented **owner, scope, TTL, invalidation strategy, and risk classification** is an **INVALID** implementation
- Security-sensitive data may **not** rely on TTL alone for correctness
- Cache changes on critical paths require review
- No cross-tenant shared cache for protected data — **no exception**
- Cache corruption or stale security-sensitive cache must be treated as a **security incident**

---

## Cache Classification Matrix

| Class | Allowed Layers | TTL Range | Invalidation | Stale OK | CDN OK |
|-------|---------------|-----------|-------------|----------|--------|
| **Public Static** (assets, fonts, images) | CDN, browser, SW | Long (days–years) | Deploy/version | Yes | Yes |
| **Public Dynamic** (landing page content) | CDN, browser | Short–medium (1m–1h) | TTL + event | Yes (bounded) | Yes |
| **Tenant-Scoped Shared** (org settings, config) | App memory, TanStack | Short (30s–5m) | Mutation + event | Limited | No |
| **User-Scoped Private** (profile, preferences) | TanStack, browser | Short (1m–5m) | Mutation | Limited | No |
| **Permission-Sensitive** (role-gated views, filtered data) | TanStack only | Very short (≤ 60s) | Role/permission change + mutation | No | No |
| **Session/Auth-Sensitive** (tokens, session state) | Memory only | Minimal (≤ 30s) or none | Logout, revoke, expiry | No | No |
| **Derived/Aggregated** (dashboard summaries, analytics) | TanStack, materialized | Medium (1m–15m) | Scheduled refresh + event | Yes (bounded) | No |
| **Offline-Capable** (approved offline data) | Service worker | Versioned | Version change, logout | Yes (with freshness indicator) | N/A |

**Rules:**
- Every cached resource must be classified before implementation
- Classification determines all caching parameters — no ad hoc decisions
- Misclassification (e.g., treating permission-sensitive data as public) is a **security violation**

---

## Cache Key Governance

Cache keys must encode all scoping dimensions to prevent leakage or collision:

### Required Key Components

| Component | When Required |
|-----------|--------------|
| Module/resource type | Always |
| Resource identifier | Always |
| Tenant/org scope | Tenant-scoped or higher sensitivity |
| User scope | User-scoped private data |
| Query params (filter, sort, page) | List/search endpoints |
| Permission/policy version | Permission-sensitive data |
| Locale | Localized content |
| Data version/ETag | Versioned resources |

### Key Format

```
[module]:[resource]:[id]:[tenant]:[user]:[params_hash]:[perm_version]
```

**Rules:**
- No cache key may omit a required scoping dimension for its classification
- Key design must be reviewed for permission-sensitive and tenant-scoped caches
- Ambiguous or under-scoped keys are prohibited

---

## Tenant / User / Permission Boundary Rules

### Tenant Isolation

- Tenant-scoped responses must include tenant identifier in cache key
- No shared cache entry may serve data across tenant boundaries
- Tenant membership changes must invalidate all tenant-scoped caches for affected user

### User Isolation

- User-private data must include user identifier in cache key
- No user cache may be readable by another user's context

### Permission Boundaries

- Permission-dependent data must include permission context or version marker in cache key
- Role/permission changes must invalidate **all** dependent caches immediately (not just on TTL expiry)
- RLS-protected query results must never be cached in a way that can be replayed across principals
- Permission evaluation results may be cached with bounded TTL (≤ 60s) and immediate invalidation on change

---

## Consistency Model

### Strong Consistency Required

The following must **never** serve stale data:

- Auth/session state
- Permission/role resolution
- Active security policies
- Critical configuration (feature flags affecting access)
- Destructive admin action results (deactivation, role revoke)

**Rule:** These resources use memory-only cache with immediate invalidation or no cache at all.

### Eventual Consistency Allowed

The following may tolerate bounded staleness:

| Resource | Max Staleness | Freshness Indicator Required |
|----------|--------------|------------------------------|
| Dashboard summaries | 5 minutes | Yes |
| Analytics/charts | 15 minutes | Yes |
| Non-critical config | 5 minutes | No |
| Public content | 1 hour | No |
| Health dashboard | 1 minute | Yes |

**Rule:** Eventual consistency must have a defined maximum staleness bound — no unbounded staleness.

---

## Invalidation Governance

### Invalidation Triggers

| Trigger | Caches Affected | Method |
|---------|----------------|--------|
| Mutation success | Resource-specific | Immediate query invalidation |
| Role/permission change | All permission-sensitive caches for user | Event-driven, immediate |
| Tenant membership change | All tenant-scoped caches for user | Event-driven, immediate |
| Logout / session revoke | All user caches | Immediate purge |
| Config change | Config-dependent caches | Event-driven |
| Deployment / version change | All caches with version-sensitive payloads | Cache-bust via version key |
| Backfill / reconciliation | Affected aggregates/summaries | Event-driven |
| Archive / retention operation | Affected summaries/counts | Event-driven |

### Invalidation Rules

- Invalidation must be **event-driven** where possible
- TTL is a **fallback safety net**, not the primary correctness control
- Cascading invalidation must be bounded (no unbounded invalidation storms)
- Failed invalidation must be retried or flagged — silent failure is prohibited
- Invalidation latency for permission-sensitive caches must be < 5 seconds

---

## Error and Negative Caching Policy

### Negative Caching (404 / Empty Results)

- 404/empty results may be negative-cached only for **public, non-sensitive** resources
- Negative cache TTL must be short (≤ 30s)
- Auth failures and permission denials must **never** be cached broadly

### Error Response Caching

| Response Type | Cacheable | Rule |
|--------------|-----------|------|
| 2xx success | Yes | Per classification |
| 304 Not Modified | Yes | Revalidation pattern |
| 404 Not Found (public) | Yes (short TTL) | ≤ 30s, non-sensitive only |
| 401/403 auth/permission errors | **No** | Never cache broadly |
| 429 rate limit | **No** | Except explicit retry-after handling |
| 5xx server errors | **No** | Except tightly controlled stale-if-error fallback |

---

## Stale-While-Revalidate and Stale-If-Error Policy

### Stale-While-Revalidate

- Allowed **only** for non-sensitive, non-destructive read paths
- **Prohibited** for auth, permission, session, or security-critical views
- Maximum stale window must be defined per resource class
- Background revalidation must not block user interaction

### Stale-If-Error

- Allowed for low-risk dashboard summaries and config with defined freshness limit
- **Prohibited** for permission-sensitive or auth-dependent data
- Stale display must show visible freshness indicator if user-facing accuracy matters
- Maximum stale-if-error window: **5 minutes** for dashboards, **0** for security-sensitive

---

## Optimistic Update and Conflict Rules

### Optimistic Updates

- Allowed only for low-risk user actions with immediate rollback path
- Critical mutations (role changes, deactivation, permission updates) require **authoritative server confirmation** before UI update
- Rollback behavior required on mutation failure — UI must revert to server state

### Conflict Resolution

- Concurrent mutation conflicts on shared resources must have defined resolution strategy
- Last-write-wins acceptable only for non-critical, user-private data
- Shared/admin resources require conflict detection (e.g., version/ETag check)
- Conflict resolution strategy must be documented per resource type

---

## API Cache Header and CDN Governance

### Required Headers

| Header | Rule |
|--------|------|
| `Cache-Control` | Must be explicitly set for every API response — no implicit defaults |
| `Cache-Control: private` | Required for all authenticated/tenant-scoped responses |
| `Cache-Control: no-store` | Required for auth, session, permission responses |
| `Cache-Control: public` | Only for explicitly public, non-sensitive resources |
| `ETag` | Required for resources supporting conditional requests |
| `If-None-Match` | Client must send for ETag-enabled resources |
| `Vary` | Required for responses that differ by `Authorization`, tenant, locale, or user context |
| `Last-Modified` | Recommended for content with meaningful modification timestamps |

### CDN Rules

- CDN caching **prohibited** for authenticated or protected API responses
- CDN caching allowed only for explicitly public resources (assets, landing pages, public content)
- `Vary` headers required where response representation differs by any dimension
- CDN cache purge must be available for emergency invalidation
- CDN configuration changes require review

---

## TanStack Query (React Query) Rules

### Stale Time by Data Class

| Data Class | Stale Time | gcTime | Refetch Strategy |
|------------|-----------|--------|-----------------|
| Auth/session | 0 (always fresh) | 5m | On focus + interval (30s) |
| Permission/role | ≤ 30s | 5m | On focus + invalidation event |
| User profile | 1m | 10m | On mutation + focus |
| Dashboard data | 2m | 15m | On focus + interval (2m) |
| Config/settings | 2m | 30m | On mutation |
| Analytics | 5m | 30m | Interval (5m) |
| Public content | 10m | 1h | On focus |

**Rules:**
- No blanket stale time for all queries — stale time must match data classification
- Query keys must include all scoping dimensions (tenant, user, filters, permission version)
- Permission/session/security-sensitive queries must use short stale time or `staleTime: 0`
- Mutations must invalidate related queries explicitly — no reliance on stale time alone
- Global query error handling must not cache error responses

---

## Stampede and Thundering Herd Protection

### Required Controls

- **Request coalescing**: identical in-flight fetches must be deduplicated (TanStack Query handles this for client-side)
- **Jittered TTL**: cache entries should use randomized TTL offset (±10%) to prevent synchronized expiry
- **Background refresh**: hot keys should refresh before expiry, not after
- **Single-flight refresh**: only one refresh request per cache key at a time
- **Lock/coalescing for server-side**: expensive recomputation must use mutex or coalescing pattern

### Rules

- Stampede protection required for any cache serving > 10 requests/second
- Hot key detection must be part of cache observability
- Stampede events must be logged and tracked

---

## Prefetch and Preload Governance

- Prefetch only high-probability next routes/data (e.g., likely navigation targets)
- Never prefetch sensitive data for unauthorized contexts
- Prefetch budget: maximum **3 concurrent prefetch requests** at any time
- Prefetch must not starve critical interactive traffic
- Prefetch must respect data classification — no prefetching permission-sensitive data without active authorization
- Prefetch results must follow same cache key and invalidation rules as regular fetches

---

## Service Worker and Offline Governance

- Service worker caching allowed only with explicit versioning and invalidation rules
- No sensitive authenticated API responses stored offline unless explicitly approved and access-controlled
- Logout must clear **all** sensitive offline caches immediately
- Version mismatch between service worker and app must trigger full cache refresh
- Offline-cached data must show clear staleness indicator to users
- Service worker updates must not serve stale security-sensitive content

---

## Cache Consistency Under Concurrency

### Write Model

- Cache updates must follow **write-through** or **write-after-invalidate** model
- Concurrent mutations must serialize updates OR use version checks (ETag/version)
- "Last write wins" allowed **only** for non-critical, user-private data
- Critical data (permissions, roles, config) must use **version-aware updates**

### Race Condition Prevention

- Mutations must invalidate cache **before** returning success to client
- Stale cache overwrites from slow responses must be prevented via version ordering
- Optimistic updates must be rolled back if server version conflicts

---

## Global Cache Versioning Strategy

All cache keys must include a **global cache version** prefix:

```
v{N}:module:resource:id:tenant:user:params_hash
```

**Rules:**

- Global cache version is bumped on:
  - Schema changes affecting cached data shapes
  - API response format changes
  - Permission model structural changes
  - Major deployments with incompatible payloads
- Version bump = instant global invalidation of all prior-version entries
- Version is managed centrally — no per-module version drift
- Old-version cache entries must be treated as misses, not served stale

---

## Cache Warmup and Prepopulation

### Strategy

- Critical caches must support **pre-warming** after deployment or cold start:
  - Permission resolution for active users
  - Config/feature flags
  - Dashboard summary data
- Cache warm jobs must follow **Jobs module** governance (idempotent, observable, backpressure-aware, kill-switch)

### Rules

- Warm jobs must not overwhelm source systems — rate-limited and batched
- Warm priority: permission caches > config > dashboard summaries
- Warm failure must be logged and surfaced — system must function with cold cache (degraded latency, not failure)

---

## Partial Cache Failure Handling

**Fundamental Rule:** Cache is a **performance optimization only**, never a correctness dependency.

- System must behave correctly when cache is:
  - Fully unavailable
  - Partially inconsistent
  - Returning errors
- Fallback: always to source of truth (DB/API)
- Cache failure must **degrade latency**, not **break functionality**
- Cache layer errors must not propagate as user-facing errors
- Cache unavailability must be detected and reported to health monitoring

---

## Cache Storage Limits and Eviction Policy

Every cache must define storage boundaries:

| Cache Layer | Max Size | Eviction Policy | Priority Protection |
|------------|----------|----------------|-------------------|
| TanStack Query (client) | Per gcTime config | Time-based GC | N/A (managed by gcTime) |
| In-memory (server/edge) | Defined per service | LRU | Permission/auth entries protected |
| Service worker | Bounded per cache name | LRU with version sweep | Versioned entries only |
| CDN | Provider-managed | TTL-based | N/A |

**Rules:**

- High-priority entries (permissions, auth) must have shorter TTL but higher refresh priority
- Eviction of security-sensitive entries must trigger immediate re-fetch on next access
- Memory pressure alerts must feed observability (see Observability section)
- No unbounded cache growth — every cache must have a defined ceiling

---

## Sensitive Data Redaction and Security

- Cached data must contain the **minimum necessary** fields — no over-caching
- Tokens, secrets, MFA codes, and passwords must **never** be cached beyond in-memory scope
- Offline/service worker storage must not contain sensitive PII unless explicitly approved and access-controlled
- Browser localStorage/sessionStorage must not store auth tokens or permission data
- Cache entries for sensitive data must be cleared on logout, session expiry, and tab close (where applicable)

---

## Cross-Tab and Multi-Session Synchronization

### Critical Invalidations Across Tabs

The following must propagate across all open tabs/sessions:

- Logout / session revoke
- Permission/role changes
- Auth state changes
- Security-critical config changes

### Mechanisms

- **BroadcastChannel API** (preferred) for same-origin tab communication
- **Storage events** (localStorage change detection) as fallback
- **Service worker messages** for offline-capable sync

**Rules:**

- Cross-tab sync must be tested as part of auth and permission flows
- Stale tab serving old permissions after role change is a **security violation**
- Cross-tab sync failure must degrade to forced refresh on next user interaction

---

## Cache Drift Detection

### Periodic Validation

- Critical caches must be periodically validated against source of truth:
  - Permission cache: sampled validation every 5 minutes
  - Config cache: validated on each deployment
  - Dashboard data: validated against fresh query on schedule

### Drift Response

- Drift detected → immediate invalidation of affected keys
- Drift detected → alert to observability
- Persistent drift (> 3 occurrences in 24h) → Action Tracker entry
- Drift on permission/auth cache → treated as security incident

---

## Freshness SLA Enforcement

- Freshness SLA (defined in Ownership Registry) must be **monitored per resource class**
- Cache entries exceeding their freshness SLA must:
  - Trigger background refresh (if stale-while-revalidate allowed)
  - Trigger alert (if strong consistency required)
  - Never be served beyond 2x the defined SLA without forced refresh
- Freshness monitoring must be part of cache observability dashboard
- Sustained SLA breaches (> 1h) must create Action Tracker entries

---

## Cache Ownership and Lifecycle Registry

Every meaningful cache must be documented:

| Cache | Owner | Scope | TTL | Invalidation Source | Storage Layer | Risk Class | Max Size | Freshness SLA |
|-------|-------|-------|-----|-------------------|--------------|-----------|----------|--------------|
| Permission resolution | Auth module | User + role | 60s | Role/perm change event | TanStack | High | Per-user | < 60s stale |
| Dashboard summary | Dashboard module | Tenant | 5m | Scheduled + mutation | TanStack | Low | Per-tenant | < 5m stale |
| User profile | User module | User | 1m | Mutation | TanStack | Medium | Per-user | < 1m stale |
| Static assets | Frontend | Global | 1 year | Deploy version | CDN + browser | None | Bounded | N/A |
| Config/feature flags | Config module | Global/tenant | 2m | Config change event | TanStack | Medium | Small | < 2m stale |

**Rules:**
- Registry must be maintained and reviewed quarterly
- Unregistered caches on critical paths are prohibited
- Owner is responsible for invalidation correctness and observability

---

## Observability and Telemetry

### Required Cache Signals

| Signal | Warning Threshold | Critical Threshold |
|--------|------------------|-------------------|
| Hit rate (per layer) | < 70% | < 50% |
| Miss rate | > 30% | > 50% |
| Stale serve rate | > 10% | > 25% |
| Invalidation count (spikes) | > 2x baseline | > 5x baseline |
| Eviction count (pressure) | > 100/min | > 500/min |
| Cache error rate | > 1% | > 5% |
| Average item size growth | > 50% month-over-month | > 100% month-over-month |
| Hot key concentration | > 20% traffic on single key | > 40% traffic on single key |
| Stampede events | > 1/hour | > 5/hour |
| Permission-cache invalidation lag | > 5s | > 30s |
| Cache drift occurrences | > 1/day | > 5/day |
| Freshness SLA breaches | > 1% of entries | > 5% of entries |

### Rules

- All signals must be collected and dashboarded
- Sustained warning-level issues (> 24h) must create Action Tracker entries
- Critical signals must trigger immediate investigation
- Cache health must feed health monitoring module

---

## Action Tracker Integration

The following **MUST** create Action Tracker entries:

| Trigger | Severity | Target Resolution |
|---------|----------|-------------------|
| Permission-cache invalidation failure | CRITICAL | 4h |
| Cross-tenant cache leakage detected | CRITICAL | Immediate |
| Sustained low hit rate | MEDIUM | 1 week |
| Stampede events (repeated) | HIGH | 24h |
| Cache corruption detected | CRITICAL | 4h |
| Stale security-sensitive data served | CRITICAL | Immediate |
| Invalidation storm (cascading) | HIGH | 24h |
| Cache drift detected (persistent) | HIGH | 24h |
| Cache warm job failure | MEDIUM | 48h |
| Cache layer outage | HIGH | 4h |
| Invalidation lag breach (permission cache) | HIGH | 4h |
| Cache key collision/bug detected | HIGH | 24h |

---

## Relationship to Jobs / Admin / Health

- Cache health metrics must feed the **health monitoring** module
- Major invalidation failures must surface in admin/health dashboards
- Cache warm/rebuild operations must follow **Jobs module** governance (observable, retry-safe, kill-switch aware)
- Cache corruption or stale security-sensitive cache must be severity-tracked as a security incident

---

## Cache Change Control

**Mandatory Rules:**

- New cache on a critical path requires architectural review
- Any cache touching permission-sensitive or tenant-sensitive data requires **security review**
- No merge if cache design lacks documented invalidation strategy
- Cache changes must document blast radius and rollback plan
- Removal of an existing cache requires performance impact assessment

**Review Required For:**

- New TanStack Query cache with stale time > 60s on protected data
- New CDN cache rules
- Service worker caching changes
- Cache key schema changes on tenant/permission-scoped data
- Changes to invalidation triggers or TTL on security-sensitive caches

---

## Dependencies

- [Performance Strategy](performance-strategy.md)
- [Database Performance](database-performance.md)
- [Architecture Overview](../01-architecture/architecture-overview.md)
- [Authorization Security](../02-security/authorization-security.md)
- [RBAC Module](../04-modules/rbac.md)

## Used By / Affects

All modules with cached data: auth, RBAC, user-management, admin-panel, user-panel, health-monitoring, jobs-and-scheduler, API.

## Risks If Changed

HIGH — caching changes can cause authorization bypass, cross-tenant data leakage, stale security state, or cascading performance degradation.

## Related Documents

- [Performance Strategy](performance-strategy.md)
- [Database Performance](database-performance.md)
- [RBAC Module](../04-modules/rbac.md)
- [Auth Module](../04-modules/auth.md)
- [Health Monitoring](../04-modules/health-monitoring.md)
- [Jobs and Scheduler](../04-modules/jobs-and-scheduler.md)
- [Security Architecture](../02-security/security-architecture.md)
