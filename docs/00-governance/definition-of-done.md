# Definition of Done

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-08

## Purpose

Defines the checklist that must be satisfied before any task can be considered complete.

## Scope

All tasks: documentation, code, plan revisions, reviews.

## Checklist

No task is complete unless ALL of the following are true:

- [ ] All impacted documentation files updated
- [ ] `action-tracker.md` updated with task entry
- [ ] Impacted modules verified (no broken dependencies)
- [ ] `regression-watchlist.md` checked (for MEDIUM/HIGH impact changes)
- [ ] AI output format included in response (Change Summary, Modules Impacted, etc.)
- [ ] `system-state.md` updated if system state changed
- [ ] Plan artifacts updated if plan-level changes occurred
- [ ] No Constitution rule violated

## Additional Requirements by Impact Level

### LOW Impact
- Standard checklist above

### MEDIUM Impact
- Standard checklist
- Pre-implementation plan documented
- Shared dependencies verified

### HIGH Impact
- Standard checklist
- Pre-implementation plan documented
- Shared dependencies verified
- Regression protection loop completed
- All reference indexes verified

## Dependencies

- [Constitution](constitution.md) — Rule 4
- [Change Control Policy](change-control-policy.md)

## Used By / Affects

Every task completion gate.

## Risks If Changed

HIGH — weakening this checklist compromises quality controls.

## Related Documents

- [Constitution](constitution.md)
- [Change Control Policy](change-control-policy.md)
- [AI Operating Model](ai-operating-model.md)
- [Action Tracker](../06-tracking/action-tracker.md)
