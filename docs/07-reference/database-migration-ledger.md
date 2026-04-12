# Database Migration Ledger

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-10

## Purpose

Human-readable ledger of database structure evolution. This does NOT replace `supabase/migrations/` or `sql/` — it references migrations and explains their order, purpose, and status so future contributors can understand the DB history without reading raw SQL.

## Scope

All SQL migrations applied to the external Supabase database, whether from `sql/` (manually applied reference files) or `supabase/migrations/` (Lovable-managed migrations).

## Enforcement Rules (CRITICAL)

- Every migration applied to production MUST have an entry here
- A broken historical migration is **never deleted** from `supabase/migrations/` — the ledger marks it as `superseded` and points to the corrective migration
- When a corrective migration is created, the original entry MUST be updated with `superseded_by`
- Entries are **append-only** — status changes are forward-only
- If a migration's objects are dropped by a later migration, the original is marked `historical-only`

## Entry Schema (MANDATORY)

| Field | Required | Description |
|-------|----------|-------------|
| `ledger_id` | Yes | Sequential: `MIG-NNN` |
| `migration_file` | Yes | Full filename |
| `source_dir` | Yes | `sql/` or `supabase/migrations/` |
| `applied_date` | Yes | Date applied to database |
| `sequence_order` | Yes | Global execution order |
| `purpose` | Yes | What this migration does |
| `objects_affected` | Yes | Tables, functions, triggers, policies created/modified |
| `status` | Yes | `active`, `superseded`, `historical-only` |
| `superseded_by` | If superseded | MIG-NNN of the replacement |
| `linked_actions` | Yes | ACT-NNN references |
| `linked_decisions` | If applicable | DEC-NNN references |
| `linked_artifacts` | Yes | ART-NNN references |
| `notes` | If applicable | Additional context |

## Status Legend

| Status | Meaning |
|--------|---------|
| `active` | Migration's objects are current in the live DB |
| `superseded` | One or more objects were replaced by a later migration |
| `historical-only` | Migration was applied but all its objects have been replaced; kept for audit trail |

---

## Ledger

### MIG-001: RBAC Schema

| Field | Value |
|-------|-------|
| **Migration File** | `01_rbac_schema.sql` |
| **Source Dir** | `sql/` |
| **Applied Date** | 2026-04-09 |
| **Sequence Order** | 1 |
| **Purpose** | Create RBAC foundation: tables, triggers, indexes |
| **Objects Affected** | Tables: `roles`, `permissions`, `user_roles`, `role_permissions`, `audit_logs`. Triggers: `prevent_immutable_role_update`, `prevent_immutable_role_delete`, `prevent_last_superadmin_delete`, `update_roles_updated_at`. Indexes on all FK columns. |
| **Status** | `active` |
| **Linked Actions** | ACT-015 |
| **Linked Artifacts** | ART-001 |

---

### MIG-002: RBAC Security Helpers

| Field | Value |
|-------|-------|
| **Migration File** | `02_rbac_security_helpers.sql` |
| **Source Dir** | `sql/` |
| **Applied Date** | 2026-04-09 |
| **Sequence Order** | 2 |
| **Purpose** | Create SECURITY DEFINER helper functions for authorization checks |
| **Objects Affected** | Functions: `is_superadmin()`, `has_role()`, `has_permission()`, `get_my_authorization_context()` |
| **Status** | `active` |
| **Linked Actions** | ACT-015 |
| **Linked Artifacts** | ART-002 |

---

### MIG-003: RBAC RLS Policies

| Field | Value |
|-------|-------|
| **Migration File** | `03_rbac_rls_policies.sql` |
| **Source Dir** | `sql/` |
| **Applied Date** | 2026-04-09 |
| **Sequence Order** | 3 |
| **Purpose** | Enable Row Level Security and create access policies |
| **Objects Affected** | RLS policies on `roles`, `permissions`, `user_roles`, `role_permissions`, `audit_logs` |
| **Status** | `active` |
| **Linked Actions** | ACT-015 |
| **Linked Artifacts** | ART-003 |

