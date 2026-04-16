# Trading System — Permission Index

> **Owner:** tesfayekb | **Version:** 1.0
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
- **Used By:** All 7 trading routes (minimum permission for any trading page)
- **Status:** `planned`

### trading.admin
- **Key:** `trading.admin`
- **Description:** Full trading system administration — manage all trading operations
- **Assigned Roles:** `superadmin`, `admin`
- **Used By:** Administrative trading operations
- **Status:** `planned`

### trading.execute
- **Key:** `trading.execute`
- **Description:** Allow the system to execute trades on the connected Tradier account
- **Assigned Roles:** `superadmin` (system-level, not directly user-invoked)
- **Used By:** Python execution engine (service_role context)
- **Note:** This permission gates whether the system is allowed to place real orders. It is checked by the execution engine, not by frontend pages.
- **Status:** `planned`

### trading.kill_switch
- **Key:** `trading.kill_switch`
- **Description:** Activate emergency trading halt — close all positions immediately
- **Assigned Roles:** `superadmin`, `admin`
- **Used By:** Kill-switch button in War Room
- **Note:** Separate from `trading.admin` to allow fine-grained control over who can trigger emergency halt. Kill-switch requires 1.5-second hold to prevent accidental activation.
- **Status:** `planned`

### trading.configure
- **Key:** `trading.configure`
- **Description:** Configure trading parameters — Tradier connection, sizing phase, alert thresholds
- **Assigned Roles:** `superadmin`, `admin`
- **Used By:** Configuration page (`/admin/trading/config`)
- **Note:** More restrictive than `trading.view`. Gates the Configuration page specifically.
- **Status:** `planned`

---

## Role Assignment Summary

| Permission | superadmin | admin | user |
|-----------|-----------|-------|------|
| `trading.view` | ✅ | ✅ | ❌ |
| `trading.admin` | ✅ | ✅ | ❌ |
| `trading.execute` | ✅ | ❌ | ❌ |
| `trading.kill_switch` | ✅ | ✅ | ❌ |
| `trading.configure` | ✅ | ✅ | ❌ |

## SQL Seed Reference

```sql
INSERT INTO public.permissions (key, description) VALUES
  ('trading.view',         'View trading signals, positions, and performance'),
  ('trading.admin',        'Full trading system administration'),
  ('trading.execute',      'Allow system to execute trades on connected account'),
  ('trading.kill_switch',  'Activate emergency trading halt'),
  ('trading.configure',    'Configure trading parameters and thresholds');
```
