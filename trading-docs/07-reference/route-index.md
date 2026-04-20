# Trading System — Route Index

> **Owner:** tesfayekb | **Version:** 1.1
> **Source:** MARKETMUSE_MASTER.md v4.0, Part 6 + `src/config/routes.ts` lines 41-59

## Purpose

Authoritative registry of all trading frontend routes. No trading route may exist in code without an entry in this index. This is the single source of truth for trading route definitions.

## Enforcement Rule (CRITICAL)

- No trading route may be added to `src/config/routes.ts` without a
  corresponding entry here
- No trading route may be used in navigation, lazy imports, or
  permission gates without being registered here
- Route changes must update this index in the same commit
- Routes live under `/trading/*` (not `/admin/trading/*` — those are
  legacy redirects only)
- All `/trading/*` routes require authentication + `trading.view`
  minimum permission. Routes marked `trading.configure` additionally
  require configure permission for write operations.

---

## Routes

### TRADING
- **Path:** `/trading`
- **Page Component:** `TradingPage` (redirect to War Room)
- **Required Permission:** `trading.view`
- **Classification:** Privileged (admin-only)
- **Layout:** `TradingLayout` → `RequirePermission`
- **Status:** `live`

### TRADING_WARROOM
- **Path:** `/trading/warroom`
- **Page Component:** `WarRoomPage` (file: `src/pages/admin/trading/WarRoomPage.tsx`)
- **Required Permission:** `trading.view`
- **Classification:** Privileged (admin-only)
- **Refetch Interval:** 5s (market hours) / 60s (off hours)
- **Realtime:** WebSocket subscription on `trading_positions`, `trading_system_health`, `trading_prediction_outputs`
- **Status:** `live`

### TRADING_POSITIONS
- **Path:** `/trading/positions`
- **Page Component:** `PositionsPage`
- **Required Permission:** `trading.view`
- **Classification:** Privileged (admin-only)
- **Refetch Interval:** WebSocket realtime (not polling)
- **Status:** `live`

### TRADING_SIGNALS
- **Path:** `/trading/signals`
- **Page Component:** `SignalsPage`
- **Required Permission:** `trading.view`
- **Classification:** Privileged (admin-only)
- **Refetch Interval:** 30s
- **Status:** `live`

### TRADING_PERFORMANCE
- **Path:** `/trading/performance`
- **Page Component:** `PerformancePage`
- **Required Permission:** `trading.view`
- **Classification:** Privileged (admin-only)
- **Refetch Interval:** 60s
- **Status:** `live`

### TRADING_HEALTH
- **Path:** `/trading/health`
- **Page Component:** `HealthPage` (file: `src/pages/admin/trading/HealthPage.tsx`)
- **Required Permission:** `trading.view`
- **Classification:** Privileged (admin-only)
- **Refetch Interval:** 10s (always)
- **Note:** SEPARATE from foundation `/admin/health`. Uses
  `trading_system_health` table, NOT `system_health_snapshots`.
  Service-class-aware degradation policy (see backend/main.py
  `_SCHEDULED_SERVICES`) ensures cron-scheduled services are not
  flagged degraded between fires.
- **Status:** `live`

### TRADING_CONFIG
- **Path:** `/trading/config`
- **Page Component:** `ConfigPage`
- **Required Permission:** `trading.configure`
- **Classification:** Privileged (admin-only, elevated permission)
- **Refetch Interval:** 30s
- **Note:** More restrictive permission than other trading pages.
  Controls Tradier connection, sizing phase, alert thresholds.
- **Status:** `live`

### TRADING_INTELLIGENCE
- **Path:** `/trading/intelligence`
- **Page Component:** `IntelligencePage`
- **Required Permission:** `trading.view`
- **Classification:** Privileged (admin-only)
- **Refetch Interval:** 30s
- **Note:** Surfaces synthesis / flow / sentiment / calendar agent
  briefs from Redis via the Railway intelligence endpoint.
- **Status:** `live`

