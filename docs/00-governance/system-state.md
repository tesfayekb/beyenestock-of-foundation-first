# System State

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-12

## Purpose

Single source of truth for the current state of the project.

This file controls:
- What actions are allowed
- What phase the system is in
- Which plan baseline is active

It MUST be read before every task.

## Scope

Tracks:
- Phase
- Code generation status
- Module implementation status
- Active work
- Plan versioning

## Enforcement Rule (CRITICAL)

- This file MUST be read before any task begins
- If this file is outdated or inconsistent → execution is **INVALID**
- If required updates are missing → tasks must **STOP** until corrected
- This file overrides assumptions — only the state defined here is valid

## Current State

```yaml
status: complete
phase: development
code_generation: allowed
modules_implemented: auth partial (A+D implemented + hardened, B+C deferred), rbac implemented (Phase 2 gate 12/12 closed + dependency enforcement + roles.edit + permissions.view separated + permissions.assign/revoke restricted to superadmin + RBAC governance hardening 2026-04-13), user-management implemented (Stage 3C closed), audit-logging implemented (Stage 3B closed + Phase 3.5 hardened + RLS INSERT policy removed [ACT-053] + correlation_id top-level column [ACT-055]), api implemented (Stage 3A closed + Phase 3.5 hardened), admin-panel implemented (Phase 4 CLOSED + Phase 5 additions: AdminHealthPage [ACT-063], AdminJobsPage [ACT-063] + performance hardening [ACT-056] + RBAC governance hardening 2026-04-13), user-panel implemented (Phase 4 CLOSED + session revocation [ACT-063]), health-monitoring implemented (Stage 5A + 5B + 5F complete [ACT-057, ACT-058, ACT-063]), jobs-and-scheduler implemented (Stage 5C + 5D + 5E complete [ACT-059, ACT-060, ACT-062])
active_work: Phase 6 — Hardening & System Validation. CLOSED. All stages 6A–6F complete. DW-011 deferred to v2. RBAC governance hardening completed 2026-04-13.
current_plan_version: v11.0
approved_plan_baseline: v11.0
plan_status: approved
artifact_governance: active (artifact-index.md, database-migration-ledger.md, phase-closures/)
deferred_work_open: []
deferred_work_v2: [DW-001, DW-002, DW-007, DW-011, DW-020]
deferred_work_closed_this_phase: [DW-008, DW-012, DW-013, DW-016, DW-017, DW-018, DW-019, DW-021, DW-022, DW-023, DW-024, DW-025, DW-026, DW-027, DW-028, DW-029]
deployment_config_required:
  - leaked_password_protection: "Enable in Supabase Dashboard → Authentication → Settings → Leaked Password Protection. Cannot be set via SQL migration or edge function. Required for A+ security posture."
last_updated: 2026-04-13
```

## RBAC Governance Hardening (2026-04-13)

Comprehensive hardening pass on RBAC enforcement across server and UI layers. Key changes:

### Server-Side Enforcement
- **Superadmin-only permissions (9 keys)**: `permissions.assign`, `permissions.revoke`, `roles.create`, `roles.edit`, `roles.delete`, `jobs.emergency`, `admin.config`, `monitoring.configure`, `audit.export` — permanently restricted to `superadmin` role at edge function level. Any attempt to assign these to a non-superadmin role returns `403 SUPERADMIN_ONLY_PERMISSION`.
- **Edge functions hardened**: `assign-permission-to-role` and `revoke-permission-from-role` both validate against `SUPERADMIN_ONLY_PERMISSIONS` set before executing.

### UI Enforcement
- **Permission inheritance visibility**: Base user-role permissions (5 keys: `users.view_self`, `users.edit_self`, `profile.self_manage`, `mfa.self_manage`, `session.self_manage`) display as checked/disabled with "inherited from user role" badge on all non-user roles.
- **Superadmin-only badge**: 9 restricted permissions show as disabled with "superadmin only" badge on all non-superadmin roles.
- **Effective permission count**: Role list and detail pages show union of direct + inherited permissions.
- **8 button-level gaps closed**: Create Role, Edit Role, Delete Role, Assign Role, Revoke Role, Deactivate User, Reactivate User, Revoke Sessions — all permission-gated with `checkPermission()`.
- **Reauth dialog fix**: Resolved TanStack Query v5 `onError` ordering conflict — moved reauth detection to global mutation `onError` handler, moved `refetch()` to `onSettled`.

