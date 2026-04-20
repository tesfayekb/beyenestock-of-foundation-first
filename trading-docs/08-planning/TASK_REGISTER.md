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

### 1F — Post-Consolidation S4-S6 Monitoring
**Run after next Railway restart post-S6 merge (commit a8175dd on main).**

**On Railway startup — confirm within 2 minutes:**
- [ ] `supabase_client_initialised http2_enabled=False patch_method=session_replacement`
  → HTTP/2 race fix still active. If missing, Railway is on old code.
- [ ] `vix_history_backfilled days=20 latest_vix=...`
  → VIX daily history seeded. z_score_daily meaningful from cycle 1.
- [ ] `feature_flags_backfilled_to_supabase count=14`
  → All 14 flags (including earnings_straddle) written with correct polarity.

**S4 kill switch verification (next time a trading session exists):**
- [ ] Toggle Kill Switch on `/trading/war-room`
  - Railway logs: `trading_cycle_skipped reason=session_halted` ✅
  - Railway logs: `position_monitor` still running (existing positions managed) ✅
  - Supabase `trading_sessions`: `session_status = 'halted'` ✅
- [ ] Confirm resume works: toggle Resume → `session_status = 'active'` ✅

**S4 flag endpoint auth verification:**
- [ ] Confirm `RAILWAY_ADMIN_KEY` is set in Railway Variables
- [ ] Confirm `RAILWAY_ADMIN_KEY` is set in Supabase Edge Function secrets
- [ ] Test toggle from `/trading/flags` still works after key is set
- [ ] If toggle fails: redeploy `set-feature-flag` Edge Function:
  `supabase functions deploy set-feature-flag --no-verify-jwt`

**S5 event regime verification (next FOMC/CPI/NFP/earnings day):**
- [ ] Railway logs at 9:30-10:00 AM ET: `regime_event_day_override`
  - Shows `has_catalyst=true` or `has_earnings=true`
  - `prediction.regime == "event"` in trading_prediction_outputs
- [ ] Strategy selector picks `long_straddle` or `calendar_spread`
  (not `iron_condor`) on event day
- [ ] If `regime_event_day_override` absent: check calendar agent fired at 8:45 AM
  (`economic_calendar_job_complete` in logs) and wrote `calendar:today:intel` to Redis

**S6 data feed verification (within 30 minutes of market open):**
- [ ] `polygon_vix_zscore_updated history_source="daily"` in Railway logs
  → Confirms VIX z-score uses 20-day daily history (not 100-min intraday window).
  If `history_source="intraday_fallback"`: daily history not yet seeded —
  wait for EOD append or redeploy to re-run backfill.
- [ ] `signal_mult_audit` shows `vix_z` values reflecting weekly/monthly
  VIX regime (typically 0.5-2.0 range), not minute-to-minute noise
- [ ] In Supabase `trading_positions`, check a closed databento-sourced trade:
  `implied_vol` field should be ~0.16-0.18 (VIX/100) not exactly 0.20
  → Confirms E-4 live VIX fix is active for GEX calculations
- [ ] `polygon:spx:return_5m` and `polygon:spx:return_1h` in Redis
  should show DIFFERENT values during an active trading session
  → Confirms E-1 fix: SPX features now use live intraday price not prev-day close

**S6 VIX daily history maturation (after first full trading day):**
- [ ] EOD (after 3 PM ET): `polygon_vix_zscore_updated history_source="daily"`
  with `daily_days=1` (first daily append)
- [ ] After 5 trading days: `daily_days=5` — z-score now uses 5 real daily values
- [ ] After 20 trading days: `daily_days=20` — full 20-day window active,
  backfill values fully replaced with real production data

**If any S4-S6 check fails, see:**
- Kill switch not halting: S4 not on Railway — force redeploy
- `history_source="intraday_fallback"` persists: `vix_daily_history` not
  being seeded — check `_backfill_vix_history` ran at startup
- `implied_vol` still 0.20: `polygon:vix:current` not in Redis —
  check polygon_feed is running and healthy on the Health page
