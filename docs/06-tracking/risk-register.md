# Risk Register

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-08

## Purpose

Governs risk identification, classification, scoring, detection, mitigation, escalation, and lifecycle management for a permission-driven, RLS-enforced, audit-heavy, multi-tenant system.

## Scope

All technical, security, operational, performance, and AI/process risks across the system.

## Enforcement Rule (CRITICAL)

- Every identified risk **MUST** be registered with full metadata (classification, score, owner, detection, mitigation)
- No risk may be accepted without documented justification and explicit approval
- Risk materialization **MUST** create Action Tracker entries
- Critical risks must feed health monitoring — active critical risk = degraded system state
- Unregistered known risks are an **INVALID** system state
- Risk register is append-only for history — risks are never deleted, only lifecycle-transitioned

---

## Risk Classification Model

### Risk Types

| Type | Description | Examples |
|------|------------|---------|
| **Security** | Authentication, session, injection, exposure | Token leak, CSRF, session fixation |
| **Authorization / RLS** | Permission bypass, tenant isolation failure | Privilege escalation, cross-tenant access |
| **Data Integrity** | Corruption, inconsistency, silent data loss | Stale cache overwrite, orphaned records |
| **Performance / Scalability** | Latency degradation, resource exhaustion | Query plan regression, connection saturation |
| **Caching / Consistency** | Stale data, cache poisoning, freshness breach | Permission cache lag, cross-tenant cache leak |
| **Jobs / Background** | Execution failure, missed schedules, poison jobs | Dead-letter overflow, duplicate execution |
| **Observability / Audit** | Missing logs, blind spots, metric gaps | Audit event dropped, health signal missing |
| **AI / Process** | SSOT drift, hallucination, governance bypass | Plan dropped, unauthorized code generation |
| **Operational / Deployment** | Deploy failure, rollback risk, config drift | Migration lock, feature flag misconfiguration |

---

## Risk Scoring Model

### Quantitative Scoring

| Factor | Scale | Definition |
|--------|-------|-----------|
| **Likelihood** | 1 (Rare) – 5 (Almost Certain) | Probability of occurrence |
| **Impact** | 1 (Negligible) – 5 (Catastrophic) | Consequence if realized |
| **Risk Score** | Likelihood × Impact | 1–25 |

### Priority Mapping

| Score Range | Priority | Review Cadence |
|------------|----------|---------------|
| 20–25 | **CRITICAL** | Continuous monitoring |
| 12–19 | **HIGH** | Weekly review |
| 6–11 | **MEDIUM** | Monthly review |
| 1–5 | **LOW** | Quarterly review |

---

## Risk Lifecycle

Each risk progresses through defined states:

```
Identified → Assessed → Mitigated → Monitored → [Triggered → Contained → Resolved] or Accepted
```

| Status | Definition |
|--------|-----------|
| **Identified** | Risk discovered, not yet fully assessed |
| **Assessed** | Scored, classified, owner assigned |
| **Mitigated** | Prevention controls implemented |
| **Monitored** | Active detection in place |
| **Triggered** | Risk materialized — active incident |
| **Contained** | Immediate response executed |
| **Resolved** | Root cause addressed, controls verified |
| **Accepted** | Risk acknowledged, residual accepted with justification |

---

## Risk Entry Template

Each risk must include:

| Field | Required | Description |
|-------|----------|-------------|
| `id` | Yes | Stable identifier (RISK-XXX) |
| `risk` | Yes | Description of the risk |
| `type` | Yes | From classification model |
| `likelihood` | Yes | 1–5 |
| `impact` | Yes | 1–5 |
| `risk_score` | Yes | Likelihood × Impact |
| `priority` | Yes | Critical / High / Medium / Low |
| `owner` | Yes | Responsible person/role |
| `affected_modules` | Yes | List of impacted modules |
| `trigger_conditions` | Yes | What causes the risk to materialize |
| `detection_method` | Yes | How materialization is detected |
| `prevention` | Yes | Design-time mitigation |
| `detection` | Yes | Runtime detection controls |
| `response` | Yes | Containment actions if triggered |
| `residual_risk` | Yes | Low / Medium / High after mitigation |
| `accepted_by` | If accepted | Who approved acceptance |
| `related_risks` | If applicable | Cross-risk dependencies |
| `status` | Yes | Lifecycle state |
| `last_reviewed` | Yes | Date of last review |

