# Artifact Index

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-10

## Purpose

Single catalog of important implementation artifacts that must remain discoverable after their creation phase. This index does NOT duplicate executable content — it references artifacts and explains their role, status, and relationships.

## Scope

All durable artifacts produced during implementation that have ongoing reference value:
- SQL migrations (applied to Supabase)
- Edge functions of record
- Phase closure documents
- Corrective migrations
- Execution/verification records
- Runbooks and manual execution docs

## Enforcement Rules (CRITICAL)

- Every artifact that affects database structure, phase closure, or security posture MUST have an entry here
- Entries are **append-only** — historical entries are never deleted, only marked `superseded` or `archived`
- When a corrective migration is created, the original must be updated to `superseded` with a `superseded_by` reference
- When a phase closure file is created, any prior review drafts MUST be removed from the repo (one-current-summary rule)
- Artifacts without an index entry are not formally governed and may be lost

## Entry Schema (MANDATORY)

| Field | Required | Description |
|-------|----------|-------------|
| `artifact_id` | Yes | Stable identifier: `ART-NNN` |
| `artifact_type` | Yes | `migration`, `phase-closure`, `runbook`, `evidence`, `execution-record`, `reference`, `edge-function` |
| `title` | Yes | Short descriptive title |
| `source_path` | Yes | Repo path to the artifact |
| `created_date` | Yes | Date artifact was created |
| `owning_phase` | Yes | Phase that produced this artifact |
| `owning_plan_section` | If applicable | PLAN-XXX-NNN reference |
| `execution_order` | For migrations | Sequence number within the phase |
| `status` | Yes | `active`, `superseded`, `archived`, `historical-only` |
| `superseded_by` | If superseded | ART-NNN of the replacement |
| `related_actions` | Yes | ACT-NNN references |
| `related_decisions` | If applicable | DEC-NNN references |
| `notes` | If applicable | Additional context |

## One-Current-Summary Rule

For each phase, only **one** authoritative closure document may exist in the repo:
- Review drafts (v1, v2, v3...) must NOT persist as separate active docs
- Version history belongs in the action tracker and plan changelog
- If a closure doc is revised, update the file in-place; the revision trail is captured through action tracker entries

---

## Registry

### ART-001: RBAC Schema Migration

| Field | Value |
|-------|-------|
| **Artifact ID** | ART-001 |
| **Type** | reference |
| **Title** | RBAC schema definition (tables, triggers, indexes) |
| **Source Path** | `sql/01_rbac_schema.sql` |
| **Created Date** | 2026-04-09 |
| **Owning Phase** | Phase 2 — Access Control (RBAC) |
| **Owning Plan Section** | PLAN-RBAC-001 |
| **Execution Order** | 1 |
| **Status** | `active` |
| **Related Actions** | ACT-015 |
| **Notes** | Defines 5 tables (roles, permissions, user_roles, role_permissions, audit_logs), immutability triggers, last-superadmin protection trigger, indexes. Applied manually to external Supabase. |

---

### ART-002: RBAC Security Helpers Migration

| Field | Value |
|-------|-------|
| **Artifact ID** | ART-002 |
| **Type** | reference |
| **Title** | RBAC security helper functions |
| **Source Path** | `sql/02_rbac_security_helpers.sql` |
| **Created Date** | 2026-04-09 |
| **Owning Phase** | Phase 2 — Access Control (RBAC) |
| **Owning Plan Section** | PLAN-RBAC-001 |
| **Execution Order** | 2 |
| **Status** | `active` |
| **Related Actions** | ACT-015 |
| **Notes** | 4 SECURITY DEFINER functions: is_superadmin, has_role, has_permission (with logical superadmin inheritance + null-safety), get_my_authorization_context. |

---

### ART-003: RBAC RLS Policies Migration

| Field | Value |
|-------|-------|
| **Artifact ID** | ART-003 |
| **Type** | reference |
| **Title** | RBAC Row Level Security policies |
| **Source Path** | `sql/03_rbac_rls_policies.sql` |
| **Created Date** | 2026-04-09 |
| **Owning Phase** | Phase 2 — Access Control (RBAC) |
| **Owning Plan Section** | PLAN-RBAC-001 |
| **Execution Order** | 3 |
| **Status** | `active` |
| **Related Actions** | ACT-015 |
| **Notes** | 5 RLS policies using has_permission for roles.view and audit.view, plus self-access on user_roles. |

---

### ART-004: RBAC Seed Data Migration

