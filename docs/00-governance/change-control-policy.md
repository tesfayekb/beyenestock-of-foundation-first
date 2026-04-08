# Change Control Policy

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-08

## Purpose

Defines the mandatory workflow for every change in this project — documentation, code, plan revisions, and configuration updates.

## Scope

Applies to ALL changes without exception.

## Enforcement Rule (CRITICAL)

- All 9 steps MUST be executed **in order**
- No step may be skipped, reordered, or partially completed
- If ANY step is not satisfied → the change is **INVALID**
- Invalid changes must **NOT** proceed or be marked complete

## Mandatory 9-Step Workflow

Every change MUST follow this exact sequence:

1. **Read** `constitution.md` and `system-state.md`
2. **Read** all relevant module documents
3. **Identify** impacted modules, dependencies, and reference indexes
4. **Validate context:**
   - Required documentation exists
   - Dependencies are understood
   - If unclear → **STOP** and request clarification
5. **Plan** changes before implementation
6. **Implement** changes (ONLY against approved plan baseline)
7. **Update** ALL affected documentation (modules + reference indexes)
8. **Update** `action-tracker.md`
9. **Verify:**
   - Dependencies intact
   - Reference indexes accurate
   - No unintended behavior changes
   - Required regression checks completed
10. **Update** `system-state.md` if system state changed

## Impact Classification

| Level | Criteria | Requirements |
|-------|----------|-------------|
| **LOW** | Isolated module, no shared dependencies | Standard workflow |
| **MEDIUM** | Affects shared services or multiple modules | Pre-implementation plan REQUIRED |
| **HIGH** | Affects auth, RBAC, schema, shared functions, or security | Pre-plan + regression validation REQUIRED |

### Critical Module Override

Auth, RBAC, and Security modules are ALWAYS classified as HIGH impact regardless of change scope. No exception.

## Reference Index Enforcement

If a change affects:
- Shared functions/services
- Routes
- Permissions
- Events
- Config or environment variables

Then corresponding reference indexes MUST be updated:
- `function-index.md`
- `route-index.md`
- `permission-index.md`
- `event-index.md`
- `config-index.md`
- `env-var-index.md`

**Failure to update reference indexes = INVALID change.**

## Regression Protection Loop

For MEDIUM/HIGH impact OR shared component changes:

1. Check `regression-watchlist.md`
2. Verify affected flows are not broken
3. If new risk discovered → MUST add to `regression-watchlist.md`

## Plan Change Rules

Plan revisions MUST:
- Produce a diff against the approved baseline
- Follow the Plan Merge Rule (Constitution Rule 10)
- Respect the Approved Plan Preservation Rule (Constitution Rule 8)
- Respect the Execution Lock Rule (Constitution Rule 9)
- Maintain stable IDs and supersession links

## Dependencies

- [Constitution](constitution.md)
- [System State](system-state.md)
- [Regression Watchlist](../06-tracking/regression-watchlist.md)

## Used By / Affects

All changes and tasks in the project.

## Risks If Changed

HIGH — improper changes here break the entire governance model.

## Related Documents

- [Constitution](constitution.md)
- [AI Operating Model](ai-operating-model.md)
- [Definition of Done](definition-of-done.md)
- [Action Tracker](../06-tracking/action-tracker.md)
- [Regression Watchlist](../06-tracking/regression-watchlist.md)
