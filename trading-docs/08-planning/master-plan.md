# Trading System — Master Plan

> **Owner:** tesfayekb | **Version:** 1.0 | **Baseline:** v1
> **Source:** MARKETMUSE_MASTER.md v4.0, Part 11

## Purpose

The authoritative 7-phase build plan for the MarketMuse trading system. Each phase has a stable ID, deliverables, and acceptance criteria with checkbox gate items. No phase may begin until the prior phase's Go/No-Go criteria are met (T-Rule 8).

---

## TPLAN-INFRA-001: Phase 1 — Data Infrastructure (Weeks 1–2)

**Goal:** All feeds live, data flowing into Supabase, monitoring active.

### Deliverables

| ID | Deliverable | Platform | Status |
|----|-------------|----------|--------|
| TPLAN-INFRA-001-A | Subscribe to Databento OPRA | External | `implemented` |
| TPLAN-INFRA-001-B | Subscribe to CBOE DataShop Option EOD Summary | External | `pending_approval` |
| TPLAN-INFRA-001-C | Tradier WebSocket connection + heartbeat monitor | Python/Railway | `implemented` |
| TPLAN-INFRA-001-D | Databento OPRA stream + Lee-Ready GEX synthesis | Python/Railway | `implemented` |
| TPLAN-INFRA-001-E | CBOE DataShop SFTP file pickup + morning OI baseline | Python/Railway | `not_started` |
| TPLAN-INFRA-001-F | VVIX 20-day baseline computation from Polygon | Python/Railway | `implemented` |
| TPLAN-INFRA-001-G | Write all data to Supabase + trading_system_health heartbeats | Python/Railway | `implemented` |
| TPLAN-INFRA-001-H | Run Supabase migration (all trading tables from Part 4) | Lovable/Supabase | `implemented` |
| TPLAN-INFRA-001-I | Engine Health page (`/admin/trading/health`) | Lovable/React | `implemented` |

### Phase Gate (ALL required)

- [ ] All data feeds verified live (Tradier WebSocket, Databento OPRA, CBOE DataShop)
- [ ] GEX computing at 8:30 AM pre-market
- [ ] Heartbeat triggering degraded mode on disconnect
- [ ] Engine Health page shows all services healthy
- [ ] All trading tables created in Supabase

---

## TPLAN-VIRTUAL-002: Phase 2 — Virtual Trade Engine (Weeks 3–5)

**Goal:** System generates signals from real data, records virtual positions.

### Deliverables

| ID | Deliverable | Platform | Status |
|----|-------------|----------|--------|
| TPLAN-VIRTUAL-002-A | Day Type Classifier (pre-market LightGBM) | Python/Railway | `implemented` |
| TPLAN-VIRTUAL-002-B | Regime detection (HMM + LightGBM 6-state) | Python/Railway | `implemented` |
| TPLAN-VIRTUAL-002-C | CV_Stress computation from options chain | Python/Railway | `implemented` |
| TPLAN-VIRTUAL-002-D | Layer B prediction pipeline (93 features) | Python/Railway | `implemented` |
| TPLAN-VIRTUAL-002-E | Strategy selection Stages 0–4 + trade frequency governor | Python/Railway | `implemented` |
| TPLAN-VIRTUAL-002-F | Walk-the-book order simulation (virtual mode) | Python/Railway | `implemented` |
| TPLAN-VIRTUAL-002-G | Virtual position recorder → trading_positions (mode='virtual') | Python/Railway | `implemented` |
| TPLAN-VIRTUAL-002-H | Regime disagreement guard (D-021) | Python/Railway | `implemented` |
| TPLAN-VIRTUAL-002-I | Capital preservation counter (D-022) | Python/Railway | `implemented` |
| TPLAN-VIRTUAL-002-J | Static slippage fallback | Python/Railway | `implemented` |

### Phase Gate (ALL required)

- [ ] ≥ 3 virtual signals generated per day
- [ ] All signals, positions, predictions stored in Supabase
- [ ] No unhandled exceptions over 5 consecutive days

---

## TPLAN-CONSOLE-003: Phase 3 — Admin Console (Weeks 6–7)

**Goal:** Full War Room operational for operator.

### Deliverables

