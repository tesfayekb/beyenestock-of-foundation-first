# Action Tracker

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-09

## Purpose

Central operational record that tracks every completed action with classification, verification evidence, SSOT traceability, lifecycle management, and system impact analysis. Serves as the enforcement backbone for change governance.

## Scope

All tasks performed on the project: features, fixes, refactors, security changes, performance work, regression fixes, risk mitigations, and documentation updates.

## Enforcement Rule (CRITICAL)

- No change is complete until:
  - Action tracker entry created with full metadata
  - Verification evidence recorded
  - Related documentation updated
- Incomplete or missing entry = **INVALID** change
- Entries are **append-only** — no retroactive editing of completed entries
- Corrections must be appended as new entries referencing the original, not edited in place
- Historical accuracy must be preserved — audit trail must be fully reconstructable

---

## Action Classification

Every action must be classified:

| Type | Description | Examples |
|------|------------|---------|
| **Feature** | New functionality | New API endpoint, UI component, job |
| **Fix** | Bug correction | Error handling fix, data correction |
| **Refactor** | Code improvement without behavior change | Architecture cleanup, performance optimization |
| **Security** | Security-related change | RLS policy, auth hardening, vulnerability fix |
| **Performance** | Performance improvement | Query optimization, caching, bundle reduction |
| **Regression** | Regression fix | Restoring broken behavior |
| **Risk** | Risk mitigation action | Control implementation, risk response |
| **Documentation** | Documentation update | SSOT updates, governance changes |

---

## Action Entry Schema

Each action must include:

| Field | Required | Description |
|-------|----------|-------------|
| `id` | Yes | Stable identifier (ACT-XXX) |
| `date` | Yes | Completion date |
| `action` | Yes | Description of what was done |
| `type` | Yes | From classification model |
| `impact_classification` | Yes | Low / Medium / High |
| `change_id` | If applicable | Reference to change control record |
| `modules_affected` | Yes | List of impacted modules |
| `docs_updated` | Yes | List of updated documents |
| `status` | Yes | Lifecycle state |

### Verification Fields

| Field | Required | Description |
|-------|----------|-------------|
| `verification_type` | Yes | Code / test / runtime / hybrid |
| `verification_scope` | Yes | Immediate / runtime / continuous |
| `evidence` | Yes | Test run ID, log reference, screenshot, monitoring link |
| `verified_by` | Yes | Role or person who verified |
| `post_deploy_validation` | For deployed changes | Pass / fail / pending |
| `validation_window` | For Medium/High | Immediate / 1h / 24h / 7d |
| `validation_notes` | If applicable | Additional validation context |
| `trace_id` | If applicable | Reference to runtime logs/monitoring trace |

### State Tracking Fields

| Field | Required | Description |
|-------|----------|-------------|
| `before_state` | For Medium/High | Summary of state before change |
| `after_state` | For Medium/High | Summary of state after change |
| `rollback_available` | For Medium/High | Yes / No |
| `rollback_method` | If rollback available | Description of rollback approach |
| `blast_radius` | For Medium/High | Small / medium / large / system-wide |

### Traceability Fields

| Field | When Required | Description |
|-------|--------------|-------------|
| `related_routes` | If routes affected | Route index references |
| `related_permissions` | If permissions affected | Permission index references |
| `related_functions` | If shared functions affected | Function index references |
| `related_events` | If events affected | Event index references |
| `related_jobs` | If jobs affected | Job references |
| `related_tests` | If tests added/modified | Test file references |
| `related_risks` | If risk resolved/mitigated | Risk register IDs |
| `related_watchlist` | If watchlist items affected | Watchlist IDs |
| `depends_on` | If sequencing required | Prerequisite action IDs |
| `blocks` | If downstream dependencies | Blocked action IDs |

### Impact Fields

| Field | When Required | Description |
|-------|--------------|-------------|
| `metrics_affected` | If measurable | Which metrics changed (with before/after values) |
| `health_impact` | For Medium/High | Improved / degraded / neutral |
| `risk_delta` | If risk affected | Reduced / increased / neutral |
| `effort_estimate` | Optional | Estimated effort |
| `actual_effort` | Optional | Actual effort spent |

---

## Action Lifecycle States

