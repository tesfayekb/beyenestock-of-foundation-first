# Risk Register

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-10

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
| **Last Reviewed** | 2026-04-09 |

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
| **Last Reviewed** | 2026-04-09 |

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
| **Last Reviewed** | 2026-04-09 |

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
| **Last Reviewed** | 2026-04-09 |

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
| **Last Reviewed** | 2026-04-09 |

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
| **Last Reviewed** | 2026-04-09 |

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
| **Last Reviewed** | 2026-04-09 |

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
| **Last Reviewed** | 2026-04-09 |

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
| **Last Reviewed** | 2026-04-09 |

### RISK-010: User Lifecycle Auth/Profile State Desynchronization

| Field | Value |
|-------|-------|
| **Type** | Security |
| **Likelihood** | 2 |
| **Impact** | 5 |
| **Risk Score** | 10 |
| **Priority** | MEDIUM |
| **Owner** | Project Lead |
| **Affected Modules** | user-management, auth |
| **Trigger Conditions** | Reactivation without clearing auth ban; deactivation without setting auth ban; partial failure in multi-step lifecycle mutation |
| **Detection** | Lifecycle E2E tests, login attempt monitoring for deactivated users, audit trail reconciliation |
| **Prevention** | Fail-closed sequencing (unban before status flip), compensating rollback on partial failure, auth-layer ban synchronized with profile status |
| **Response** | Manual auth admin unban/re-ban, audit investigation, incident report |
| **Residual Risk** | Low (after ACT-029 fix) |
| **Related Risks** | RISK-001 |
| **Related Watchlist** | RW-007 |
| **Status** | Mitigated → Monitored |
| **Last Reviewed** | 2026-04-10 |

### RISK-011: Narrow Base Role Revocation Guard

| Field | Value |
|-------|-------|
| **Type** | Authorization / RLS |
| **Likelihood** | 1 |
| **Impact** | 4 |
| **Risk Score** | 4 |
| **Priority** | LOW |
| **Owner** | Project Lead |
| **Affected Modules** | rbac, admin-panel |
| **Trigger Conditions** | A new base role (is_base=true) is added with a key other than `user`, `admin`, or `superadmin`. The revoke-role edge function guard (`role.is_base && role.key === 'user'`) would not protect it. |
| **Detection** | Code review when adding new base roles; migration review checklist |
| **Prevention** | Current mitigation: privilege hierarchy prevents non-superadmin from revoking admin/superadmin. Only the `user` key lacks hierarchy protection — and it is explicitly guarded. Future hardening: broaden guard to `if (role.is_base)` to protect all base roles unconditionally. |
| **Response** | Broaden the revoke-role guard condition before deploying the new base role |
| **Residual Risk** | Low (no unprotected base roles exist today) |
| **Related Risks** | RISK-001 |
| **Status** | Accepted |
| **Accepted By** | Project Lead |
| **Last Reviewed** | 2026-04-12 |

---

Each risk must define early warning (leading) and post-occurrence (lagging) indicators:

| Risk ID | Leading Indicators (Early Warning) | Lagging Indicators (After Occurrence) |
|---------|-----------------------------------|--------------------------------------|
| RISK-001 | Unusual role assignment frequency, unauthorized API attempts | Confirmed privilege escalation, unauthorized data access |
| RISK-002 | AI output diverging from SSOT patterns, missed reading steps | Plan sections dropped, incorrect code generated |
| RISK-003 | Function signature changes without cross-module review | Downstream module failures, test regressions |
| RISK-004 | Plan revision without diff, merge rule violations | Approved sections missing, stable IDs broken |
| RISK-005 | Cache key validation failures rising, missing tenant scope | Actual cross-tenant data exposure |
| RISK-006 | RLS policy changes without benchmark, query plan drift | Unauthorized row access, tenant data leak |
| RISK-007 | AI generating unindexed permissions/routes | Code contradicting SSOT, security logic errors |
| RISK-008 | Rising retry rates, DLQ depth increasing | Job cascade failure, audit gaps, health degradation |
| RISK-009 | p99 trending upward, connection pool > 60% | SLO breach, query timeouts, user-facing degradation |
| RISK-011 | New base role migration without guard review | Base role revoked, user left in undefined permission state |

**Rules:**
- Leading indicators must be monitored continuously for CRITICAL/HIGH risks
- Leading indicator threshold breach → preventive action before materialization
- Lagging indicators confirm materialization → trigger response plan

---

## Risk Appetite and Tolerance

