# Cursor AI Rules — Trading System

> **Scope:** This file governs Cursor AI behavior for ALL trading system work.
> **Authority:** MARKETMUSE_MASTER.md v4.0 is the single source of truth.

## STOP — READ BEFORE DOING ANYTHING

Before writing, modifying, or deleting ANY trading file, you MUST read these in order:

1. `MARKETMUSE_MASTER.md` — complete specification
2. `trading-docs/00-governance/constitution.md` — 10 T-Rules
3. `trading-docs/00-governance/system-state.md` — current phase and gates
4. `trading-docs/08-planning/approved-decisions.md` — 22 locked decisions

If ANY required document is missing or unclear → **STOP and ask for clarification.**

---

## Module Structure (Python Backend)

```
backend/
├── data_ingestor.py       — WebSocket feeds, heartbeat, GEX pipeline
├── prediction_engine.py   — 3-layer prediction (Layer A/B/C)
├── strategy_selector.py   — Stage 0-4 selection + walk-the-book
├── risk_engine.py         — Sizing, Greeks, circuit breakers
├── execution_engine.py    — Tradier orders, OCO, state machine
├── learning_engine.py     — Fast/slow/intraday calibration loops
└── sentinel.py            — Independent monitoring (deploy on GCP)
```

Storage: Supabase (permanent) + Redis (intraday cache) + QuestDB (feature store)

---

## Silent Failure Rules (MANDATORY)

1. **Every function must have explicit error handling** — no bare `except:` or `except Exception:` without logging.
2. **Every Supabase write must verify success** — check response, log failures.
3. **Every heartbeat must upsert to `trading_system_health`** — 10-second interval minimum.
4. **Every automated trade action must log to `audit_logs`** — with `correlation_id` linking to `job_executions`.
5. **Every circuit breaker trigger must be logged** — action, reason, positions affected.
6. **Data feed disconnects must trigger degraded mode within 3 seconds** — not silently continue.
7. **Sentinel must detect primary app failure within 120 seconds** — and close all positions.
8. **No `print()` statements** — use structured logging with severity levels.
9. **No hardcoded credentials** — all API keys from environment variables.
10. **No TODO/FIXME without a tracked action item** in `trading-docs/06-tracking/action-tracker.md`.

---

## 22 Locked Decisions Reference

| ID | Decision | Value |
|---|---|---|
| D-001 | Instruments | SPX, XSP, NDX, RUT only (Section 1256) |
| D-002 | Primary mode | 0DTE |
| D-003 | Secondary mode | 1–5 day swing, regime-gated |
| D-004 | Capital allocation | Core + Satellites + Reserve (RCS-dynamic) |
| D-005 | Daily loss limit | −3% hardcoded, no override |
| D-006 | Broker | Tradier API only, OCO pre-submitted at every fill |
| D-007 | Execution | Fully automated, single operator account |
| D-008 | Data budget | ~$150–200/month |
| D-009 | X/Twitter | Tier-3 only, ±5% max, ≥2 accounts to confirm |
| D-010 | Short-gamma exit | 2:30 PM EST, automated, no override |
| D-011 | Long-gamma exit | 3:45 PM EST, automated, no override |
| D-012 | RUT | Satellite-only, 50% size, stricter liquidity |
| D-013 | Paper phase | 45 days, 12 go-live criteria, all required |
| D-014 | Position sizing | 4 phases with advance criteria and auto-regression |
| D-015 | Slippage model | Predictive LightGBM, not static |
| D-016 | Volatility blending | sigma = max(realized, 0.70 × implied) |
| D-017 | CV_Stress exit | Only triggers when P&L ≥ 50% of max profit |
| D-018 | VVIX thresholds | Adaptive Z-score vs 20-day rolling baseline |
| D-019 | Execution feedback | If actual > predicted × 1.25 → tighten for session |
| D-020 | Trade frequency | Max trades per regime type per session |
| D-021 | Regime guard | HMM ≠ LightGBM → size 50% reduction |
| D-022 | Capital preservation | 3 consecutive losses → size 50%; 5 → halt session |

---

## Frontend Rules (For Cursor Working on React)

If Cursor is asked to work on frontend trading files:

1. **Follow existing patterns exactly** — `PageHeader`, `StatCard`, `LoadingSkeleton`, `ErrorState`, `RequirePermission`
2. **All pages lazy-loaded** — `lazy(() => import('./pages/admin/trading/PageName'))`
3. **Use `useQuery` from TanStack Query** — single combined query where possible
4. **Permission gates:** minimum `trading.view`, config requires `trading.configure`
5. **Refetch intervals:** War Room 5s (market hours) / 60s (off hours), Health 10s, Performance 60s
6. **WebSocket realtime** for `trading_positions`, `trading_system_health`, `trading_prediction_outputs`
7. **All components in `src/components/trading/`**, pages in `src/pages/admin/trading/`, hooks in `src/hooks/trading/`

---

## Database Rules

1. **All new tables use `trading_` prefix**
2. **RLS enabled on every trading table** — `service_role` writes, `authenticated` reads
3. **Insert into existing tables where specified** — `job_registry`, `alert_configs`, `permissions`, `role_permissions`
4. **Never modify existing foundation table schemas** — except approved `profiles` ALTER
5. **UUID primary keys, `TIMESTAMPTZ` timestamps, `snake_case` columns**
6. **Indexes on frequently queried columns** — session_id, created_at DESC, status

---

## Build Phase Enforcement

Check `trading-docs/00-governance/system-state.md` before implementing:

- If `trading_phase: phase_1_not_started` → only data infrastructure and database schema work allowed
- If `trading_phase: phase_2_*` → prediction and virtual trading work allowed
- If `trading_phase: phase_3_*` → admin console frontend work allowed
- Do NOT skip phases. Each phase has Go/No-Go criteria that must be met.

---

## FINAL WARNING

If you skip reading governance docs, generate code for a phase that isn't active, modify foundation files, override locked decisions, create silent failure paths, or skip the paper phase — the work is INVALID and must be reverted.