- Event regime not firing: check `calendar:today:intel` key exists in Redis
  after 8:45 AM ET on a FOMC/CPI/NFP day

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

### Phase 5A — Earnings Volatility System
- [x] New directory: `backend_earnings/` (isolated from `backend/`)
- [x] Universe: AAPL, NVDA, META, TSLA, AMZN, GOOGL
- [x] earnings_scanner / earnings_monitor / iv_analyzer wired to scheduler
- [x] earnings_straddle strategy registered in strategy_selector
- [x] Feature flag `strategy:earnings_straddle:enabled` (default OFF —
      enable manually after operator review)
- [x] `/trading/earnings` page live (route TRADING_EARNINGS)
- [x] Status surfaces through `earnings_scanner` health row
      (in `_SCHEDULED_SERVICES` exempt set as of commit abaf8db)

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
**All sessions complete. See commit log for details.**

| Session | Focus | Commit | Status |
|---|---|---|---|
| S1 | Signal polarity + VIX writers | 270b2f6 | ✅ |
| S2 | Earnings units + synthesis flag + kill switch | 5db2dec | ✅ |
| S3 | Reliability fixes (service name, scheduler, logging) | ad85ab4 | ✅ |
| S4 | P&L sign + kill switch enforcement + auth + RLS | ac02230 | ✅ |
| S5 | Event regime + ROI levers + P1 UX | a739751 | ✅ |
| S6 | Data feed correctness (SPX, VIX z-score, GEX IV) | a8175dd | ✅ |
| S7 | Reliability cleanup (shutdown, scheduler, logger, DB) | a4c73cb | ✅ |
| S8 | Test hardening (91 new tests across S1-S8) | d64e4ff | ✅ |
| S9 | Documentation reconciliation | (this commit) | ✅ |

**Known deferred items (not blocking):**
- VVIX daily history bug (mirrors S6 E-2 for VVIX) — tracked as xfail in `test_consolidation_s8.py`
- Calendar spread MTM stub — replace in future session
- RAILWAY_ADMIN_KEY operator setup — manual action, documented in Section 1F

**Post-S8 hot fix (commit: abaf8db):** `heartbeat_check` made
service-class-aware via `_SCHEDULED_SERVICES` frozenset — eliminates
false-positive "degraded" entries on the Health page for the 11
cron-scheduled services. Continuous services keep the original
90 s gate. See `backend/tests/test_heartbeat_policy.py`.

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

- [ ] Phase C — Adaptive Risk Parameters: replace hardcoded 3% daily halt
  threshold with volatility-scaled threshold (2.5× daily_stddev from real
  trade history). Prevents false halts on volatile-but-profitable days.
  Build after Loop 2 trained + 100 real closed trades. Extend
  calibration_engine.py — infrastructure already exists.

- [ ] Phase 5B — Earnings Learning Loop: AI learning layer on top of
  rule-based earnings straddle system. Optimize edge score weights,
  entry/exit timing per ticker, earnings universe expansion via vol
  clustering. Build after 50+ earnings trades. Requires outcome labeling
  (~4-6 hours once data exists). Current system (backend_earnings/) is
  fully rule-based with no feedback loop.

---

## SECTION 10 — CURRENT SYSTEM STATUS

Last updated: April 19, 2026

**Consolidation Sprint:** S1-S9 complete. System operationally correct.
See Section 8 sprint table for per-session commits.

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
| Calendar Spread | ✅ Wired — OFF | strategy:calendar_spread:enabled |

### Railway API Keys
| Key | Status |
|---|---|
| FINNHUB_API_KEY | ✅ Added |
| ANTHROPIC_API_KEY | ✅ Added |
| NEWSAPI_KEY | ✅ Added |
| UNUSUAL_WHALES_API_KEY | ✅ Added (validity unconfirmed) |

---

## SECTION 11 — PROFIT MAXIMIZATION ROADMAP

Full specification: `trading-docs/08-planning/archive/profit-maximization-roadmap-v2.md`
Phases are sequenced — do not skip ahead. Each phase gates on the prior.

---