---

### MIG-004: RBAC Seed Data

| Field | Value |
|-------|-------|
| **Migration File** | `04_rbac_seed.sql` |
| **Source Dir** | `sql/` |
| **Applied Date** | 2026-04-09 |
| **Sequence Order** | 4 |
| **Purpose** | Seed base roles, permissions, role-permission mappings, and auto-assign trigger |
| **Objects Affected** | Data: 3 roles, 29 permissions, role-permission mappings. Functions: `handle_new_user()`, `handle_new_user_role()`. Triggers: `on_auth_user_created`, `on_auth_user_created_role`. |
| **Status** | `active` (seed data and `handle_new_user_role`); `handle_new_user` function superseded by MIG-009 |
| **Linked Actions** | ACT-015 |
| **Linked Artifacts** | ART-004 |
| **Notes** | Original `handle_new_user()` in this file contained correct logic. Later MIG-007 introduced a broken version. See MIG-007 → MIG-009 chain for full history. |

---

### MIG-005: Superadmin Role Assignment

| Field | Value |
|-------|-------|
| **Migration File** | `20260410041231_0271722c-6c01-4096-a9ea-9b4c2b83fe5e.sql` |
| **Source Dir** | `supabase/migrations/` |
| **Applied Date** | 2026-04-10 |
| **Sequence Order** | 5 |
| **Purpose** | Assign superadmin role to initial admin user |
| **Objects Affected** | Data: `user_roles` row for superadmin assignment |
| **Status** | `active` |
| **Linked Actions** | ACT-015 |
| **Linked Artifacts** | ART-005 |

---

### MIG-006: User Role Assignment

| Field | Value |
|-------|-------|
| **Migration File** | `20260410041459_5f9277ff-3b9c-436d-882c-0147b2e4222f.sql` |
| **Source Dir** | `supabase/migrations/` |
| **Applied Date** | 2026-04-10 |
| **Sequence Order** | 6 |
| **Purpose** | Assign user base role to initial admin user |
| **Objects Affected** | Data: `user_roles` row for user role assignment |
| **Status** | `active` |
| **Linked Actions** | ACT-015 |
| **Linked Artifacts** | ART-006 |

---

### MIG-007: handle_new_user Fix Attempt (BROKEN — SUPERSEDED)

| Field | Value |
|-------|-------|
| **Migration File** | `20260410041727_9c12d489-2bf2-4f1c-ab8e-39463d360900.sql` |
| **Source Dir** | `supabase/migrations/` |
| **Applied Date** | 2026-04-10 |
| **Sequence Order** | 7 |
| **Purpose** | Fix trigger functions with search_path security |
| **Objects Affected** | Functions (CREATE OR REPLACE): `handle_new_user`, `handle_new_user_role`, `update_updated_at`, `update_updated_at_column`, `prevent_immutable_role_delete`, `prevent_immutable_role_update`, `prevent_last_superadmin_delete` |
| **Status** | `superseded` |
| **Superseded By** | MIG-008, MIG-009 |
| **Linked Actions** | ACT-020, ACT-021 |
| **Linked Artifacts** | ART-007 |
| **Notes** | ⚠️ **CONTAINS BUG.** `handle_new_user()` includes `INSERT INTO user_roles (user_id, role)` but the `user_roles` table has no `role` column (correct column is `role_id`). All other function definitions in this migration are correct and remain active. File is immutable — never deleted. |

---

### MIG-008: handle_new_user Partial Fix