| Status | Definition |
|--------|-----------|
| **Planned** | Action identified, not yet started |
| **In Progress** | Actively being worked on |
| **Completed** | Implementation done, pending verification |
| **Verified** | Verification evidence recorded, all checks passed |
| **Rolled Back** | Change reverted due to issue |
| **Superseded** | Replaced by a newer action |

**Rules:**
- Only `Verified` status satisfies Definition of Done
- `Completed` without verification evidence cannot be marked `Verified`
- `Rolled Back` must reference the issue and link to follow-up action

---

## Action Register

### ACT-001: Created SSOT Documentation System

| Field | Value |
|-------|-------|
| **Date** | 2026-04-08 |
| **Type** | Feature |
| **Impact** | HIGH |
| **Modules Affected** | All |
| **Docs Updated** | All governance, architecture, security, performance, module, quality, tracking, reference, planning docs |
| **Verification Type** | Code + manual review |
| **Evidence** | Full document tree created and cross-referenced |
| **Verified By** | Project Lead |
| **Before State** | No documentation system |
| **After State** | 42-file SSOT documentation system active |
| **Rollback Available** | Yes |
| **Rollback Method** | Remove docs directory |
| **Health Impact** | Improved |
| **Status** | Verified |

### ACT-002: Hardened Performance Documentation Suite

| Field | Value |
|-------|-------|
| **Date** | 2026-04-08 |
| **Type** | Documentation |
| **Impact** | HIGH |
| **Modules Affected** | performance-strategy, database-performance, caching-strategy |
| **Docs Updated** | performance-strategy.md, database-performance.md, caching-strategy.md |
| **Verification Type** | Manual review |
| **Evidence** | Expert review scoring 100/100 for all three docs |
| **Verified By** | Project Lead |
| **Before State** | Base-level performance docs (~72-80/100) |
| **After State** | Institutional-grade performance governance (100/100) |
| **Health Impact** | Improved |
| **Status** | Verified |

### ACT-003: Hardened Quality Documentation Suite

| Field | Value |
|-------|-------|
| **Date** | 2026-04-08 |
| **Type** | Documentation |
| **Impact** | HIGH |
| **Modules Affected** | testing-strategy, regression-strategy |
| **Docs Updated** | testing-strategy.md, regression-strategy.md |
| **Verification Type** | Manual review |
| **Evidence** | Expert review scoring 100/100 for both docs |
| **Verified By** | Project Lead |
| **Before State** | Base-level quality docs (~70-78/100) |
| **After State** | Institutional-grade testing + regression governance (100/100) |
| **Health Impact** | Improved |
| **Status** | Verified |

### ACT-004: Hardened Tracking Documentation Suite

| Field | Value |
|-------|-------|
| **Date** | 2026-04-08 |
| **Type** | Documentation |
| **Impact** | HIGH |
| **Modules Affected** | risk-register, regression-watchlist, action-tracker |
| **Docs Updated** | risk-register.md, regression-watchlist.md, action-tracker.md |
| **Verification Type** | Manual review |
| **Evidence** | Expert review scoring 100/100 for all tracking docs |
| **Verified By** | Project Lead |
| **Before State** | Base-level tracking docs (~70-85/100) |
| **After State** | Institutional-grade risk + watchlist + action tracking (100/100) |
| **Health Impact** | Improved |
| **Status** | Verified |

### ACT-005: Approved All Implementation Plan Sections (Review Round 2)

| Field | Value |
|-------|-------|
| **Date** | 2026-04-09 |
| **Type** | Documentation |
| **Impact** | HIGH |
| **Modules Affected** | All (auth, RBAC, user-management, admin-panel, user-panel, audit-logging, health-monitoring, API, jobs-and-scheduler) |
| **Docs Updated** | master-plan.md, plan-review-log.md, approved-decisions.md, plan-changelog.md, system-state.md, action-tracker.md |
| **Verification Type** | Manual review |
| **Evidence** | All 9 sections reviewed; DEC-008 through DEC-016 created; plan-review-log Review Round 2 recorded; changelog v2→v3 logged |
| **Verified By** | Project Lead |
| **Before State** | All 9 implementation sections `proposed`, no approved baseline |
| **After State** | All 9 sections `approved`, baseline v3 active, implementation unblocked |
| **Rollback Available** | Yes |
| **Rollback Method** | Revert statuses to `proposed`, remove DEC-008–DEC-016, restore v2 baseline |
| **Blast Radius** | System-wide (governance state change) |
| **Health Impact** | Improved |
| **Status** | Verified |

