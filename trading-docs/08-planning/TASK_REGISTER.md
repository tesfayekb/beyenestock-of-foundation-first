# MarketMuse — Operational Task Register

**Owner:** tesfayekb | **Updated:** April 2026
**Authority:** This document is the single source of task tracking.
Cursor must update checkboxes after completing any item.

---

## HOW TO USE THIS DOCUMENT

- `[ ]` = Not done
- `[x]` = Complete
- `[~]` = In progress
- Cursor: after completing any task, update the checkbox and add
  the commit hash in parentheses. Example: `[x] (a1b2c3d)`

---

## SECTION 1 — MONDAY APRIL 21 TASKS (Time-Sensitive)

### 1A — Pre-Market (Before 9:30 AM ET)

- [ ] Verify Railway diplomatic-mercy service shows "Active"
- [ ] Run Supabase migration check — regime constraint has 11 values
- [ ] Run Supabase migration check — last_valid_trade_at column exists
- [ ] Confirm Phase 2C PR merged to main (done Saturday)

### 1B — At 9:40 AM ET (Run Diagnostic)

Run this command from the repo root and paste output:
```powershell
railway run python -m scripts.diagnostic
```

The script lives at `backend/scripts/diagnostic.py` and reports:
Databento OPRA tail, today's calendar intel, last 3 predictions,
last 3 positions, GEX values, all 6 feature-flag states, and the
closed paper-trade count vs activation thresholds.

Expected: real SPXW symbols, predictions in DB, positions opening.

### 1C — If Scenario A or B Confirmed (System Trading)

- [ ] Enable AI synthesis:
  Railway → Redis → New Key: `agents:ai_synthesis:enabled` = `true`

- [ ] Watch Railway logs for:
  `synthesis_written_to_redis`
  `prediction_from_ai_synthesis direction=... confidence=...`

- [ ] Verify calendar agent fired:
  Railway logs: `economic_calendar_job_complete`
  Railway logs: `macro_agent_complete`

### 1D — Phase 1 Exit Gate (Confirm ALL before real capital)

- [ ] Real SPXW symbols in Databento Redis (not empty, not zero)
- [ ] Predictions appearing in trading_prediction_outputs table
- [ ] At least 1 paper position opened and closed same day
- [ ] No unhandled exceptions in Railway logs during market hours
- [ ] Calendar agent firing correctly at 8:25 AM ET
- [ ] Macro agent firing correctly at 8:30 AM ET

---

## SECTION 2 — FEATURE FLAG ACTIVATION (In Order)

Enable ONE flag at a time. Wait for paper trade validation between each.

### 2A — Iron Butterfly (enable after 5+ paper trades)

- [ ] Enable: Railway Redis → `strategy:iron_butterfly:enabled` = `true`
- [ ] Verify logs: `gamma_pin_detected nearest_wall=...`
- [ ] Validate: iron_butterfly positions appear on pin days
- [ ] Disable if win rate < 60% over 10+ trades

### 2B — Long Straddle (enable after 20+ total trades)

- [ ] Enable: Railway Redis → `strategy:long_straddle:enabled` = `true`
- [ ] Verify logs: `straddle_pre_event_exit mins_to_event=...`
- [ ] Validate: straddle opens on event days, closes 30 min before announcement
- [ ] Disable if net negative P&L over 5+ straddle trades

### 2C — Flow Agent (enable after 20+ total trades)

- [ ] Enable: Railway Redis → `agents:flow_agent:enabled` = `true`
- [ ] Verify logs: `flow_agent_complete flow_score=... direction=...`
- [ ] Check if Unusual Whales key is valid (look for unusual_activity_count > 0)
  If key invalid: `unusual_whales_fetch_failed error=401` → falls back to Polygon P/C

### 2D — Sentiment Agent (enable after 20+ total trades)

- [ ] Enable: Railway Redis → `agents:sentiment_agent:enabled` = `true`
- [ ] Verify logs: `sentiment_agent_complete sentiment_score=... fear_greed=...`

### 2E — AI Hint Override (enable after 40+ total trades with synthesis validated)

