# MarketMuse — Master Strategic Plan v3.2
**Owner:** tesfayekb | **Updated:** April 2026 | **Supersedes:** All prior planning docs
**Repo:** https://github.com/tesfayekb/beyenestock-of-foundation-first

---

## THE VISION (Permanent — Never Loses Context)

Build the most profitable AI-powered autonomous trading system that:
1. Trades SPX/NDX 0DTE options using multi-agent AI decisions across multiple strategies
2. Covers every meaningful market condition — no profitable day left untouched
3. Is modular — each strategy, data source, and UI panel is fully independent
4. Is hardened — one module failing never crashes another
5. Shows live paper trading performance transparently
6. Allows 1-3 trusted users to follow the system (invitation only, no billing yet)
7. Targets 35-55% annual returns at full build-out
8. Is the foundation for future modules: futures, earnings, crypto, multi-asset

**Capital:** $200k-$500k admin account, margin available.
**Tax:** Section 1256 / 60-40 on all SPX/SPXW index options.
**No subscription billing in current build.**

---

## ARCHITECTURE PRINCIPLES (Non-Negotiable)

### Rule 1 — Separate Directories for Separate Systems
```
backend/           → Core SPX 0DTE engine (never destabilize this)
backend_agents/    → AI decision layer (Phase 2C)
backend_earnings/  → Earnings volatility system (Phase 5A)
backend_futures/   → Futures momentum system (Phase 5B)
```
Each directory deploys independently. If `backend_earnings/` crashes, `backend/` keeps trading.

### Rule 2 — Modules Communicate via Redis or REST Only
No direct Python imports between directories.
Signals flow through Redis keys or HTTP endpoints.
`backend/` reads `ai:synthesis:latest` from Redis — it never imports from `backend_agents/`.

### Rule 3 — Every External Dependency Has a Fallback
- Databento fails → GEX uses last known value (TTL 1hr)
- AI agents fail → prediction_engine uses rule-based GEX/ZG
- Kelly DB query fails → Kelly returns 1.0
- Tradier fails → execution engine logs and halts, never guesses

### Rule 4 — Health Checks Validate Output Quality, Not Just Uptime
Every service must assert meaningful output, not just "process is running":
- `gex_engine` → healthy only if `gex:by_strike` has >5 entries
- `prediction_engine` → healthy only if prediction written in last 10 min (market hours)
- `databento_feed` → healthy only if valid trade in last 30s (market hours)
- `execution_engine` → healthy only if Tradier responded in last 5 min

### Rule 5 — Feature Flags for Every New Strategy
New strategies are gated by Redis flags — OFF by default until 20+ paper trades:
```
strategy:iron_butterfly:enabled     → false
strategy:long_straddle:enabled      → false
strategy:bull_debit_spread:enabled  → false
strategy:bear_debit_spread:enabled  → false
strategy:calendar_spread:enabled    → false
```
Admin console toggle — no code deploy needed to enable/disable a strategy.

### Rule 6 — Audit Trail on Every Trade
Every trade must log: entry reason, prediction score, strategy selected,
Greeks at entry, exit reason, P&L attribution. This feeds the meta-label model.

---

## BACKEND MODULE MAP

### Current (production — handle with care)
```
backend/
├── prediction_engine.py   ← Regime classifier (GEX/ZG rule-based today, AI in Phase 2C)
├── strategy_selector.py   ← Picks strategy from prediction output + feature flags
├── strike_selector.py     ← Computes actual strike prices
├── risk_engine.py         ← Kelly sizing, position limits, -3% drawdown halt
├── execution_engine.py    ← Places orders via Tradier
├── position_monitor.py    ← Monitors open positions, fires exits
├── gex_engine.py          ← Computes GEX from Databento options flow
├── databento_feed.py      ← Real-time OPRA options trade stream (fixed Apr 2026)
├── tradier_feed.py        ← SPX quotes, options chain
├── polygon_feed.py        ← VIX, VVIX, indices data
├── session_manager.py     ← Daily session lifecycle (fixed Apr 2026)
├── model_retraining.py    ← Accuracy tracking, Kelly from DB
├── calibration_engine.py  ← Weekly parameter recalibration
└── main.py                ← APScheduler, all job wiring
```