| Field | Value |
|-------|-------|
| **Migration File** | `20260410043317_7272bb37-26e5-4612-b976-e5ab9837b9de.sql` |
| **Source Dir** | `supabase/migrations/` |
| **Applied Date** | 2026-04-10 |
| **Sequence Order** | 8 |
| **Purpose** | Fix handle_new_user to profile-only insert (remove broken user_roles insert) |
| **Objects Affected** | Functions: `handle_new_user` (CREATE OR REPLACE) |
| **Status** | `superseded` |
| **Superseded By** | MIG-009 |
| **Linked Actions** | ACT-020 |
| **Linked Artifacts** | ART-008 |
| **Notes** | Applied the correct profile-only version to the live DB. Superseded by MIG-009 as the formal corrective record. |

---

### MIG-009: handle_new_user Authoritative Corrective

| Field | Value |
|-------|-------|
| **Migration File** | `20260410045232_aab0e02e-9dfe-4340-ac56-601f37c09992.sql` |
| **Source Dir** | `supabase/migrations/` |
| **Applied Date** | 2026-04-10 |
| **Sequence Order** | 9 |
| **Purpose** | ACT-021: Formal corrective record for handle_new_user() — profile creation only |
| **Objects Affected** | Functions: `handle_new_user` (CREATE OR REPLACE) |
| **Status** | `active` |
| **Linked Actions** | ACT-021 |
| **Linked Artifacts** | ART-009 |
| **Notes** | Authoritative definition. `handle_new_user()` creates profile only. `handle_new_user_role()` (defined in MIG-007, correct) handles role assignment via `role_id`. |

---

### MIG-010: Audit Logs INSERT Policy

| Field | Value |
|-------|-------|
| **Ledger ID** | MIG-010 |
| **Migration File** | `20260410060801_3dcde460-0ec4-415c-a1ff-0630fd7e9e8f.sql` |
| **Source Dir** | `supabase/migrations/` |
| **Applied Date** | 2026-04-10 |
| **Sequence Order** | 10 |
| **Purpose** | Add INSERT policy on audit_logs for append-only writes from authenticated edge functions |
| **Objects Affected** | RLS policy: `audit_logs_insert_policy` on `audit_logs` |
| **Status** | `active` |
| **Linked Actions** | ACT-023 |
| **Linked Artifacts** | ART-012 |
| **Notes** | Defense-in-depth INSERT policy. WITH CHECK (true) is intentional — actual authorization is enforced in edge function code. No UPDATE/DELETE policies — append-only preserved. |

---

### MIG-011: User Management Schema & Lifecycle

| Field | Value |
|-------|-------|
| **Ledger ID** | MIG-011 |
| **Migration File** | Lovable-managed migration (auto-generated) |
| **Source Dir** | `supabase/migrations/` |
| **Applied Date** | 2026-04-10 |
| **Sequence Order** | 11 |
| **Purpose** | Add status column to profiles, admin RLS policies, seed user management permissions, validation trigger, login-block function |
| **Objects Affected** | Column: `profiles.status`; Trigger: `trg_validate_profile_status`; Function: `validate_profile_status()`, `check_user_active_on_login()`; RLS policies: `Admins can view all profiles`, `Admins can update any profile`; Index: `idx_profiles_status`; Permissions: 6 seeded; Role-permissions: user + admin assignments |
| **Status** | `active` |
| **Linked Actions** | ACT-026 |
| **Notes** | Status values restricted to 'active'/'deactivated' via validation trigger. check_user_active_on_login() is defense-in-depth (Option B); primary enforcement in edge function code (Option A). |

---

### MIG-012: Login-Block Trigger + Self-Scope RLS

| Field | Value |
|-------|-------|
| **Ledger ID** | MIG-012 |
| **Migration File** | Lovable-managed migration (auto-generated) |
| **Source Dir** | `supabase/migrations/` |
| **Applied Date** | 2026-04-10 |
| **Sequence Order** | 12 |
| **Purpose** | Wire `check_user_active_on_login()` to auth.users trigger for actual login blocking; add self-scope RLS policies on profiles |
| **Objects Affected** | Trigger: `check_user_active_before_login` on `auth.users`; RLS policies: `Users can read own profile` (re-created), `Users can update own profile` (re-created) |
| **Status** | `active` |
| **Linked Actions** | ACT-027 |
| **Notes** | Login-block trigger fires on `last_sign_in_at` changes, raising exception for deactivated users. Self-scope RLS provides defense-in-depth alongside edge function requireSelfScope(). |