---

## Active Risk Register

### RISK-001: Privilege Escalation via Role Manipulation

| Field | Value |
|-------|-------|
| **Type** | Authorization / RLS |
| **Likelihood** | 2 |
| **Impact** | 5 |
| **Risk Score** | 10 |
| **Priority** | MEDIUM |
| **Owner** | Project Lead |
| **Affected Modules** | auth, rbac, admin-panel, user-management |
| **Trigger Conditions** | Unauthorized role assignment, RLS bypass, client-side role check |
| **Detection** | Audit logs (role change events), anomaly detection on permission grants, adversarial tests |
| **Prevention** | Roles in separate table, security definer functions, RLS, server-side enforcement only |
| **Response** | Revoke roles immediately, lock affected accounts, alert, audit investigation |
| **Residual Risk** | Low |
| **Related Risks** | RISK-005, RISK-006 |
| **Status** | Mitigated → Monitored |
| **Last Reviewed** | 2026-04-08 |

### RISK-002: Context Drift Across AI Sessions

| Field | Value |
|-------|-------|
| **Type** | AI / Process |
| **Likelihood** | 3 |
| **Impact** | 4 |
| **Risk Score** | 12 |
| **Priority** | HIGH |
| **Owner** | Project Lead |
| **Affected Modules** | All (governance layer) |
| **Trigger Conditions** | AI fails to read SSOT, interprets rules inconsistently, generates code against outdated context |
| **Detection** | Manual review of AI outputs, SSOT diff checks, change-control verification |
| **Prevention** | SSOT system, mandatory reading order, plan governance, constitution rules |
| **Response** | Halt implementation, re-read SSOT, revert unauthorized changes |
| **Residual Risk** | Medium |
| **Related Risks** | RISK-004, RISK-007 |
| **Status** | Mitigated → Monitored |
| **Last Reviewed** | 2026-04-08 |

### RISK-003: Silent Behavior Change in Shared Functions

| Field | Value |
|-------|-------|
| **Type** | Data Integrity |
| **Likelihood** | 3 |
| **Impact** | 4 |
| **Risk Score** | 12 |
| **Priority** | HIGH |
| **Owner** | Project Lead |
| **Affected Modules** | All modules using shared functions |
| **Trigger Conditions** | Shared function modified without cross-module review, signature change |
| **Detection** | Function index tracking, regression tests, snapshot/golden dataset comparison |
| **Prevention** | Function index, shared component protection rule, cross-module regression mapping |
| **Response** | Revert change, run full regression suite, update affected modules |
| **Residual Risk** | Low |
| **Related Risks** | RISK-002 |
| **Status** | Mitigated → Monitored |
| **Last Reviewed** | 2026-04-08 |

### RISK-004: Approved Plan Sections Dropped in Revisions

| Field | Value |
|-------|-------|
| **Type** | AI / Process |
| **Likelihood** | 4 |
| **Impact** | 4 |
| **Risk Score** | 16 |
| **Priority** | HIGH |
| **Owner** | Project Lead |
| **Affected Modules** | All (planning layer) |
| **Trigger Conditions** | AI rewrites plan instead of merging, sections silently removed |
| **Detection** | Diff requirement enforcement, stable ID tracking, plan review log |
| **Prevention** | Plan preservation rule, stable IDs, merge rule, diff requirement |
| **Response** | Reject revision, restore from approved baseline, re-merge |
| **Residual Risk** | Medium |
| **Related Risks** | RISK-002, RISK-007 |
| **Status** | Mitigated → Monitored |
| **Last Reviewed** | 2026-04-08 |

### RISK-005: Cross-Tenant Data Leakage via Cache

| Field | Value |
|-------|-------|
| **Type** | Caching / Consistency |
| **Likelihood** | 2 |
| **Impact** | 5 |
| **Risk Score** | 10 |
| **Priority** | MEDIUM |
| **Owner** | Project Lead |
| **Affected Modules** | caching, rbac, user-panel, admin-panel |
| **Trigger Conditions** | Cache key missing tenant scope, shared cache serving cross-tenant data |
| **Detection** | Cache key governance tests, tenant isolation tests, cache drift detection |
| **Prevention** | Cache key governance (mandatory tenant scope), classification matrix, CDN prohibition for protected data |
| **Response** | Cache purge, immediate investigation, incident classification |
| **Residual Risk** | Low |
| **Related Risks** | RISK-001, RISK-006 |
| **Status** | Mitigated → Monitored |
| **Last Reviewed** | 2026-04-08 |