### Future Directories (new, isolated)
```
backend_agents/            ← AI DECISION LAYER (Phase 2C)
├── macro_agent.py         ← FRED calendar, Fed watch, yield curve
├── flow_agent.py          ← Unusual Whales, put/call ratios
├── sentiment_agent.py     ← NewsAPI headlines, Fear & Greed
├── synthesis_agent.py     ← Claude API synthesis → trade recommendation
└── agent_scheduler.py     ← Runs agents 8:30/9:00/9:15 AM ET

backend_earnings/          ← EARNINGS VOLATILITY (Phase 5A)
├── earnings_calendar.py   ← AAPL/NVDA/META/TSLA/AMZN/GOOGL schedule
├── iv_analyzer.py         ← Historical vs implied move comparison
├── straddle_engine.py     ← Entry/exit logic
└── earnings_main.py       ← Standalone scheduler

backend_futures/           ← FUTURES MOMENTUM (Phase 5B)
├── ib_feed.py             ← Interactive Brokers ES/NQ data
├── momentum_detector.py   ← Trend signals
├── futures_risk.py        ← Leverage-adjusted sizing
└── futures_main.py        ← Standalone scheduler
```

---

## CONSOLE ARCHITECTURE

### Current Consoles
```
/admin/                → Admin only (user mgmt, system health)
├── trading/health     ← Service health ✅ built
├── trading/positions  ← Open/closed positions ✅ built
├── trading/signals    ← Prediction outputs ✅ built
├── trading/performance← P&L, win rate ✅ built
├── trading/war-room   ← Live monitoring ✅ built
└── trading/config     ← System config ✅ built

/user/                 → 1-3 invited users (read-only)
├── dashboard          ← Performance summary (Phase 4B)
└── profile            ← Settings ✅ built
```

### New: Trading Console (Phase 4C+)
```
/trading/              → TRADING CONSOLE (new section)
│
├── overview/          ← Cross-module P&L, capital allocation pie,
│                         combined Sharpe/drawdown, module comparison
│
├── options/           ← SPX 0DTE Module (Phase 4C)
│   ├── Live prediction + regime + AI rationale
│   ├── Current open position Greeks
│   ├── Strategy toggle switches (feature flags)
│   ├── Today's session P&L + rolling stats
│   └── Backtest results per strategy
│
├── earnings/          ← Earnings Volatility Module (Phase 5A)
│   ├── Upcoming calendar with IV rank vs historical move
│   ├── Active straddle positions
│   ├── P&L by ticker
│   └── Enable/disable per ticker
│
└── futures/           ← Futures Momentum Module (Phase 5B)
    ├── ES/NQ live momentum signals
    ├── Active futures positions
    ├── Correlation vs options module
    └── Enable/disable
```

The trading console shows all modules in one place but each module is
independently enabled/disabled. An operator can run options-only,
earnings-only, or all three simultaneously.

---

## COMPLETE STRATEGY LIBRARY

### Market Condition → Strategy Map

| # | Condition | VIX | Direction | Strategy | Win Rate | Days/Yr | Status |
|---|---|---|---|---|---|---|---|
| 1 | Range, low vol | <15 | Neutral | Iron Condor | 81% | 40-60 | ✅ Live |
| 2 | Range, normal vol | 15-20 | Neutral | Iron Condor | 72% | 80-100 | ✅ Live |
| 3 | Gamma pin | Any | Neutral+pin | Iron Butterfly | 75-85% | 20-30 | ⚠️ Partial |
| 4 | Pre-catalyst | Any | Unknown | Long Straddle | 60-65% | 30-40 | ❌ Phase 2A |
| 5 | Strong bull | Any | Bull >70% | Bull Call Spread | 55-65% | 50-70 | ❌ Phase 2B |
| 6 | Strong bear | Any | Bear >70% | Bear Put Spread | 55-65% | 30-50 | ❌ Phase 2B |
| 7 | Post-catalyst | >20 | Fading vol | Calendar Spread | 65-70% | 20-30 | ❌ Phase 3C |
| 8 | Crisis/VIX>35 | >35 | Any | Sit out | N/A | 10-20 | ✅ Live |

**Current coverage: ~120-160 trading days/year**
**Full library at Phase 3C: ~270-320 trading days/year**
**Honest addressable gain from coverage expansion: +6-14% annually (overlap-adjusted)**

---

## PROFIT REGISTER (Nothing Dropped)