### Phase 0 — Remove Active ROI Suppressors
**Gate:** Complete before Phase A. Paper data will be cleaner.
**Expected lift: +8-13pp annual return**

- [ ] P0.1 — Fix commission model: $0.65 → $0.35 per leg (Tradier standard rate)
- [x] P0.2 — Entry floor at 9:35 AM ET (done in S13 T1-2)
- [ ] P0.3 — Fix signal_weak threshold: 0.10 → 0.05 (reduces no-trade false positives)
- [ ] P0.4 — IV/RV no-trade filter: skip when IV < realized vol (premium too thin)
- [x] P0.5 — Event-day size override: 40% on FOMC/CPI/NFP (built)
- [x] P0.6 — Partial exit at 25% profit (built in S4)

---

### Phase A — LightGBM Direction Model + Real HMM Regime
**Gate:** 30+ paper trading sessions with labeled outcomes
**Expected annual return: 18-26%**

- [x] A1 — Real accuracy measurement via outcome_correct (done in S15 T2-1)
- [ ] A2 — Historical data download: OptionsDX SPX 0DTE chains 2022-2026 (~$50/mo)
        Optional but adds +3-5pp. Enables GEX feature reconstruction in training.
- [ ] A3 — Train LightGBM direction model
        Replaces hardcoded probability lookup tables with real ML model.
        Features: VVIX z-score, GEX confidence, SPX momentum (5m/30m/1h/4h),
        VIX term ratio, breadth, IV rank, time-of-day, day-of-week, prior session return.
        Requires: 90+ labeled sessions. Target: ≥58% directional accuracy on holdout.
- [ ] A4 — Train real HMM regime classifier (parallel with A3)
        Replace VVIX z-score if/else with trained 6-state Gaussian HMM.
        Fit on SPX daily log-returns + VIX daily change 2010-2026.
        States: quiet_bullish, quiet_bearish, trending, volatile, event, crisis.
- [ ] A5 — Kelly-fractional sizing (after A3 deployed and calibrated)
        Replace fixed risk_pct with f* = (edge / odds) from LightGBM probability.
        Do NOT build before A3 — current tables are not well-calibrated.

---

### Phase B — Complete the Prediction Engine
**Gate:** Phase A validated (LightGBM running 30+ days)
**Expected annual return: 20-28%**

- [ ] B1 — Expand to 93 features
        Add: VWAP distance, morning range, gap fill probability, overnight futures,
        cross-asset signals (bonds/dollar/VIX futures), options microstructure
        (put/call ratio by strike, unusual flow score), GEX flip zone proximity,
        earnings proximity score.
- [ ] B2 — Dynamic spread width optimizer
        Width = f(IV rank, VIX, time-to-expiry). Higher IV → wider wings.
- [ ] B3 — Asymmetric iron condor wing optimizer
        Skew put/call wings based on GEX asymmetry ratio.
- [ ] B4 — Width-aware stop-loss (depends on B2)
        Stop-loss = f(spread width, IV at entry) not fixed 150%.

---

### Phase C — Execution Quality
**Gate:** Phase B validated
**Expected annual return: 22-30%**

- [ ] C1 — OCO bracket orders
        Submit take-profit and stop-loss as OCO on Tradier at entry.
        Reduces exit slippage 30-50%. Does NOT require walk-the-book.
        Use realized fill price from Tradier — not predicted price.
- [ ] C2 — Walk-the-book entry simulation
        Replace random.gauss() slippage noise with depth-aware model.
        Model: bid_ask_spread × f(size, time_of_day, IV).
- [ ] C3 — Predictive slippage model
        Gate: 200+ observations in trading_calibration_log (GLC-011).
        Train LightGBM regression on {VIX, time-of-day, contracts, OTM distance, IV rank}.
        Replaces STATIC_SLIPPAGE_BY_STRATEGY dict.

---

### Phase D — Learning Engine
**Gate:** After Phase C, runs alongside live trading. Compounds continuously.
**Expected annual return: 26-34%**