| Risk Type | Tolerance Level | Boundary |
|-----------|----------------|----------|
| **Security** | Zero | No accepted security risk without CRITICAL-level approval |
| **Authorization / RLS** | Zero | No accepted authorization bypass |
| **Data Integrity** | Zero | No accepted silent data corruption |
| **Audit / Observability** | Low | Minor audit gaps may be temporarily accepted with timeline |
| **Performance** | Moderate | Degradation within defined SLO bands acceptable |
| **Jobs / Background** | Low | Non-critical job delays tolerable; critical job failures = zero tolerance |
| **AI / Process** | Low | Governance drift must be caught within same session |
| **UX / Workflow** | Moderate | Non-critical UX issues tracked but not release-blocking |

**Rules:**
- Zero-tolerance risks may **never** be accepted — must be mitigated or eliminated
- Tolerance boundaries inform decision-making under pressure — not permission to ignore
- Tolerance levels reviewed annually or after significant incidents

---

## Risk Trend Tracking

Each risk must track directional trend:

| Trend | Definition | Action |
|-------|-----------|--------|
| **Improving** | Likelihood decreasing, controls proving effective | Continue monitoring |
| **Stable** | No change in likelihood or impact | Standard review cadence |
| **Degrading** | Likelihood increasing, mitigation less effective, repeated triggers | Escalate review, strengthen controls |

### Current Risk Trends

| Risk ID | Current Trend | Evidence |
|---------|--------------|---------|
| RISK-001 | Stable | RLS + security definer in place, no triggers |
| RISK-002 | Stable | SSOT reading enforced, no recent drift |
| RISK-003 | Improving | Function index + regression tests active |
| RISK-004 | Improving | Merge rule + diff requirement enforced |
| RISK-005 | Stable | Cache key governance defined, not yet production-tested |
| RISK-006 | Stable | Benchmark requirements defined |
| RISK-007 | Stable | SSOT traceability improving |
| RISK-008 | Stable | Job governance hardened |
| RISK-009 | Stable | Capacity planning defined |
| RISK-011 | Stable | No new base roles planned; accepted with documented hardening path |

**Rule:** Degrading trend for > 2 review cycles → mandatory architectural review.

---

## Risk-to-Metric Correlation

Each risk maps to specific measurable signals:

| Risk ID | Correlated Metrics |
|---------|--------------------|
| RISK-001 | Unauthorized API attempts, role change frequency, audit anomalies |
| RISK-002 | SSOT reading compliance rate, AI output diff score |
| RISK-003 | Shared function change frequency, downstream test failures |
| RISK-005 | Cache key validation pass rate, tenant isolation test results |
| RISK-006 | RLS benchmark results, query plan stability |
| RISK-008 | Job failure rate, DLQ depth, retry storm count |
| RISK-009 | p99 latency, DB connection saturation, slow query count |

**Rule:** Metric thresholds must align with risk trigger conditions — crossing threshold = leading indicator alert.

---

## Preventive Control Effectiveness Review

Mitigation must be periodically validated — not assumed effective:

| Review Element | Question | Frequency |
|---------------|----------|-----------|
| Prevention controls | Are they reducing likelihood? | Per priority cadence |
| Detection controls | Are they catching events early (leading indicators)? | Monthly |
| Response controls | Is response effective and timely? | After each trigger |
| Residual risk accuracy | Is residual risk still correctly assessed? | Quarterly |

**Rules:**
- Controls found ineffective must be strengthened or replaced
- Effectiveness review results documented in risk entry
- Repeated control failure → architectural review

---

## Pre-Mortem Risk Analysis

### Before HIGH-Impact Changes

Before implementing any HIGH-impact change, perform pre-mortem analysis:

1. **Ask:** "How could this change fail?"
2. **Identify:** New risks introduced by the change
3. **Evaluate:** Impact on existing risks (score increase?)
4. **Output:**
   - New risk entries added to register (if needed)
   - Existing risk mitigation updated
   - Rollback/containment plan confirmed

**Rules:**
- Pre-mortem is **mandatory** for HIGH-impact changes
- Pre-mortem findings must be documented before implementation begins
- Skipping pre-mortem = INVALID change (per change control policy)

---

## Risk Simulation and Drills

### Periodic Simulation Requirements

| Scenario | Frequency | Verifies |
|----------|-----------|---------|
| Privilege escalation attempt | Quarterly | Detection + response + escalation |
| Cross-tenant cache leak | Quarterly | Detection + cache purge + investigation |
| Job failure cascade | Semi-annually | Kill switch + DLQ + health monitoring |
| RLS bypass attempt | Quarterly | Detection + access restriction + audit |
| AI governance failure | Semi-annually | SSOT enforcement + revert process |

### Rules

- Simulations must verify end-to-end: detection → response → escalation → resolution
- Simulation failures must create Action Tracker entries and improve controls
- Simulation results documented and reviewed
- First simulation after initial implementation, then per schedule

---

## System-Wide Risk Gate (Release Control)

