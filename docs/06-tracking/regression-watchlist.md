# Regression Watchlist

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-11

## Purpose

Operational guardrail that tracks known regression risks, fragile areas, and past failures. Used as a mandatory pre-change verification checklist for every MEDIUM/HIGH impact change.

## Scope

All areas with known fragility, past regressions, or identified risk from the regression strategy and risk register.

## Enforcement Rule (CRITICAL)

- No MEDIUM/HIGH change may be completed without reviewing **all relevant** watchlist items
- Any relevant watchlist item not verified = change **cannot proceed**
- Watchlist verification must include evidence (test pass, runtime data, or documented manual check)
- Ignoring known watchlist risks is an **INVALID** change
- Critical-priority items must be checked **every time** their affected module changes

---

## Watchlist Entry Schema

Each watchlist item must include:

| Field | Required | Description |
|-------|----------|-------------|
| `id` | Yes | Stable identifier (RW-XXX) |
| `area` | Yes | System area (auth, RBAC, caching, jobs, etc.) |
| `risk_description` | Yes | What can regress and how |
| `regression_class` | Yes | From Regression Strategy (functional, security, authorization, performance, caching, data integrity, audit, UX) |
| `priority` | Yes | Critical / High / Medium / Low |
| `affected_modules` | Yes | List of impacted modules |
| `trigger_conditions` | Yes | What change types activate this watchlist item |
| `detection_method` | Yes | How regression is detected |
| `required_checks` | Yes | Specific verification steps |
| `verification_type` | Yes | Code / automated test / runtime / manual / hybrid |
| `related_tests` | Yes (or justification) | Linked regression test IDs |
| `related_risk` | If applicable | Link to Risk Register entry |
| `recurrence_count` | Yes | How many times this has triggered |
| `owner` | Yes | Responsible for verification |
| `added_date` | Yes | When first identified |
| `last_verified` | Yes | Date of most recent verification |
| `status` | Yes | Active / Resolved / Archived |
| `resolution_date` | If resolved | When resolved |

---

## Active Watchlist

### RW-001: Permission Cache Invalidation Delay

| Field | Value |
|-------|-------|
| **Area** | Caching / RBAC |
| **Risk Description** | Role/permission change not immediately reflected in UI or API due to stale cache |
| **Regression Class** | Caching / Authorization |
| **Priority** | Critical |
| **Affected Modules** | rbac, caching, admin-panel, user-panel, api |
| **Trigger Conditions** | Any change to: cache TTL, invalidation triggers, RBAC logic, permission resolution |
| **Detection** | Permission cache invalidation tests, cross-tab sync tests, manual role-change verification |
| **Required Checks** | 1) Assign role → verify immediate API access. 2) Revoke role → verify immediate denial. 3) Verify cross-tab propagation |
| **Verification Type** | Automated test + runtime |
| **Related Tests** | RBAC invalidation suite, cache isolation tests |
| **Related Risk** | RISK-005 |
| **Recurrence Count** | 0 |
| **Owner** | Project Lead |
| **Added Date** | 2026-04-08 |
| **Last Verified** | — |
| **Status** | Active |

### RW-002: RLS Policy Change Causing Visibility Mismatch

| Field | Value |
|-------|-------|
| **Area** | Database / RLS |
| **Risk Description** | RLS policy modification causes rows to become visible or invisible unexpectedly across tenants |
| **Regression Class** | Authorization / Data Integrity |
| **Priority** | Critical |
| **Affected Modules** | database, auth, rbac, all data-access modules |
| **Trigger Conditions** | Any RLS policy change, migration on RLS-protected tables, schema change on tenant-scoped tables |
| **Detection** | Tenant isolation E2E tests, RLS-specific DB tests, cross-tenant query verification |
| **Required Checks** | 1) Tenant A cannot see tenant B rows. 2) Policy change takes immediate effect. 3) Query plans verified |
| **Verification Type** | Automated test |
| **Related Tests** | Tenant isolation suite, RLS policy tests |
| **Related Risk** | RISK-006 |
| **Recurrence Count** | 0 |
| **Owner** | Project Lead |
| **Added Date** | 2026-04-08 |
| **Last Verified** | — |
| **Status** | Active |