- [ ] D1 — Daily outcome loop (4:15 PM ET)
        Label predictions with realized SPX outcomes.
        Isotonic recalibration on probability outputs.
        Drift z-test: alert if 10-day accuracy drops >5pp.
- [ ] D2 — Weekly champion/challenger retrain (Sunday 6 PM ET)
        Retrain LightGBM on rolling 90-day labeled window.
        Compare challenger vs champion on 30-day holdout.
        Swap only if challenger wins by ≥1pp. Keep prior as emergency fallback.
- [ ] D3 — Regime × Strategy performance matrix
        Running P&L by strategy × regime. Auto-reduce allocation 25% if any
        strategy loses 3 consecutive sessions in a regime. Updates daily.
        New file: backend/strategy_performance_matrix.py
- [ ] D4 — Counterfactual Engine
        Post-session: simulate alternate entries (±15 min), alternate widths,
        and skipped trades (including halt days and no-trade days).
        Identifies systematic improvements without new risk.
        Feeds feature importance into weekly retrain (D2).
        Gate: 30+ closed sessions. Build: ~2 Cursor sessions.
- [ ] D5 — Intraday micro-calibration (every 2 hours)
        Check if morning prediction consistent with current GEX state.
        If regime shifted, emit advisory (human decides, not forced exit).
        Update signal_weak threshold dynamically from intraday realized vol.

---

### Phase E — Sizing Ramp + Multi-Instrument
**Gate:** milestone-gated, cannot be rushed.

- [ ] E1 — Phase 2 sizing advance
        Gate: 45 live days + Sharpe ≥1.2 rolling 45-day
        Core: 0.5% → 1.0% | Satellite: 0.25% → 0.5%
- [ ] E2 — Phase 3 sizing advance
        Gate: 90 live days + Sharpe ≥1.5 rolling 60-day
        Core: 1.0% → 1.5% | Satellite: 0.5% → 0.75%
- [ ] E3 — Multi-instrument expansion
        Gate: 120 live days + stable performance
        XSP (mini-SPX), NDX, RUT — all Section 1256 tax treatment.
- [ ] E4 — Daily 0DTE Tuesday/Thursday expansion
        Gate: 90 live days + historical validation on Tue/Thu liquidity.
        Validate bid/ask spreads and open interest on OptionsDX data first.

---

### Already Tracked in Section 9 (cross-reference)
- Phase C Adaptive Halt Threshold — after 100 real closed trades
- Phase 5B Earnings Learning Loop — after 50+ earnings trades

---
---

## SECTION 12 — BUILD-NOW QUEUE (Auto-Activation on Data Threshold)

**Philosophy:** Every item here is built immediately. Activation is gated in code on
a data threshold — no human action needed. Nothing waits on a human to remember.

Items are ordered by ROI impact. Mark `[x]` when built, note commit hash.

---

### 12A — True 20-Day Daily Realized Vol
**Priority: IMMEDIATE — unblocks P0.4 which is already built but using garbage data**
**Auto-activates when:** `daily_len >= 5` (warmth guard already in prediction_engine)

Problem: `polygon:spx:realized_vol_20d` is computed from 5-min intraday bars (5-8 samples).
Returns 1.05-1.29% instead of true ~15-20% annualized. Every downstream consumer
(IV/RV filter, LGBM iv_rv_ratio feature) reads garbage.

- [ ] In `backend/polygon_feed.py`, add `self.spx_daily_returns: List[float] = []`
- [ ] Add `self._spx_daily_date_written: Optional[str] = None`
- [ ] At EOD (19:00 UTC gate, same pattern as VIX daily history S6 T1-7):
      append today's session return from `polygon:spx:prior_day_return`,
      cap list at 20, persist last-date to Redis `polygon:spx:daily_returns:last_date`
- [ ] Compute `realized_vol = std(daily_returns) * sqrt(252) * 100` when len >= 5
- [ ] Write to `polygon:spx:realized_vol_20d` with 86400s TTL
- [ ] Add Redis persistence guard (same pattern as T1-7) to prevent double-append on restart
- [ ] Test: realized_vol from 20 daily returns is ~10-25% not ~1%

