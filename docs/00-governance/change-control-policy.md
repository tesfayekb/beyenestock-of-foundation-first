# Change Control Policy

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-08

## Purpose

Defines the mandatory workflow for every change in this project — documentation or code.

## Scope

All changes: documentation edits, code changes, plan revisions, configuration updates.

## Mandatory 9-Step Workflow

Every change must follow these steps in order:

1. **Read** `constitution.md` and `system-state.md`
2. **Read** all relevant module documents
3. **Identify** impacted modules and references
4. **Plan** changes before implementation
5. **Implement** changes
6. **Update** ALL affected documentation
7. **Update** `action-tracker.md`
8. **Verify** (tests or runtime if required)
9. **Update** `system-state.md` if system state changed

## Impact Classification

| Level | Criteria | Requirements |
|-------|----------|-------------|
| **LOW** | Isolated module, no shared dependencies | Standard workflow |
| **MEDIUM** | Affects shared services or multiple modules | Must plan before implementation |
| **HIGH** | Affects auth, RBAC, schema, shared functions, or security | Must plan before implementation + verify against `regression-watchlist.md` |

## Regression Protection Loop

Before completing any MEDIUM or HIGH change:

1. Check `regression-watchlist.md`
2. Verify affected flows are not broken
3. If new risk discovered → add to `regression-watchlist.md`

## Plan Change Rules

Plan revisions follow all rules above PLUS:

- Must produce a diff against the approved baseline (see AI Operating Model)
- Must follow the Plan Merge Rule (Constitution Rule 10)
- Must respect the Approved Plan Preservation Rule (Constitution Rule 8)
- Must respect the Execution Lock Rule (Constitution Rule 9)

## Dependencies

- [Constitution](constitution.md) — Rules 2, 7, 8, 9, 10
- [System State](system-state.md)
- [Regression Watchlist](../06-tracking/regression-watchlist.md)

## Used By / Affects

Every task and change in the project.

## Risks If Changed

HIGH — this governs all change processes.

## Related Documents

- [Constitution](constitution.md)
- [AI Operating Model](ai-operating-model.md)
- [Definition of Done](definition-of-done.md)
- [Action Tracker](../06-tracking/action-tracker.md)
- [Regression Watchlist](../06-tracking/regression-watchlist.md)
