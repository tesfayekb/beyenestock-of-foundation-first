# Definition of Done

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-09

## Purpose

Defines the strict completion criteria for all tasks.
A task is not considered complete unless ALL conditions are satisfied.

## Scope

Applies to all tasks:
- Documentation updates
- Code changes
- Plan revisions
- Reviews

## Enforcement Rule (CRITICAL)

If ANY checklist item is not satisfied:
- The task is **INVALID** (not partially complete)
- The task must **NOT** be marked as done
- The task must **NOT** proceed to next steps
- **No partial completion is allowed.**
- If required documentation (module, dependency, or reference index) is missing or unclear, the task must **STOP** and request clarification instead of proceeding with assumptions.

## Core Checklist (ALL must be satisfied)

- [ ] All impacted documentation files updated
- [ ] `action-tracker.md` updated with task entry
- [ ] Impacted modules verified (no broken dependencies or references)
- [ ] `regression-watchlist.md` checked (for MEDIUM/HIGH impact OR shared component changes)
- [ ] Mandatory AI output format included in response
- [ ] `system-state.md` updated if system state changed
- [ ] Plan artifacts updated if plan-level changes occurred
- [ ] Execution performed ONLY against approved plan baseline (no proposed sections used)
- [ ] No Constitution rule violated

## Verification Requirements (CLARIFIED)

Verification must include:
- **Dependency validation** (no broken module relationships)
- **Reference validation** (indexes reflect current usage)
- **Flow validation** (existing behavior not unintentionally altered)

Verification must be **explicit — not assumed.**

## Additional Requirements by Impact Level

### LOW Impact
- Core checklist only

### MEDIUM Impact
- Core checklist
- Pre-implementation plan documented
- Shared dependencies verified
- Reference indexes updated if shared components affected

### HIGH Impact

Includes:
- Auth
- RBAC
- Security-related modules
- Schema changes
- Shared functions/services

Requirements:
- Core checklist
- Pre-implementation plan documented
- Shared dependencies verified
- Reference indexes updated
- Regression protection loop completed
- All impacted flows explicitly verified

## Regression Protection Rule

For MEDIUM/HIGH impact OR shared component changes:
1. Must check `regression-watchlist.md`
2. Must validate affected flows
3. If new risk is identified → MUST add to `regression-watchlist.md`

## Plan Integrity Requirement

Plan-related changes MUST update:
- `master-plan.md`
- `approved-decisions.md` (if applicable)
- `plan-changelog.md`

No change may bypass approved plan baseline.

## Dependencies

- [Constitution](constitution.md)
- [Change Control Policy](change-control-policy.md)
- [AI Operating Model](ai-operating-model.md)

## Used By / Affects

All task completion decisions.

## Risks If Changed

HIGH — weakening this checklist allows regression, drift, and inconsistent system behavior.

## Related Documents

- [Constitution](constitution.md)
- [Change Control Policy](change-control-policy.md)
- [AI Operating Model](ai-operating-model.md)
- [Action Tracker](../06-tracking/action-tracker.md)
- [Regression Watchlist](../06-tracking/regression-watchlist.md)