**Cursor sessions: 1 | Commit tag: fix(polygon): true 20-day daily realized vol**

---

### 12B — Butterfly Gate Instrumentation
**Priority: IMMEDIATE — needed before tuning any thresholds**
**Auto-activates:** immediately, counters always increment

- [ ] In `backend/strategy_selector.py`, add Redis counter for each butterfly gate:
      `redis.incr(f"butterfly:blocked:reason={reason}:date={today}")` with 7-day TTL
      Reasons: `regime_mismatch`, `time_gate`, `failed_today`, `low_concentration`,
      `drawdown_block`, `wall_unstable`, `allowed`
- [ ] In EOD job, log `butterfly_gate_stats` with all counters as structured log
- [ ] After 2 weeks: query counters to tune thresholds (feeds 12G)

**Cursor sessions: 0.5 | Commit tag: feat(instrumentation): butterfly gate counters**

---

### 12C — GEX Wall Stability (30-Minute Rolling Check)
**Priority: HIGH — directly caused today's losses (2026-04-20)**
**Auto-activates when:** `wall_history_len >= 4` (self-gated in code)

Today's failure: GEX wall moved 7115→7195 (80 points) while system opened 3 butterflies.
A rolling range check over 30 minutes would have blocked all 3 trades.

- [ ] In `backend/gex_engine.py`, after computing `nearest_wall`, append to Redis list:
      `gex:wall_history` → JSON `{"ts": time.time(), "wall": nearest_wall}`
      Prune entries older than 1800s (30 min). TTL 3600s on key.
- [ ] In `backend/strategy_selector.py` butterfly gate block, add:
      Read `gex:wall_history`, require `len >= 4` before applying check.
      Compute `wall_range_pct = (max(walls) - min(walls)) / spx_price`
      If `wall_range_pct > 0.005` (0.5% ≈ 35 SPX points): set `butterfly_forbidden = True`
      Log `butterfly_blocked_wall_unstable` with range_pct and wall min/max
- [ ] Use RANGE not stddev. Do NOT stack with a separate point-to-point check.
- [ ] Test: wall moved 40pts in 30 min → blocked; wall stable → allowed

**Cursor sessions: 1 | Commit tag: feat(butterfly): GEX wall stability 30-min rolling gate**

---

### 12D — D3 Regime × Strategy Performance Matrix
**Priority: HIGH — starts collecting from trade 1, influences sizing after 10+ trades per cell**
**Auto-activates:** immediately for collection; sizing adjustment after 10 trades per cell

- [ ] New file: `backend/strategy_performance_matrix.py`
- [ ] Daily EOD job (4:20 PM ET): query closed positions, group by (regime, strategy_type)
      Compute win_rate, avg_pnl, profit_factor, trade_count per cell
      Write to Redis `strategy_matrix:{regime}:{strategy}` with 90-day TTL
      Also persist to Supabase `strategy_regime_performance` table (migration needed)
- [ ] In `backend/strategy_selector.py`, after strategy selected:
      Read matrix cell for (current_regime, strategy_type)
      If trade_count >= 10 AND win_rate < 0.40: reduce sizing by 25%
      If trade_count >= 10 AND win_rate < 0.30: add strategy to butterfly_forbidden equivalent
      Log `strategy_matrix_sizing_applied` with win_rate and trade_count
- [ ] Schedule in `backend/main.py` at 4:20 PM ET daily (mon-fri)
- [ ] Test: cell with 12 trades win_rate=0.35 → 25% size reduction applied

**Cursor sessions: 1 | Commit tag: feat(learning): regime-strategy performance matrix D3**

---

### 12E — D4 Counterfactual Engine
**Priority: HIGH — collect from day 1, report activates at 30 sessions**
**Auto-activates reporting when:** `closed_sessions >= 30`

- [ ] New file: `backend/counterfactual_engine.py`
- [ ] Post-session job (4:25 PM ET): for each `no_trade_signal=True` prediction row:
      Fetch SPX price 30 min after signal (same as label_prediction_outcomes)
      Simulate what P&L would have been if trade had opened
      Write `counterfactual_pnl` to `trading_prediction_outputs` table