---

### MIG-013: Orphaned Test User Cleanup

| Field | Value |
|-------|-------|
| **Ledger ID** | MIG-013 |
| **Migration File** | `20260410094323_07a7f7d5-46f4-4dd6-b1b7-bcfbdb64e853.sql` |
| **Source Dir** | `supabase/migrations/` |
| **Applied Date** | 2026-04-10 |
| **Sequence Order** | 13 |
| **Purpose** | Remove orphaned test user and nullify assigned_by FK reference |
| **Objects Affected** | Data: removed test user from `auth.users`, `user_roles.assigned_by` nullified |
| **Status** | `active` |
| **Linked Actions** | ACT-035 |
| **Notes** | Cleanup of test data created during runtime verification. |

---

### MIG-014: Denial Test User (Create)

| Field | Value |
|-------|-------|
| **Ledger ID** | MIG-014 |
| **Migration File** | `20260410114737_7df7b041-1cc8-48f8-9fd2-66fc6f0a7651.sql` |
| **Source Dir** | `supabase/migrations/` |
| **Applied Date** | 2026-04-10 |
| **Sequence Order** | 14 |
| **Purpose** | Create denial-test user for permission denial E2E testing |
| **Objects Affected** | Data: `auth.users` row for denial-test user |
| **Status** | `superseded` |
| **Superseded By** | MIG-017 |
| **Linked Actions** | ACT-035 |
| **Notes** | Test user for verifying 403 responses. Cleaned up by MIG-017. |

---

### MIG-015: Denial Test User (Identity)

| Field | Value |
|-------|-------|
| **Ledger ID** | MIG-015 |
| **Migration File** | `20260410114816_4fed871b-8da6-4477-b8a1-5f9132ab37d8.sql` |
| **Source Dir** | `supabase/migrations/` |
| **Applied Date** | 2026-04-10 |
| **Sequence Order** | 15 |
| **Purpose** | Add identity record for denial-test user |
| **Objects Affected** | Data: `auth.identities` row |
| **Status** | `superseded` |
| **Superseded By** | MIG-017 |
| **Linked Actions** | ACT-035 |

---

### MIG-016: Denial Test User (Token Cleanup)

| Field | Value |
|-------|-------|
| **Ledger ID** | MIG-016 |
| **Migration File** | `20260410114851_9b540bfe-469e-498e-9d69-8c7540ca0246.sql` |
| **Source Dir** | `supabase/migrations/` |
| **Applied Date** | 2026-04-10 |
| **Sequence Order** | 16 |
| **Purpose** | Clear token fields on denial-test user to avoid conflicts |
| **Objects Affected** | Data: `auth.users` token fields cleared |
| **Status** | `superseded` |
| **Superseded By** | MIG-017 |
| **Linked Actions** | ACT-035 |

---

### MIG-017: Denial Test User (Full Cleanup)

| Field | Value |
|-------|-------|
| **Ledger ID** | MIG-017 |
| **Migration File** | `20260410114940_4cd8c806-e107-4e0b-b4e0-0f2c9c003fc2.sql` |
| **Source Dir** | `supabase/migrations/` |
| **Applied Date** | 2026-04-10 |
| **Sequence Order** | 17 |
| **Purpose** | Remove denial-test user and all related data (audit logs, roles, profile, identity) |
| **Objects Affected** | Data: cleanup across `audit_logs`, `user_roles`, `profiles`, `auth.identities`, `auth.users` |
| **Status** | `active` |
| **Linked Actions** | ACT-035 |
| **Notes** | Completes the test-user lifecycle: create → test → cleanup. |

---

### MIG-018: Seed roles.edit Permission

