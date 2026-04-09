# Lovable AI Rules — Mandatory Governance Bootstrap
# ================================================
# This file is a BINDING CONTRACT. Lovable MUST obey these rules before ANY action.
# Violation = invalid work product. No exceptions.

## STOP — READ BEFORE DOING ANYTHING

Before writing, modifying, or deleting ANY file (code or documentation), you MUST read these in order:

1. `docs/00-governance/constitution.md` — the 11 non-negotiable rules
2. `docs/00-governance/system-state.md` — current phase and what is allowed RIGHT NOW
3. `docs/08-planning/approved-decisions.md` — binding decisions
4. `docs/08-planning/master-plan.md` — the approved execution plan

If ANY required document is missing or unclear → **STOP and ask for clarification.** Do not assume.

## TASK TYPE BRANCHING

- **Review-only task** (no file edits): No action tracker updates unless instructed. No output format required unless requested.
- **Change task** (any file edit): Full 9-step workflow required. Output format mandatory.

## EXECUTION GATES (HARD BLOCKS)

Check `system-state.md` YAML block. Obey these gates absolutely:

- If `code_generation: blocked` → **DO NOT generate any code.** Documentation tasks only.
- If `phase: documentation-only` → **DO NOT create implementation files.** Docs only.
- If `approved_plan_baseline: none` → **DO NOT implement anything.** No baseline = no execution.
- Execution MUST use the `approved_plan_baseline` version defined in system-state.md.
- Only plan sections with status `approved` or `approved-partial` may be executed.

## MANDATORY READING ORDER (Every Task)

For every task — no matter how small — read these in order:

1. `docs/00-governance/constitution.md` (11 rules)
2. `docs/00-governance/system-state.md` (current phase + gates)
3. `docs/08-planning/approved-decisions.md` (binding decisions)
4. `docs/08-planning/master-plan.md` (plan sections with stable IDs)
5. Relevant module docs from `docs/04-modules/` (for the module you're working on)
6. `docs/01-architecture/dependency-map.md` (if shared logic is involved)
7. Relevant reference indexes from `docs/07-reference/` (if shared components involved)

## CHANGE CONTROL (9-Step Workflow)

Follow the exact 9-step workflow in `docs/00-governance/change-control-policy.md` without reinterpretation or reordering. Do not restate or paraphrase it here — the canonical source is the policy document.

HIGH-impact changes require pre/post state tracking, blast radius assessment, and rollback plan.

Auth, RBAC, and Security modules are ALWAYS classified as HIGH impact regardless of change scope.

## OUTPUT FORMAT (Mandatory After Every Change Task)

After completing any task that modifies files, produce this output. Optional for pure review/verification tasks unless explicitly requested.

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

## PLAN REVISION FORMAT (When Modifying master-plan.md)

This format supplements but does not replace Constitution Rules 8/9/10, Approved Decisions, and Plan Merge/Preservation rules. Stable IDs must be preserved. Approved sections may only be superseded per Constitution Rule 8.

```
## Plan Version
[New version identifier]

## Sections Preserved (unchanged, listed by ID)
[e.g., PLAN-AUTH-001, PLAN-RBAC-001]

## Sections Modified (ID, reason, superseded-by link)
[Table of modifications]

## New Sections Added (with new IDs)
[List]

## Sections Removed (ID, justification, prior approval reference)
[List]

## Approved Decisions Affected (by decision ID, or successor if superseded)
[List]

## Review Required (yes/no, which section IDs)
[List]
```

## CONSTITUTIONAL COMPLIANCE

Obey all 11 constitutional rules exactly as written in `docs/00-governance/constitution.md`. This file does not redefine them.

Key reminders (non-authoritative — the Constitution is the source of truth):

- Roles MUST be in a separate `user_roles` table — NEVER on profile/users table
- Feature scope is locked — no expansion without approval
- Moderator role is deferred to v2 per active decision record — do not implement
- MFA recovery follows the active decision record (currently: 10 codes, 8 alphanumeric chars)
- If required documents are missing or unclear → STOP, do not assume

## AUTHORITY HIERARCHY

For shared contracts (functions, permissions, routes, events, config keys, env vars), **reference indexes are authoritative**. Module docs must align to them, not the other way around.

## NO INVENTION WITHOUT INDEXING

Do not invent new shared functions, permissions, routes, events, config keys, or env vars unless they are added to the appropriate reference index in the same governed change.

## REFERENCE INDEX MAINTENANCE

When modifying code that affects shared components, you MUST update the relevant indexes:

- `docs/07-reference/function-index.md` — shared/reusable functions
- `docs/07-reference/permission-index.md` — RBAC permissions
- `docs/07-reference/route-index.md` — API and UI routes
- `docs/07-reference/event-index.md` — system events
- `docs/07-reference/config-index.md` — configuration keys
- `docs/07-reference/env-var-index.md` — environment variables

## DEPENDENCY ORDER (Implementation Sequence)

Implementation must follow the dependency order defined in `docs/08-planning/master-plan.md`. Do NOT implement a module before its dependencies are complete.

Current sequence (non-authoritative convenience summary — master-plan.md is canonical):

1. ~~PLAN-GOV-001~~ (implemented)
2. PLAN-AUTH-001 (Authentication)
3. PLAN-RBAC-001 (RBAC — depends on Auth)
4. PLAN-USRMGMT-001, PLAN-AUDIT-001, PLAN-API-001 (parallel, after RBAC)
5. PLAN-ADMIN-001 (after RBAC + User Management)
6. PLAN-USRPNL-001 (after Auth)
7. PLAN-HEALTH-001, PLAN-JOBS-001 (independent, any time after GOV)

## DOCUMENTATION LOCATIONS

```
docs/
├── 00-governance/    — Constitution, change control, system state, AI rules
├── 01-architecture/  — Architecture overview, dependency map, design principles
├── 02-security/      — Auth security, authorization, input validation
├── 03-performance/   — Caching, DB performance, strategy
├── 04-modules/       — Module specs (auth, rbac, admin, user, audit, health, api, jobs)
├── 05-quality/       — Testing strategy, regression strategy
├── 06-tracking/      — Action tracker, risk register, regression watchlist
├── 07-reference/     — Function, permission, route, event, config, env var indexes
└── 08-planning/      — Master plan, approved decisions, changelog, review log
```

## FEATURE PROPOSAL PROTOCOL (MANDATORY)

If you identify a feature, enhancement, or capability that is NOT in the approved `master-plan.md`:

1. **STOP** — do NOT implement it, do NOT modify the master plan, do NOT create code or schema
2. **Log a proposal** in `docs/08-planning/feature-proposals.md` using the mandatory schema
3. **Notify** the user that a feature proposal has been logged and requires review
4. **Wait** for explicit approval from the project lead
5. **Only after approval**: integrate into master-plan.md (with stable ID, DEC entry, changelog entry) and THEN implement via normal 9-step workflow

This applies to ALL unplanned features — no matter how small, useful, or obvious they seem. Scope is locked. No exceptions.

## FINAL WARNING

If you skip reading governance docs, generate code when blocked, drop plan sections, or fail to update documentation — the work is INVALID and must be reverted. This is not advisory. This is mandatory.