### RISK-006: RLS Policy Bypass Under Load or Schema Change

| Field | Value |
|-------|-------|
| **Type** | Authorization / RLS |
| **Likelihood** | 2 |
| **Impact** | 5 |
| **Risk Score** | 10 |
| **Priority** | MEDIUM |
| **Owner** | Project Lead |
| **Affected Modules** | database, auth, rbac, all data-access modules |
| **Trigger Conditions** | Migration changes RLS policy, query bypasses policy via function, load causes policy timeout |
| **Detection** | RLS tests on all migrations, tenant isolation E2E tests, query plan review |
| **Prevention** | RLS benchmark on realistic datasets, migration safety review, DB change control |
| **Response** | Rollback migration, restrict access, audit impacted data |
| **Residual Risk** | Low |
| **Related Risks** | RISK-001, RISK-005 |
| **Status** | Mitigated → Monitored |
| **Last Reviewed** | 2026-04-08 |

### RISK-007: AI Hallucination Affecting Code or Documentation

| Field | Value |
|-------|-------|
| **Type** | AI / Process |
| **Likelihood** | 3 |
| **Impact** | 4 |
| **Risk Score** | 12 |
| **Priority** | HIGH |
| **Owner** | Project Lead |
| **Affected Modules** | All (code + documentation) |
| **Trigger Conditions** | AI generates code that contradicts SSOT, invents permissions/routes, produces incorrect security logic |
| **Detection** | SSOT traceability checks, test coverage, code review against indexes |
| **Prevention** | Mandatory SSOT reading, change-control workflow, test-first enforcement |
| **Response** | Revert generated code, re-validate against SSOT, add regression test |
| **Residual Risk** | Medium |
| **Related Risks** | RISK-002, RISK-004 |
| **Status** | Mitigated → Monitored |
| **Last Reviewed** | 2026-04-08 |

### RISK-008: Job System Failure Cascading to Audit/Health

| Field | Value |
|-------|-------|
| **Type** | Jobs / Background |
| **Likelihood** | 2 |
| **Impact** | 4 |
| **Risk Score** | 8 |
| **Priority** | MEDIUM |
| **Owner** | Project Lead |
| **Affected Modules** | jobs-and-scheduler, health-monitoring, audit-logging |
| **Trigger Conditions** | Job retry storm, dead-letter overflow, scheduler failure, poison job |
| **Detection** | Job telemetry, DLQ depth monitoring, SLO tracking, health signals |
| **Prevention** | Kill switch, circuit breakers, backpressure, poison detection, concurrency limits |
| **Response** | Kill switch activation, DLQ review, job pause, incident investigation |
| **Residual Risk** | Low |
| **Related Risks** | RISK-009 |
| **Status** | Mitigated → Monitored |
| **Last Reviewed** | 2026-04-08 |

### RISK-009: Performance Degradation Under Tenant Growth

| Field | Value |
|-------|-------|
| **Type** | Performance / Scalability |
| **Likelihood** | 3 |
| **Impact** | 3 |
| **Risk Score** | 9 |
| **Priority** | MEDIUM |
| **Owner** | Project Lead |
| **Affected Modules** | database, caching, api, admin-panel |
| **Trigger Conditions** | Tenant data exceeds benchmarked tier, query plans regress, connection saturation |
| **Detection** | Multi-tenant performance benchmarks, p99 monitoring, capacity planning thresholds |
| **Prevention** | Query classification, index governance, partitioning strategy, capacity planning |
| **Response** | Query optimization, scaling evaluation, partitioning, read replicas |
| **Residual Risk** | Medium |
| **Related Risks** | RISK-006 |
| **Status** | Assessed → Monitored |
| **Last Reviewed** | 2026-04-08 |

---

## Top Risk Summary

### Top 5 Active Risks (by Score)