### RW-003: Shared Function Change Affecting Multiple Modules

| Field | Value |
|-------|-------|
| **Area** | Architecture / Shared Services |
| **Risk Description** | Modification to shared function silently breaks downstream consumers |
| **Regression Class** | Functional |
| **Priority** | High |
| **Affected Modules** | All modules consuming the changed function |
| **Trigger Conditions** | Any change to functions listed in function-index.md |
| **Detection** | Cross-module regression tests, snapshot tests on function outputs |
| **Required Checks** | 1) All consuming modules retested. 2) Function signature unchanged or consumers updated. 3) Golden dataset comparison |
| **Verification Type** | Automated test |
| **Related Tests** | Shared function regression suite |
| **Related Risk** | RISK-003 |
| **Recurrence Count** | 0 |
| **Owner** | Project Lead |
| **Added Date** | 2026-04-08 |
| **Last Verified** | — |
| **Status** | Active |

### RW-004: Job Retry Misconfiguration

| Field | Value |
|-------|-------|
| **Area** | Jobs / Scheduler |
| **Risk Description** | Retry count, backoff, or concurrency changes cause duplicate execution, retry storms, or silent failure |
| **Regression Class** | Functional / Performance |
| **Priority** | High |
| **Affected Modules** | jobs-and-scheduler, health-monitoring, audit-logging |
| **Trigger Conditions** | Any change to: job retry config, backoff logic, concurrency policy, kill switch |
| **Detection** | Job telemetry tests, retry behavior verification, DLQ depth monitoring |
| **Required Checks** | 1) Retry count matches config. 2) Backoff verified in logs. 3) No duplicate execution. 4) DLQ receives after max retries |
| **Verification Type** | Automated test + runtime |
| **Related Tests** | Job idempotency suite, retry behavior tests |
| **Related Risk** | RISK-008 |
| **Recurrence Count** | 0 |
| **Owner** | Project Lead |
| **Added Date** | 2026-04-08 |
| **Last Verified** | — |
| **Status** | Active |

### RW-005: Audit Event Missing After Mutation

| Field | Value |
|-------|-------|
| **Area** | Audit / Observability |
| **Risk Description** | Critical action completes but audit log entry is not created, causing compliance gap |
| **Regression Class** | Observability / Audit |
| **Priority** | High |
| **Affected Modules** | audit-logging, auth, rbac, user-management, admin-panel |
| **Trigger Conditions** | Any change to: mutation flows, audit emission logic, event structure, error handling paths |
| **Detection** | Audit reconciliation tests, event emission verification, audit completeness checks |
| **Required Checks** | 1) Every critical action produces audit entry. 2) All required fields present. 3) No sensitive data in logs. 4) Event count matches action count |
| **Verification Type** | Automated test |
| **Related Tests** | Audit integrity suite |
| **Related Risk** | — |
| **Recurrence Count** | 0 |
| **Owner** | Project Lead |
| **Added Date** | 2026-04-08 |
| **Last Verified** | — |
| **Status** | Active |

### RW-006: Health Monitoring Blind Spot

| Field | Value |
|-------|-------|
| **Area** | Health / Monitoring |
| **Risk Description** | Health monitoring system change causes false positives, missed alerts, or monitoring blind spots — system health appears healthy when degraded |
| **Regression Class** | Observability |
| **Priority** | High |
| **Affected Modules** | health-monitoring, admin-panel |
| **Trigger Conditions** | Any change to: health check logic, alert thresholds, monitoring config, `evaluateAlerts()`, `getSystemHealth()`, health endpoint |
| **Detection** | Health check endpoint tests, alert threshold evaluation tests, monitoring self-check (monitor-the-monitor) |
| **Required Checks** | 1) Health endpoint returns correct status. 2) Alert thresholds trigger correctly at boundary values. 3) `health.monitoring_failed` event emits when monitoring system fails. 4) Dashboard reflects actual system state |
| **Verification Type** | Automated test + runtime |
| **Related Tests** | Health check tests, alert evaluation tests, monitoring failure emission tests |
| **Related Risk** | RISK-009 |
| **Recurrence Count** | 0 |
| **Owner** | Project Lead |
| **Added Date** | 2026-04-09 |
| **Last Verified** | — |
| **Status** | Active |