### ACT-006: Pre-Implementation Audit Fixes (v3 → v4)

| Field | Value |
|-------|-------|
| **Date** | 2026-04-09 |
| **Type** | Documentation |
| **Impact** | HIGH |
| **Modules Affected** | All (governance, reference indexes, tracking, planning) |
| **Docs Updated** | function-index.md, permission-index.md, route-index.md, event-index.md, config-index.md, env-var-index.md, open-questions.md, approved-decisions.md, plan-changelog.md, plan-review-log.md, regression-watchlist.md, risk-register.md, action-tracker.md, system-state.md |
| **Verification Type** | Manual review + automated grep verification |
| **Evidence** | All RSK→RISK mismatches resolved (0 remaining); 3 open questions resolved (DEC-017/018/019); 5 self-scope permissions added; 3 missing UUID placeholders added; RW-006 created; all Last Reviewed dates updated; changelog v2→v3 wording corrected |
| **Verified By** | Project Lead |
| **Before State** | 10 audit issues (2 critical blockers, 5 medium, 3 low); plan baseline v3 |
| **After State** | 0 remaining issues; all cross-references consistent; plan baseline v4 |
| **Rollback Available** | Yes |
| **Rollback Method** | Revert to v3 baseline, remove DEC-017/018/019, restore original index versions |
| **Blast Radius** | System-wide (documentation governance) |
| **Health Impact** | Improved |
| **Status** | Verified |

### ACT-007: Final Audit Remediation (v4 Polish)

| Field | Value |
|-------|-------|
| **Date** | 2026-04-09 |
| **Type** | Documentation |
| **Impact** | HIGH |
| **Modules Affected** | rbac, input-validation, config-index, permission-index, all docs (metadata) |
| **Docs Updated** | rbac.md, input-validation-and-sanitization.md, config-index.md, permission-index.md, 27 files (Last Reviewed dates), risk-register.md |
| **Verification Type** | Manual review + automated grep verification |
| **Evidence** | (1) Moderator removed from validation schema per DEC-018; (2) admin added as seed role in rbac.md; (3) MFA default corrected to ["admin","superadmin"]; (4) 15 missing UUID placeholders added (total now 28); (5) All 27 stale dates updated to 2026-04-09; (6) risk-register internal dates updated |
| **Verified By** | Project Lead |
| **Before State** | 6 issues (2 critical, 4 medium/low); score 97/100 |
| **After State** | 0 remaining issues; score 100/100 |
| **Rollback Available** | Yes |
| **Rollback Method** | Revert individual file changes |
| **Blast Radius** | System-wide (documentation governance) |
| **Health Impact** | Improved |
| **Status** | Verified |

---

## Risk and Regression Integration

### Risk Resolution Tracking

- If action resolves a risk → must link risk ID in `related_risks`
- Risk register entry must be updated to reflect resolution
- Resolution evidence in action tracker = risk resolution evidence

### Regression Tracking

- If action introduces regression → must link watchlist item in `related_watchlist`
- Regression fix actions must reference the original regression
- Repeated failures in same area → tracked via recurrence in watchlist, referenced here

### Watchlist Verification

- Watchlist verification during changes → must reference action tracker entry
- Action tracker provides the evidence chain for watchlist compliance

---

## Change Control Integration

- Every action must reference its change control classification (Low/Medium/High)
- HIGH impact actions must include pre/post state tracking
- Actions resulting from change control workflow reference the change ID
- Actions that bypass normal workflow must document override justification

---

## Summary Dashboard

### Actions by Type (Current Period)

| Type | Count | High Impact |
|------|-------|-------------|
| Feature | 1 | 1 |
| Documentation | 5 | 5 |
| Fix | 0 | 0 |
| Security | 0 | 0 |
| Performance | 0 | 0 |
| Regression | 0 | 0 |

### Status Overview

