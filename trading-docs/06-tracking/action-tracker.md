# Trading System — Action Tracker

> **Owner:** tesfayekb | **Version:** 1.0

## Purpose

Single register of every trading change action. Every change to trading code, schema, or governance MUST have an entry here.

---

## Entry Schema

| Field | Required | Description |
|-------|----------|-------------|
| `id` | Yes | Sequential: `T-ACT-NNN` |
| `date` | Yes | ISO date the action was completed |
| `action` | Yes | Short description |
| `type` | Yes | `migration`, `code`, `documentation`, `governance`, `verification` |
| `phase` | Yes | Trading build phase (e.g. `phase_1`, `pre_phase_1`) |
| `impact` | Yes | `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` |
| `owner` | Yes | Who/what performed the action (Lovable, Cursor, Operator) |
| `modules_affected` | Yes | List of trading and/or foundation modules touched |
| `docs_updated` | Yes | List of trading-docs files updated |
| `foundation_impact` | Yes | `NONE`, or description of foundation files touched (with justification) |
| `verification` | Yes | How the action was verified |
| `t_rules_checked` | Yes | List of T-Rules verified during action (T-Rule 1, T-Rule 2, etc.) |

---

## Register

### T-ACT-001 — Initial Trading Schema Migration Applied

- **id:** T-ACT-001
- **date:** 2026-04-16
- **action:** Applied T-MIG-001 — initial trading database schema (8 new tables, profiles ALTER, 5 permissions seed, role_permissions seed, 10 job_registry entries, 20 alert_configs entries)
- **type:** migration
- **phase:** pre_phase_1 (schema is a Phase 1 prerequisite, not a Phase 1 deliverable completion)
- **impact:** HIGH (database schema change affecting profiles + 8 new tables)
- **owner:** Lovable (Supabase migration tool)
- **modules_affected:**
  - Trading: trading_operator_config, trading_sessions, trading_prediction_outputs, trading_signals, trading_positions, trading_system_health, trading_model_performance, trading_calibration_log
  - Foundation: profiles (3 new columns: trading_tier, tradier_connected, tradier_account_id), permissions (5 new rows), role_permissions (admin role), job_registry (10 new rows), alert_configs (20 new rows)
- **docs_updated:**
  - trading-docs/07-reference/database-migration-ledger.md (T-MIG-001 status: pending → applied)
  - trading-docs/00-governance/system-state.md (Trading Database Schema: not_started → implemented; added trading_schema_migration: T-MIG-001_applied)
  - trading-docs/06-tracking/action-tracker.md (this entry)
- **foundation_impact:** Approved per MARKETMUSE_MASTER.md Part 4.1 — `profiles` ALTER adds 3 trading-specific columns. Inserts into `permissions`, `role_permissions`, `job_registry`, `alert_configs` use `ON CONFLICT DO NOTHING` to avoid affecting existing foundation rows. No foundation schemas modified or destroyed.
- **verification:**
  - Migration completed successfully (Supabase migration tool confirmation)
  - Security linter: 8 pre-existing warnings unchanged, 0 new warnings from this migration
  - All 8 new tables have RLS enabled with appropriate policies
  - All trading_* tables follow naming convention
  - PENDING: Manual post-migration checklist from regression-strategy.md (sign-in, /admin/health, /admin/jobs, /admin/audit, /admin/permissions, /profile, /admin/users)
- **t_rules_checked:**
  - T-Rule 1 (Foundation Isolation): ✅ Only approved profiles ALTER, no other foundation modifications
  - T-Rule 2 (Table Prefix Isolation): ✅ All 8 new tables use trading_ prefix
  - T-Rule 4 (Locked Decisions): ✅ Schema implements D-005, D-006, D-010, D-011, D-013, D-014, D-018, D-022 storage requirements
  - T-Rule 7 (Security Inheritance): ✅ RLS on every table, service_role writes, authenticated reads (calibration log: service_role only)
  - T-Rule 10 (No Silent Failures): ✅ trading_system_health table created for heartbeat monitoring

---

### T-ACT-002 — Engine Health Page Implemented (TPLAN-INFRA-001-I)

- **id:** T-ACT-002
- **date:** 2026-04-16
- **action:** Implemented `/admin/trading/health` (Engine Health). Added `ADMIN_TRADING_*` route constants, "Trading System" navigation section, lazy-loaded `TradingHealthPage` with `RequirePermission` (`trading.view`), 10s polling on `trading_system_health`, market-hours CRITICAL banner, and last-10 trading alerts panel.
- **type:** code
- **phase:** phase_1
- **impact:** MEDIUM (new admin page, isolated trading namespace, no foundation logic touched)
- **owner:** Lovable
- **modules_affected:**
  - Trading: `src/pages/admin/trading/HealthPage.tsx` (new)
  - Foundation routing/nav (additive only): `src/config/routes.ts`, `src/config/admin-navigation.ts`, `src/App.tsx`
- **docs_updated:**
  - trading-docs/07-reference/route-index.md (ADMIN_TRADING_HEALTH: planned → implemented)
  - trading-docs/06-tracking/action-tracker.md (this entry)
- **foundation_impact:** Additive only — appended trading route constants, appended a "Trading System" nav section, appended one nested route under `/admin`. No foundation routes, components, or behavior modified.
- **verification:**
  - Page queries `trading_system_health` (NOT `system_health_snapshots`) — confirmed in code
  - `refetchInterval: 10_000` set unconditionally per route-index.md
  - Empty state ("Services not yet reporting") shown when table is empty — not an error
  - CRITICAL banner gated on `isMarketHoursET()` (9:30–16:00 America/New_York, weekdays) AND offline count > 0
  - Permission gate `trading.view` enforced at route level via `PermissionGate`
  - Single combined `Promise.all` query for health + alerts (matches existing pattern)
  - PENDING: Operator E2E sign-in + visit `/admin/trading/health` to confirm empty state renders
- **t_rules_checked:**
  - T-Rule 1 (Foundation Isolation): ✅ Only additive changes to routes/nav/App; foundation pages untouched
  - T-Rule 2 (Table Prefix Isolation): ✅ Reads from `trading_system_health` and filters `alert_history` by `trading.%` metric_key
  - T-Rule 3 (Route Namespace Isolation): ✅ Lives under `/admin/trading/*`
  - T-Rule 7 (Security Inheritance): ✅ Reuses `RequirePermission`, `AdminLayout`, `trading.view` permission from index
  - T-Rule 10 (No Silent Failures): ✅ Empty state distinguishes "no backend yet" from errors; ErrorState shown on real failures