- [ ] Also simulate halt-day blocked cycles
- [ ] Weekly report: `counterfactual_summary` — top 3 missed opportunities
      Only emit report when `closed_sessions >= 30`. Collect data from day 1.
- [ ] Migration: `ALTER TABLE trading_prediction_outputs ADD COLUMN IF NOT EXISTS counterfactual_pnl NUMERIC(10,2)`
- [ ] Test: no_trade row gets counterfactual_pnl populated after job runs

**Cursor sessions: 2 | Commit tag: feat(learning): counterfactual engine D4**

---

### 12F — Phase C Adaptive Halt Threshold
**Priority: MEDIUM — scaffold now, activates at 100 closed trades**
**Auto-activates when:** `closed_trades >= 100`

Currently hardcoded: -3% daily halt. Should be 2.5 × daily_pnl_stddev from real history.
Prevents false halts on volatile-but-profitable days.

- [ ] In `backend/calibration_engine.py`, add `calibrate_halt_threshold()`:
      Query last 60 closed sessions, compute daily P&L stddev
      `halt_threshold = -2.5 * daily_pnl_stddev`
      Floor: never looser than -2% | Ceiling: never tighter than -5%
      Write to Redis `risk:halt_threshold_pct` with 86400s TTL
      Auto-gate: only writes when `closed_trades >= 100`
- [ ] In `backend/risk_engine.py` `check_daily_drawdown()`:
      Read `risk:halt_threshold_pct` from Redis, fallback to -0.03 if absent
      Log `halt_threshold_source=adaptive|default`
- [ ] Add to existing weekly calibration job (already runs Sunday 6 PM ET)
- [ ] Test: with 100 trades stddev=0.8% → threshold=-2.0% (floor applied)

**Cursor sessions: 1 | Commit tag: feat(risk): adaptive halt threshold Phase C**

---

### 12G — Butterfly Threshold Auto-Tuning
**Priority: MEDIUM — requires 12B instrumentation + 20 butterfly trades**
**Auto-activates when:** `closed_butterfly_trades >= 20`

Current thresholds (0.25 concentration, 0.75 drawdown, 0.003 wall distance, 0.40 gex_conf)
were shipped without empirical validation. Need calibration against real outcomes.

- [ ] In `backend/calibration_engine.py`, add `calibrate_butterfly_thresholds()`:
      Query closed butterfly trades, replay each through saved gate metric values
      Compute ROC curve per gate: blocked-correctly (trade lost) vs blocked-incorrectly (trade won)
      Find optimal threshold at max F1 per gate
      Write tuned values to Redis: `butterfly:threshold:concentration`,
      `butterfly:threshold:gex_conf`, `butterfly:threshold:wall_distance`
- [ ] In `backend/strategy_selector.py`, read thresholds from Redis with hardcoded fallbacks
      Log `butterfly_threshold_source=calibrated|default`
- [ ] Auto-gate: only calibrate when `closed_butterfly_trades >= 20`
- [ ] Add to weekly calibration job
- [ ] Test: 25 butterfly trades → calibration runs and writes Redis keys

**Cursor sessions: 1 | Commit tag: feat(calibration): butterfly threshold auto-tuning 12G**

---

### 12H — Phase A LightGBM Feature Engineering Scaffold
**Priority: MEDIUM — start collection now, training at 90 labeled sessions**
**Auto-activates training when:** `labeled_sessions >= 90`

- [ ] In `backend/prediction_engine.py`, persist additional features to `trading_prediction_outputs`:
      Add columns: `prior_session_return`, `vix_term_ratio`, `spx_momentum_4h`,
      `gex_flip_proximity`, `earnings_proximity_score`
      Migration needed for each new column (IF NOT EXISTS)
- [ ] New script `backend/scripts/download_historical_data.py`:
      SPX daily OHLCV 2010-2026 via Polygon historical API
      VIX daily 2010-2026 via FRED API (free)
      Write to `backend/data/spx_daily.parquet` and `backend/data/vix_daily.parquet`
