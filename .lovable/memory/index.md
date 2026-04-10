# Project Memory

## Core
⛔ STOP: Before ANY action, read docs/00-governance/constitution.md + docs/00-governance/system-state.md. No exceptions.
Phase: development. Code generation: allowed. Auth Phase 1 approved-partial (A+D done, B+C deferred).
Unplanned features → STOP, log in docs/08-planning/feature-proposals.md, wait for approval. Do NOT implement.
🏛️ INSTITUTIONAL GRADE: Every output must be A+/100/100. Security-first, performance-aware, auditable, diagnosable, testable.
After every implementation: test E2E → verify security → verify performance → if fail, fix & retest until pass. No partial passes.
🌿 BRANCHING: All work in feature branches (feature/PLAN-{MODULE}-{NNN}-{desc}). No direct commits to main.
📦 DEPENDENCIES: Only well-maintained npm packages (>1000 weekly downloads, updated <12mo). No experimental/niche/native-binary packages. Justify every new dep.
SSOT documentation system active — 47 files across 9 dirs under /docs.
11 constitutional rules govern all changes (see mem://governance/constitution-rules).
Mandatory reading order: constitution → system-state → approved-decisions → master-plan → modules → deps → refs.
Implementation tasks MUST also read: testing-strategy.md + regression-strategy.md.
Feature scope locked: auth, RBAC, admin/user panels, audit, monitoring, API, jobs. No expansion without approval.
Roles MUST be in separate user_roles table — NEVER on profile/users table.
Reference indexes are authoritative for shared contracts; module docs must align to them.
No new shared functions/permissions/routes/events without adding to reference indexes in same change.
⚠️ PHASE GATE PROTOCOL: After ANY implementation, update master-plan.md phase gate checkboxes with evidence (ACT-NNN). Failure = governance violation (ACT-012).
⚠️ RECONCILIATION: Reference index entries MUST match actual code (routes, functions, events). Mismatches are INVALID.
Approved plan sections cannot be dropped without explicit supersession (Constitution Rule 8).
Execution only from approved baseline v4 (Rule 9). Plan revisions are merges, not rewrites (Rule 10).
Audit retention: 90 days default (DEC-007). OAuth: Google + Apple only v1 (DEC-020).
⛔ External Supabase backend — do NOT suggest Lovable Cloud. SQL files in sql/ dir, edge functions in supabase/functions/.
📋 DEFERRED WORK: All deferred plan items MUST have entry in docs/08-planning/deferred-work-register.md. Review at every phase boundary.
📦 ARTIFACT GOVERNANCE: New migrations → update artifact-index.md + database-migration-ledger.md. Phase closures → one file in docs/08-planning/phase-closures/. Old review drafts deleted.

## Memories
- [Constitution rules](mem://governance/constitution-rules) — All 11 non-negotiable rules (updated via DEC-006)
- [Bootstrap backup](mem://governance/bootstrap-backup) — Compressed governance gates for redundancy if rules file not loaded
- [Change control workflow](mem://governance/change-control) — 9-step mandatory workflow + impact classification
- [AI operating model](mem://governance/ai-model) — Reading order, output formats, diff requirements
- [Plan governance](mem://governance/plan-governance) — Stable IDs, statuses, merge rule, execution lock, current baseline v4
- [Phase gate protocol](mem://governance/phase-gate-protocol) — Mandatory post-implementation phase gate update + reference index reconciliation
- [Feature scope](mem://features/scope) — Locked feature list, no expansion without approval
- [SSOT structure](mem://reference/ssot-structure) — Full 47-file directory listing of the SSOT documentation system
- [External Supabase](mem://constraints/external-supabase) — Uses external Supabase, migrations in sql/ dir, no Lovable Cloud
- [Deferred work protocol](mem://governance/deferred-work) — Deferred items must be registered in deferred-work-register.md with blocking deps and future phase assignment
- [Artifact governance](mem://governance/artifact-governance) — Artifact index, DB migration ledger, phase closure records, one-current-summary rule