Every profitable idea ever discussed. Status: ACTIVE / BACKLOG / REJECTED.

### ACTIVE — Year 1

| # | Item | Phase | Build Time | Honest ROI |
|---|---|---|---|---|
| 1 | Iron Condor + B1/B2/B3/B4 improvements | Done | — | Baseline 18-25% |
| 2 | Kelly sizing wired to live WR | Done | — | Included in baseline |
| 3 | Catalyst regime gate (FRED calendar) | 2A | 1-2 wks | +2-4% (loss avoidance) |
| 4 | Iron Butterfly on gamma pin days | 2A | 1 wk | +1-2% |
| 5 | Long Straddle on catalyst days | 2A | 2 wks | +3-6% |
| 6 | Bull Call Debit Spread | 2B | 1 wk | +2-4% |
| 7 | Bear Put Debit Spread | 2B | 1 wk | +1-3% |
| 8 | Multi-agent AI morning brief (4 agents) | 2C | 4-6 wks | +4-8% |
| 9 | Options flow intelligence (Unusual Whales as AI input) | 2C | 1 wk | Included in #8 |
| 10 | Meta-label model on real trade outcomes | 3A | 3 wks | +3-6% |
| 11 | 90-day A/B paper test gate | 3B | 13 wks | Go/no-go gate |
| 12 | Calendar spread post-catalyst | 3C | 2 wks | +2-4% |
| 13 | User auth + read-only dashboard | 4A/B | 2 wks | Platform foundation |
| 14 | Trading console options module | 4C | 2-3 wks | Visibility + confidence |

**Overlap-adjusted cumulative target at Phase 3 completion: 32-45% annually**

### BACKLOG — Year 2

| # | Item | Why Deferred | ROI When Live |
|---|---|---|---|
| 15 | Real-broker per-user mirror | Governance review + 3-5 wks build | Platform enabler |
| 16 | Earnings volatility system (backend_earnings/) | 8-12 week standalone system | +3-6% on 15% allocation |
| 17 | Futures momentum system (backend_futures/) | New broker (IB), 12-16 weeks | +2-5% on 15% allocation |
| 18 | Unusual Whales paid tier | Validate free flow data first | +1-2% marginal |
| 19 | Trading console earnings + futures modules | After systems exist | Visibility |
| 20 | AI Research Engine as reusable microservice | Extract from backend_agents/ when 2nd system needs it | Platform |
| 21 | Subscription SaaS revenue | After 5+ live users confirmed working | $50-200k/yr at scale |

### BACKLOG — Year 3+

| # | Item | Why | Timeframe |
|---|---|---|---|
| 22 | Multi-asset trend following | Multiple brokers, $500k+ capital | Year 2 |
| 23 | Statistical arbitrage (SPY/SPX/VIX) | Retail execution bleeds the edge | Year 2 |
| 24 | Crypto options (Deribit BTC/ETH) | 24/7 monitoring, different tax | Year 2 |
| 25 | Reinforcement learning agent | Needs 10k+ real trade outcomes | Year 3 |
| 26 | Options market making | Sophisticated infrastructure | Year 3+ |

### REJECTED (Do Not Revisit)

| # | Item | Reason |
|---|---|---|
| R1 | Naked options (naked puts/calls/ratio spreads) | Undefined risk, violates Section 1256 |
| R2 | Strategies promising >60% annualized consistently | Backtest overfit or marketing |
| R3 | "200-400% catalyst returns" as system-level headline | Per-trade peak ≠ annualized system return |
| R4 | "29-58% CAGR trend following" as baseline | 1980s numbers; live CTA benchmark is 5-12% |

---

## ROI PROJECTION — HONEST AND OVERLAP-ADJUSTED

| Stage | Cumulative Timeline | Annual Return | Revenue |
|---|---|---|---|
| Phase 1 stable | Now | 18-25% | — |
| + Phase 2 complete | +10 weeks | 28-40% | — |
| + Phase 3 A/B validated | +8 weeks | 32-45% | — |
| + Phase 4 platform | +4 weeks | 32-45% | — |
| + Phase 5 earnings+futures | +6-9 months | 38-55% | — |
| + Subscription billing | +12 months | 38-55% trading | $50-200k SaaS |

**Cost drag: -3-5% annually. On $200k account, costs ~3.5% of capital.**
**Gate: directional AI accuracy ≥55% live required for upper band (A/B test answers this).**

