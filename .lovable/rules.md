# Lovable AI Rules — Mandatory Governance Bootstrap
# ================================================
# This file is a BINDING CONTRACT. Lovable MUST obey these rules before ANY action.
# Violation = invalid work product. No exceptions.

## STOP — READ BEFORE DOING ANYTHING

Before writing, modifying, or deleting ANY file (code or documentation), you MUST read these in order:

1. `trading-docs/00-governance/constitution.md` — trading system rules
2. `trading-docs/00-governance/system-state.md` — current phase and gates
3. `trading-docs/08-planning/approved-decisions.md` — binding decisions
4. `trading-docs/08-planning/MASTER_PLAN.md` — the approved execution plan (v3.2)

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

1. `trading-docs/00-governance/constitution.md` (11 rules)
2. `trading-docs/00-governance/system-state.md` (current phase + gates)
3. `trading-docs/08-planning/approved-decisions.md` (binding decisions)
4. `trading-docs/08-planning/MASTER_PLAN.md` (plan sections with stable IDs)
5. Relevant module docs from `trading-docs/04-modules/` (for the module you're working on)
6. `trading-docs/01-architecture/dependency-map.md` (if shared logic is involved)
7. Relevant reference indexes from `trading-docs/07-reference/` (if shared components involved)

## CHANGE CONTROL (9-Step Workflow)

Follow the exact 9-step workflow in `trading-docs/00-governance/change-control-policy.md` without reinterpretation or reordering. Do not restate or paraphrase it here — the canonical source is the policy document.

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

## PLAN REVISION FORMAT (When Modifying MASTER_PLAN.md)

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

Obey all 11 constitutional rules exactly as written in `trading-docs/00-governance/constitution.md`. This file does not redefine them.

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

## REFERENCE INDEX MAINTENANCE AND RECONCILIATION

When modifying code that affects shared components, you MUST update the relevant indexes:

- `trading-docs/07-reference/function-index.md` — shared/reusable functions
- `trading-docs/07-reference/permission-index.md` — RBAC permissions
- `trading-docs/07-reference/route-index.md` — API and UI routes
- `trading-docs/07-reference/event-index.md` — system events
- `trading-docs/07-reference/config-index.md` — configuration keys
- `trading-docs/07-reference/env-var-index.md` — environment variables

**Reconciliation rule:** When implementing code that corresponds to reference index entries, the actual implementation (names, paths, signatures) MUST match the index. If you use a different name/path than what the index specifies, you MUST update the index to match reality. Mismatches between indexes and code are INVALID.

## PHASE GATE VERIFICATION PROTOCOL (MANDATORY)

After completing ANY implementation task that falls within a phase (as defined in `MASTER_PLAN.md` Development Phases):

1. **Open the phase gate checklist** in `MASTER_PLAN.md` for the current phase
2. **Check each gate item** — does this task satisfy or partially satisfy any gate condition?
3. **Update the checkbox** from `[ ]` to `[x]` with an evidence reference (ACT-NNN + brief description)
4. **If partially satisfied**, leave as `[ ]` but add an italicized note showing partial progress
5. **Record the gate update** in your action tracker entry under a `phase_gates_updated` field

This is not optional. Failure to update phase gates after phase-relevant work is a governance violation (ACT-012 root cause).

## DEPENDENCY ORDER (Implementation Sequence)

Implementation must follow the dependency order defined in `trading-docs/08-planning/MASTER_PLAN.md`. Do NOT implement a module before its dependencies are complete.

Current sequence (non-authoritative convenience summary — MASTER_PLAN.md is canonical):

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

## VERSION CONTROL — BRANCHING RULES (MANDATORY)

All implementation work MUST be done in feature branches, NOT on the main/default branch.

- **Branch naming**: `feature/PLAN-{MODULE}-{NNN}-{short-description}` (e.g., `feature/PLAN-AUTH-001-email-password`)
- **One branch per feature/phase**: Each implementation task or phase gate gets its own branch
- **No direct commits to main**: All work merges via pull request after phase gate verification
- **Branch scope**: Each branch should correspond to a single plan section or sub-task — do not bundle unrelated changes
- **Clean history**: Branches must pass all tests before merge. Failed branches must be fixed, not force-merged.

## DEPENDENCY COMPATIBILITY — NO UNSUPPORTED SOFTWARE (MANDATORY)

Do NOT install packages, tools, or dependencies that may not be supported by other AI platforms or standard toolchains working on this project.

- **Only use well-established, actively maintained npm packages** — no experimental, abandoned, or niche libraries
- **No platform-specific tooling** that locks the project to a single AI IDE or environment
- **No packages requiring native binaries** unless explicitly approved (e.g., no node-gyp dependencies)
- **Prefer packages already in the project** (`package.json`) before adding new ones
- **Before adding ANY new dependency**: verify it is actively maintained (updated within last 12 months), has >1000 weekly npm downloads, and does not introduce security vulnerabilities
- **Document new dependencies**: Every new package added must be justified in the change summary output format
- **No version pinning to pre-release/alpha/beta** unless explicitly approved

## FEATURE PROPOSAL PROTOCOL (MANDATORY)

If you identify a feature, enhancement, or capability that is NOT in the approved `MASTER_PLAN.md`:

1. **STOP** — do NOT implement it, do NOT modify the master plan, do NOT create code or schema
2. **Log a proposal** in `trading-docs/08-planning/feature-proposals.md` using the mandatory schema
3. **Notify** the user that a feature proposal has been logged and requires review
4. **Wait** for explicit approval from the project lead
5. **Only after approval**: integrate into MASTER_PLAN.md (with stable ID, DEC entry, changelog entry) and THEN implement via normal 9-step workflow

This applies to ALL unplanned features — no matter how small, useful, or obvious they seem. Scope is locked. No exceptions.

## QUALITY MANDATE — INSTITUTIONAL GRADE (NON-NEGOTIABLE)

This is an institutional-grade project. Every output must meet A+ / 100/100 standard. "Good enough" is not acceptable.

### Quality Standard (Every Task)

# Note: docs/02-security/ and docs/03-performance/ are foundation-layer docs.
# No trading-docs equivalents exist. These references are intentionally kept.

1. **Security-first**: Every task must assess security implications. Read and follow `docs/02-security/` guidelines. Auth, RBAC, input validation, and data access are never optional considerations.
2. **Performance-aware**: Every task must assess performance implications. Read and follow `docs/03-performance/` guidelines. No unoptimized queries, unbounded lists, or missing indexes.
3. **Auditable**: Every piece of code must have a clear audit trail — who did what, when, why. Logging, structured errors, and action tracking are mandatory.
4. **Diagnosable**: Every failure path must be clear and traceable. No silent failures, no swallowed errors, no ambiguous states. Errors must be structured, logged, and actionable.
5. **Testable**: Every piece of code must be testable at unit, integration, and E2E levels. No tightly coupled, untestable logic. Separation of concerns is mandatory.

### End-to-End Verification (Every Implementation Task)

After completing any implementation task:

1. **Test end-to-end** — verify the feature works in its complete flow, not just the changed file
2. **Verify security** — confirm no new attack surfaces, no permission gaps, no data leaks
3. **Verify performance** — confirm no regressions in latency, bundle size, or query performance
4. **If ANY test fails → FIX and RETEST** — repeat until ALL tests pass. No partial passes accepted. Do not declare done with known failures.
5. **Verify documentation alignment** — confirm all docs reflect the implementation accurately

### Mandatory Testing Reading (Implementation Tasks)

For any implementation task, you MUST also read:

- `trading-docs/05-quality/testing-strategy.md` — testing governance, coverage targets, test pyramid
- `trading-docs/05-quality/regression-strategy.md` — regression prevention, baselines, cross-module checks

These are not optional. They define the testing contract for this project.

### Code Quality Non-Negotiables

- No `any` types in TypeScript (use proper typing)
- No disabled ESLint rules without documented justification
- No hardcoded secrets, tokens, or credentials
- No console.log in production code (use structured logging)
- No TODO/FIXME without a tracked action item
- No dead code or unused imports
- Error boundaries on all major UI sections
- Loading and error states for all async operations
- Input validation on all user-facing forms (client + server)
- Proper HTTP status codes and error responses

## FINAL WARNING

If you skip reading governance docs, generate code when blocked, drop plan sections, fail to update documentation, skip testing, or produce code that is not auditable/diagnosable/testable — the work is INVALID and must be reverted. This is not advisory. This is mandatory.