| Status | Count |
|--------|-------|
| Verified | 6 |
| Completed (unverified) | 0 |
| In Progress | 0 |
| Rolled Back | 0 |

### Trend Indicators

- Regressions introduced: 0
- Regressions resolved: 0
- Open (unverified) actions: 0
- High-impact actions this period: 6

_Updated as actions are added._

---

## Action Quality Gate

An action **cannot** be marked `Verified` unless:

| Gate | Requirement |
|------|------------|
| Verification evidence present | Test run, log, screenshot, or monitoring link |
| Related watchlist items verified | All matching items checked with evidence |
| Related risks updated | Risk register reflects resolution/status change |
| Post-deploy validation completed | If validation window defined, stability confirmed |
| No regression introduced | Regression checks passed, no new watchlist items from this action |
| Metrics validated | If `metrics_affected` defined, before/after values recorded |

**Rule:** Quality gate is mandatory for all actions. HIGH-impact actions require all gates; LOW-impact actions require at minimum evidence + no regression.

---

## System-Level Action Gate

Before any HIGH-impact change is finalized, the system must confirm:

| Confirmation | Source |
|-------------|--------|
| Action recorded with full metadata | This document |
| Evidence validated | Verification fields |
| Regression checks passed | Regression Strategy |
| Risk register updated | Risk Register |
| Watchlist items verified | Regression Watchlist |
| Metrics validated (if applicable) | Before/after values |
| Validation window defined | For runtime/continuous verification |
| Blast radius documented | State tracking fields |

**Gate failure = action cannot be marked Verified.**

---

## Verification Scope Rules

| Scope | Definition | Required For |
|-------|-----------|-------------|
| **Immediate** | One-time verification at completion | All actions |
| **Runtime** | Verified via monitoring after deployment | Medium/High deployed changes |
| **Continuous** | Ongoing monitoring confirms sustained correctness | HIGH impact: RBAC, RLS, auth, security changes |

**Rules:**
- HIGH impact actions must include runtime or continuous verification scope
- Continuous verification must define what signals confirm ongoing correctness
- Verification scope failure (e.g., runtime regression detected) → status reverts to `Completed` + new corrective action created

---

## Metric Correlation Enforcement

When `metrics_affected` is defined, the entry must include:

| Field | Example |
|-------|---------|
| Metric name | API p95 latency |
| Before value | 420ms |
| After value | 310ms |
| Measurement method | Monitoring dashboard, load test |

**Rule:** Metric claims without before/after values are not valid evidence.

---

## Action Drift Detection

Over time, action outcomes may become invalid due to later changes:

- Periodic review (quarterly) must check:
  - Are HIGH-impact action outcomes still valid?
  - Has subsequent work invalidated assumptions?
  - Have metrics regressed since verification?
- If drift detected:
  - Create new corrective action referencing the original
  - Update related risks and watchlist items

---

## Immutability Rules

- Entries are **append-only** — historical entries must never be modified
- Corrections to past entries must be appended as new correction entries:
  - Reference original entry ID
  - Explain correction
  - Preserve original for audit trail
- Status changes are forward-only (except `Rolled Back` which references the issue)
- Audit trail must be fully reconstructable from the action log

---

## Dependencies

- [Definition of Done](../00-governance/definition-of-done.md) — requires action tracker update
- [Change Control Policy](../00-governance/change-control-policy.md) — governs change classification
- [Regression Strategy](../05-quality/regression-strategy.md) — regression actions tracked here
- [Risk Register](risk-register.md) — risk resolution tracked here
- [Regression Watchlist](regression-watchlist.md) — verification evidence linked here

## Used By / Affects

Definition of Done verification, project audit trail, risk resolution tracking, regression verification, change control compliance, health monitoring.

## Risks If Changed

HIGH — action tracker is the operational evidence backbone for the entire governance system.

## Related Documents

- [Definition of Done](../00-governance/definition-of-done.md)
- [Change Control Policy](../00-governance/change-control-policy.md)
- [Regression Watchlist](regression-watchlist.md)
- [Risk Register](risk-register.md)
- [Regression Strategy](../05-quality/regression-strategy.md)
- [Testing Strategy](../05-quality/testing-strategy.md)
- [Health Monitoring](../04-modules/health-monitoring.md)
