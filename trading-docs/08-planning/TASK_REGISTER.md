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

## SECTION 1 — ONGOING OPERATIONAL TASKS

### 1A — Pre-Market (Before 9:30 AM ET each trading day)

- [ ] Verify Railway diplomatic-mercy service shows "Active"
- [ ] Check Railway logs for overnight errors or alerts
- [ ] Confirm no open positions from prior day (eod_reconciliation_clean)

### 1B — At 9:40 AM ET (Run Diagnostic)

Run this command from the repo root and paste output:
```powershell
railway run python -m scripts.diagnostic
```

The script lives at `backend/scripts/diagnostic.py` and reports:
Databento OPRA tail, today's calendar intel, last 3 predictions,
last 3 positions, GEX values, all 6 feature-flag states, and the
closed paper-trade count vs activation thresholds.

### 1C — Post-Consolidation Session 1 Monitoring
**Run after merging `feature/consolidation-s1` and redeploying Railway.**
These checks confirm the signal polarity fix is working in production.

**Check within 30 minutes of Railway restart:**
- [ ] Search Railway logs for `signal_mult_audit`
  - `has_vix_z_data: true` → VIX z-score writer confirmed working ✅
  - `has_vix_z_data: false` → Restart Railway again (polygon_feed needs 5 cycles × ~5 min warm-up)
- [ ] Search logs for `polygon_vix_zscore_updated`
  - Should appear every ~5 min once vix_history has 5+ entries
- [ ] Search logs for `signal_sizing_applied`
  - Should appear on sessions where VIX z-score > 1.5 or term ratio > 1.10
  - If never appearing: conditions may simply be calm — check `signal_mult_audit` values

**Confirm after first full trading session:**
- [ ] In Supabase `trading_feature_flags` table: 13 rows present (from startup backfill)
  - All 6 signal flags should show `enabled: true`
  - Strategy/agent flags should show `enabled: false` (until manually enabled)
- [ ] In Supabase `trading_positions` table: `decision_context` column is non-empty
  - Should contain `flags_at_selection`, `signal_mult`, `has_vix_z_data` fields
  - Previously was all-false due to C-2 bug — now populated from strategy_selector
- [ ] In Lovable frontend `/trading/flags`:
  - Signal flags show as ON (toggle in enabled state)
  - Were previously showing as OFF due to B-4 frontend polarity bug

**If any check fails:**
- `has_vix_z_data` always false: Railway needs restart; polygon_feed.py wasn't updated
- Signal flags show OFF in UI: CSP fix not deployed (run `supabase functions deploy set-feature-flag`)
- `decision_context` empty: Session 1 PR not merged to main; check Railway deployment

### 1D — Enable AI Synthesis (After Confirming Trading is Live)

- [ ] Enable from `/trading/activation` page → toggle AI Synthesis ON
  OR: Railway Redis → `agents:ai_synthesis:enabled` = `true`
- [ ] Watch Railway logs for:
  `synthesis_written_to_redis`
  `prediction_from_ai_synthesis direction=... confidence=...`
- [ ] Verify calendar agent fired: `economic_calendar_job_complete`
- [ ] Verify macro agent fired: `macro_agent_complete`

### 1E — Phase 1 Exit Gate (Confirm ALL before real capital)

- [ ] Real SPXW symbols in Databento Redis (not empty, not zero)
- [ ] Predictions appearing in trading_prediction_outputs table
- [ ] At least 1 paper position opened and closed same day
- [ ] No unhandled exceptions in Railway logs during market hours
- [ ] Calendar agent firing correctly at 8:45 AM ET
- [ ] Macro agent firing correctly at 8:45 AM ET
- [ ] `has_vix_z_data: true` in signal_mult_audit logs
- [ ] `trading_feature_flags` table has 13 rows with correct polarity
- [ ] `decision_context` column populated in trading_positions

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

- [x] Phase 3C Calendar Spread built and wired (feature/phase-3c-calendar-spread)
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

## SECTION 7 — COMPLETED PHASES (April 2026)

### Phase 2A — Economic Intelligence Layer
- [x] Economic calendar agent (Finnhub + FRED, day classification)
- [x] Macro agent (CME FedWatch, consensus direction bias)
- [x] Synthesis agent (Claude/OpenAI, configurable via AI_PROVIDER env var)
- [x] Surprise detector (actual vs consensus on catalyst days)
- [x] Prediction engine reads ai:synthesis:latest when fresh

