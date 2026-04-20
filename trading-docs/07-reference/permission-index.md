# Trading System — Permission Index

> **Owner:** tesfayekb | **Version:** 1.1
> **Source:** MARKETMUSE_MASTER.md v4.0, Part 4.2–4.3

## Purpose

Authoritative registry of all trading-specific permissions. No trading permission may be used in code (frontend gates, edge functions, RLS policies) without an entry in this index.

## Enforcement Rule (CRITICAL)

- No trading permission may be added to the `permissions` table without a corresponding entry here
- No `RequirePermission` gate may reference a trading permission not listed here
- No edge function authorization check may use a trading permission not listed here
- Permission changes must update this index in the same commit

---

## Permissions

### trading.view
- **Key:** `trading.view`
- **Description:** View trading signals, positions, performance, engine health, and War Room
- **Assigned Roles:** `superadmin`, `admin`
- **Used By:** All 15 trading routes (minimum permission for any trading page),
  RLS policies on `trading_positions`, `trading_sessions`,
  `trading_prediction_outputs`, `trading_system_health`,
  `paper_phase_criteria`
- **Status:** `implemented`

### trading.configure
- **Key:** `trading.configure`
- **Description:** Configure trading parameters — Tradier connection, sizing phase, alert thresholds, feature flags, kill switch
- **Assigned Roles:** `superadmin`, `admin`
- **Used By:** `/trading/config`, `/trading/flags`, `/trading/subscriptions`,
  `/trading/activation`, `set-feature-flag` Edge Function
  (`trading.configure` check), `kill-switch` Edge Function
  (`trading.configure` check), Railway flag endpoint
  (`X-Api-Key` header)
- **Note:** More restrictive than `trading.view`. Gates every page
  and endpoint that performs a write to trading configuration.
- **Status:** `implemented`

### trading.kill_switch
- **Key:** `trading.kill_switch`
- **Description:** Activate emergency trading halt — close all positions immediately
- **Assigned Roles:** `superadmin`, `admin`
- **Used By:** Kill-switch button in War Room (gated separately from
  `trading.configure` for fine-grained operator control). The
  `kill-switch` Edge Function currently accepts either
  `trading.configure` or `trading.kill_switch`.
- **Note:** Kill-switch requires 1.5-second hold to prevent
  accidental activation.
- **Status:** `implemented`

### trading.execute
- **Key:** `trading.execute`
- **Description:** Allow the system to execute trades on the connected Tradier account
- **Assigned Roles:** `superadmin` (system-level, not directly user-invoked)
- **Used By:** Reserved for future real-money execution gating in
  the Python execution engine (service_role context). Not yet
  checked by any code path.
- **Status:** `planned` (not yet used in any gate — reserved for future real-money execution)

### trading.admin
- **Key:** `trading.admin`
- **Description:** Full trading system administration — manage all trading operations
- **Assigned Roles:** `superadmin`, `admin`
- **Used By:** Reserved for future administrative trading operations.
  Not yet checked by any code path.
- **Status:** `planned` (not yet used — reserved for future admin operations)

### trading.view_own
- **Key:** `trading.view_own`
- **Description:** View only the requesting user's own trading positions and P&L (multi-tenant scoping)
- **Assigned Roles:** `user` (planned — not yet seeded)
- **Used By:** Reserved for the multi-tenant Phase 4A/4B user
  dashboard. Not yet checked by any code path or RLS policy.
- **Status:** `planned` (not yet used — reserved for multi-tenant future)

---

## Role Assignment Summary

| Permission | superadmin | admin | user |
|-----------|-----------|-------|------|
| `trading.view` | ✅ | ✅ | ❌ |
| `trading.configure` | ✅ | ✅ | ❌ |
| `trading.kill_switch` | ✅ | ✅ | ❌ |
| `trading.execute` | ✅ | ❌ | ❌ |
| `trading.admin` | ✅ | ✅ | ❌ |
| `trading.view_own` | ❌ | ❌ | (planned) |

## SQL Seed Reference

```sql
INSERT INTO public.permissions (key, description) VALUES
  ('trading.view',         'View trading signals, positions, and performance'),
  ('trading.configure',    'Configure trading parameters and thresholds'),
  ('trading.kill_switch',  'Activate emergency trading halt'),
  ('trading.execute',      'Allow system to execute trades on connected account'),
  ('trading.admin',        'Full trading system administration'),
  ('trading.view_own',     'View only own trading positions (multi-tenant)');
```
