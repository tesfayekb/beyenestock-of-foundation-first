# Trading System — Component Inventory

> **Owner:** tesfayekb | **Version:** 1.0
> **Source:** MARKETMUSE_MASTER.md v4.0, Part 6

## Purpose

Registry of all trading UI components: pages, shared components, and hooks. All trading UI lives in dedicated directories, isolated from foundation components.

---

## Pages (`src/pages/admin/trading/`)

| Component | Path | Purpose | Permission | Status |
|-----------|------|---------|-----------|--------|
| `AdminTradingWarRoomPage` | `src/pages/admin/trading/WarRoomPage.tsx` | Primary operator view — real-time regime, CV_Stress, GEX, positions, kill-switch | `trading.view` | `planned` |
| `AdminTradingPositionsPage` | `src/pages/admin/trading/PositionsPage.tsx` | Open/closed positions table with detail drawer | `trading.view` | `planned` |
| `AdminTradingSignalsPage` | `src/pages/admin/trading/SignalsPage.tsx` | Signal log — executed, rejected, expired with filters | `trading.view` | `planned` |
| `AdminTradingPerformancePage` | `src/pages/admin/trading/PerformancePage.tsx` | Rolling metrics, model accuracy, drift status, charts | `trading.view` | `planned` |
| `AdminTradingHealthPage` | `src/pages/admin/trading/HealthPage.tsx` | Trading engine health — 11 service cards, alert history | `trading.view` | `planned` |
| `AdminTradingConfigPage` | `src/pages/admin/trading/ConfigPage.tsx` | Tradier connection, paper phase, sizing phase, thresholds | `trading.configure` | `planned` |

---

## Shared Components (`src/components/trading/`)

| Component | Path | Purpose | Status |
|-----------|------|---------|--------|
| `RegimePanel` | `src/components/trading/RegimePanel.tsx` | Regime badge, day type, RCS gauge, HMM vs LightGBM disagreement banner | `planned` |
| `CVStressPanel` | `src/components/trading/CVStressPanel.tsx` | CV_Stress score 0–100, velocity arrow, exit condition status | `planned` |
| `GEXMap` | `src/components/trading/GEXMap.tsx` | Bar chart of GEX by strike, SPX marker, positive/negative zones, confidence, staleness | `planned` |
| `PredictionConfidence` | `src/components/trading/PredictionConfidence.tsx` | P(bull)/P(bear)/P(neutral) progress bars, no-trade signal display | `planned` |
| `CapitalPreservationStatus` | `src/components/trading/CapitalPreservationStatus.tsx` | Consecutive losses indicator, size reduction, trades used vs cap | `planned` |
| `ExecutionQuality` | `src/components/trading/ExecutionQuality.tsx` | Predicted vs actual slippage, execution degraded alert | `planned` |
| `AutomationActivityLog` | `src/components/trading/AutomationActivityLog.tsx` | Real-time stream of decisions with timestamp, reason, outcome | `planned` |
| `KillSwitchButton` | `src/components/trading/KillSwitchButton.tsx` | Red button, 1.5s hold, confirmation with positions list | `planned` |
| `PositionDetailDrawer` | `src/components/trading/PositionDetailDrawer.tsx` | Full attribution, Greeks, CV_Stress chart, exit rationale | `planned` |
| `TradingServiceCard` | `src/components/trading/TradingServiceCard.tsx` | Health card per service — status badge, heartbeat, latency, errors | `planned` |
| `TradingCriticalBanner` | `src/components/trading/TradingCriticalBanner.tsx` | Full-page red banner when any service offline >2 min during market hours | `planned` |
| `PaperPhaseDashboard` | `src/components/trading/PaperPhaseDashboard.tsx` | 12 go-live criteria with green/amber/red status | `planned` |
| `SizingPhaseControl` | `src/components/trading/SizingPhaseControl.tsx` | Phase 1–4 display, advance/regress buttons with confirmation | `planned` |

---

## Hooks (`src/hooks/trading/`)

| Hook | Path | Purpose | Refetch | Status |
|------|------|---------|---------|--------|
| `useTradingSession` | `src/hooks/trading/useTradingSession.ts` | Current session data (regime, RCS, allocation, P&L) | 30s | `planned` |
| `useTradingPositions` | `src/hooks/trading/useTradingPositions.ts` | Open/closed positions with WebSocket realtime | Realtime | `planned` |
| `useTradingPrediction` | `src/hooks/trading/useTradingPrediction.ts` | Latest prediction output (probabilities, CV_Stress, GEX) | 5s (market) / 60s | `planned` |
| `useTradingSystemHealth` | `src/hooks/trading/useTradingSystemHealth.ts` | Trading engine health per service | 10s | `planned` |
| `useTradingPerformance` | `src/hooks/trading/useTradingPerformance.ts` | Rolling model metrics (accuracy, Sharpe, drift) | 60s | `planned` |
| `useKillSwitch` | `src/hooks/trading/useKillSwitch.ts` | Kill-switch state and activation mutation | On demand | `planned` |
| `useTradingSignals` | `src/hooks/trading/useTradingSignals.ts` | Signal history with filters (date, instrument, status) | 30s | `planned` |
| `useTradingConfig` | `src/hooks/trading/useTradingConfig.ts` | Operator config (Tradier connection, sizing phase) | 30s | `planned` |
| `useGEXData` | `src/hooks/trading/useGEXData.ts` | GEX map data (per-strike values, confidence, staleness) | 5s (market) | `planned` |

---

## Navigation Config

| File | Addition | Status |
|------|----------|--------|
| `src/config/routes.ts` | 7 new `ADMIN_TRADING_*` route constants | `planned` |
| `src/config/admin-navigation.ts` | New "Trading System" section with 6 items | `planned` |

## Directory Structure

```
src/
├── components/trading/     — 13 shared trading UI components
├── pages/admin/trading/    — 6 page components
└── hooks/trading/          — 9 trading-specific hooks
```