### Phase 2B — Strategy Wiring
- [x] Iron butterfly (gamma pin, GEX wall within 0.3%)
- [x] Long straddle (pre-catalyst, exits 30min before announcement)
- [x] AI hint override flag (confidence ≥0.65 overrides regime)
- [x] Risk engine debit risk table per strategy type

### Phase 2C — Flow + Sentiment Agents
- [x] Flow agent (Unusual Whales + Polygon P/C ratio)
- [x] Sentiment agent (NewsAPI + Fear/Greed + overnight gap)
- [x] Synthesis reads flow + sentiment briefs, computes confluence_score

### Phase 3C — Calendar Spread
- [x] Post-catalyst IV crush strategy (sell 0DTE ATM / buy next-Friday)
- [x] Fires only after announcement time (≥14:30 ET on event days)
- [x] DB migration: long_straddle + calendar_spread constraint, far_expiry_date

### Phase 4C — Trading Console
- [x] Dedicated /trading/* dashboard (TradingLayout, own nav, own permissions)
- [x] /admin/trading/* backward-compat redirects
- [x] Trading Console in dashboard switcher (gated on trading.view)
- [x] /trading/intelligence — AI Intelligence page (synthesis/flow/sentiment/calendar)
- [x] /trading/flags — Feature Flags page (toggle switches, confirmation dialogs)
- [x] /trading/strategies — Strategy Library (all 7 strategies, conditions, sizing)
- [x] /trading/milestones — Trade milestones with progress bar
- [x] /trading/subscriptions — All services, costs, masked API key previews
- [x] Backend: /admin/trading/intelligence, /admin/trading/feature-flags endpoints
- [x] Backend: /admin/subscriptions/key-status endpoint

### Phase A — Closed-Loop AI Feedback (Loop 1)
- [x] feedback_agent.py with temporal lateral join (not session-level)
- [x] Wilson CI on every win-rate cell (95% confidence intervals)
- [x] Per-cell avg winner / avg loser / net P&L (not just win rate)
- [x] Bootstrap floor: no brief published below 10 closed trades
- [x] 4-day Redis TTL (survives long weekends)
- [x] Regime-conditional breakdown via GROUP BY
- [x] Calendar-aware: skips non-market days
- [x] Failure mode documented: DEL ai:feedback:brief resets to neutral
- [x] synthesis_agent reads feedback brief, adds PERFORMANCE FEEDBACK section
- [x] Insufficient_history → feedback section completely absent from prompt
- [x] decision_context JSONB column on trading_positions (A/B audit trail)
- [x] prediction_id FK on trading_positions (Loop 2 training prep)
- [x] Per-day token counter: ai:tokens:in/out:YYYY-MM-DD (90-day TTL)
- [x] get_feedback_trades() Postgres RPC function (lateral join)

### Market Calendar Awareness
- [x] backend/market_calendar.py: 2026 holiday list + early-close days
- [x] is_market_open(), is_market_day(), get_time_stop_345pm(), get_time_stop_230pm()
- [x] src/lib/market-calendar.ts: frontend mirror
- [x] Feeds write idle (not degraded) outside market hours
- [x] Time stops adjusted for early-close days (12:45 PM instead of 3:45 PM)
- [x] Health page: critical banner suppressed outside market hours
- [x] DB migration: idle added to trading_system_health status constraint

### AI Provider Swappable
- [x] AI_PROVIDER, AI_MODEL, OPENAI_API_KEY in config.py
- [x] synthesis_agent dispatches to Anthropic or OpenAI via _call_ai_provider()
- [x] Safety bounds enforced identically for both providers
- [x] provider + model fields in synthesis output for auditability

### Agent Health Monitoring
- [x] All 6 agents write healthy/idle/error to trading_system_health
- [x] EXPECTED_SERVICES: 19 services (9 engine + 7 agents + 3 circuit breakers)

### HARD-A — Circuit Breakers & Emergency Recovery
- [x] run_emergency_backstop() at 3:55 PM ET — closes stuck positions
- [x] run_prediction_watchdog() every 5 min — closes positions if engine silent >12 min
- [x] run_eod_position_reconciliation() at 4:15 PM ET — force-closes stale opens
- [x] _validate_brief() in feedback_agent — prevents corrupt Redis writes
- [x] _safe_redis() in prediction_engine — staleness-aware Redis reads
- [x] prediction_watchdog, emergency_backstop, position_reconciliation in health monitoring

---

## SECTION 8 — ONGOING HARDENING (Any Sprint)

### Consolidation Sprint — P0/P1 Fixes (April 2026)

These items fix silent failures identified in the 2026-04-19 audit.
See CONSOLIDATION_SPRINT_PLAN.md for full detail on each fix.

**Session 1 — Signal Polarity + VIX Writers (branch: consolidation-s1)**
- [~] B-3: _check_feature_flag polarity inverted — all 6 signals silently OFF (commit: 15605d5)
- [~] B-1: polygon:vix:z_score never written — Signals D + F no-ops (commit: 15605d5)
- [~] B-2: polygon:vix9d:current never written — Signal A degraded (commit: 15605d5)
- [~] B-4: SIGNAL_FLAG_KEYS missing 3 of 6 in frontend (commit: 15605d5)
- [~] A2: decision_context captured at selection time (commit: 15605d5)
- [~] A5: signal_mult_audit log with has_vix_z_data smoke signal (commit: 15605d5)
Status: PR open, baking 1 trading day before merge

**Session 2 — Earnings + Synthesis + Kill Switch (pending)**
- [ ] B-5: Earnings unit mismatch — percent vs fraction in has_sufficient_edge
- [ ] B-6: strategy:earnings_straddle:enabled not in _TRADING_FLAG_KEYS (no kill switch)
- [ ] B-7: Normalize earnings Redis key name (earnings:upcoming_events)
- [ ] B-8: AI synthesis bypasses agents:ai_synthesis:enabled flag check
- [ ] C-1: KillSwitchButton silently fails — RLS denies authenticated users
- [ ] C-2: ExecutionEngine prefers signal decision_context over stale flag reads

**Session 3 — Reliability Fixes (pending)**
- [ ] C-3: polygon_feed health writes to wrong service name (data_ingestor → polygon_feed)
- [ ] C-4: strategy:long_straddle:enabled flag not enforced in selector
- [ ] C-5: bare except: pass with no logging in macro/flow/sentiment agents
- [ ] C-6: useTradeIntelligence swallows query errors — blank Intelligence page
- [ ] C-7: useAbComparison.gate.built always true — inconsistent with useActivationStatus
- [ ] C-8: Missing replace_existing + day_of_week guards on agent scheduler entries

**Session 4 — Test Hardening (pending)**
- [ ] Integration test: strategy_selector.select() full signal_mult composition
- [ ] Polarity test: all 6 signal flags default ON in live select() call
- [ ] Feature flag mirror upsert test
- [ ] _backfill_feature_flags_to_supabase test
- [ ] Earnings unit test matrix (fraction inputs)
- [ ] Edge Function auth tests (set-feature-flag, subscription-key-status)

**Session 5 — Documentation Reconciliation (pending)**
- [ ] TASK_REGISTER: mark Phase 5A items [x] with commit hashes
- [ ] TASK_REGISTER: fix Section 10 strategy status table
- [ ] MASTER_PLAN: Phase 3B status "COMPLETE (infra built)"
- [ ] MASTER_PLAN: Phase 5A status "IN PRODUCTION"
- [ ] reference/route-index.md: add all /trading/* routes
- [ ] reference/database-migration-ledger.md: add 8 missing migrations
- [ ] reference/permission-index.md: trading.view + trading.configure → implemented
- [ ] reference/config-index.md: add 12 flag keys
- [ ] Phase closure docs: 2A, 2B, 2C, 3C, 4C, Phase A
- [ ] Risk register: add 4 new risks from audit

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
- [x] DB constraint: long_straddle added to trading_positions (20260419 migration)
- [x] DB column: far_expiry_date added for calendar_spread near/far legs

---

## SECTION 9 — FUTURE ROADMAP ITEMS (Year 2+)

Document and preserve. Do not build yet.

- [ ] Multi-asset trend following (Year 2 — needs $500k+ capital)
- [ ] Statistical arbitrage SPY/SPX/VIX (Year 2 — needs sub-ms execution)
- [ ] Crypto options on Deribit (Year 2 — 24/7 monitoring)
- [ ] Reinforcement learning agent (Year 3 — needs 10k+ real outcomes)
- [ ] Subscription SaaS revenue model (after 5+ live users proven)
- [ ] Unusual Whales paid API subscription
  (validate Polygon P/C alone adds value first — if yes, subscribe)

---

## SECTION 10 — CURRENT SYSTEM STATUS

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
