# Constitution

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-08

## Purpose

The supreme governance document for this project. All other documents, decisions, and actions are subordinate to the rules defined here.

## Scope

Applies to every contributor (human and AI), every document, every code change, and every plan revision across the entire project lifecycle.

## Non-Negotiable Rules

### Rule 1 — Documentation Phase Lock

No application code may be generated during the documentation phase. The current phase is tracked in `system-state.md`. Code generation is only permitted when `code_generation` is set to `allowed`.

### Rule 2 — Documentation-Code Coupling

No code change is allowed without updating all impacted documentation. If a code change affects a module, that module's doc must be updated in the same task.

### Rule 3 — No Pattern Duplication

No new pattern may be introduced if an existing pattern already covers the use case. Before creating any new utility, service, or abstraction, check `function-index.md` and existing module docs.

### Rule 4 — Definition of Done Enforcement

No task is complete without satisfying the full Definition of Done checklist defined in `definition-of-done.md`.

### Rule 5 — No Duplicate Documentation

No duplicate or conflicting documentation is allowed. Every concept has exactly one authoritative document. Cross-reference; do not copy.

### Rule 6 — Shared Component Protection

Any function, service, or component used in 2 or more modules MUST be tracked in `function-index.md` with all usage points listed. The index MUST be updated whenever a shared component is modified, added, or removed.

### Rule 7 — No Silent Behavior Change

No change may alter the behavior of existing flows without: (a) documenting the change, (b) identifying all impacted modules, (c) updating `system-state.md`.

### Rule 8 — Approved Plan Preservation

Once a plan section is marked `approved` or `approved-with-modifications`, it may NOT be dropped, rewritten, or contradicted in later plans unless:

1. The prior approved section is explicitly referenced by its stable ID
2. The reason for change is documented
3. Affected docs are listed
4. The change is recorded in `plan-changelog.md` with a `superseded-by` link
5. The updated section is re-approved

### Rule 9 — Execution Lock

No implementation may begin from a proposed or partially revised plan. Execution may ONLY use the latest approved baseline in `master-plan.md`. Any section not in `approved` or `approved-partial` status is off-limits for execution.

### Rule 10 — Plan Merge Rule

When a revised plan is created, it MUST merge new proposals into the current approved baseline rather than regenerate the plan from scratch. The approved baseline is the starting document; revisions are additive diffs, not replacements.

### Rule 11 — Critical Module Override

Auth, RBAC, and Security modules are ALWAYS classified as HIGH impact regardless of change scope. No exception. All changes to these modules require full planning, regression verification, and documentation updates.

## Dependencies

None — this is the root document.

## Used By / Affects

Every document and process in this project.

## Risks If Changed

Changing this document affects the entire governance model. Any modification is classified as **HIGH** impact and requires full review.

## Related Documents

- [System State](system-state.md)
- [AI Operating Model](ai-operating-model.md)
- [Change Control Policy](change-control-policy.md)
- [Definition of Done](definition-of-done.md)