---

## 5-PHASE ROADMAP

### PHASE 1 — Stabilize (COMPLETE)
**Exit gate:** Real SPXW symbols in Redis + predictions in DB + positions opening.

### PHASE 2 — Multi-Strategy + AI Brain (COMPLETE)
All sub-phases 2A, 2B, 2C complete. All strategies wired and feature-flagged.
All AI agents built and deployed. See TASK_REGISTER.md Section 7 for details.

### PHASE 3 — Meta-Label + Validation (IN PROGRESS)
- 3A: Meta-label model — infrastructure built, dormant until 100 closed trades
- 3B: A/B shadow infrastructure — COMPLETE (commit: 20260426_ab_shadow_tables.sql)
  - `ab_session_comparison` table live
  - `shadow_engine.py` running daily
  - `useAbComparison` hook feeding Activation Dashboard
  - 90-day gate tracked in `paper_phase_criteria`
- 3C: Calendar spread — COMPLETE

### PHASE 4 — User Platform (IN PROGRESS)
- 4C: Trading Console — COMPLETE (see Section 7)
- 4A, 4B, 4D — NOT YET BUILT

### NEXT BUILDS (in priority order as of April 2026):
1. HARD-B: External alerting (Gmail/Slack on halt/drawdown events)
2. VVIX daily history fix (mirrors S6 E-2 — deferred, tracked in S8 xfail test)
3. Calendar spread MTM pricing (replace entry-value stub with real far/near differential)
4. Loop 2 meta-label model training (requires 100+ clean closed trades post-S4)
5. Real capital deployment (requires A/B gate: 90 days + 100 trades + +8% B lead)
6. Phase 4A/4B/4D: User platform expansion (post real-capital validation)

See trading-docs/08-planning/MASTER_PLAN.md for full phase specifications.
Full roadmap: Download MARKETMUSE_PHASE_PLAN_V2.md from project lead.

**Monday 9:40 AM ET verification:**
```powershell
railway run python -c "
import sys, json; sys.path.insert(0,'backend')
import os, redis
from db import get_client
r = redis.from_url(os.environ['REDIS_URL'])
entries = r.lrange('databento:opra:trades', -3, -1)
print('=== Databento ===')
for e in entries:
    d = json.loads(e)
    print(f'  symbol={d.get(\"symbol\")!r} price={d.get(\"price\")} strike={d.get(\"strike\")}')
r2 = get_client().table('trading_prediction_outputs').select('predicted_at,no_trade_signal,direction').order('predicted_at',desc=True).limit(3).execute()
print()
print('=== Predictions ===')
for p in r2.data or []: print(f'  {p[\"predicted_at\"]} no_trade={p[\"no_trade_signal\"]} dir={p[\"direction\"]}')
r3 = get_client().table('trading_positions').select('id,strategy_type,entry_at,status').order('entry_at',desc=True).limit(3).execute()
print()
print('=== Positions ===')
for p in r3.data or []: print(f'  {p[\"entry_at\"]} {p[\"strategy_type\"]} {p[\"status\"]}')
"
```

---

### PHASE 2 — Multi-Strategy + AI Brain (Weeks 5-14)

#### 2A: Catalyst Gate + Iron Butterfly + Long Straddle (Weeks 5-7)
Cursor tasks to generate: `CURSOR_TASK_PHASE_2A_CATALYST_GATE.md`,
`CURSOR_TASK_PHASE_2A_IRON_BUTTERFLY.md`, `CURSOR_TASK_PHASE_2A_LONG_STRADDLE.md`
- Modifies: `backend/` only, feature-flagged OFF by default
- New data: FRED API (free)

#### 2B: Directional Debit Spreads (Weeks 7-9)
Cursor tasks: `CURSOR_TASK_PHASE_2B_BULL_SPREAD.md`, `CURSOR_TASK_PHASE_2B_BEAR_SPREAD.md`
- Modifies: `backend/` only, feature-flagged OFF by default
- Fires only when AI confidence > 0.70 (safe until AI layer is live)

#### 2C: Multi-Agent AI Brain (Weeks 9-14, new `backend_agents/` directory)
Cursor task: `CURSOR_TASK_PHASE_2C_AI_AGENTS.md`
- New directory: `backend_agents/` — zero changes to `backend/`
- Redis interface: agents write to `ai:synthesis:latest`
- `backend/prediction_engine.py` reads it with fallback to rule-based
- New data subscriptions: Unusual Whales ($50/mo), NewsAPI ($50/mo)
- New cost: Claude API ~$100-200/mo