### TRADING_FLAGS
- **Path:** `/trading/flags`
- **Page Component:** `FlagsPage`
- **Required Permission:** `trading.configure`
- **Classification:** Privileged (admin-only, elevated permission)
- **Refetch Interval:** 30s
- **Note:** Toggles Redis feature flags via the
  `set-feature-flag` Edge Function (Bearer auth +
  `trading.configure` check).
- **Status:** `live`

### TRADING_STRATEGIES
- **Path:** `/trading/strategies`
- **Page Component:** `StrategiesPage`
- **Required Permission:** `trading.view`
- **Classification:** Privileged (admin-only)
- **Status:** `live`

### TRADING_MILESTONES
- **Path:** `/trading/milestones`
- **Page Component:** `MilestonesPage`
- **Required Permission:** `trading.view`
- **Classification:** Privileged (admin-only)
- **Status:** `live`

### TRADING_SUBSCRIPTIONS
- **Path:** `/trading/subscriptions`
- **Page Component:** `SubscriptionsPage`
- **Required Permission:** `trading.configure`
- **Classification:** Privileged (admin-only, elevated permission)
- **Status:** `live`

### TRADING_ACTIVATION
- **Path:** `/trading/activation`
- **Page Component:** `ActivationPage`
- **Required Permission:** `trading.configure`
- **Classification:** Privileged (admin-only, elevated permission)
- **Note:** Phase Activation Dashboard — surfaces 90-day A/B gate,
  trade count thresholds, and AI synthesis enable/disable.
- **Status:** `live`

### TRADING_AB_COMPARISON
- **Path:** `/trading/ab-comparison`
- **Page Component:** `AbComparisonPage`
- **Required Permission:** `trading.view`
- **Classification:** Privileged (admin-only)
- **Note:** Reads `ab_session_comparison` rows produced by the
  Phase 3B `shadow_engine.py` daily job.
- **Status:** `live`

### TRADING_EARNINGS
- **Path:** `/trading/earnings`
- **Page Component:** `EarningsPage`
- **Required Permission:** `trading.view`
- **Classification:** Privileged (admin-only)
- **Note:** Phase 5A — surfaces upcoming earnings IV vs historical
  move and active straddle positions from `backend_earnings/`.
- **Status:** `live`

---

## Current Route Summary

| Route ID | Path | Permission | Status |
|---|---|---|---|
| TRADING | `/trading` | `trading.view` | `live` |
| TRADING_WARROOM | `/trading/warroom` | `trading.view` | `live` |
| TRADING_POSITIONS | `/trading/positions` | `trading.view` | `live` |
| TRADING_SIGNALS | `/trading/signals` | `trading.view` | `live` |
| TRADING_PERFORMANCE | `/trading/performance` | `trading.view` | `live` |
| TRADING_HEALTH | `/trading/health` | `trading.view` | `live` |
| TRADING_CONFIG | `/trading/config` | `trading.configure` | `live` |
| TRADING_INTELLIGENCE | `/trading/intelligence` | `trading.view` | `live` |
| TRADING_FLAGS | `/trading/flags` | `trading.configure` | `live` |
| TRADING_STRATEGIES | `/trading/strategies` | `trading.view` | `live` |
| TRADING_MILESTONES | `/trading/milestones` | `trading.view` | `live` |
| TRADING_SUBSCRIPTIONS | `/trading/subscriptions` | `trading.configure` | `live` |
| TRADING_ACTIVATION | `/trading/activation` | `trading.configure` | `live` |
| TRADING_AB_COMPARISON | `/trading/ab-comparison` | `trading.view` | `live` |
| TRADING_EARNINGS | `/trading/earnings` | `trading.view` | `live` |

**Legacy redirects** (still functional, redirect to new paths):
- `/admin/trading` → `/trading/warroom`
- `/admin/trading/warroom` → `/trading/warroom`
- `/admin/trading/positions` → `/trading/positions`
- `/admin/trading/signals` → `/trading/signals`
- `/admin/trading/performance` → `/trading/performance`
- `/admin/trading/health` → `/trading/health`
- `/admin/trading/config` → `/trading/config`

**Note:** All `/trading/*` routes require authentication + `trading.view`
minimum permission. Routes marked `trading.configure` additionally require
configure permission for write operations.