### RW-007: User Lifecycle Deactivation/Reactivation Regression

| Field | Value |
|-------|-------|
| **Area** | User Management / Auth |
| **Risk Description** | Deactivation or reactivation fails to synchronize auth-layer ban state with profile status, resulting in users locked out after reactivation or still able to login after deactivation |
| **Regression Class** | Security / Authorization |
| **Priority** | Critical |
| **Affected Modules** | user-management, auth |
| **Trigger Conditions** | Any change to: deactivate-user, reactivate-user, auth admin API calls, profile status update logic, `check_user_active_on_login` trigger, compensating rollback logic |
| **Detection** | Full lifecycle E2E test (create → deactivate → verify blocked → reactivate → verify login restored), rollback path tests |
| **Required Checks** | 1) Deactivated user cannot login (HTTP 400). 2) Reactivated user can login (HTTP 200). 3) Auth ban cleared on reactivation. 4) Compensating rollback fires on partial failure. 5) Audit events emitted for both paths. |
| **Verification Type** | Automated test + runtime |
| **Related Tests** | deactivate-user/index_test.ts, reactivate-user/index_test.ts, lifecycle E2E suite |
| **Related Risk** | RISK-010 |
| **Recurrence Count** | 1 (ACT-029 — reactivation did not clear auth ban) |
| **Owner** | Project Lead |
| **Added Date** | 2026-04-10 |
| **Last Verified** | 2026-04-10 (ACT-029: 8/8 lifecycle tests passed) |
| **Status** | Active |

### RW-008: PERMISSION_DEPS Map Drift Across 3 Copies

| Field | Value |
|-------|-------|
| **Area** | RBAC / Configuration |
| **Risk Description** | The PERMISSION_DEPS map exists in 3 locations: `src/config/permission-deps.ts`, `assign-permission-to-role/index.ts`, and `revoke-permission-from-role/index.ts`. Adding or removing a dependency in one copy without updating the others causes silent enforcement inconsistency — client may allow what server blocks, or server may not enforce what client shows. |
| **Regression Class** | Authorization / Data Integrity |
| **Priority** | High |
| **Affected Modules** | rbac, admin-panel |
| **Trigger Conditions** | Any change to permission dependencies, adding new permissions, modifying PERMISSION_DEPS in any of the 3 files |
| **Detection** | Manual diff of all 3 copies, automated hash comparison (future) |
| **Required Checks** | 1) All 3 PERMISSION_DEPS maps have identical entries. 2) Any new permission with dependencies is added to all 3 files. 3) permission-index.md `depends_on` field matches. |
| **Verification Type** | Manual (automated drift detection deferred — DW-027) |
| **Related Tests** | — |
| **Related Risk** | — |
| **Recurrence Count** | 0 |
| **Owner** | Project Lead |
| **Added Date** | 2026-04-12 |
| **Last Verified** | 2026-04-12 (all 3 copies confirmed identical — 23 entries each) |
| **Status** | Active |

### RW-011: Empty CAPTCHA Payload Breaks Password Auth