| Rank | ID | Risk | Score | Priority | Status |
|------|----|------|-------|----------|--------|
| 1 | RISK-004 | Plan sections dropped in revisions | 16 | HIGH | Monitored |
| 2 | RISK-002 | Context drift across AI sessions | 12 | HIGH | Monitored |
| 3 | RISK-003 | Silent behavior change in shared functions | 12 | HIGH | Monitored |
| 4 | RISK-007 | AI hallucination affecting code/docs | 12 | HIGH | Monitored |
| 5 | RISK-001 | Privilege escalation via role manipulation | 10 | MEDIUM | Monitored |

### Recently Triggered Risks

_None currently active._

---

## Escalation Policy

| Priority | Escalation Path | Timeline |
|----------|----------------|----------|
| **CRITICAL** | Immediate action → health board impact → project lead notification | < 1 hour |
| **HIGH** | Rapid response → action tracker → owner investigation | < 4 hours |
| **MEDIUM** | Action tracker entry → scheduled review | < 1 week |
| **LOW** | Tracked → quarterly review | Next review cycle |

### Escalation Rules

- Risk materialization at any level → Action Tracker entry
- Repeated trigger (3+ in 30 days) → escalate priority by one level
- Unresolved risk beyond SLA → escalate to project lead
- Critical risk active → system health degraded on health board

---

## Action Tracker Integration

The following **MUST** create Action Tracker entries:

| Trigger | Severity | Target Resolution |
|---------|----------|-------------------|
| Risk materialized | Per risk priority | Per escalation SLA |
| Critical risk triggered | CRITICAL | 1 hour |
| Repeated risk trigger (3+ in 30 days) | Escalated +1 level | Architectural review |
| Unresolved high risk beyond SLA | Escalated | Immediate |
| New critical/high risk identified | HIGH | Assessment within 24h |
| Risk acceptance requires review | MEDIUM | Review within 1 week |

---

## Health Monitoring Integration

- Critical and high risks must feed the **health monitoring** module
- Active critical risk = system marked **degraded** on health board
- Risk resolution restores health status (with evidence)
- Risk monitoring signals must be part of health dashboard
- Sustained high-risk state (> 7 days unresolved) = system flagged **unstable**

---

## Cross-Risk Dependencies

Risks can amplify each other. The following dependency chains are tracked:

| Primary Risk | Amplified By | Combined Effect |
|-------------|-------------|----------------|
| RISK-001 (Privilege escalation) | RISK-005 (Cache leak) | Escalated access + data exposure |
| RISK-002 (AI drift) | RISK-004 (Plan drop) | Governance failure cascade |
| RISK-006 (RLS bypass) | RISK-009 (Performance degradation) | Load-induced security failure |
| RISK-008 (Job failure) | RISK-009 (Performance degradation) | Cascading system degradation |

**Rule:** When a risk triggers, check related risks for cascading impact.

---

## Rules

- New risks added immediately when identified — full metadata required within 24 hours
- Risks are never deleted — only lifecycle-transitioned
- Risk acceptance requires documented justification and explicit approval
- Accepted risks must be reviewed at their priority cadence
- Risk register reviewed in full quarterly; critical/high risks reviewed per cadence
- Cross-risk dependencies must be evaluated when any linked risk changes status

---

## Dependencies

- [Constitution](../00-governance/constitution.md)
- [Change Control Policy](../00-governance/change-control-policy.md)
- [Health Monitoring](../04-modules/health-monitoring.md)
- [Regression Strategy](../05-quality/regression-strategy.md)
- [Testing Strategy](../05-quality/testing-strategy.md)

## Used By / Affects

Project planning, change control decisions, health monitoring, action tracker, regression strategy, release gating.

## Risks If Changed

HIGH — weakening risk governance directly increases exposure to security, integrity, and operational failures.

## Related Documents

- [Regression Watchlist](regression-watchlist.md)
- [Action Tracker](action-tracker.md)
- [Constitution](../00-governance/constitution.md)
- [Security Architecture](../02-security/security-architecture.md)
- [RBAC Module](../04-modules/rbac.md)
- [Caching Strategy](../03-performance/caching-strategy.md)
- [Jobs and Scheduler](../04-modules/jobs-and-scheduler.md)
