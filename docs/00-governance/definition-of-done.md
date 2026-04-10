# Definition of Done

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-10

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
- [ ] **Phase gate checkboxes** in `master-plan.md` updated if work satisfies any phase gate condition (with evidence reference)
- [ ] Plan artifacts updated if plan-level changes occurred
- [ ] Execution performed ONLY against approved plan baseline (no proposed sections used)
- [ ] `artifact-index.md` updated if new migrations, closure docs, or durable artifacts created
- [ ] `database-migration-ledger.md` updated if any SQL migration applied
- [ ] Phase closure file created/updated if a phase gate status changed
- [ ] No Constitution rule violated

## Quality Checklist (ALL must be satisfied for implementation tasks)

- [ ] **End-to-end tested** — feature verified in its complete flow, not just the changed file
- [ ] **Security assessed** — no new attack surfaces, no permission gaps, no data leaks
- [ ] **Performance assessed** — no regressions in latency, bundle size, or query performance
- [ ] **All tests pass** — if any test fails, fix and retest until ALL pass. No partial passes.
- [ ] **Code is auditable** — clear audit trail: who did what, when, why. Structured logging.
- [ ] **Code is diagnosable** — no silent failures, no swallowed errors, clear error paths
- [ ] **Code is testable** — unit, integration, and E2E testable. Separation of concerns maintained.
- [ ] **Testing strategy followed** — coverage targets met per `testing-strategy.md`
- [ ] **Regression strategy followed** — baseline comparisons done per `regression-strategy.md`

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
- `master-plan.md` (including **phase gate checkboxes** with evidence references)
- `approved-decisions.md` (if applicable)
- `plan-changelog.md`

No change may bypass approved plan baseline.

## Reference Index Reconciliation Requirement

When implementing code that corresponds to reference index entries (routes, functions, events, permissions):
- The **actual implementation** must match the reference index contract
- If the implementation uses different names/paths than the index, the index MUST be updated to reflect the actual implementation
- Mismatches between reference indexes and code are **INVALID** — they must be caught and corrected during Step 9 (verification)

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