- [ ] Confirm `agents:ai_synthesis:enabled` is ON and working first
- [ ] Enable: Railway Redis → `strategy:ai_hint_override:enabled` = `true`
- [ ] Verify logs: `strategy_from_ai_hint hint=... confidence=...`
- [ ] Compare: strategies selected via AI hint vs regime-based over 20+ trades
- [ ] Disable if AI-hint strategies underperform regime-based

---

## SECTION 3 — TRADE COUNT MILESTONES

Track progress toward key thresholds.

Check current count anytime:
```powershell
railway run python -c "
import sys; sys.path.insert(0,'backend')
from db import get_client
closed = get_client().table('trading_positions').select('id',count='exact').eq('status','closed').eq('position_mode','virtual').execute()
print(f'Closed trades: {closed.count}')
print('Thresholds: 5=butterfly, 20=kelly+straddle+flow+sentiment, 40=ai_hint, 100=meta_label')
"
```

- [ ] 1 closed trade — system confirmed working
- [ ] 5 closed trades — enable iron butterfly (Section 2A)
- [ ] 20 closed trades — Kelly sizing activates automatically
- [ ] 20 closed trades — enable straddle, flow, sentiment (Sections 2B/2C/2D)
- [ ] 40 closed trades — enable AI hint override (Section 2E)
- [ ] 100 closed trades — meta-label model can be trained (Phase 3A)

---

## SECTION 4 — PHASE 3 TASKS (After 100 Closed Trades)

### 3A — Meta-Label Model

- [ ] Confirm 100+ closed paper trades in DB
- [ ] Generate CURSOR_TASK_PHASE_3A_META_LABEL.md
- [ ] Build meta-label model (predict will this specific trade hit 40% profit)
- [ ] Features: IV rank, VIX, GEX confidence, dist_pct, strategy type,
      spread width, entry regime, AI confidence score
- [ ] Threshold: probability >= 0.65 = enter trade

### 3B — 90-Day A/B Paper Test

- [ ] Run two virtual portfolios in parallel:
      Portfolio A: rule-based GEX/ZG baseline
      Portfolio B: Phase 2 AI synthesis system
- [ ] Gate: if B shows >= +8% annualized uplift → allocate real capital
- [ ] Kill: any strategy Sharpe drops > 1σ below paper over 20 trades → disable

### 3C — Calendar Spread (Post-Catalyst IV Crush)

- [ ] Generate CURSOR_TASK_PHASE_3C_CALENDAR_SPREAD.md
- [ ] More complex (two expirations, vega management)
- [ ] Lower priority than 3A/3B

---

## SECTION 5 — PHASE 4 TASKS (Months 3-6)

### 4A — Multi-User Auth

- [ ] Add 2-3 user accounts with `user` role in Supabase RBAC
- [ ] Row-level security by user_id on all trading tables
- [ ] Generate CURSOR_TASK_PHASE_4A_USER_AUTH.md

### 4B — User Dashboard (Read-Only)

- [ ] System P&L display (today/week/month/all time)
- [ ] Win rate and profit factor
- [ ] Recent 10 trades (entry, exit, P&L — no strategy internals)
- [ ] Current open position if any
- [ ] Generate CURSOR_TASK_PHASE_4B_USER_DASHBOARD.md

### 4C — Trading Console: Options Module

- [ ] New /trading/options/ section in frontend
- [ ] Live prediction + regime + AI rationale display
- [ ] Strategy feature flag toggles (admin only)
- [ ] Session P&L and rolling stats
- [ ] Generate CURSOR_TASK_PHASE_4C_TRADING_CONSOLE.md

### 4D — Optional Broker Mirror (Requires Governance Review First)

- [ ] Document disclaimer — confirm no RIA registration required
- [ ] Per-user Tradier credential storage (encrypted)
- [ ] Position sizing to user account size
- [ ] Risk limits inherited from master
- [ ] Generate CURSOR_TASK_PHASE_4D_BROKER_MIRROR.md (after governance review)

---

## SECTION 6 — PHASE 5 TASKS (Months 6-18)

### 5A — Earnings Volatility System

- [ ] Universe: AAPL, NVDA, META, TSLA, AMZN, GOOGL
- [ ] New directory: backend_earnings/
- [ ] Straddle/strangle when historical earnings move > implied move
- [ ] 15% capital allocation
- [ ] Trading console: /trading/earnings/ module
- [ ] Generate CURSOR_TASK_PHASE_5A_EARNINGS.md