---

### PHASE 3 — Meta-Label + Validation (Weeks 14-22)

#### 3A: Meta-Label Model (gated on ≥100 closed paper trades)
- Predict "will THIS trade hit 40% profit before stop?" — not direction
- Trains on Phase A1 outcome labels already being collected
- Feature flag: `model:meta_label:enabled`

#### 3B: 90-Day A/B Paper Test
- Portfolio A: rule-based GEX/ZG baseline
- Portfolio B: Phase 2C AI synthesis
- Gate: ≥+8% annualized uplift → allocate real capital 25%→50%→100%
- Kill: any strategy Sharpe drops >1σ below paper over 20 trades → auto-disable

#### 3C: Calendar Spread
- Feature flag: `strategy:calendar_spread:enabled`
- More complex (two expirations), lower priority than 3A/3B

---

### PHASE 4 — User Platform (Months 3-6, parallel to Phase 3)

#### 4A: Multi-User Auth (1 Cursor session)
- 2-3 users, `user` role, row-level security by user_id

#### 4B: User Dashboard (1-2 Cursor sessions)
- Read-only: system P&L, win rate, recent trades, drawdown

#### 4C: Trading Console — Options Module (2-3 Cursor sessions)
- New `/trading/options/` section in frontend
- Live prediction + regime + AI rationale
- Strategy feature flag toggles
- Designed to extend to earnings and futures modules later

#### 4D: Optional Broker Mirror (3-5 weeks, after governance review)
- Per-user Tradier credentials, position sizing to their account
- Requires disclaimer documentation before building

---

## PHASE 5 — Strategy Expansion (Months 6-18)

#### 5A: Earnings Volatility System — COMPLETE (April 2026)
`backend_earnings/` built, `earnings_straddle` strategy wired,
flag `strategy:earnings_straddle:enabled` (default OFF — enable
manually after operator review). `/trading/earnings` page live.
- Universe: AAPL, NVDA, META, TSLA, AMZN, GOOGL
- Straddle/strangle when historical earnings move > implied move
- 15% capital allocation
- Trading console: `/trading/earnings/`

#### 5B: Futures Momentum (backend_futures/, 12-16 weeks)
- ES/NQ trending day capture — hedges iron condor losses on trend days
- Interactive Brokers API
- 15% capital allocation
- Trading console: `/trading/futures/`

---

## STRATEGIC DECISIONS LOCKED

1. Section 1256/SPX/SPXW only in core system
2. Defined risk only — no naked options ever
3. No subscription billing until proven with 5+ live users
4. 90-day A/B gate mandatory before real capital
5. Feature flags for all new strategies — admin toggle, no deploy needed
6. Separate directories for separate systems — never merge earnings or futures into backend/
7. Every module has a fallback — AI fails → rule-based continues
8. Kelly sizing max 2× multiplier — daily -3% halt non-negotiable

---

## ITEMS THAT MUST NEVER BE DROPPED

Regardless of how this plan is refined, every item below must remain tracked:

**Strategies:** Iron Butterfly · Long Straddle · Bull/Bear Debit Spreads · Calendar Spread · Earnings System · Futures System · Multi-asset Trend · Crypto Options

**Intelligence:** Multi-agent AI brief · Options Flow (Unusual Whales) · Meta-label model · Reinforcement learning agent

**Platform:** 90-day A/B gate · Trading console module architecture · Per-user broker mirror · Subscription revenue model

**Hardening:** Feature flags for all strategies · Circuit breakers on all external calls · Output-quality health checks · Per-module kill switches · Complete trade audit trail

---

## OPERATING COSTS

| Service | Monthly |
|---|---|
| Databento OPRA | $199 |
| Polygon Indices | $49 |
| Railway | ~$50 |
| Claude API (Phase 2C+) | $100-200 |
| NewsAPI | $50 |
| Unusual Whales | $50 |
| Commissions | variable |
| **Total** | **~$500-600** |

$200k account: **3-3.6% annual drag** · $500k account: **1.2-1.4% drag**

---
*MarketMuse v3.2 | April 2026 | tesfayekb*
