# Regression Strategy

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-08

## Purpose

Defines regression governance: how regressions are classified, prevented, detected, contained, and tracked across a permission-driven, RLS-enforced, audit-heavy, multi-tenant system.

## Scope

All changes — with escalating rigor for MEDIUM and HIGH impact changes. Regression strategy is the glue layer that prevents drift across all hardened modules.

## Enforcement Rule (CRITICAL)

- No MEDIUM/HIGH impact change may merge without documented regression review
- No critical-path regression may ship without explicit approved exception
- Regression checks must cover code, tests, runtime behavior, **and** documentation alignment
- Any untracked known regression risk is an **INVALID** implementation
- Regression means deviation from **approved baseline**, not just failing tests
- No regression item may be marked resolved solely by code inspection when runtime verification is required

---

## Regression Classification Matrix

| Class | Detection Source | Required Tests | Severity | Release Blocking |
|-------|----------------|---------------|----------|-----------------|
| **Functional** | Unit, integration, E2E | Feature tests, flow tests | Varies | Yes if critical path |
| **Security** | Adversarial tests, security scan | Auth, RBAC, injection tests | CRITICAL | Always |
| **Authorization / RLS** | Permission tests, RLS tests | Allow/deny matrix, tenant isolation | CRITICAL | Always |
| **Performance** | Load tests, monitoring, CI budgets | Latency benchmarks, bundle size | HIGH | Yes for critical endpoints |
| **Caching / Freshness** | Cache tests, drift detection | Invalidation, staleness, isolation | HIGH | Yes for permission cache |
| **Data Integrity** | Invariant checks, reconciliation | Pre/post state validation | CRITICAL | Always |
| **Observability / Audit** | Audit reconciliation, event tests | Event emission, completeness | HIGH | Yes |
| **UX / Workflow** | E2E, manual verification | User journey tests | MEDIUM | Yes for critical journeys |

**Rules:**
- Every regression must be classified before resolution planning
- Classification determines containment action, ownership priority, and release blocking status

---

## Baseline and Expected-State Control

### Baseline Concept

Every critical path must have an **approved baseline** — regression is any deviation from it.

### Required Baselines

| Domain | Baseline Includes |
|--------|------------------|
| Auth/session | Expected login/logout/MFA behavior, token lifecycle |
| RBAC/permissions | Expected allow/deny outcomes per role per resource |
| API contracts | Expected request/response shapes, status codes |
| Performance | Expected p95/p99 latency, bundle size |
| Audit/events | Expected event emissions per action |
| Query plans | Expected access paths for critical queries |
| Cache behavior | Expected TTL, invalidation triggers, key format |
| RLS | Expected row visibility per role/tenant |

### Rules

- Baselines must be version-controlled (golden datasets, snapshots, documented expectations)
- Baseline changes require explicit approval — not silent drift
- Comparison against baseline is part of every regression check

---

## Cross-Module Regression Mapping

Changes to interconnected modules must trigger linked regression review:

| Change In | Must Review Regression In |
|-----------|--------------------------|
| **Auth** | RBAC, caching, session, audit, health monitoring |
| **RBAC** | Admin panel, API, cache invalidation, RLS, user panel |
| **Jobs** | Health monitoring, audit, action tracker, performance |
| **Caching** | Permissions, tenant isolation, freshness, dashboards |
| **Database / RLS** | All permissioned data access, query performance, audit |
| **Performance** | Health scoring, user-critical flows, SLO compliance |
| **Audit** | Admin panel, compliance, health monitoring |
| **API** | Frontend, caching, permission enforcement, E2E flows |

### Rules

- Cross-module regression review is **mandatory** for HIGH impact changes
- Reviewer must check impacted modules' baselines, not just the changed module
- Cross-module regressions are treated as the **highest severity** among affected modules

---

## Change-Type Regression Triggers

The following change types **require** regression review regardless of impact label:

| Change Type | Required Regression Checks |
|------------|---------------------------|
| Permission or RLS policy changes | Authorization matrix, tenant isolation, cache invalidation |
| Cache key / TTL / invalidation changes | Permission freshness, tenant isolation, staleness SLA |
| Job schedule / retry / kill-switch changes | Execution correctness, SLO, health monitoring |
| Audit schema / event changes | Event completeness, log structure, compliance |
| New dependencies added | Bundle size, security scan, performance impact |
| Migration on large/hot tables | Query plan stability, latency, lock contention |
| Health threshold changes | Alert accuracy, false positive/negative rate |
| API contract changes | Backward compatibility, frontend integration, cache validity |

---

## Regression Protection Loop

Before completing any MEDIUM or HIGH impact change:

1. **Classify** the regression risk (use Classification Matrix)
2. **Check** `regression-watchlist.md` for known risks in the affected area
3. **Identify** cross-module dependencies (use Cross-Module Mapping)
4. **Run** required regression tests for all affected domains
5. **Compare** against approved baselines
6. **Verify** SSOT artifacts are still accurate (routes, permissions, events, functions)
7. **If new risk discovered** → add to `regression-watchlist.md` with full metadata
8. **Document** regression review evidence in change record

---

## SSOT Traceability

Every regression check must cite impacted SSOT artifacts:

| SSOT Document | Regression Mapping |
|--------------|-------------------|
| Route Index | Affected routes retested |
| Permission Index | Affected permissions retested (allow + deny) |
| Event Index | Affected events verified for emission |
| Function Index | Affected shared functions retested |
| Dependency Map | Downstream modules reviewed |
| Regression Watchlist | Related items checked and updated |

### Rules

- New regression risks must map to affected routes, functions, and modules
- Orphaned watchlist items must be reviewed quarterly and retired formally
- Every critical SSOT rule must have at least one regression test

---

## Project-Specific Regression Checks

Required regression checks for this system's critical concerns:

| Concern | Regression Check |
|---------|-----------------|
| Permission change not reflected (stale cache) | Cache invalidation verified within SLA |
| RLS policy change breaking visibility/isolation | Tenant isolation tests re-run |
| Audit event missing after workflow change | Event emission reconciliation |
| Job schedule change breaking freshness/SLO | SLO compliance verified |
| p99 latency regression on critical paths | Performance baseline comparison |
| Bundle size increase | CI budget check |
| Cross-tenant cache/key leakage risk | Cache key isolation verified |
| Query plan regression | Plan comparison against stored baseline |
| Permission evaluation latency regression | Permission cache performance check |

---

## Runtime Regression Detection

Not all regressions are caught at test time. Post-deploy detection is critical:

### Detection Sources

| Source | Detects |
|--------|---------|
| Health monitoring | Performance degradation, error rate spikes |
| Action tracker | Operational issues surfaced by other modules |
| Audit reconciliation | Missing or malformed audit entries |
| Performance threshold breach | Latency, throughput, query plan regressions |
| Error rate anomalies | New failure patterns post-deploy |
| Cache drift detection | Stale or inconsistent cached data |
| User reports | UX/workflow regressions not caught by automation |

### Rules

- Runtime regressions are as valid as test-time regressions
- Critical runtime regression must trigger **rollback or kill-switch evaluation**
- Runtime regression detection feeds directly into Action Tracker

---

## Rollback and Containment Rules

When regression is detected, containment action is determined by class:

| Regression Class | Containment Options |
|-----------------|-------------------|
| **Security / Authorization** | Immediate rollback, feature flag disable, cache purge |
| **Data Integrity** | Rollback, data reconciliation, traffic halt if needed |
| **Performance (critical)** | Rollback, degrade mode, traffic limiting |
| **Caching** | Cache purge, fallback to source, TTL override |
| **Jobs** | Job pause, kill-switch, DLQ review |
| **Functional (critical path)** | Feature flag disable, rollback |
| **UX / non-critical** | Hotfix, no immediate rollback required |

### Rules

- Containment action must be executed **before** root cause analysis for critical regressions
- Containment must preserve audit trail (no silent state changes)
- Rollback readiness is a release prerequisite for HIGH impact changes

---

## Ownership and Resolution SLA

Every regression / watchlist item must include:

| Field | Required |
|-------|----------|
| Owner | Yes — responsible for resolution |
| Severity | Critical / High / Medium / Low |
| Detection source | Test, runtime, manual, monitoring |
| First seen | Date of discovery |
| Affected modules | List of impacted modules |
| Release blocker | Yes / No |
| Target resolution time | Per severity SLA |
| Verification type | Code / automated test / runtime / hybrid |

### Resolution SLA

| Severity | Target Resolution | Escalation If Missed |
|----------|------------------|---------------------|
| CRITICAL | 4 hours | Immediate escalation |
| HIGH | 24 hours | Escalate to project lead |
| MEDIUM | 1 week | Action tracker follow-up |
| LOW | 2 weeks | Quarterly review |

---

## Regression Test Mapping

- Every known regression risk must have at least one regression test (where automatable)
- Manual-only regression checks must be explicitly justified
- Fixed regressions **must** add a permanent regression test unless technically impossible
- Tests must map to specific watchlist item ID
- Regression tests must be tagged/labeled for targeted execution

---

## Manual Verification Governance

- Manual verification allowed **only** for areas not reliably automated (visual/layout, complex UX flows)
- Manual checks must use a checklist tied to critical user journeys
- Manual verification must record evidence (screenshots, session recordings, sign-off)
- Manual verification cannot substitute for missing automatable tests
- Manual regression checklist reviewed and updated quarterly

---

## Post-Release Regression Surveillance

### Watch Window

- MEDIUM impact changes: **24-hour** increased monitoring post-release
- HIGH impact changes: **72-hour** increased monitoring post-release
- Critical module changes (auth, RBAC, RLS): **1-week** surveillance

### Rules

- Compare live metrics against pre-release baseline during watch window
- Regressions found during watch window create Action Tracker entries automatically
- Post-release regression in a critical module = immediate investigation
- Watch window findings feed back into regression watchlist

---

## Verification Evidence Rules

- No regression item may be marked resolved without evidence matching its verification type:

| Verification Type | Required Evidence |
|------------------|------------------|
| Code | Code review approval + diff reference |
| Automated test | Test pass in CI (linked run) |
| Runtime | Monitoring data showing stable behavior post-deploy |
| Hybrid | Both test pass AND runtime verification |

### Rules

- "Completed" status requires evidence consistent with verification type
- Evidence must be linked or referenced in the watchlist/tracker entry
- False completion (marking resolved without proper evidence) is an **INVALID** action

---

## Action Tracker and Health Integration

### Action Tracker

The following **MUST** create Action Tracker entries:

| Trigger | Severity | Target Resolution |
|---------|----------|-------------------|
| Regression detected (any class) | Per classification | Per SLA |
| Critical regression in production | CRITICAL | 4h |
| Repeated regression in same area (3+) | HIGH | Architectural review |
| Unresolved regression beyond SLA | Escalated +1 level | Immediate |
| Post-release regression in watch window | HIGH | 24h |
| Regression watchlist item stale (> 30 days) | MEDIUM | Review/retire |

### Health Board Integration

- Critical regression = health board entry (system marked degraded)
- Repeated regression in same module = stability concern flagged
- Unresolved critical regressions degrade system health score
- Regression resolution restores health status with evidence

---

## Dependencies

- [Change Control Policy](../00-governance/change-control-policy.md)
- [Dependency Map](../01-architecture/dependency-map.md)
- [Testing Strategy](testing-strategy.md)
- [Performance Strategy](../03-performance/performance-strategy.md)
- [Caching Strategy](../03-performance/caching-strategy.md)
- [Health Monitoring](../04-modules/health-monitoring.md)

## Used By / Affects

All changes — regression strategy governs the integrity verification layer for the entire system.

## Risks If Changed

HIGH — weakening regression strategy directly increases defect rate, security risk, and system instability across all modules.

## Related Documents

- [Testing Strategy](testing-strategy.md)
- [Regression Watchlist](../06-tracking/regression-watchlist.md)
- [Change Control Policy](../00-governance/change-control-policy.md)
- [Action Tracker](../06-tracking/action-tracker.md)
- [Permission Index](../07-reference/permission-index.md)
- [Route Index](../07-reference/route-index.md)
- [Event Index](../07-reference/event-index.md)
- [Function Index](../07-reference/function-index.md)