| ID | Deliverable | Platform | Status |
|----|-------------|----------|--------|
| TPLAN-CONSOLE-003-A | Trading navigation section in admin-navigation.ts | Lovable/React | `implemented` |
| TPLAN-CONSOLE-003-B | Trading routes in routes.ts | Lovable/React | `implemented` |
| TPLAN-CONSOLE-003-C | War Room page (`/admin/trading/warroom`) | Lovable/React | `implemented` |
| TPLAN-CONSOLE-003-D | Positions page (`/admin/trading/positions`) | Lovable/React | `implemented` |
| TPLAN-CONSOLE-003-E | Signals page (`/admin/trading/signals`) | Lovable/React | `implemented` |
| TPLAN-CONSOLE-003-F | Performance page (`/admin/trading/performance`) | Lovable/React | `implemented` |
| TPLAN-CONSOLE-003-G | Configuration page (`/admin/trading/config`) | Lovable/React | `implemented` |
| TPLAN-CONSOLE-003-H | Kill-switch button in War Room header | Lovable/React | `implemented` |
| TPLAN-CONSOLE-003-I | Global CRITICAL banner for trading engine failures | Lovable/React | `implemented` |
| TPLAN-CONSOLE-003-J | WebSocket realtime subscriptions (positions + health) | Lovable/React | `in_progress` |

### Phase Gate (ALL required)

- [ ] Operator can see live predictions, virtual positions, regime state, CV_Stress, GEX map, engine health — all in real time
- [ ] All 6 trading admin pages functional and permission-gated
- [ ] Kill-switch renders and is hold-to-activate
- [ ] WebSocket realtime subscriptions working for positions and health

---

## TPLAN-PAPER-004: Phase 4 — Paper Phase (Weeks 8–14)

**Goal:** 45 days of automated paper trading, all 12 criteria tracked.

### Deliverables

| ID | Deliverable | Platform | Status |
|----|-------------|----------|--------|
| TPLAN-PAPER-004-A | All 12 go-live criteria tracked and written to Supabase | Python/Railway | `implemented` |
| TPLAN-PAPER-004-B | Predictive slippage model training (LightGBM) | Python/Railway | `implemented` |
| TPLAN-PAPER-004-C | CV_Stress threshold calibration (weekly CWER) | Python/Railway | `implemented` |
| TPLAN-PAPER-004-D | Touch probability calibration (grid search weekly) | Python/Railway | `implemented` |
| TPLAN-PAPER-004-E | GEX vs OCC validation (CBOE DataShop) | Python/Railway | `blocked` |
| TPLAN-PAPER-004-F | Regime model retraining + champion/challenger | Python/Railway | `implemented` |
| TPLAN-PAPER-004-G | Paper phase progress dashboard on Config page | Lovable/React | `implemented` |
| TPLAN-PAPER-004-H | Kill-switch tested against Tradier sandbox (Day 10 deadline) | Manual | `not_started` |
| TPLAN-PAPER-004-I | Sentinel deployed to GCP and tested weekly | Python/GCP | `implemented` |
| TPLAN-PAPER-004-J | Intraday execution feedback loop tested | Python/Railway | `implemented` |

### Phase Gate (ALL required — 12 Go-Live Criteria)

- [ ] 1. Aggregate prediction accuracy ≥ 58% over full 45 days
- [ ] 2. Per-regime accuracy ≥ 55% for every day type with ≥ 8 observations
- [ ] 3. Minimum 50 training examples per regime-strategy cell
- [ ] 4. Under-sampled cells flagged — live trading at 25% sizing until 50 examples
- [ ] 5. Paper Sharpe ≥ 1.5
- [ ] 6. Zero unhandled exceptions in final 20 paper sessions
- [ ] 7. All 6 circuit breaker scenarios tested in Tradier sandbox
- [ ] 8. Kill-switch response confirmed < 5 seconds from mobile
- [ ] 9. Independent Sentinel verified operational on GCP
- [ ] 10. WebSocket heartbeat verified — disconnect triggers degraded mode within 3 seconds
- [ ] 11. Predictive slippage model calibrated — minimum 200 fill observations
- [ ] 12. GEX tracking error ≤ ±15% vs OCC actuals

---

## TPLAN-HARDENING-008: Fix Group 8 — Pre-Live Hardening Gate

**Goal:** Complete all security and reliability fixes required before
live trading is enabled. Must be completed before Phase 5 begins.

**Trigger:** Generate Fix Group 8 Cursor tasks when GLC-001 through
GLC-006 show in_progress AND ≥ 25 paper sessions completed.

