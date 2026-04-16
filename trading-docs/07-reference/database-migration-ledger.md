# Trading System — Database Migration Ledger

> **Owner:** tesfayekb | **Version:** 1.0
> **Source:** MARKETMUSE_MASTER.md v4.0, Part 4

## Purpose

Ordered ledger of all trading database migrations. Every migration applied to the database MUST have an entry here. This is separate from the foundation `docs/07-reference/database-migration-ledger.md` — trading migrations use `T-MIG-NNN` IDs.

## Enforcement Rules (CRITICAL)

- Every trading migration applied to Supabase MUST have an entry here
- Broken migrations are never deleted — marked `superseded` with pointer to corrective migration
- Entries are append-only — status changes forward-only
- Trading migrations MUST NOT modify foundation tables except the approved `profiles` ALTER (Part 4.1)

## Entry Schema

| Field | Required | Description |
|-------|----------|-------------|
| `id` | Yes | Sequential: `T-MIG-NNN` |
| `description` | Yes | What this migration does |
| `tables_affected` | Yes | Tables created, modified, or seeded |
| `reversible` | Yes | Whether migration can be cleanly rolled back |
| `applied_by` | Yes | Who/what applied it (Lovable, manual, Cursor) |
| `verified_by` | Yes | Who verified it post-application |
| `status` | Yes | `pending`, `applied`, `superseded`, `failed` |
| `applied_date` | If applied | Date migration was run |
| `superseded_by` | If superseded | T-MIG-NNN of replacement |
| `notes` | If applicable | Additional context |

---

## Ledger

### T-MIG-001: Initial Trading Schema

- **ID:** T-MIG-001
- **Description:** Create all trading database tables, extend profiles, seed permissions, register trading jobs, and configure trading alerts. This is the foundational trading schema from MARKETMUSE_MASTER.md Part 4.
- **Tables Affected:**
  - **ALTER:** `profiles` — add `trading_tier`, `tradier_connected`, `tradier_account_id` columns
  - **CREATE:** `trading_operator_config` — single operator Tradier credentials and sizing phase
  - **CREATE:** `trading_sessions` — one record per trading day with regime, RCS, P&L
  - **CREATE:** `trading_prediction_outputs` — every 5-minute prediction cycle output
  - **CREATE:** `trading_signals` — system's decision to open a trade (virtual or real)
  - **CREATE:** `trading_positions` — open/closed positions with full attribution
  - **CREATE:** `trading_system_health` — per-module health status (11 services)
  - **CREATE:** `trading_model_performance` — rolling accuracy, drift, champion/challenger
  - **CREATE:** `trading_calibration_log` — append-only CV_Stress and touch prob readings
  - **SEED:** `permissions` — 5 new trading permissions
  - **SEED:** `role_permissions` — assign trading permissions to admin role
  - **SEED:** `job_registry` — 10 trading scheduled jobs
  - **SEED:** `alert_configs` — 20 trading alert threshold configurations
- **RLS Policies:**
  - `trading_operator_config`: owner-only (user_id = auth.uid())
  - `trading_sessions`: authenticated read, service_role write
  - `trading_prediction_outputs`: authenticated read, service_role write
  - `trading_signals`: authenticated read, service_role write
  - `trading_positions`: authenticated read, service_role write
  - `trading_system_health`: authenticated read, service_role write
  - `trading_model_performance`: authenticated read, service_role write
  - `trading_calibration_log`: service_role only (read + write)
- **Indexes:**
  - `idx_trading_sessions_date` — session_date DESC
  - `idx_prediction_session` — session_id, predicted_at DESC
  - `idx_prediction_time` — predicted_at DESC
  - `idx_signal_session` — session_id, signal_at DESC
  - `idx_signal_status` — signal_status, created_at DESC
  - `idx_position_session` — session_id, entry_at DESC
  - `idx_position_status` — status, entry_at DESC
  - `idx_position_mode` — position_mode, status
  - `idx_model_perf_time` — recorded_at DESC
  - `idx_calib_position` — position_id, ts DESC
  - `idx_calib_type` — signal_type, regime, ts DESC
- **Reversible:** Yes — DROP tables in reverse order, remove seeded rows, ALTER TABLE DROP COLUMN
- **Applied By:** Pending
- **Verified By:** Pending
- **Status:** `pending`
- **Applied Date:** —
- **Notes:** Full SQL is in MARKETMUSE_MASTER.md Part 4 (sections 4.1–4.13). Must be applied as a single migration to maintain referential integrity.