- [ ] New script `backend/scripts/train_direction_model.py`:
      Loads parquet files + labeled predictions from Supabase
      47-feature LightGBM with walk-forward validation (no data leakage)
      Auto-gates: only trains when `labeled_sessions >= 90`, logs `insufficient_data` otherwise
      Output: `backend/models/lgbm_direction_v1.pkl`
- [ ] Test: scaffold runs, returns `insufficient_data` when < 90 sessions

**Cursor sessions: 2 | Commit tag: feat(ml): Phase A LightGBM feature engineering scaffold**

---

### 12I — OCO Bracket Orders (C1)
**Priority: MEDIUM — reduces exit slippage 30-50%**
**Auto-activates when:** `TRADIER_SANDBOX=false` (real capital only)

- [ ] In `backend/execution_engine.py`, after real position opened:
      If `TRADIER_SANDBOX=false`: submit OCO bracket via Tradier bracket order API
      Take-profit leg: limit at `entry_credit * 0.40` profit
      Stop-loss leg: stop at `entry_credit * 1.50` loss
- [ ] In `backend/position_monitor.py`: if `oco_order_id` on position,
      check OCO fill status from Tradier instead of computing P&L manually
- [ ] Migration: `ALTER TABLE trading_positions ADD COLUMN IF NOT EXISTS oco_order_id TEXT`
- [ ] Test: in sandbox mode → no OCO submitted; real mode → OCO submitted

**Cursor sessions: 1 | Commit tag: feat(execution): OCO bracket orders C1**

---

### 12J — Phase 5B Earnings Learning Loop Scaffold
**Priority: LOW-MEDIUM — scaffold now, activates at 50 earnings trades**
**Auto-activates when:** `closed_earnings_trades >= 50`

- [ ] In `backend_earnings/edge_calculator.py`, add `label_earnings_outcome()`:
      After position closes: label correct_direction, pnl_vs_expected, iv_crush_captured
      Write to Supabase `earnings_trade_outcomes` table (migration needed)
- [ ] Add `train_earnings_model()` scaffold in same file:
      Features: days_to_earnings, iv_rank, sector, historical_move, current_iv_rv
      Output: per-ticker edge score weights replacing hardcoded EARNINGS_HISTORY
      Auto-gate: only trains when `closed_earnings_trades >= 50`
- [ ] Test: labeling fires on close; training returns `insufficient_data` below 50

**Cursor sessions: 2 | Commit tag: feat(earnings): learning loop scaffold Phase 5B**

---

### 12K — Loop 2 Meta-Label Model Scaffold
**Priority: LOW-MEDIUM — scaffold now, activates at 100 closed trades**
**Auto-activates when:** `closed_trades >= 100`

- [ ] In `backend/model_retraining.py`, add `train_meta_label_model()`:
      Features: iv_rank, VIX, gex_confidence, dist_pct, strategy_type,
      spread_width, entry_regime, ai_confidence, signal_mult, time_of_day
      Target: `outcome_correct` (already labeled by label_prediction_outcomes)
      Output: `backend/models/meta_label_v1.pkl`
      Auto-gate: only trains when `closed_trades >= 100`
- [ ] In `backend/execution_engine.py`, if meta-label model file exists:
      Score trade before opening.
      score < 0.55 → skip (0 contracts)
      0.55-0.65 → normal sizing
      >= 0.75 → allow 1.5× sizing (capped by existing risk gates)
- [ ] Test: model absent → normal sizing; model present score=0.45 → trade skipped

**Cursor sessions: 2 | Commit tag: feat(ml): Loop 2 meta-label scaffold 12K**

---

### 12L — D1 Daily Outcome Loop Drift Alert
**Priority: LOW — extends existing label_prediction_outcomes**
**Auto-activates:** immediately

- [ ] In `backend/model_retraining.py`, after `label_prediction_outcomes()` runs:
      Compute rolling 10-day directional accuracy from `outcome_correct` column
      If accuracy drops > 5pp from 30-day baseline: write `model_drift_alert=1` to Redis (TTL 86400)
      Log `drift_alert_fired` with current_accuracy and baseline_accuracy