| Field | Value |
|-------|-------|
| **Ledger ID** | MIG-018 |
| **Migration File** | `20260412031302_392e6a97-0e9f-4e62-a918-a49ddce7f616.sql` |
| **Source Dir** | `supabase/migrations/` |
| **Applied Date** | 2026-04-12 |
| **Sequence Order** | 18 |
| **Purpose** | Add `roles.edit` permission and assign to admin role |
| **Objects Affected** | Data: `permissions` row, `role_permissions` row |
| **Status** | `active` |
| **Linked Actions** | ACT-051 |

---

### MIG-019: permissions.view Separation + Superadmin Restriction

| Field | Value |
|-------|-------|
| **Ledger ID** | MIG-019 |
| **Migration File** | `20260412032343_866f12ae-0a5b-47d3-bc54-40e230c0d642.sql` |
| **Source Dir** | `supabase/migrations/` |
| **Applied Date** | 2026-04-12 |
| **Sequence Order** | 19 |
| **Purpose** | Add `permissions.view` permission, assign to admin; remove `permissions.assign` and `permissions.revoke` from admin (superadmin-only) |
| **Objects Affected** | Data: `permissions` row, `role_permissions` inserts + deletes |
| **Status** | `active` |
| **Linked Actions** | ACT-052 |

---

### MIG-020: Drop audit_logs INSERT Policy

| Field | Value |
|-------|-------|
| **Ledger ID** | MIG-020 |
| **Migration File** | `20260412033224_d8a7f542-9e13-417c-a695-06e7f528d5b6.sql` |
| **Source Dir** | `supabase/migrations/` |
| **Applied Date** | 2026-04-12 |
| **Sequence Order** | 20 |
| **Purpose** | Remove overly permissive INSERT policy from audit_logs (service_role bypasses RLS — policy was redundant and dangerous) |
| **Objects Affected** | RLS policy: `audit_logs_insert_policy` dropped |
| **Status** | `active` |
| **Linked Actions** | ACT-053 |
| **Notes** | Closes audit trail fabrication vulnerability. MIG-010 policy superseded. |

---

### MIG-021: RLS Fix + target_id Index

| Field | Value |
|-------|-------|
| **Ledger ID** | MIG-021 |
| **Migration File** | `20260412033957_7cfe13c5-199a-4b49-9b69-065bb74e7b37.sql` |
| **Source Dir** | `supabase/migrations/` |
| **Applied Date** | 2026-04-12 |
| **Sequence Order** | 21 |
| **Purpose** | Update `permissions_select_policy` to check `permissions.view` (was `roles.view`); add index on `audit_logs.target_id` |
| **Objects Affected** | RLS policy: `permissions_select_policy` re-created; Index: `idx_audit_logs_target_id` |
| **Status** | `active` |
| **Linked Actions** | ACT-054 |

---

### MIG-022: correlation_id Column + Index

| Field | Value |
|-------|-------|
| **Ledger ID** | MIG-022 |
| **Migration File** | `20260412035203_b58e597c-8634-434d-9d79-0d367e396a00.sql` |
| **Source Dir** | `supabase/migrations/` |
| **Applied Date** | 2026-04-12 |
| **Sequence Order** | 22 |
| **Purpose** | Add `correlation_id` as top-level indexed column on `audit_logs`; backfill from metadata JSONB |
| **Objects Affected** | Column: `audit_logs.correlation_id`; Index: `idx_audit_logs_correlation_id` (partial, WHERE NOT NULL) |
| **Status** | `active` |
| **Linked Actions** | ACT-055 |

---

### MIG-023: system_health_snapshots Table

| Field | Value |
|-------|-------|
| **Ledger ID** | MIG-023 |
| **Migration File** | `20260412043940_5d8b246c-3d1d-421a-9277-d174019b14be.sql` |
| **Source Dir** | `supabase/migrations/` |
| **Applied Date** | 2026-04-12 |
| **Sequence Order** | 23 |
| **Purpose** | Create `system_health_snapshots` table for health monitoring (Stage 5A) |
| **Objects Affected** | Table: `system_health_snapshots`; RLS policy: `monitoring_view_select` |
| **Status** | `active` |
| **Linked Actions** | ACT-057 |

