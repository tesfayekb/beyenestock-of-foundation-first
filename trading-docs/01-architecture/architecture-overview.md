# Trading System — Architecture Overview

> **Owner:** tesfayekb | **Version:** 1.0
> **Source:** MARKETMUSE_MASTER.md v4.0, Parts 5 and 7

## Purpose

End-to-end architecture for the MarketMuse trading system, covering layers, data flow, storage, monitoring, and invariants.

---

## 1. Three-Layer System Diagram

```
┌────────────────────────────────────────────────────────────────────┐
│  LAYER 1 — FOUNDATION (existing, unchanged)                         │
│  React/Vite app + Supabase (auth, RBAC, audit, MFA, jobs, alerts)   │
│  Foundation tables: profiles, roles, permissions, user_roles, etc.  │
└────────────────────────────────────────────────────────────────────┘
                                    ▲
                                    │ Inherits auth, RBAC, MFA, RLS
                                    │
┌────────────────────────────────────────────────────────────────────┐
│  LAYER 2 — TRADING FRONTEND (Lovable)                               │
│  /admin/trading/* pages — War Room, Positions, Signals,             │
│  Performance, Engine Health, Configuration                          │
│  Permission-gated by trading.view / trading.configure               │
│  Reads from trading_* Supabase tables + WebSocket realtime          │
└────────────────────────────────────────────────────────────────────┘
                                    ▲
                                    │ Supabase reads + realtime
                                    │
┌────────────────────────────────────────────────────────────────────┐
│  LAYER 3 — TRADING BACKEND (Cursor / Python / Railway)              │
│  data_ingestor, prediction_engine, strategy_selector,               │
│  risk_engine, execution_engine, learning_engine                     │
│  Writes to trading_* Supabase tables (service_role)                 │
│  Storage: Supabase + Redis (intraday) + QuestDB (feature store)     │
└────────────────────────────────────────────────────────────────────┘
                                    ▲
                                    │ Independent monitoring
                                    │
┌────────────────────────────────────────────────────────────────────┐
│  LAYER 4 — INDEPENDENT SENTINEL (GCP, separate process)             │
│  sentinel.py — close-only Tradier permissions                       │
│  Polls Tradier balance, SPX, primary heartbeat, recomputes CV_Stress│
│  Triggers panic close-all when primary fails                        │
└────────────────────────────────────────────────────────────────────┘
```

---

## 2. Data Flow

```
Market Data Providers
  ├── Tradier WebSocket (streaming quotes)
  ├── Databento OPRA (trade-by-trade for GEX)
  ├── CBOE DataShop (EOD OI baseline)
  ├── Polygon (VVIX, breadth)
  └── Unusual Whales / Finnhub
            │
            ▼
   data_ingestor.py
     ├── Heartbeat (3s) → trading_system_health
     ├── GEX synthesis (Lee-Ready) → Redis + Supabase
     └── Feature computation → QuestDB
            │
            ▼
   prediction_engine.py (every 5 min)
     Layer A — Day Type + 6-state regime (HMM + LightGBM)
     Layer B — 93-feature LightGBM prediction
     Layer C — Volatility surface (RV vs IV, skew)
            │
            ▼
   trading_prediction_outputs (Supabase)
            │
            ▼
   strategy_selector.py
     Stage 0–4: Time gate, regime gate, GEX optimizer, EV utility, liquidity
            │
            ▼
   trading_signals (Supabase)
            │
            ▼
   risk_engine.py → position sizing, stressed loss, capital preservation
            │
            ▼
   execution_engine.py
     Walk-the-book limit improvement
     Tradier order + OCO
            │
            ▼
   trading_positions (Supabase) ──→ WebSocket realtime ──→ War Room
            │
            ▼
   learning_engine.py (4:15 PM daily, Sunday slow loop)
     Isotonic recalibration, slippage model retrain, drift z-test
```

---

## 3. Storage Architecture

| Storage | Purpose | Latency Target | Retention |
|---------|---------|---------------|-----------|
| **Supabase (Postgres)** | Permanent storage of sessions, signals, positions, predictions, audit | <50ms reads | Indefinite (audit 2yr+) |
| **Redis** | Intraday cache: GEX, regime state, position state, walk-the-book attempts | <1ms | Session-only |
| **QuestDB** | 93-feature time-series store for LightGBM prediction queries | <1ms | Rolling 90d |

Permanent decisions live in Supabase. Intraday hot state lives in Redis. Historical features for model queries live in QuestDB.

---

## 4. Three-Layer Monitoring Architecture

```
Layer 1 — DATABASE (always on, even if app crashes)
├── trading_system_health   — heartbeat table (10s upserts)
├── trading_calibration_log — every exit/entry decision
├── audit_logs              — every automated action (correlation_id)
└── alert_history           — every threshold breach

Layer 2 — PRIMARY APPLICATION (in-process)
├── Intraday execution feedback loop (D-019)
├── Capital preservation counter (D-022)
├── Regime disagreement guard (D-021)
└── Circuit breaker cascade

Layer 3 — INDEPENDENT SENTINEL (separate GCP process)
├── Monitors Layer 1 independently via Supabase replica
├── Polls Tradier balance every 5s (drawdown check)
├── Polls SPX every 2s
├── Recomputes CV_Stress from own Tradier option chain
└── Acts even when Layer 1 and Layer 2 are both down
```

---

## 5. Seven Key Invariants

These must ALWAYS be true. Any violation is a CRITICAL incident.

| # | Invariant | Detection |
|---|-----------|-----------|
| **I-1** | Heartbeat to `trading_system_health` is < 30s old during market hours | `trading_heartbeat_check` job (every 1 min) |
| **I-2** | Every fill has an OCO order pre-submitted within 2 seconds | `audit_logs` action `trading.oco_submitted` correlated with `trading.fill_received` |
| **I-3** | RLS enabled on every `trading_*` table — service_role writes, authenticated reads | DB linter + manual policy audit |
| **I-4** | Every automated trade action has an `audit_logs` entry with `correlation_id` | Audit reconciliation: `trading_signals.correlation_id` ↔ `audit_logs.correlation_id` |
| **I-5** | Daily drawdown never exceeds −3% — circuit breaker triggers session halt (D-005) | `alert_history` + `trading_sessions.session_status='halted'` |
| **I-6** | Time stops at 2:30 PM (short-gamma) and 3:45 PM (long-gamma) execute every trading day (D-010, D-011) | `job_executions` for `trading_time_stop_*` jobs |
| **I-7** | Sentinel heartbeat is fresh (< 60s) and Sentinel can independently close all positions | Separate sentinel heartbeat in `trading_system_health` (service_name='sentinel') |

Violation of any invariant during market hours = full-page CRITICAL banner + page operator immediately.

---

## References

- MARKETMUSE_MASTER.md Part 5 — Trading Engine architecture
- MARKETMUSE_MASTER.md Part 7 — Comprehensive Monitoring Strategy
- trading-docs/00-governance/constitution.md — 10 T-Rules
- trading-docs/04-modules/prediction-engine.md — Layer A/B/C details
- trading-docs/04-modules/exit-engine.md — State machine and exit triggers