| Field | Value |
|-------|-------|
| **Artifact ID** | ART-004 |
| **Type** | reference |
| **Title** | RBAC seed data (roles, permissions, mappings) |
| **Source Path** | `sql/04_rbac_seed.sql` |
| **Created Date** | 2026-04-09 |
| **Owning Phase** | Phase 2 — Access Control (RBAC) |
| **Owning Plan Section** | PLAN-RBAC-001 |
| **Execution Order** | 4 |
| **Status** | `active` |
| **Related Actions** | ACT-015 |
| **Notes** | 3 base roles (superadmin/admin/user), 29 permissions, admin→28 permissions, user→5 self-scope, auto-assign trigger. |

---

### ART-005: Superadmin Role Assignment

| Field | Value |
|-------|-------|
| **Artifact ID** | ART-005 |
| **Type** | migration |
| **Title** | Assign superadmin role to initial user |
| **Source Path** | `supabase/migrations/20260410041231_0271722c-6c01-4096-a9ea-9b4c2b83fe5e.sql` |
| **Created Date** | 2026-04-10 |
| **Owning Phase** | Phase 2 — Access Control (RBAC) |
| **Execution Order** | 5 |
| **Status** | `active` |
| **Related Actions** | ACT-015 |
| **Notes** | Assigns superadmin role to tesfayekb@gmail.com via role_id lookup. |

---

### ART-006: User Role Assignment

| Field | Value |
|-------|-------|
| **Artifact ID** | ART-006 |
| **Type** | migration |
| **Title** | Assign user role to initial user |
| **Source Path** | `supabase/migrations/20260410041459_5f9277ff-3b9c-436d-882c-0147b2e4222f.sql` |
| **Created Date** | 2026-04-10 |
| **Owning Phase** | Phase 2 — Access Control (RBAC) |
| **Execution Order** | 6 |
| **Status** | `active` |
| **Related Actions** | ACT-015 |
| **Notes** | Assigns user base role to tesfayekb@gmail.com via role_id lookup. |

---

### ART-007: handle_new_user Fix (BROKEN — SUPERSEDED)

| Field | Value |
|-------|-------|
| **Artifact ID** | ART-007 |
| **Type** | migration |
| **Title** | handle_new_user fix attempt — contains broken INSERT |
| **Source Path** | `supabase/migrations/20260410041727_9c12d489-2bf2-4f1c-ab8e-39463d360900.sql` |
| **Created Date** | 2026-04-10 |
| **Owning Phase** | Phase 2 — Access Control (RBAC) |
| **Execution Order** | 7 |
| **Status** | `superseded` |
| **Superseded By** | ART-008, ART-009 |
| **Related Actions** | ACT-020, ACT-021 |
| **Notes** | ⚠️ **HISTORICAL ONLY.** Contains broken `INSERT INTO user_roles (user_id, role)` using non-existent `role` column. The `handle_new_user()` definition in this file was superseded by ART-008 and authoritatively corrected by ART-009. Other functions in this file (handle_new_user_role, update_updated_at, immutability triggers, last-superadmin guard) are correct and remain active. Migration file is immutable per Supabase convention — never deleted. |

---

### ART-008: handle_new_user Partial Fix

| Field | Value |
|-------|-------|
| **Artifact ID** | ART-008 |
| **Type** | migration |
| **Title** | handle_new_user partial fix — profile-only |
| **Source Path** | `supabase/migrations/20260410043317_7272bb37-26e5-4612-b976-e5ab9837b9de.sql` |
| **Created Date** | 2026-04-10 |
| **Owning Phase** | Phase 2 — Access Control (RBAC) |
| **Execution Order** | 8 |
| **Status** | `superseded` |
| **Superseded By** | ART-009 |
| **Related Actions** | ACT-020 |
| **Notes** | Applied the profile-only fix to the live DB. Superseded by ART-009 as the formal corrective record. |

---

### ART-009: handle_new_user Authoritative Corrective Migration

| Field | Value |
|-------|-------|
| **Artifact ID** | ART-009 |
| **Type** | migration |
| **Title** | ACT-021: Authoritative corrective migration for handle_new_user() |
| **Source Path** | `supabase/migrations/20260410045232_aab0e02e-9dfe-4340-ac56-601f37c09992.sql` |
| **Created Date** | 2026-04-10 |
| **Owning Phase** | Phase 2 — Access Control (RBAC) |
| **Execution Order** | 9 |
| **Status** | `active` |
| **Related Actions** | ACT-021 |
| **Related Decisions** | — |
| **Notes** | Formal corrective record per governance rules. `handle_new_user()` = profile creation ONLY. `handle_new_user_role()` = role assignment via `role_id` lookup. DB was already correct via ART-008; this migration serves as the authoritative governance artifact. |

