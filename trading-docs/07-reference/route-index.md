# Trading System — Route Index

> **Owner:** tesfayekb | **Version:** 1.0
> **Source:** MARKETMUSE_MASTER.md v4.0, Part 6

## Purpose

Authoritative registry of all trading frontend routes. No trading route may exist in code without an entry in this index. This is the single source of truth for trading route definitions.

## Enforcement Rule (CRITICAL)

- No trading route may be added to `src/config/routes.ts` without a corresponding entry here
- No trading route may be used in navigation, lazy imports, or permission gates without being registered here
- Route changes must update this index in the same commit
- All trading routes are children of `/admin/trading` and require authentication + permission gate

---

## Routes

### ADMIN_TRADING
- **Path:** `/admin/trading`
- **Page Component:** `AdminTradingPage` (redirect to War Room)
- **Required Permission:** `trading.view`
- **Classification:** Privileged (admin-only)
- **Layout:** `AdminLayout` → `DashboardLayout` → `RequirePermission`
- **Status:** `planned`

### ADMIN_TRADING_WARROOM
- **Path:** `/admin/trading/warroom`
- **Page Component:** `AdminTradingWarRoomPage`
- **Required Permission:** `trading.view`
- **Classification:** Privileged (admin-only)
- **Refetch Interval:** 5s (market hours) / 60s (off hours)
- **Realtime:** WebSocket subscription on `trading_positions`, `trading_system_health`, `trading_prediction_outputs`
- **Status:** `planned`

### ADMIN_TRADING_POSITIONS
- **Path:** `/admin/trading/positions`
- **Page Component:** `AdminTradingPositionsPage`
- **Required Permission:** `trading.view`
- **Classification:** Privileged (admin-only)
- **Refetch Interval:** WebSocket realtime (not polling)
- **Status:** `planned`

### ADMIN_TRADING_SIGNALS
- **Path:** `/admin/trading/signals`
- **Page Component:** `AdminTradingSignalsPage`
- **Required Permission:** `trading.view`
- **Classification:** Privileged (admin-only)
- **Refetch Interval:** 30s
- **Status:** `planned`

### ADMIN_TRADING_PERFORMANCE
- **Path:** `/admin/trading/performance`
- **Page Component:** `AdminTradingPerformancePage`
- **Required Permission:** `trading.view`
- **Classification:** Privileged (admin-only)
- **Refetch Interval:** 60s
- **Status:** `planned`

### ADMIN_TRADING_HEALTH
- **Path:** `/admin/trading/health`
- **Page Component:** `TradingHealthPage` (file: `src/pages/admin/trading/HealthPage.tsx`)
- **Required Permission:** `trading.view`
- **Classification:** Privileged (admin-only)
- **Refetch Interval:** 10s (always)
- **Note:** SEPARATE from foundation `/admin/health`. Uses `trading_system_health` table, NOT `system_health_snapshots`.
- **Status:** `implemented` (T-ACT-002, 2026-04-16)

### ADMIN_TRADING_CONFIG
- **Path:** `/admin/trading/config`
- **Page Component:** `AdminTradingConfigPage`
- **Required Permission:** `trading.configure`
- **Classification:** Privileged (admin-only, elevated permission)
- **Refetch Interval:** 30s
- **Note:** More restrictive permission than other trading pages. Controls Tradier connection, sizing phase, alert thresholds.
- **Status:** `planned`

---

## Summary

| Route Key | Path | Permission | Status |
|-----------|------|-----------|--------|
| ADMIN_TRADING | `/admin/trading` | `trading.view` | `planned` |
| ADMIN_TRADING_WARROOM | `/admin/trading/warroom` | `trading.view` | `planned` |
| ADMIN_TRADING_POSITIONS | `/admin/trading/positions` | `trading.view` | `planned` |
| ADMIN_TRADING_SIGNALS | `/admin/trading/signals` | `trading.view` | `planned` |
| ADMIN_TRADING_PERFORMANCE | `/admin/trading/performance` | `trading.view` | `planned` |
| ADMIN_TRADING_HEALTH | `/admin/trading/health` | `trading.view` | `implemented` |
| ADMIN_TRADING_CONFIG | `/admin/trading/config` | `trading.configure` | `planned` |