---

### Tables (6)

| Table | Created By | Status |
|-------|-----------|--------|
| `roles` | MIG-001 | Active |
| `permissions` | MIG-001 | Active |
| `user_roles` | MIG-001 | Active |
| `role_permissions` | MIG-001 | Active |
| `audit_logs` | MIG-001 | Active |
| `profiles` | (pre-existing) | Active — status column added MIG-011 |

### Functions (12)

| Function | Current Definition | Status |
|----------|-------------------|--------|
| `is_superadmin()` | MIG-002 | Active |
| `has_role()` | MIG-002 | Active |
| `has_permission()` | MIG-002 | Active |
| `get_my_authorization_context()` | MIG-002 | Active |
| `handle_new_user()` | MIG-009 (corrected) | Active |
| `handle_new_user_role()` | MIG-007 | Active |
| `update_updated_at()` | MIG-007 | Active |
| `prevent_immutable_role_delete()` | MIG-007 | Active |
| `prevent_immutable_role_update()` | MIG-007 | Active |
| `prevent_last_superadmin_delete()` | MIG-007 | Active |
| `update_updated_at_column()` | MIG-007 | Active |
| `validate_profile_status()` | MIG-011 | Active |
| `check_user_active_on_login()` | MIG-011 | Active |

### Triggers (8)

| Trigger | Table | Function | Created By |
|---------|-------|----------|-----------|
| `on_auth_user_created` | `auth.users` | `handle_new_user` | MIG-004 |
| `on_auth_user_created_role` | `auth.users` | `handle_new_user_role` | MIG-004 |
| `prevent_immutable_role_update` | `roles` | `prevent_immutable_role_update` | MIG-001 |
| `prevent_immutable_role_delete` | `roles` | `prevent_immutable_role_delete` | MIG-001 |
| `prevent_last_superadmin_delete` | `user_roles` | `prevent_last_superadmin_delete` | MIG-001 |
| `update_roles_updated_at` | `roles` | `update_updated_at` | MIG-001 |
| `trg_validate_profile_status` | `profiles` | `validate_profile_status` | MIG-011 |
| `check_user_active_before_login` | `auth.users` | `check_user_active_on_login` | MIG-012 |

### RLS Policies (9)

| Policy | Table | Created By | Status |
|--------|-------|-----------|--------|
| Roles view (roles.view permission) | `roles` | MIG-003 | Active |
| Permissions view (permissions.view permission) | `permissions` | MIG-021 (re-created from MIG-003) | Active |
| User roles self-access | `user_roles` | MIG-003 | Active |
| Role permissions view (roles.view permission) | `role_permissions` | MIG-003 | Active |
| Audit logs view (audit.view permission) | `audit_logs` | MIG-003 | Active |
| Audit logs insert (authenticated, append-only) | `audit_logs` | MIG-010 | Dropped (MIG-020) |
| Admins can view all profiles | `profiles` | MIG-011 | Active |
| Admins can update any profile | `profiles` | MIG-011 | Active |
| Users can read own profile (self-scope) | `profiles` | MIG-012 | Active |
| Users can update own profile (self-scope) | `profiles` | MIG-012 | Active |

---

## Dependencies

- [Artifact Index](artifact-index.md)
- [Action Tracker](../06-tracking/action-tracker.md)

## Used By / Affects

All future database changes, debugging, onboarding, and schema interpretation.

## Risks If Changed

HIGH — inaccurate migration history makes future schema changes dangerous and debugging impossible.

## Related Documents

- [Artifact Index](artifact-index.md)
- [Action Tracker](../06-tracking/action-tracker.md)
- [RBAC Module](../04-modules/rbac.md)
- [Project Structure](../01-architecture/project-structure.md)