---

### ART-010: Phase 2 RBAC Closure Record

| Field | Value |
|-------|-------|
| **Artifact ID** | ART-010 |
| **Type** | phase-closure |
| **Title** | Phase 2 — Access Control (RBAC) closure record |
| **Source Path** | `docs/08-planning/phase-closures/phase-02-rbac-closure.md` |
| **Created Date** | 2026-04-10 |
| **Owning Phase** | Phase 2 — Access Control (RBAC) |
| **Status** | `active` |
| **Related Actions** | ACT-015, ACT-016, ACT-017, ACT-018, ACT-019, ACT-020, ACT-021 |
| **Related Decisions** | DEC-021, DEC-022 |
| **Notes** | Authoritative single-file closure record for Phase 2. All prior review drafts (v1–v7) deleted per one-current-summary rule. |

---

## Summary Dashboard

| ART ID | Type | Title | Phase | Status |
|--------|------|-------|-------|--------|
| ART-001 | reference | RBAC schema | Phase 2 | `active` |
| ART-002 | reference | RBAC security helpers | Phase 2 | `active` |
| ART-003 | reference | RBAC RLS policies | Phase 2 | `active` |
| ART-004 | reference | RBAC seed data | Phase 2 | `active` |
| ART-005 | migration | Superadmin role assignment | Phase 2 | `active` |
| ART-006 | migration | User role assignment | Phase 2 | `active` |
| ART-007 | migration | handle_new_user fix (BROKEN) | Phase 2 | `superseded` |
| ART-008 | migration | handle_new_user partial fix | Phase 2 | `superseded` |
| ART-009 | migration | handle_new_user corrective | Phase 2 | `active` |
| ART-010 | phase-closure | Phase 2 RBAC closure | Phase 2 | `active` |
| ART-011 | edge-function | Shared API helpers (_shared/) | Phase 3 | `active` |
| ART-012 | migration | Audit logs INSERT policy | Phase 3 | `active` |

---

### ART-011: Shared API Helpers

| Field | Value |
|-------|-------|
| **Artifact ID** | ART-011 |
| **Type** | edge-function |
| **Title** | Shared edge function infrastructure (Stage 3A) |
| **Source Path** | `supabase/functions/_shared/` |
| **Created Date** | 2026-04-10 |
| **Owning Phase** | Phase 3 — Core Services |
| **Owning Plan Section** | PLAN-API-001, PLAN-AUDIT-001 |
| **Status** | `active` |
| **Related Actions** | ACT-023 |
| **Notes** | 10 files: mod.ts (barrel), errors.ts, api-error.ts, authenticate-request.ts, validate-request.ts, normalize-request.ts, authorization.ts, audit.ts, handler.ts, cors.ts, supabase-admin.ts. 26 unit tests passing. Implements: authenticateRequest, validateRequest, normalizeRequest, apiError, checkPermissionOrThrow, requireSelfScope, requireRole, requireRecentAuth, logAuditEvent, createHandler, apiSuccess. |

---

### ART-012: Audit Logs INSERT Policy Migration

| Field | Value |
|-------|-------|
| **Artifact ID** | ART-012 |
| **Type** | migration |
| **Title** | Audit logs INSERT policy (append-only defense-in-depth) |
| **Source Path** | `supabase/migrations/20260410060801_3dcde460-0ec4-415c-a1ff-0630fd7e9e8f.sql` |
| **Created Date** | 2026-04-10 |
| **Owning Phase** | Phase 3 — Core Services |
| **Owning Plan Section** | PLAN-AUDIT-001 |
| **Execution Order** | 10 |
| **Status** | `active` |
| **Related Actions** | ACT-023 |
| **Notes** | Adds INSERT policy on audit_logs for authenticated users. WITH CHECK (true) is intentional — audit writes come from server-side edge functions. No UPDATE/DELETE policies — append-only preserved. |

---

## Dependencies

- [Database Migration Ledger](database-migration-ledger.md)
- [Action Tracker](../06-tracking/action-tracker.md)
- [Phase Closures](../08-planning/phase-closures/)

## Used By / Affects

All future implementation work, onboarding, debugging, and audit trail.

## Risks If Changed

HIGH — lost artifact references make historical reasoning and DB structure interpretation impossible.

## Related Documents

- [Database Migration Ledger](database-migration-ledger.md)
- [Action Tracker](../06-tracking/action-tracker.md)
- [Deferred Work Register](../08-planning/deferred-work-register.md)
- [Project Structure](../01-architecture/project-structure.md)