| Field | Value |
|-------|-------|
| **Area** | Auth / CAPTCHA |
| **Risk Description** | Password auth forwards an empty or placeholder CAPTCHA payload to Supabase Auth, causing `captcha verification process failed` even when CAPTCHA is disabled or bypassed in development |
| **Regression Class** | Functional / Security |
| **Priority** | High |
| **Affected Modules** | auth, user-panel, admin-panel |
| **Trigger Conditions** | Any change to sign-in/sign-up auth payload shaping, Turnstile integration, dev-mode bypass logic, or CAPTCHA configuration handling |
| **Detection** | Password sign-in runtime verification, network payload inspection, auth error monitoring |
| **Required Checks** | 1) Password sign-in request omits `gotrue_meta_security` when no real CAPTCHA token exists. 2) Real CAPTCHA tokens are still forwarded when present. 3) Password sign-in succeeds with CAPTCHA disabled in Supabase. |
| **Verification Type** | Runtime + manual |
| **Related Tests** | `e2e/sign-in-flow.spec.ts` |
| **Related Risk** | — |
| **Recurrence Count** | 1 |
| **Owner** | Project Lead |
| **Added Date** | 2026-04-14 |
| **Last Verified** | — |
| **Status** | Active |

---

## Pre-Change Verification Workflow

Before completing any MEDIUM/HIGH impact change:

1. **Identify** affected modules from the change
2. **Pull** all watchlist items matching affected modules or trigger conditions (automated matching where available)
3. **Execute** required checks for each matching item
4. **Record** verification evidence in standardized format (see Evidence Standardization)
5. **If any check fails** → change cannot proceed until resolved
6. **If new fragility discovered** → add new watchlist item before completing change

### System-Level Watchlist Gate

Before any HIGH-impact change completes, the system must confirm:

- All matching watchlist items verified with evidence
- No critical items skipped
- Evidence recorded in standardized format
- No new untracked fragility introduced
- Override protocol followed if any item unresolvable (see Override Protocol)

**Gate failure = change cannot proceed.**

---

## Leading vs Lagging Indicators

Each watchlist item should define early warning and post-occurrence signals:

| Item | Leading Indicators (Early Warning) | Lagging Indicators (After Occurrence) |
|------|-----------------------------------|--------------------------------------|
| RW-001 | Cache invalidation delay > threshold, invalidation error rate rising | Actual permission mismatch observed in UI/API |
| RW-002 | RLS policy change without benchmark, query plan drift on tenant tables | Unauthorized row access, cross-tenant data exposure |
| RW-003 | Function signature change detected, no cross-module test update | Downstream module failures, unexpected behavior |
| RW-004 | Retry config change without test, DLQ depth trend increasing | Duplicate execution, retry storm, job cascade |
| RW-005 | Audit emission logic changed, error handling path modified | Missing audit entries in reconciliation |
| RW-006 | Health check logic changed, alert threshold modified, monitoring config updated | False positive/negative alerts, monitoring blind spot, dashboard shows incorrect state |

**Rule:** Leading indicators should be monitored proactively — catching them prevents the regression from materializing.

---

## SSOT Artifact Traceability

Each watchlist item should map to specific SSOT artifacts for instant test targeting:

| Item | Related Routes | Related Permissions | Related Functions | Related Events |
|------|---------------|-------------------|------------------|----------------|
| RW-001 | All permission-gated routes | All RBAC permissions | `has_role()`, `checkPermission()` | `rbac.role_assigned`, `rbac.role_revoked` |
| RW-002 | All tenant-scoped data routes | `users.*`, `audit.*` | RLS policy functions | — |
| RW-003 | Routes consuming shared functions | Per function | All shared functions (function-index) | — |
| RW-004 | Admin job management routes | `jobs.*` | Job execution functions | `job.failed`, `job.dead_lettered` |
| RW-005 | All mutation routes | `audit.view`, `audit.export` | `logAuditEvent()` | `audit.logged`, `audit.write_failed` |
| RW-006 | `/admin/monitoring`, `/admin/monitoring/config`, `GET /health` | `monitoring.view`, `monitoring.configure` | `getSystemHealth()`, `evaluateAlerts()`, `getMetrics()` | `health.alert_triggered`, `health.status_changed`, `health.monitoring_failed` |
| RW-007 | `/admin/users/:id/deactivate`, `/admin/users/:id/reactivate` | `users.deactivate`, `users.reactivate` | `deactivateUser()`, `reactivateUser()` | `user.account_deactivated`, `user.account_reactivated` |
| RW-008 | `/admin/roles/:id` (permission assign/revoke) | `permissions.assign`, `permissions.revoke` | `PERMISSION_DEPS` config | `rbac.permission_assigned`, `rbac.permission_revoked` |
| RW-009 | All Phase 4 routes | All UI-gated permissions | All shared components | — |
| RW-010 | `/mfa-enroll`, `/admin` | `admin.access` | `checkMfaStatus()` | `auth.mfa_enrolled` |