### Regression Tests
- Updated `rw008-permission-deps-drift.test.ts` to align with `_shared/permission-deps.ts` import architecture.

### Related Documents
- [RBAC Governance Hardening Closure](../08-planning/phase-closures/rbac-governance-hardening-closure.md)
- DW-015 supersession note in [Deferred Work Register](../08-planning/deferred-work-register.md)

## Execution Control Rules

- If `code_generation: blocked` → **NO** code may be generated
- If `phase: documentation-only` → **ONLY** documentation tasks allowed
- If `approved_plan_baseline: none` → **NO** implementation allowed
- Execution MUST use the approved plan baseline defined here

## Update Rule

This file MUST be updated when any of the following occur:
- Architecture changes
- Module status changes (started, in progress, completed)
- Phase changes (documentation → development)
- Plan version changes (new version approved)
- Code generation status changes

**Failure to update this file = INVALID system state**

## Consistency Requirement

This file MUST remain consistent with:
- `master-plan.md`
- `approved-decisions.md`
- `action-tracker.md`
- Module documentation status

If inconsistency is detected → execution must **STOP** and be corrected.

## Module Status Tracker

| Module | Status | Last Updated |
|--------|--------|-------------|
| auth | implemented (A+D + hardened + MFA recovery codes [Stage 6A]; B+C deferred to v2 [DW-001/002]) | 2026-04-12 |
| rbac | implemented (Phase 2 gate 12/12 closed + Phase 3.5 hardened + ACT-049/051/052 + **RBAC governance hardening 2026-04-13**: superadmin-only permission enforcement, user-role inheritance visibility, 8 button-level gaps closed, reauth dialog fix) | 2026-04-13 |
| user-management | implemented (Phase 3C closed [ACT-032]: lifecycle, deactivate/reactivate, auth ban/unban; Phase 3D Gate 1 runtime-verified [ACT-035]) | 2026-04-10 |
| admin-panel | implemented (Phase 4 CLOSED [ACT-048] + post-closure enhancements + **RBAC governance hardening 2026-04-13**: permission inheritance badges, superadmin-only badges, effective permission counts, permission-gated action buttons) | 2026-04-13 |
| user-panel | implemented (Phase 4 CLOSED [ACT-048]: ProfilePage, SecurityPage, UserDashboard, useProfile, useMfaFactors, ReauthDialog, useInactivityTimeout) | 2026-04-12 |
| audit-logging | implemented (Phase 3B closed + Phase 3.5 hardened + ACT-053: removed overly permissive INSERT RLS policy) | 2026-04-12 |
| health-monitoring | implemented (5A + 5B + 5F complete [ACT-057, ACT-058, ACT-063]) | 2026-04-12 |
| api | implemented (Phase 3A closed + Phase 3.5 hardened: PermissionDeniedError enriched with userId/reason, centralized denial interception in handler.ts) | 2026-04-10 |
| jobs-and-scheduler | implemented (5C + 5D + 5E complete [ACT-059, ACT-060, ACT-062]) | 2026-04-12 |

## AI Behavior Constraint

- AI must **NOT** modify this file unless triggered by the defined update rules
- AI must **NOT** assume state — only this file defines the current system state
- If unclear → **STOP** and request clarification

## Dependencies

- [Constitution](constitution.md)
- [Master Plan](../08-planning/master-plan.md)

## Used By / Affects

All tasks, planning, and execution decisions.

## Risks If Changed

HIGH — incorrect state causes incorrect execution, plan drift, and system inconsistency.

## Related Documents

- [Constitution](constitution.md)
- [Master Plan](../08-planning/master-plan.md)
- [Approved Decisions](../08-planning/approved-decisions.md)
- [Action Tracker](../06-tracking/action-tracker.md)
- [Deferred Work Register](../08-planning/deferred-work-register.md)