### 5B — Futures Momentum System

- [ ] New directory: backend_futures/
- [ ] Interactive Brokers API integration
- [ ] ES/NQ trending day momentum signals
- [ ] 15% capital allocation — hedges iron condor on trend days
- [ ] Trading console: /trading/futures/ module
- [ ] Generate CURSOR_TASK_PHASE_5B_FUTURES.md

---

## SECTION 7 — ONGOING HARDENING (Any Sprint)

### Health Check Quality

- [ ] gex_engine: healthy only if gex:by_strike has > 5 entries
- [ ] prediction_engine: healthy only if prediction written in last 10 min (market hours)
- [ ] execution_engine: healthy only if Tradier responded in last 5 min
- [ ] Add output-quality assertions to all health writes

### Backtest Improvements

- [ ] Rerun backtest after 30 days of live paper data to compare
- [ ] Add T-1 ZG feature (fix look-ahead bias)
- [ ] Extend coverage to pre-2022 data if available

### Known False Positives

- [ ] Review known-false-positives.md — address any D- items that remain open
- [x] D-018: Partial exit session P&L update (commit: 18ef436)
- [x] D-019: contracts variable stale after partial exit (commit: 18ef436)
- [~] D-017: SPX /prev dedup — ACCEPTED for paper phase (rv>0 guard handles it)
- [ ] D-020: IV/RV block rate monitoring (monitor after 10 paper sessions)

---

## SECTION 8 — FUTURE ROADMAP ITEMS (Year 2+)

Document and preserve. Do not build yet.

- [ ] Multi-asset trend following (Year 2 — needs $500k+ capital)
- [ ] Statistical arbitrage SPY/SPX/VIX (Year 2 — needs sub-ms execution)
- [ ] Crypto options on Deribit (Year 2 — 24/7 monitoring)
- [ ] Reinforcement learning agent (Year 3 — needs 10k+ real outcomes)
- [ ] Subscription SaaS revenue model (after 5+ live users proven)
- [ ] Unusual Whales paid API subscription
  (validate Polygon P/C alone adds value first — if yes, subscribe)

---

## SECTION 9 — CURRENT SYSTEM STATUS

Last updated: April 19, 2026

### Infrastructure
| Component | Status |
|---|---|
| Databento OPRA feed | ✅ Fixed — real SPXW symbols |
| Session management | ✅ Fixed — upsert, regime constraint |
| Health monitoring | ✅ Fixed — market-hours gate |
| Phase B1/B2/B3/B4 | ✅ Live |

### Agents (backend_agents/)
| Agent | Status | Flag |
|---|---|---|
| economic_calendar.py | ✅ Always on | N/A |
| macro_agent.py | ✅ Always on | N/A |
| surprise_detector.py | ✅ Always on (catalyst days) | N/A |
| synthesis_agent.py | ✅ Built — OFF | agents:ai_synthesis:enabled |
| flow_agent.py | ✅ Built — OFF | agents:flow_agent:enabled |
| sentiment_agent.py | ✅ Built — OFF | agents:sentiment_agent:enabled |

### Strategies
| Strategy | Status | Flag |
|---|---|---|
| Iron Condor | ✅ Live | N/A |
| Iron Butterfly | ✅ Wired — OFF | strategy:iron_butterfly:enabled |
| Long Straddle | ✅ Wired — OFF | strategy:long_straddle:enabled |
| Bull Call Debit Spread | ✅ Wired via AI — OFF | strategy:ai_hint_override:enabled |
| Bear Put Debit Spread | ✅ Wired via AI — OFF | strategy:ai_hint_override:enabled |
| Calendar Spread | ❌ Phase 3C | N/A |

### Railway API Keys
| Key | Status |
|---|---|
| FINNHUB_API_KEY | ✅ Added |
| ANTHROPIC_API_KEY | ✅ Added |
| NEWSAPI_KEY | ✅ Added |
| UNUSUAL_WHALES_API_KEY | ✅ Added (validity unconfirmed) |

---
*Task Register v1.0 — April 2026 — tesfayekb*