- [ ] In `backend/main.py` EOD job: if `model_drift_alert` key exists in Redis:
      Send alert via `alerting.py` with drift details
- [ ] Test: accuracy injected below threshold → drift alert fires and alert sent

**Cursor sessions: 0.5 | Commit tag: feat(learning): D1 daily outcome loop drift alert**

---

### 12M — D2 Weekly Champion/Challenger Retrain Scaffold
**Priority: LOW — scaffold now, activates when LightGBM model exists (12H)**
**Auto-activates when:** `backend/models/lgbm_direction_v1.pkl` exists

- [ ] New job in `backend/main.py` Sunday 6 PM ET: `run_weekly_retrain_job()`
- [ ] In `backend/model_retraining.py`, add `run_champion_challenger()`:
      Load champion from `backend/models/lgbm_direction_v1.pkl`
      Retrain challenger on rolling 90-day labeled window
      Compare on 30-day holdout: swap if challenger wins by >= 1pp
      Keep prior as `lgbm_direction_v0.pkl` emergency fallback
      Log `model_swapped` or `model_retained` with accuracy delta
      Auto-gate: skip gracefully if no model file exists
- [ ] Test: challenger wins by 2pp → swap; wins by 0.5pp → no swap; no model → skip

**Cursor sessions: 1 | Commit tag: feat(learning): D2 champion-challenger retrain scaffold**

---

### 12N — Sizing Phase Auto-Advance (Phase E1/E2)
**Priority: LOW — no human action needed once built**
**Auto-activates: E1 at 45 live days + Sharpe ≥1.2 | E2 at 90 live days + Sharpe ≥1.5**

- [ ] In `backend/calibration_engine.py`, add `evaluate_sizing_phase()`:
      Query trading_sessions: count live days, compute rolling Sharpe
      If days >= 45 AND sharpe_45d >= 1.2 AND current_phase == 1:
          Write `capital:sizing_phase=2` to Redis, log `sizing_phase_advanced phase=2`
      If days >= 90 AND sharpe_60d >= 1.5 AND current_phase == 2:
          Write `capital:sizing_phase=3` to Redis, log `sizing_phase_advanced phase=3`
- [ ] In `backend/risk_engine.py`, read `capital:sizing_phase` from Redis, fallback to 1
      Log `sizing_phase_source=redis|default`
- [ ] Add to weekly calibration job (Sunday 6 PM ET)
- [ ] Test: 46 days Sharpe=1.3 → phase advances to 2; below threshold → stays at 1

**Cursor sessions: 0.5 | Commit tag: feat(sizing): auto-advance sizing phase E1/E2**

---

### SECTION 12 BUILD ORDER

| # | Item | Sessions | Dependency | Do When |
|---|---|---|---|---|
| 12A | True 20-day daily RV | 1 | None | Now |
| 12B | Butterfly instrumentation | 0.5 | None | Now |
| 12C | GEX wall stability | 1 | None | Now |
| 12D | Regime × strategy matrix | 1 | None | Now |
| 12E | Counterfactual engine | 2 | None (collect now) | This week |
| 12F | Adaptive halt threshold | 1 | None (scaffold now) | This week |
| 12G | Butterfly threshold tuning | 1 | 12B + 20 trades | This week |
| 12H | Phase A LightGBM scaffold | 2 | None (scaffold now) | This week |
| 12I | OCO bracket orders | 1 | Real capital gate | Before live trading |
| 12J | Earnings learning scaffold | 2 | None (scaffold now) | This month |
| 12K | Loop 2 meta-label scaffold | 2 | None (scaffold now) | This month |
| 12L | D1 drift alert | 0.5 | None | This week |
| 12M | D2 retrain scaffold | 1 | 12H model | This month |
| 12N | Sizing phase auto-advance | 0.5 | None | This week |

**Total: ~17 Cursor sessions. All infrastructure built now. Activation gates in code.**

---

*Task Register v1.0 — April 2026 — tesfayekb*