**Rule:** When reviewing a change, match changed SSOT artifacts against watchlist traceability to identify all relevant items.

---

## Verification Evidence Standardization

All verification evidence must follow a standardized format:

| Evidence Type | Required Content |
|--------------|-----------------|
| **Automated test** | Test run ID + pass/fail + timestamp + CI link |
| **Runtime verification** | Monitoring dashboard link + metric values + time range |
| **Manual check** | Screenshot/recording + timestamp + verifier name |
| **Log/trace reference** | Trace ID + relevant log entries + timestamp |
| **Hybrid** | Combination of above as appropriate |

**Rules:**
- "Checked" without evidence is **not valid** verification
- Evidence must be linked or embedded in the change record
- Evidence must be timestamped within the current change cycle

---

## Automatic Population Rules

Watchlist must be updated when:

| Event | Action |
|-------|--------|
| Regression detected (from regression strategy) | Add watchlist item |
| Risk materializes (from risk register) | Add watchlist item for affected area |
| Test failure reveals fragility | Add watchlist item |
| Post-release issue found | Add watchlist item |
| Manual verification finds edge case | Add watchlist item |
| Adversarial test reveals vulnerability | Add watchlist item |

**Rule:** Population is both manual and event-driven — any discovery of fragility must result in a watchlist entry.

### Automated Watchlist Matching (Design Rule)

The system should support automatic mapping of changed modules to relevant watchlist items:

- On each change, identify affected modules and files
- Match against watchlist `affected_modules` and `trigger_conditions`
- Surface matching items to the developer before completion
- Even if implemented later, all watchlist items must be structured to support automated matching

---

## Recurrence Tracking and Escalation

| Recurrence Count | Action |
|-----------------|--------|
| 1 | Normal — item remains active |
| 2 | Warning — enhanced test coverage required |
| 3+ | **Escalate to Risk Register** if not already linked |
| 5+ | Mandatory architectural review — point fixes insufficient |

### Regression Test Auto-Generation Rule

- Watchlist items with recurrence ≥ 2 **must** be converted into automated regression tests
- Goal: reduce manual verification over time
- Once automated test exists and passes consistently, manual verification requirement may be relaxed (item remains active but verification = test pass)

**Rules:**
- Recurrence count incremented each time the regression actually occurs (not each time checked)
- Recurrent items must be flagged in Top Fragile Areas summary
- Escalation creates Action Tracker entry

---

## Lifecycle Management

| Status | Definition | Rules |
|--------|-----------|-------|
| **Active** | Known risk, must be checked on relevant changes | Mandatory verification |
| **Resolved** | Root cause fixed, regression test in place | Must include resolution date + evidence |
| **Archived** | Stale (> 90 days resolved) or no longer relevant | Reviewed before archival |

### Cleanup Rules

- Resolved items remain for history — never deleted
- Items active > 90 days without verification → must be reviewed (confirm relevance or archive)
- Archival requires confirmation that:
  - Root cause addressed
  - Regression test exists (or justified exception)
  - No recent recurrence

### Watchlist Drift Detection

- Periodic review (monthly) must check:
  - Missing new risk patterns not yet on watchlist
  - Outdated items no longer relevant
  - Items never triggered or verified (stale detection)
- Drift detected → update watchlist + Action Tracker entry if gap is critical

---

## Watchlist Coverage Completeness

**Rule:** Every critical module must have at least one active watchlist item.

