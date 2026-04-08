# AI Operating Model

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-08

## Purpose

Defines how AI agents must behave when working on this project. This is not advisory — it is mandatory.

## Scope

Applies to every AI interaction: code generation, documentation updates, plan revisions, and reviews.

## Mandatory Reading Order

Before performing ANY task, the AI must read these documents in order:

1. `docs/00-governance/constitution.md`
2. `docs/00-governance/system-state.md`
3. `docs/08-planning/approved-decisions.md`
4. `docs/08-planning/master-plan.md`
5. Relevant module docs (from `docs/04-modules/`)
6. `docs/01-architecture/dependency-map.md` (if shared logic is involved)
7. Relevant reference indexes (from `docs/07-reference/`) (if shared components are involved)

## AI Behavior Rules

1. Must read governance + relevant module docs before any action
2. Must identify impacted modules first
3. Must follow the 9-step change-control workflow
4. Must not introduce new patterns if existing ones apply
5. Must not generate code without updating documentation
6. Must reference the approved plan baseline before execution
7. Must never execute against a proposed or partially revised plan
8. Must produce the mandatory output format after every task
9. Must produce the plan revision output format after every plan update

## Mandatory AI Output Format (Every Task)

```
## Change Summary
[What was done]

## Modules Impacted
[List of affected modules]

## Docs Updated
[List of documentation files modified]

## References Updated
[List of reference index files modified]

## Verification Status
[How the change was verified]

## Risks / Follow-up
[Any outstanding risks or required follow-up]
```

## Mandatory Plan Revision Output Format (Every Plan Update)

```
## Plan Version
[New version identifier]

## Sections Preserved (unchanged from approved baseline, listed by ID)
[List of section IDs unchanged]

## Sections Modified (with ID, reason, superseded-by link)
[Table of modifications]

## New Sections Added (with new IDs)
[List of new section IDs and descriptions]

## Sections Removed (with ID, justification, reference to prior approval)
[List of removed section IDs with rationale]

## Approved Decisions Affected (by decision ID)
[List of DEC-NNN IDs affected]

## Review Required (yes/no, which section IDs)
[Sections requiring re-approval]
```

## Diff Requirement

Before accepting any revised plan, the AI must produce a diff against the approved baseline showing:

- Sections unchanged (by ID)
- Sections modified (by ID with reason)
- Newly added sections (with new IDs)
- Removed sections (by ID with justification)
- Conflicts with previously approved decisions (by decision ID)

## Dependencies

- [Constitution](constitution.md)
- [System State](system-state.md)
- [Master Plan](../08-planning/master-plan.md)
- [Approved Decisions](../08-planning/approved-decisions.md)

## Used By / Affects

All AI-driven tasks. This is the behavioral contract for AI agents.

## Risks If Changed

HIGH — changes here alter AI behavior across the entire project.

## Related Documents

- [Constitution](constitution.md)
- [Change Control Policy](change-control-policy.md)
- [Definition of Done](definition-of-done.md)