### Before Release of HIGH-Impact Changes

The system must confirm:

| Gate | Verification |
|------|-------------|
| No new unmitigated CRITICAL/HIGH risks | Risk register reviewed |
| All affected risks reviewed | Cross-module mapping checked |
| Risk scores not increased without approval | Score comparison against baseline |
| Rollback/containment plan exists | Plan documented for all affected risks |
| Pre-mortem completed | Findings documented |
| Leading indicators stable | No warning signals active |

**Rules:**
- Risk gate failure = **release blocker**
- Risk gate is evaluated alongside regression gate and testing gate
- Gate results linked to release record

---

## Top Risk Summary

### Top 5 Active Risks (by Score)

| Rank | ID | Risk | Score | Priority | Trend | Status |
|------|----|------|-------|----------|-------|--------|
| 1 | RISK-004 | Plan sections dropped in revisions | 16 | HIGH | Improving | Monitored |
| 2 | RISK-002 | Context drift across AI sessions | 12 | HIGH | Stable | Monitored |
| 3 | RISK-003 | Silent behavior change in shared functions | 12 | HIGH | Improving | Monitored |
| 4 | RISK-007 | AI hallucination affecting code/docs | 12 | HIGH | Stable | Monitored |
| 5 | RISK-001 | Privilege escalation via role manipulation | 10 | MEDIUM | Stable | Monitored |

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
| Leading indicator threshold breached | Per risk priority | Preventive action |
| Risk simulation failure | HIGH | Control improvement within 1 week |
| Degrading trend detected | MEDIUM | Review within 1 week |

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

### RISK-011: Test-User Cleanup Fragility

| Field | Value |
|-------|-------|
| **ID** | RISK-011 |
| **Title** | Supabase auth user deletion blocked by trigger dependencies |
| **Category** | Operational |
| **Severity** | Low |
| **Likelihood** | Medium |
| **Priority** | Low |
| **Description** | Programmatic deletion of auth.users via `auth.admin.deleteUser()` fails when profile-creation triggers or FK constraints exist. This leaves orphaned test users after lifecycle verification runs. |
| **Impact** | Orphaned auth entries accumulate; test reruns may collide with stale data |
| **Current Controls** | Manual dashboard deletion documented in ACT-031 |
| **Planned Mitigations** | DW-013: auto-cleanup test harness; investigate trigger-safe deletion order |
| **Related Risks** | — |
| **Related Actions** | ACT-031 |
| **Owner** | Project Lead |
| **Status** | Open |
| **Review Cadence** | Quarterly |

---

### RISK-012: UI Contract Drift

| Field | Value |
|-------|-------|
| **Type** | AI / Process |
| **Description** | Stage 4 plan vs route-index/permission-index route and permission key mismatches. If undetected, implementation builds against wrong contracts. |
| **Likelihood** | 3 (Possible) |
| **Impact** | 4 (Major) |
| **Risk Score** | 12 |
| **Risk Level** | High |
| **Detection** | SSOT reconciliation review before implementation |
| **Current Controls** | Stage 4 plan v2 reconciled. Route-index v1.6 updated. Permission mismatch corrected. |
| **Planned Mitigations** | Mandatory reconciliation check before each Stage 4 sub-stage begins |
| **Related Actions** | ACT-036 |
| **Owner** | Project Lead |
| **Status** | Mitigated |
| **Review Cadence** | Per-stage |

### RISK-013: UI Inconsistency / Design Drift

| Field | Value |
|-------|-------|
| **Type** | AI / Process |
| **Description** | If design tokens/components are built before governed design-system docs exist, pages may have inconsistent visual language. |
| **Likelihood** | 3 (Possible) |
| **Impact** | 3 (Moderate) |
| **Risk Score** | 9 |
| **Risk Level** | Medium |
| **Detection** | Visual review, component inventory reconciliation |
| **Current Controls** | 3 governance docs created (ui-architecture.md, ui-design-system.md, component-inventory.md). Stage 4A prerequisite gate. |
| **Planned Mitigations** | Component inventory reconciliation at Phase 4 closure. No page-local variants rule. |
| **Related Actions** | ACT-036 |
| **Owner** | Project Lead |
| **Status** | Mitigated |
| **Review Cadence** | Per-stage |

---

- New risks added immediately when identified — full metadata required within 24 hours
- Risks are never deleted — only lifecycle-transitioned
- Risk acceptance requires documented justification and explicit approval
- Accepted risks must be reviewed at their priority cadence
- Risk register reviewed in full quarterly; critical/high risks reviewed per cadence
- Cross-risk dependencies must be evaluated when any linked risk changes status
- Pre-mortem mandatory for HIGH-impact changes
- Risk simulations executed per schedule

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