| Module | Required Coverage | Current Items |
|--------|------------------|---------------|
| Auth / Session | ≥ 1 item | RW-001 (via RBAC) |
| RBAC / Permissions | ≥ 1 item | RW-001 |
| RLS / Database | ≥ 1 item | RW-002 |
| Jobs / Scheduler | ≥ 1 item | RW-004 |
| Audit Logging | ≥ 1 item | RW-005 |
| Caching | ≥ 1 item | RW-001 (via cache) |
| Shared Functions | ≥ 1 item | RW-003 |
| Admin Panel | Covered via module items | RW-001, RW-005 |
| Health Monitoring | ≥ 1 item | RW-006 |

**Gap Detection:** Absence of watchlist item for a fragile module = coverage gap → must be addressed.

---

## Watchlist Performance Constraint

The watchlist must remain **high-signal, not bloated**:

- Target: ≤ 20 active items at any time
- Low-value items should be:
  - Merged with related items
  - Archived if risk is fully mitigated by automated tests
  - Escalated to permanent regression tests (removing manual verification need)
- Quarterly review must prune or consolidate

**Rule:** Watchlist overhead must not materially slow development velocity — if it does, items must be converted to automated tests.

---

## High-Risk Change Override Protocol

When a change must proceed despite unresolved watchlist items:

| Requirement | Details |
|------------|---------|
| **Explicit approval** | Project lead or designated authority |
| **Documented justification** | Why override is necessary |
| **Mitigation plan** | How risk will be managed post-merge |
| **Follow-up Action Tracker item** | With owner, severity, and resolution timeline |
| **Time-bounded** | Override expires — follow-up must resolve within SLA |

**Rules:**
- Override is exceptional — not routine
- Override count tracked — frequent overrides = systemic problem
- Critical-priority items cannot be overridden without CRITICAL-level approval

---

## Testing Integration

- Every watchlist item **must** link to at least one regression test (if automatable)
- If no automated test exists, justification must be documented:

| Justification | Example |
|--------------|---------|
| Visual/layout only | Complex UI interaction not reliably automated |
| Environment-dependent | Requires production-like infra for meaningful test |
| Pending implementation | Test planned, not yet built (must have timeline) |

**Rule:** "Pending implementation" justification expires after 30 days — test must be built or item escalated.

---

## Action Tracker Integration

The following **MUST** create Action Tracker entries:

| Trigger | Severity | Target Resolution |
|---------|----------|-------------------|
| Watchlist check failure during change | HIGH | 24h (blocks change) |
| Repeated failure of same item (3+) | HIGH | Architectural review |
| Unresolved active item > 90 days | MEDIUM | Review/resolve within 1 week |
| Critical item triggered | CRITICAL | 4h |
| New critical item added | HIGH | Verification within 24h |
| Override invoked | MEDIUM | Follow-up per SLA |
| Coverage gap detected | MEDIUM | 1 week |
| Watchlist drift detected | MEDIUM | 1 week |

---

## Top Fragile Areas

### Most Critical Active Items

| Rank | ID | Area | Priority | Recurrence |
|------|----|------|----------|------------|
| 1 | RW-001 | Permission cache invalidation | Critical | 0 |
| 2 | RW-002 | RLS policy visibility | Critical | 0 |
| 3 | RW-007 | User lifecycle deactivation/reactivation | Critical | 1 |
| 4 | RW-003 | Shared function changes | High | 0 |
| 5 | RW-004 | Job retry configuration | High | 0 |
| 6 | RW-005 | Audit event completeness | High | 0 |
| 7 | RW-006 | Health monitoring blind spot | High | 0 |
| 8 | RW-008 | PERMISSION_DEPS map drift | High | 0 |
| 9 | RW-009 | UI design system compliance | High | 0 |
| 10 | RW-010 | MFA enroll route state drift | High | 1 |

_Updated as items are added, triggered, or resolved._

---

### RW-009: UI Design System Compliance