| ID | Deliverable | Platform | Priority | Status |
|----|-------------|----------|----------|--------|
| TPLAN-HARD-008-A | Sentinel close_all_positions_tradier calls real Tradier API for live positions | Python/GCP | P1-CRITICAL | `not_started` |
| TPLAN-HARD-008-B | Session P&L atomic UPDATE (optimistic locking) | Python/Railway | P1-HIGH | `not_started` |
| TPLAN-HARD-008-C | Sentinel separate SENTINEL_TRADIER_API_KEY credential | Python/GCP | P1-HIGH | `not_started` |
| TPLAN-HARD-008-D | RLS trading tables scoped to trading.view permission | Supabase | P2-HIGH | `not_started` |
| TPLAN-HARD-008-E | Time-stop jobs Postgres advisory lock | Python/Railway | P2-MEDIUM | `not_started` |
| TPLAN-HARD-008-F | get_or_create_session upsert ON CONFLICT | Python/Railway | P2-MEDIUM | `not_started` |
| TPLAN-HARD-008-G | Sentinel operator ACK before re-arm | Python/GCP | P2-MEDIUM | `not_started` |
| TPLAN-HARD-008-H | Error-code taxonomy in write_health_status (no raw DSNs) | Python/Railway | P3-LOW | `not_started` |
| TPLAN-HARD-008-I | Seed all 11 trading_system_health rows at migration time (status=offline) | Supabase | P2-MEDIUM | `not_started` |
| TPLAN-HARD-008-J | Databento Live graceful shutdown — call client.stop() when _stop_event fires | Python/Railway | P2-MEDIUM | `not_started` |
| TPLAN-HARD-008-K | Atomic error_count_1h increment via Postgres UPDATE...SET error_count_1h = error_count_1h + 1 | Python/Railway | P2-MEDIUM | `not_started` |
| TPLAN-HARD-008-L | encrypted_key column encryption-at-rest via pgcrypto or KMS reference before live Tradier key stored in DB | Supabase | P1-HIGH | `not_started` |

### Phase Gate (ALL P1 items required before Phase 5)
- [ ] TPLAN-HARD-008-A: Sentinel closes real Tradier positions
- [ ] TPLAN-HARD-008-B: Session P&L race condition eliminated
- [ ] TPLAN-HARD-008-C: Sentinel has isolated close-only credentials
- [ ] TPLAN-HARD-008-D: RLS scoped to trading.view permission
- [ ] TPLAN-HARD-008-L: encrypted_key enforces encryption before any live Tradier key is stored

---

## TPLAN-LIVE-005: Phase 5 — Live Execution (Week 15+)

**Goal:** Real trades executing on operator's Tradier account.

### Deliverables

| ID | Deliverable | Platform | Status |
|----|-------------|----------|--------|
| TPLAN-LIVE-005-A | Tradier OAuth connection flow on Config page | Lovable/React | `not_started` |
| TPLAN-LIVE-005-B | Live order execution engine (position_mode='live') | Python/Railway | `not_started` |
| TPLAN-LIVE-005-C | OCO orders pre-submitted at every fill | Python/Railway | `not_started` |
| TPLAN-LIVE-005-D | Actual slippage tracking vs predicted | Python/Railway | `not_started` |
| TPLAN-LIVE-005-E | Intraday execution feedback loop active | Python/Railway | `not_started` |
| TPLAN-LIVE-005-F | Sentinel live on GCP with actual account monitoring | Python/GCP | `not_started` |
| TPLAN-LIVE-005-G | Kill-switch live (not sandbox) | Manual | `not_started` |

### Phase Gate (ALL required)

- [ ] Start at Phase 2 sizing (0.5% per trade)
- [ ] OCO orders confirmed on every fill
- [ ] Sentinel independently monitoring live account
- [ ] Kill-switch tested on live (not sandbox)

---

## TPLAN-LEARN-006: Phase 6 — Learning Engine (Parallel with Phase 5)

**Goal:** Continuous model improvement running in background.

### Deliverables

| ID | Deliverable | Platform | Status |
|----|-------------|----------|--------|
| TPLAN-LEARN-006-A | Daily fast loop (isotonic recalibration, slippage update, drift z-test) | Python/Railway | `not_started` |
| TPLAN-LEARN-006-B | Weekly slow loop (model retrain, champion/challenger) | Python/Railway | `not_started` |
| TPLAN-LEARN-006-C | Intraday micro-calibration (every 2 hours) | Python/Railway | `not_started` |
| TPLAN-LEARN-006-D | Counterfactual backtest (daily post-session) | Python/Railway | `not_started` |

### Phase Gate (ALL required)

- [ ] Fast loop running daily at 4:15 PM
- [ ] Slow loop running weekly Sunday 8 PM
- [ ] Drift detection operational with z-test alerts
- [ ] Champion/challenger infrastructure passing all 7 criteria checks

---

## TPLAN-SCALE-007: Phase 7 — Phase 3 Sizing (Month 6+)

**Goal:** Graduate to standard live sizing after sustained performance.

### Deliverables

| ID | Deliverable | Platform | Status |
|----|-------------|----------|--------|
| TPLAN-SCALE-007-A | Auto-detection of advance criteria (90+ live days, ≥62% win rate) | Python/Railway | `not_started` |
| TPLAN-SCALE-007-B | Operator notification when criteria met | Lovable/React | `not_started` |
| TPLAN-SCALE-007-C | Manual advance on Config page with confirmation dialog | Lovable/React | `not_started` |

### Phase Gate (ALL required)

- [ ] 90+ live trading days completed
- [ ] Rolling 60-day win rate ≥ 62%
- [ ] Max drawdown has not exceeded 12%
- [ ] Operator manually advances (system cannot auto-advance)