| Field | Value |
|-------|-------|
| **Area** | UI (Phase 4) |
| **Risk Description** | Phase 4 pages may introduce off-system colors, page-local component variants, ungoverned dialog/table/form patterns, or route/permission keys not in SSOT indexes |
| **Regression Class** | UX |
| **Priority** | High |
| **Affected Modules** | admin-panel, user-panel |
| **Trigger Conditions** | Any Phase 4 page creation or modification |
| **Detection Method** | Code review: grep for raw Tailwind palette colors, check imports against component inventory, verify routes against route-index |
| **Required Checks** | (1) No raw colors (`bg-red-*`, `text-blue-*`, `bg-[#...]`) in component code. (2) All tables use `DataTable`. (3) All destructive flows use `ConfirmActionDialog`. (4) All async states use governed LoadingSkeleton/ErrorState/EmptyState. (5) All routes exist in route-index. (6) All permission keys exist in permission-index. |
| **Verification Type** | Code review + manual |
| **Related Tests** | Visual regression checklist (Phase 4 closure) |
| **Related Risk** | RISK-013 |
| **Recurrence Count** | 0 |
| **Owner** | Project Lead |
| **Added Date** | 2026-04-10 |
| **Last Verified** | 2026-04-10 (initial creation) |
| **Status** | Active |

---

### RW-010: MFA Enroll Route State Drift

| Field | Value |
|-------|-------|
| **Area** | Auth / MFA |
| **Risk Description** | `/mfa-enroll` may ignore existing verified or incomplete TOTP factors, causing duplicate-enrollment errors or trapping admins on the enrollment route instead of returning them to the requested admin page |
| **Regression Class** | UX / Workflow |
| **Priority** | High |
| **Affected Modules** | auth, admin-panel, user-panel |
| **Trigger Conditions** | Any change to AuthContext MFA status resolution, AdminLayout MFA guard, MfaEnroll.tsx, MfaChallenge.tsx, factor naming, or factor cleanup behavior |
| **Detection Method** | Manual route verification, preview network traces, auth journey testing |
| **Required Checks** | 1) Admin without MFA visiting `/admin` is redirected to `/mfa-enroll`. 2) Successful enroll auto-returns with a visible fallback button. 3) Already-enrolled admin does not see a blind re-enroll CTA in forced-enrollment context. 4) Adding another factor from Security Settings does not reuse a conflicting friendly name. 5) Incomplete unverified factors can be cleared and restarted. |
| **Verification Type** | Manual + code review |
| **Related Tests** | No dedicated automated regression test yet — manual MFA route checklist required until auth E2E coverage is expanded |
| **Related Risk** | — |
| **Recurrence Count** | 1 |
| **Owner** | Project Lead |
| **Added Date** | 2026-04-11 |
| **Last Verified** | 2026-04-11 |
| **Status** | Active |

---

## Link to Risk Register

- Watchlist = **tactical** (day-to-day change verification)
- Risk Register = **strategic** (system-level risk governance)
- Every watchlist item should reference a risk (if applicable)
- High-recurrence watchlist items must be escalated to risk register
- Risk materialization creates corresponding watchlist item for ongoing verification

---

## Dependencies

- [Regression Strategy](../05-quality/regression-strategy.md)
- [Change Control Policy](../00-governance/change-control-policy.md)
- [Risk Register](risk-register.md)
- [Testing Strategy](../05-quality/testing-strategy.md)

## Used By / Affects

All MEDIUM/HIGH impact changes — mandatory pre-change verification tool.

## Risks If Changed

MEDIUM — weakening watchlist verification directly increases regression risk across all modules.

## Related Documents

- [Regression Strategy](../05-quality/regression-strategy.md)
- [Risk Register](risk-register.md)
- [Action Tracker](action-tracker.md)
- [Testing Strategy](../05-quality/testing-strategy.md)
- [Function Index](../07-reference/function-index.md)
- [Permission Index](../07-reference/permission-index.md)
- [Route Index](../07-reference/route-index.md)
- [Event Index](../07-reference/event-index.md)
