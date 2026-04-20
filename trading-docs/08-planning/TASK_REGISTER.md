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

**2026-04-20 infra audit (commit: 3cd1c8c):** two unrelated
production-hygiene fixes bundled together — no ROI impact.

- **Agent module paths.** e417113 fixed the Railway-cwd `sys.path`
  bug for 5 earnings jobs + the `economic_calendar` job. The
  2026-04-22 audit of `backend/main.py` found 6 agent jobs still
  using the raw-relative pattern that caused the original bug:
  `_run_macro_agent_job`, `_run_synthesis_agent_job`,
  `_run_surprise_detector_job`, `_run_flow_agent_job`,
  `_run_sentiment_agent_job`, `_run_feedback_agent_job`. All six
  now use the canonical
  `os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend_agents"))`
  pattern with the `if _AGENTS_PATH not in sys.path:` guard.
  Pinned by `backend/tests/test_agent_paths.py` (3 AST/regex
  guards on `main.py`).
- **Prediction outcome columns re-apply.** Added migration
  `20260422_ensure_prediction_outcome_columns.sql` — fully
  idempotent (`IF NOT EXISTS` on every statement). Re-asserts
  `outcome_direction`, `outcome_correct`, `spx_return_30min`, and
  the `idx_prediction_outcome` index originally added by
  `20260417130000_add_prediction_outcome_labels.sql`. Safe to run
  in any environment. Deliberately skipped `outcome_labeled_at`
  and `spx_price_at_outcome` from an earlier draft — ripgrep
  confirmed zero code consumers, so adding them would be dead
  schema (documented inline in the migration).

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

**STATUS: ALL 14 ITEMS COMPLETE — 2026-04-20**

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

- [x] In `backend/strategy_selector.py`, add Redis counter for each butterfly gate:
      `redis.incr(f"butterfly:blocked:{reason}:{today}")` with 7-day TTL
      Reasons: `regime_mismatch`, `time_gate`, `failed_today`, `low_concentration`,
      `drawdown_block` (placeholder, 0 until execution_engine writer ships),
      `wall_unstable` (placeholder, 0 until 12C ships), `allowed`
- [x] In EOD job, log `butterfly_gate_daily_stats` with all counters as structured log
- [ ] After 2 weeks: query counters to tune thresholds (feeds 12G)

**Cursor sessions: 0.5 | Commit tag: feat(instrumentation): butterfly gate counters**
**Status: Built 2026-04-20 | Commit: `7983d6c` — counters live, 2-week analysis window opens**

---

### 12C — GEX Wall Stability (30-Minute Rolling Check)
**Priority: HIGH — directly caused today's losses (2026-04-20)**
**Auto-activates when:** `wall_history_len >= 4` (self-gated in code)

Today's failure: GEX wall moved 7115→7195 (80 points) while system opened 3 butterflies.
A rolling range check over 30 minutes would have blocked all 3 trades.

- [x] In `backend/gex_engine.py`, after computing `nearest_wall`, append to Redis list:
      `gex:wall_history` → JSON `{"ts": time.time(), "wall": nearest_wall}`
      Prune entries older than 1800s (30 min). TTL 3600s on key.
      (Implemented as `GexEngine._append_wall_history()` helper — testable
      in isolation, guards against None/0/non-positive wall values.)
- [x] In `backend/strategy_selector.py` butterfly gate block, add:
      Read `gex:wall_history`, require `len >= 4` before applying check.
      Compute `wall_range_pct = (max(walls) - min(walls)) / spx_price`
      If `wall_range_pct > 0.005` (0.5% ≈ 35 SPX points): set `butterfly_forbidden = True`
      Log `butterfly_blocked_wall_unstable` with range_pct and wall min/max
      (Integrates with 12B counter via `butterfly_block_reason = "wall_unstable"` —
      no separate `redis.incr` to avoid double-counting.)
- [x] Use RANGE not stddev. Do NOT stack with a separate point-to-point check.
- [x] Test: wall moved 40pts in 30 min → blocked; wall stable → allowed
      (8 tests in `backend/tests/test_gex_wall_stability.py` covering
      writer pruning/TTL, gate blocking/allowing, self-gating below 4
      samples, fail-open on Redis error, and 12B counter integration.)

**Cursor sessions: 1 | Commit tag: feat(butterfly): GEX wall stability 30-min rolling gate**
**Status: SHIPPED `acccfd7` — 2026-04-20 | 8 new tests, suite 598 passed.**

---

### 12D — D3 Regime × Strategy Performance Matrix
**Priority: HIGH — starts collecting from trade 1, influences sizing after 10+ trades per cell**
**Auto-activates:** immediately for collection; sizing adjustment after 10 trades per cell

- [x] New file: `backend/strategy_performance_matrix.py`
      (`update_performance_matrix()`, `get_matrix_sizing_multiplier()`,
      `run_matrix_update()` — single-pass aggregation over the last
      90 days of closed virtual positions.)
- [x] Daily EOD job (4:20 PM ET): query closed positions, group by (regime, strategy_type)
      Compute win_rate, avg_pnl, profit_factor, trade_count per cell
      Write to Redis `strategy_matrix:{regime}:{strategy}` with 90-day TTL
      (`entry_regime` + `net_pnl` columns confirmed present in
      `trading_positions` migration `20260416172751` — no new Supabase
      migration required. Supabase-side `strategy_regime_performance`
      persistence deferred; Redis with 90-day TTL already covers the
      sizing gate and EOD observability.)
- [x] In `backend/strategy_selector.py`, after strategy selected:
      Read matrix cell for (current_regime, strategy_type)
      If trade_count >= 10 AND win_rate < 0.40: reduce sizing by 25%
      Log `strategy_matrix_contracts_adjusted` with win_rate and trade_count
      (The optional `< 0.30 -> forbidden` escalation from the draft
      was deliberately dropped: this task's invariant is "MUST NOT
      reduce ROI", and a hard block is strictly riskier than the 25%
      cut. Escalation can land once 20+ trades/cell of instrumentation
      data justifies the threshold — same pattern as 12G will use.)
- [x] Schedule in `backend/main.py` at 4:20 PM ET daily (mon-fri)
      (`scheduler.add_job` with `hour=16, minute=20`. Scheduler TZ is
      `America/New_York` per line 57, not UTC — the spec's `hour=20`
      would have fired at the wrong wall-clock time post-DST.)
- [x] Test: cell with 12 trades win_rate=0.35 → 25% size reduction applied
      (8 tests in `backend/tests/test_strategy_performance_matrix.py`
      covering cold start, below-threshold trade count, active
      down-size, passing win_rate, Redis-error fail-open, full
      aggregation of 4 cells from 10 fixture positions, and the
      contracts-floor arithmetic used in `select()`.)

**Cursor sessions: 1 | Commit tag: feat(learning): regime-strategy performance matrix D3**
**Status: SHIPPED `5a4fa2a` — 2026-04-20 | 8 new tests, suite 606 passed.**

---

### 12E — D4 Counterfactual Engine
**Priority: HIGH — collect from day 1, report activates at 30 sessions**
**Auto-activates reporting when:** `closed_sessions >= 30`

- [x] New file: `backend/counterfactual_engine.py`
      (`_fetch_spx_price_after_signal`, `_simulate_pnl`,
      `label_counterfactual_outcomes`, `generate_weekly_summary`,
      `run_counterfactual_job`. Pure observability — never reads
      into a trading-decision path.)
- [x] Post-session job (4:25 PM ET): for each `no_trade_signal=True` prediction row:
      Fetch SPX price 30 min after signal (same as label_prediction_outcomes)
      Simulate what P&L would have been if trade had opened
      Write `counterfactual_pnl` to `trading_prediction_outputs` table
      (SPX fetch mirrors `model_retraining.label_prediction_outcomes`
      exactly — Polygon I:SPX 1-min aggregate at t+30, same API key
      path, same failure-as-skip semantics. Scheduler TZ is
      `America/New_York` so `hour=16, minute=25` is wall-clock 4:25
      PM ET across DST; the spec's `hour=20` would have fired at
      8 PM ET.)
- [~] Also simulate halt-day blocked cycles
      (Deferred: halt-day cycles don't produce
      `trading_prediction_outputs` rows — they short-circuit earlier.
      Needs a separate data source to simulate cleanly; filed as
      12E follow-up rather than fabricating halt-day rows here.)
- [x] Weekly report: `counterfactual_summary` — top 3 missed opportunities
      Only emit report when `closed_sessions >= 30`. Collect data from day 1.
      (Sundays at 6:30 PM ET — self-gates on
      `closed_sessions >= 30` inside `generate_weekly_summary`,
      returning None and logging
      `counterfactual_summary_skipped_insufficient_data` below that.)
- [x] Migration: `ALTER TABLE trading_prediction_outputs ADD COLUMN IF NOT EXISTS counterfactual_pnl NUMERIC(10,2)`
      (`supabase/migrations/20260421_add_counterfactual_pnl.sql` —
      adds `counterfactual_pnl`, `counterfactual_strategy`,
      `counterfactual_simulated_at` + partial index on
      `(predicted_at DESC) WHERE no_trade_signal=true AND
      counterfactual_pnl IS NULL` so the daily labeler query stays
      cheap as the table grows. Operator deploys the migration via
      the normal Supabase pipeline.)
- [x] Test: no_trade row gets counterfactual_pnl populated after job runs
      (9 tests in `backend/tests/test_counterfactual_engine.py`:
      3 simulate-math cases, 2 skip paths (missing entry / missing
      exit), 1 write-payload shape check, 2 weekly-summary cases
      (below/above the 30-session gate), and 1 fail-open test
      covering a Supabase outage.)

Spec deviations flagged before implementation: Polygon fetch vs the
spec's next-row Supabase proxy (went with the INSTRUCTION "mirror
label_prediction_outcomes exactly" over the contradictory example
code); `strategy_hint` dropped from the SELECT because the column
does not exist on `trading_prediction_outputs` — simulation defaults
to `iron_condor` and persists the choice to
`counterfactual_strategy` for future re-simulation.

**Cursor sessions: 2 | Commit tag: feat(learning): counterfactual engine D4**
**Status: SHIPPED `2400e98` — 2026-04-20 | 9 new tests, suite 615 passed.**

---

### 12F — Phase C Adaptive Halt Threshold
**Priority: MEDIUM — scaffold now, activates at 100 closed trades**
**Auto-activates when:** `closed_trades >= 100`

Currently hardcoded: -3% daily halt. Should be 2.5 × daily_pnl_stddev from real history.
Prevents false halts on volatile-but-profitable days.

- [x] In `backend/calibration_engine.py`, add `calibrate_halt_threshold()`:
      Queries last 60 non-null `virtual_pnl` sessions (90-day window),
      normalises each by `capital:live_equity` from Redis (falls back to
      $100k), computes population stddev, `halt_threshold = -2.5 * stddev`.
      Floor -0.02 / ceiling -0.05 clamp. Writes Redis
      `risk:halt_threshold_pct` with 8-day TTL (survives a weekend).
      Auto-gates on `closed_trades >= 100` AND `nonzero_sessions >= 20`.
- [x] In `backend/risk_engine.py` `check_daily_drawdown()`:
      Added optional `redis_client=None` param. Reads
      `risk:halt_threshold_pct`, defensively clamps to [-0.05, -0.02]
      before use, falls back to -0.03 on absent key / parse error /
      Redis error. Warning band upper bound also uses the adaptive
      threshold so the "approaching halt" relationship stays intact.
      Logs `halt_threshold_applied` with `source=adaptive|default`.
- [x] `backend/trading_cycle.py` now passes `redis_client` through to
      `check_daily_drawdown` (sourced from the prediction engine).
- [x] Added to `run_weekly_calibration_job` in `backend/main.py` —
      runs alongside existing slippage/CV_stress/touch calibration.
- [x] Tests (`backend/tests/test_adaptive_halt_threshold.py`): 10 cases
      covering <100 trades gate, <20 sessions gate, happy path
      (stddev=0.01 → -0.025), floor clamp (stddev=0.002 → -0.02),
      ceiling clamp (stddev=0.03 → -0.05), adaptive read, default
      fallback, fail-open on Redis error, halt fires at adaptive
      threshold, halt does not fire below threshold.

**Cursor sessions: 1 | Commit tag: feat(risk): adaptive halt threshold Phase C**
**Status: SHIPPED `6271d5b` — 2026-04-20 | 10 new tests, suite 625 passed.**

---

### 12G — Butterfly Threshold Auto-Tuning
**Priority: MEDIUM — requires 12B instrumentation + 20 butterfly trades**
**Auto-activates when:** `closed_butterfly_trades >= 20`

Current thresholds (0.25 concentration, 0.75 drawdown, 0.003 wall distance, 0.40 gex_conf)
were shipped without empirical validation. Need calibration against real outcomes.

- [x] In `backend/calibration_engine.py`, add `calibrate_butterfly_thresholds()`:
      Queries last 90 days of closed butterfly trades, parses per-trade
      gate metrics (`gex_conf`, `dist_pct`, `wall_concentration`) out of
      `decision_context`, and runs a candidate-grid search per threshold.
      Objective: maximise dollar P&L improvement vs. blocking nothing
      (equivalent to `-sum(net_pnl)` over the blocked subset, i.e.
      counts correctly-blocked losses against incorrectly-blocked wins).
      Writes tuned values to `butterfly:threshold:{gex_conf,
      wall_distance, concentration}` with 8-day TTL (survives a weekend).
      Partial data is OK — any threshold whose metric is missing in
      `decision_context` is simply left at the default.
- [x] **Writer extension (critical fix):** added `_capture_butterfly_metrics`
      on `StrategySelector` to stash `gex_conf`, `dist_pct`, and
      `wall_concentration` on the instance once per stage-1 invocation,
      then spread those into `signal["decision_context"]` in `select()`
      when `strategy_type == "iron_butterfly"`. Without this the
      calibrator would have no per-trade metric history to learn from
      — 12G would have shipped permanently dormant. Pre-existing
      butterfly rows lack the new keys and are skipped by the parser,
      matching the 20-trade gate exactly.
- [x] In `backend/strategy_selector.py`, added `_read_butterfly_thresholds`
      helper called once at the top of `_stage1_regime_gate`. Reads
      `butterfly:threshold:*` keys with per-key defensive clamps
      (gex_conf ∈ [0.1, 0.9], wall_distance ∈ [0.0005, 0.01],
      concentration ∈ [0.05, 0.6]). Missing key / parse error /
      out-of-band value falls back to the hardcoded default for that
      single threshold — a partial calibration never regresses other
      thresholds. The three gates (concentration < min,
      gex_conf >= min, dist_to_wall < max) now consume the local
      `_BFLY_*` variables. Emits a `butterfly_thresholds_applied`
      debug log with `source=calibrated|default`.
- [x] Auto-gates on `closed_butterfly_trades >= 20` AND
      `parsed_context_rows >= 10` — either gate missed → Redis
      untouched, defaults stay in force.
- [x] Added to `run_weekly_calibration_job` in `backend/main.py`, right
      after 12F's adaptive halt threshold calibration.
- [x] Tests (`backend/tests/test_butterfly_threshold_calibration.py`):
      12 cases covering <20 trades gate, <10 parsed context rows gate,
      `_find_best_threshold` direction=above (gex_conf split), direction=below
      (dist_pct split), Redis write/TTL verification, Supabase fail-open,
      selector reads calibrated gex_conf, fallback to default when key
      absent, fail-open on Redis error, defensive out-of-band rejection,
      `_capture_butterfly_metrics` populates stash, capture fail-open.
- [x] Companion change: `test_consolidation_s6.py::test_strategy_selector_
      pin_still_uses_04_threshold` updated to grep for both
      `gex_conf_min = 0.4` (default) AND `gex_conf >= _BFLY_GEX_CONF_MIN`
      (variable consumption) — the old literal-string regression guard
      would have false-positived after the refactor.

**Cursor sessions: 1 | Commit tag: feat(calibration): butterfly threshold auto-tuning 12G**
**Status: SHIPPED `8cb2fa5` — 2026-04-20 | 12 new tests, suite 637 passed.**

---

### 12H — Phase A LightGBM Feature Engineering Scaffold ✅ COMPLETE (2026-04-20, `8bc3c85`)
**Priority: MEDIUM — start collection now, training at 90 labeled sessions**
**Auto-activates training when:** `labeled_sessions >= 90`

- [x] In `backend/prediction_engine.py`, persist additional features to `trading_prediction_outputs`:
      Added columns: `prior_session_return`, `vix_term_ratio`, `spx_momentum_4h`,
      `gex_flip_proximity`, `earnings_proximity_score`
      Migration `supabase/migrations/20260422_add_prediction_features.sql` (IF NOT EXISTS, idempotent)
      Feature logic extracted to `_compute_phase_a_features()` for independent unit testing.
      Fail-open convention: three numeric features default to 0.0 (valid warmup value),
      two ratio features return NULL when inputs missing (LightGBM handles NULL natively;
      fabricated 1.0/0 would teach a phantom signal during feed gaps).
      Incidental fix: corrected `vix` field in output dict (was always collapsing to 18.0
      fallback because the prior call passed a pre-fetched value through the inline
      `_safe_float(key, default)` helper that expects a Redis key, not a value).
- [x] New script `backend/scripts/download_historical_data.py`:
      **Already existed** with a superset of the spec: SPX 5-min bars, SPX daily
      (Polygon + CBOE + yfinance), VIX/VVIX/VIX9D daily (CBOE free CSV) →
      `backend/data/historical/*.parquet` + `download_manifest.json`. Per instruction
      not to overwrite existing functionality, left intact.
- [x] `backend/scripts/train_direction_model.py` — added 90-session auto-gate:
      `count_labeled_sessions()` queries `trading_prediction_outputs` for distinct
      session_ids with `outcome_correct IS NOT NULL`. Fails CLOSED (returns 0) on
      Supabase error — refusing to train is safer than shipping a random-weight model.
      `check_labeled_sessions_gate()` wraps this with the `>= 90` threshold.
      `main()` calls the gate first and exits(0) cleanly on `insufficient_data`.
      Exit code 0 (not non-zero) so a scheduled job doesn't page on-call during
      the warming window.
- [x] Tests (+9 new, 650 total passing, 0 failures, 0 regressions):
      `test_prediction_engine.py`: 3 new covering feature contract, fail-open, and
      div-by-zero guard on `spx_price=0`.
      `test_phase_a_feature_scaffold.py`: 6 new — script existence, importability,
      gate at 50 sessions, distinct-session counting (not raw rows), fail-closed
      on Supabase outage, and 90-session boundary pinning.

**FIX A / FIX B bundled with this task** (shipped in separate commit `4970095`
on 2026-04-20, one commit earlier than the 12H commit):
- FIX A — `src/hooks/trading/useActivationStatus.ts`: `feedback:counterfactual:enabled`
  flipped to `builtStatus: 'live'` with updated description now that 12E
  (counterfactual engine) is actually running in production.
- FIX B — `trading_system_health` upserts wired into both EOD batch jobs:
  `run_counterfactual_job()` and `run_matrix_update()`. Uses `status='idle'` on
  success (batch jobs are not heartbeat services) with per-run stats in the
  `details` JSONB column, and `status='error'` with `last_error_message` on
  exception. Health writes wrapped in their own try/except so observability
  failures never mask the real job result. Required companion migration
  `20260421_health_service_name_eod_jobs.sql` that expands the
  `trading_system_health_service_name_check` CHECK constraint to allow
  `counterfactual_engine` and `strategy_matrix` — without it Postgres would
  silently reject every upsert. `HealthPage.tsx` `EXPECTED_SERVICES` now
  includes both services.
  Tests: 4 new (idle-on-success + error-on-exception for each job), asserting
  exact service name, status, and `details` payload shape.

**Pre-deploy actions**:
- Apply `supabase/migrations/20260422_add_prediction_features.sql` to production
  (idempotent via IF NOT EXISTS, safe any order).
- Apply `supabase/migrations/20260421_health_service_name_eod_jobs.sql` to production
  if FIX B is being deployed — without it the EOD health writes are rejected
  by the CHECK constraint.

**Cursor sessions: 2 | Commit tag: feat(ml): Phase A feature scaffold (12H)**

---

### 12I — OCO Bracket Orders (C1)
**Priority: MEDIUM — reduces exit slippage 30-50%**
**Status: SCAFFOLD COMPLETE — SHIPPED `d1eab32` (2026-04-20)**
**Auto-activates when:** `TRADIER_SANDBOX=false` AND `OCO_BRACKET_ENABLED=true`

- [x] In `backend/execution_engine.py`, after real position opened:
      `_submit_oco_bracket()` helper posts to
      `/v1/accounts/{id}/orders` with `class=bracket`, gated on
      `(not TRADIER_SANDBOX) and OCO_BRACKET_ENABLED`. Outer try/except
      guarantees OCO failure can never fail a position open.
      Take-profit leg: limit at `entry_credit * 0.40` profit.
      Stop-loss leg: stop at `entry_credit * 1.50` loss.
      (`d1eab32`)
- [x] In `backend/position_monitor.py`: TODO 12I comment added above
      the stop-loss branch noting a future OCO fill-status check via
      Tradier GET. Current P&L polling is safe — first exit wins,
      second close attempt is a no-op because `close_virtual_position`
      gates on `status='open'`. (`d1eab32`)
- [x] Migration: `supabase/migrations/20260422_add_oco_order_id.sql`
      adds `trading_positions.oco_order_id TEXT` idempotently via
      `IF NOT EXISTS`. (`d1eab32`)
- [x] Test: 10 new tests in `backend/tests/test_oco_bracket.py`
      covering dual-guard, fail-open, missing credentials, payload
      shape, and persistence. pytest: 660 passed, 1 skipped, 1 xfailed
      (was 650, +10 for 12I). (`d1eab32`)

**SHIPPED DIVERGENCE (safer than spec):** the spec called for activation
via `TRADIER_SANDBOX=false` alone. Shipped implementation adds a
deliberate second switch `OCO_BRACKET_ENABLED` (default `False`) because
the scaffold has four **MUST-FIX** items documented in the docstring of
`_submit_oco_bracket` that would produce rejected orders or wrong-sided
closes if activated as-is:

1. Hardcoded `side="buy_to_close"` is wrong for debit strategies
   (long_*, debit_*_spread, long_straddle, calendar_spread).
2. TP/SL math (`entry_credit * 0.60` / `entry_credit * 2.50`) is
   inverted for debit strategies.
3. `class: bracket` with `symbol: SPX` cannot close multi-leg spreads;
   Tradier requires `class: multileg` with per-leg OCC option symbols.
4. Sandbox round-trip verification (submit -> fill -> cancel) must
   precede any production enable.

The dual-flag guard preserves the ROI-neutral claim: today's production
state (real mode with `OCO_BRACKET_ENABLED=false`, the default) is a
no-op, and flipping a single env var can never accidentally submit
broken orders. Base URL also routes to `sandbox.tradier.com` when
`TRADIER_SANDBOX=true` so MUST-FIX #4 verification can be staged
cleanly with both flags on against the sandbox account first.

**Cursor sessions: 1 | Commit tag: feat(execution): OCO bracket orders C1**

---

### 12J — Phase 5B Earnings Learning Loop Scaffold
**Priority: LOW-MEDIUM — scaffold now, activates at 50 earnings trades**
**Status: SCAFFOLD COMPLETE — SHIPPED `390f478` (2026-04-20)**
**Auto-activates when:** `closed_earnings_trades >= 50`

- [x] In `backend_earnings/edge_calculator.py`, added
      `label_earnings_outcome()`: fires from trade #1 on every close
      with no warmup gate. Writes correct_direction,
      pnl_vs_expected (= net_pnl / total_debit), iv_crush_captured,
      expected/actual move pct, and net_pnl to the new
      `earnings_trade_outcomes` table. Fail-open — any labeling
      failure is swallowed and never affects the parent close path.
      Wired into `earnings_monitor.py` right after a successful
      `close_earnings_position`, using the pre-close `pos` row
      plus freshly computed `net_pnl` and `exit_at`. (`390f478`)
- [x] Added `train_earnings_model()` scaffold in the same file.
      Auto-gates on `MIN_EARNINGS_OUTCOMES_FOR_TRAINING = 50`
      (below that: `trained=False`, no Redis write). Above: builds
      per-ticker stats (win_rate, avg_pnl, sample_count, edge_score
      = win_rate * 0.6 + normalized avg_pnl * 0.4), excludes any
      ticker with fewer than `MIN_PER_TICKER_SAMPLES = 3` trades,
      and writes the dict to Redis key `earnings:ticker_weights`
      with an 8-day TTL. Wired into `run_weekly_calibration_job`
      in `backend/main.py` (Sunday 6 PM ET) via the same sys.path
      insert pattern as the earnings scan/entry/monitor jobs.
      Fail-open — a training failure leaves the previous weights
      (or the hardcoded `EARNINGS_HISTORY`) in place. (`390f478`)
- [x] Migration `supabase/migrations/20260422_earnings_trade_outcomes.sql`:
      new table + service-role RLS + ticker index. Idempotent.
      (`390f478`)
- [x] Tests: `backend/tests/test_earnings_learning.py` with 8 new
      tests covering labeling field shape, win/loss direction,
      labeling fail-open, training gate at 50, training above 50,
      per-ticker sample floor at 3, and training fail-open.
      pytest: 668 passed, 1 skipped, 1 xfailed (was 660, +8 for 12J).
      (`390f478`)

**SHIPPED DIVERGENCES from spec** (required for code to execute
against the live schema; all documented in the migration and in the
docstrings of the new functions):

1. **Migration FK correction.** `position_id REFERENCES
   public.earnings_positions(id) ON DELETE SET NULL`, not
   `trading_positions(id)`. Earnings positions live in
   `earnings_positions` (see `20260426_earnings_system.sql`); a FK
   to `trading_positions` would reject every insert because the
   UUIDs come from a different table.

2. **Field mapping.** Spec used SPX-side names on the input dict
   (`instrument`, `entry_credit`, `expected_move_pct`).
   Implementation reads the actual `earnings_positions` columns
   (`ticker`, `total_debit`, `implied_move_pct`) while still
   emitting the outcome-table column names spelled out in the
   migration, so analytics downstream stays consistent.

3. **Monitor wiring.** Spec mentioned "called by `earnings_monitor`
   when a position closes" but did not include the diff.
   `close_earnings_position` returns `bool` (not the closed row),
   so the label input dict is built at the call site in
   `earnings_monitor.py` from the pre-close `pos` plus the freshly
   computed `net_pnl = exit_value - total_debit` and the current
   UTC timestamp as `exit_at`. Wrapped in an outer try/except so
   any labeling failure is invisible to the monitor summary.

**ROI impact: zero today.** Labeling is pure observability, training
is dormant below 50 earnings trades, and even above threshold the
learned weights are written to a fresh Redis key that no consumer
reads yet — `compute_edge_score()` still uses the hardcoded
`EARNINGS_HISTORY` dict until a follow-up change wires it to prefer
the learned weights.

**Cursor sessions: 2 | Commit tag: feat(earnings): learning loop scaffold Phase 5B**

---

### 12K — Loop 2 Meta-Label Model Scaffold ✅ COMPLETE (2026-04-20, `bf41175`)
**Priority: LOW-MEDIUM — scaffold now, activates at 100 closed trades**
**Auto-activates when:** `closed_trades >= 100`

- [x] In `backend/model_retraining.py`, add `train_meta_label_model()`:
      Features: iv_rank, VIX, gex_confidence, dist_pct, strategy_type,
      spread_width, entry_regime, ai_confidence, signal_mult, time_of_day
      Target: `outcome_correct` (already labeled by label_prediction_outcomes)
      Output: `backend/models/meta_label_v1.pkl`
      Auto-gate: only trains when `closed_trades >= 100`
- [x] In `backend/execution_engine.py`, if meta-label model file exists:
      Score trade before opening.
      score < 0.55 → skip (0 contracts)
      0.55-0.65 → normal sizing
      >= 0.75 → allow 1.5× sizing (capped by existing risk gates)
- [x] Test: model absent → normal sizing; model present score=0.45 → trade skipped

**Cursor sessions: 2 | Commit tag: feat(ml): Loop 2 meta-label scaffold 12K**

**Shipped deviations (discussed + approved before coding):**
1. Training query adds `.order("predicted_at")` so the 80/20 split is
   genuinely walk-forward. Without this, PostgREST row order is not
   guaranteed chronological and future information leaks into training.
2. High-score sizing boost carries an explicit 2× hard ceiling on top
   of the 1.5× multiplier: `min(_orig * 2, max(_orig, int(_orig * 1.5)))`.
   Bounds the upstream Kelly/RCS sizing contract to a known multiple.
3. `val_auc` logged alongside `val_accuracy` (accuracy collapses the
   calibration info that the 0.55/0.75 thresholds are sensitive to).
   Gracefully skipped on single-class validation folds.

**Feature set actually used** (kept in lockstep on both training and
inference sides): `confidence`, `vvix_z_score`, `gex_confidence`,
`cv_stress_score`, `vix`, `signal_weak`, `prior_session_return`,
`vix_term_ratio`, `spx_momentum_4h`, `gex_flip_proximity`. Diverges
from the spec-listed features above because those (iv_rank, dist_pct,
strategy_type one-hot, etc.) are not persisted today — the 12H Phase A
columns ARE, and line up with what `prediction_engine` actually emits.

---

### 12L — D1 Daily Outcome Loop Drift Alert ✅ COMPLETE (2026-04-20, db4c9d9)
**Priority: LOW — extends existing label_prediction_outcomes**
**Auto-activates:** immediately

- [x] In `backend/model_retraining.py`, after `label_prediction_outcomes()` runs:
      Compute rolling 10-day directional accuracy from `outcome_correct` column
      If accuracy drops > 5pp from 30-day baseline: write `model_drift_alert=1` to Redis (TTL 86400)
      Log `drift_alert_fired` with current_accuracy and baseline_accuracy
- [x] In `backend/main.py` EOD job: if `model_drift_alert` key exists in Redis:
      Send alert via `alerting.py` with drift details
- [x] Test: accuracy injected below threshold → drift alert fires and alert sent

**Notes on the shipped scaffold (db4c9d9):**
- `check_prediction_drift(redis_client)` implemented in `backend/model_retraining.py`; both 10d and 30d windows require ≥ 10 labeled rows (from `trading_prediction_outputs` with `outcome_correct IS NOT NULL` and `no_trade_signal = False`) before a ratio is computed. Below that gate, returns `checked=False` without touching Redis.
- On recovery (drop ≤ 5pp) the function also calls `redis.delete("model_drift_alert")` so a single bad day cannot leave dashboards persistently red — not explicitly in the spec but a necessary symmetry for a live alert channel.
- Uses local `DRIFT_DROP_THRESHOLD = 0.05` (delta in percentage points) to avoid shadowing the pre-existing module-level `DRIFT_THRESHOLD = 0.50` (absolute accuracy floor used by `detect_drift`) — the two constants measure different quantities.
- Wired into `run_eod_criteria_evaluation` in `backend/main.py` **between** the labeling step and the criteria evaluation step, in its own try/except so failures never cascade. On `alert=True`, calls `alerting.send_alert(level="warning", event="model_drift_detected", detail=...)` using the real three-positional signature in `alerting.py` (the spec's `title=/message=` keywords were adapted per the spec's own instruction to check the real signature).
- Tests: 6 new cases in `backend/tests/test_prediction_drift.py` covering fire, clear, both insufficient-data gates, fail-open on Supabase exceptions, and an AST-level ROI invariant check that `check_prediction_drift` contains zero Import/ImportFrom/Name/Attribute references to `execution_engine` / `strategy_selector` / `risk_engine` / `trading_cycle`. Backend suite: 672 passed. `tsc --noEmit` clean.
- ROI invariant: pure observability. No trade decision is modified or gated by the drift check.

**Cursor sessions: 0.5 | Commit tag: feat(learning): D1 daily outcome loop drift alert**

---

### 12M — D2 Weekly Champion/Challenger Retrain Scaffold ✅ COMPLETE (2026-04-20, 12cffd7)
**Priority: LOW — scaffold now, activates when meta-label model exists (12K)**
**Auto-activates when:** `backend/models/meta_label_v1.pkl` exists (see deviations below)

- [x] New job in `backend/main.py` Sunday 6 PM ET: added as a dedicated block inside the existing `run_weekly_calibration_job` — runs immediately after `train_meta_label_model` so the champion read here is always the most recently trained v1.
- [x] In `backend/model_retraining.py`, add `run_meta_label_champion_challenger()`:
      Load champion from `backend/models/meta_label_v1.pkl`
      Retrain challenger on rolling 90-day labeled window from `trading_prediction_outputs`
      Compare on 30-day walk-forward holdout: swap if challenger wins by >= 1pp
      Keep prior as `meta_label_v0.pkl` emergency fallback (shutil.copy runs BEFORE pickle.dump so a dump crash never loses both files)
      Log `model_swapped` or `model_retained` with accuracy delta
      Auto-gate: skip gracefully if no champion pkl, if lightgbm unavailable, if <50 labeled rows in the 90d window, or if the 30/10 train/holdout split legs fall below their floors
- [x] Test: 8 cases in `backend/tests/test_champion_challenger.py` covering no-model pass-through, both insufficiency gates (data / split), swap (2pp improvement with v1→v0 backup assertion), retain-losing (-1pp), retain-below-threshold (0.5pp with 200-row holdout), fail-open on Supabase exceptions, and a walk-forward ordering invariant (`.order("predicted_at")` must be in the query).

**Deviations from the literal spec (operator-approved Option A, 2026-04-20):**
1. **Filename.** Spec said `lgbm_direction_v1.pkl`; the directional model that `prediction_engine.py:71` actually loads is `direction_lgbm_v1.pkl` (token order). Gating on the spec's path would never fire in production.
2. **Feature space.** Spec's challenger trains on the 10-column Phase-A live set (`confidence, vvix_z_score, gex_confidence, cv_stress_score, vix, signal_weak, prior_session_return, vix_term_ratio, spx_momentum_4h, gex_flip_proximity`). The directional champion was trained on the 25-column bar-engineered `FEATURE_COLS` list in `backend/scripts/train_direction_model.py`. A cross-space comparison either crashes on `.predict()` shape mismatch or silently padded/truncates, producing meaningless accuracy numbers to base a swap on.
3. **Label space.** Directional champion predicts `"bull"/"bear"` strings; spec's challenger predicts `{0, 1} outcome_correct`. `preds == y_hold` would always be False, champion_acc pinned at 0, and the directional model would be replaced with a trade-outcome classifier on the first Sunday run.
4. **Target model.** Retargeted at `meta_label_v1.pkl` (written by 12K's `train_meta_label_model`). Feature set, target, and label space all match natively — the comparison is valid by construction. A real champion/challenger for the directional model belongs in a Phase-A3 follow-up that retrains from `backend/data/historical/` parquet data, not from `trading_prediction_outputs`.

**Invariants pinned by tests:**
- v1→v0 backup ordering (safety rail — dump-after-copy; assertion on `mock_copy.call_args`).
- Walk-forward `.order("predicted_at")` (prevents future-leak via PostgREST's default arbitrary ordering).
- No Supabase query when champion pkl is absent (cheap-scaffold property).
- Fail-open dict rather than propagation on any exception.
- Current production state remains pure pass-through (`meta_label_v1.pkl` does not yet exist).

**Cursor sessions: 1 | Commit tag: feat(learning): D2 champion-challenger retrain scaffold**

---

### 12N — Sizing Phase Auto-Advance (Phase E1/E2)
**Priority: LOW — no human action needed once built**
**Auto-activates: E1 at 45 live days + Sharpe ≥1.2 | E2 at 90 live days + Sharpe ≥1.5**

✅ **COMPLETE (2026-04-20, d11b8fd)**

- [x] In `backend/calibration_engine.py`, add `evaluate_sizing_phase()`:
      Query trading_sessions: count live days, compute rolling Sharpe
      If days >= 45 AND sharpe_45d >= 1.2 AND current_phase == 1:
          Write `capital:sizing_phase=2` to Redis (setex, TTL 1 year)
      If days >= 90 AND sharpe_60d >= 1.5 AND current_phase == 2:
          Write `capital:sizing_phase=3` to Redis (setex, TTL 1 year)
- [x] Redis read lives in `calibration_engine.read_sizing_phase(client)`
      (not `risk_engine.py` as originally specced — see deviation 1 below)
      and is consumed at the single `main.run_prediction_cycle` call
      site into `run_trading_cycle`. Falls back to 1 on missing key,
      None client, or a raising client.
- [x] Added to `run_weekly_calibration_job` after the 12M
      champion/challenger block, in its own try/except.
- [x] Tests in `backend/tests/test_sizing_phase_advance.py` pin: below
      the 45-day floor → no write; E1 gate passes → `setex("2")` with
      1-year TTL; Sharpe below gate → no write; phase 2 + E2 passes →
      `setex("3")`; already at max → no write and no Supabase call;
      Supabase error → phase=1 error dict + no write; Redis error →
      phase=1 error dict + no write; reader returns ints correctly
      across all four input shapes AND `main.py` imports the reader
      from `calibration_engine` (no copy-paste drift).

**Deviations from the literal spec (documented here so a future
reader auditing against the original prompt doesn't think anything
went missing):**

1. **Redis read moved from `risk_engine.py` to `calibration_engine.py`.**
   The spec said "In `backend/risk_engine.py`, read `capital:sizing_phase`
   from Redis, fallback to 1". But `risk_engine.compute_position_size()`
   already takes `sizing_phase` as a plain int parameter (line 220),
   which keeps it pure/testable. Adding Redis I/O inside the risk
   function would bury a side-effecting dependency in the sizing
   core. Instead the Redis read lives in `calibration_engine` next
   to the writer (sharing `SIZING_PHASE_REDIS_KEY`), and
   `main.run_prediction_cycle` — the one place the int originates —
   calls the reader before passing the value through unchanged.
   Tests assert the shared key name to prevent drift.

2. **No `sizing_phase_source=redis|default` log.** The spec asked for
   this tag, but the reader was factored into a helper and now logs
   `sizing_phase_read_failed_fail_open` only on the raise path
   (the common success / cache-miss paths are called once per
   5-minute prediction cycle and logging each one would be noise).
   The weekly writer emits `sizing_phase_advanced` when a gate
   passes and `weekly_sizing_phase_complete` on every run, which
   is the higher-signal observability surface.

3. **`_RISK_PCT` phase-1-vs-phase-2 equivalence is intentionally
   NOT fixed here.** The spec's descriptive copy says "E1 doubles
   gross P&L with same win rate", but today's
   `backend/risk_engine.py:48-53` assigns identical risk percentages
   to phases 1 and 2 (core=0.005) and identical percentages to
   phases 3 and 4 (core=0.010). So the E1 advance (1→2) is
   currently a no-op on position size, and only E2 (2→3) actually
   doubles risk_pct. 12N writes the Redis key correctly either
   way; bringing the `_RISK_PCT` table in line with the "doubles at
   E1" intent belongs in a separate task so the infrastructure
   change (this PR) is cleanly reviewable from the payload change.

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

## SECTION 13 — POST-SECTION-12 DIAGNOSTIC FIXES (2026-04-20)

Following a comprehensive end-to-end audit of Section 12 (12A–12N), 12 issues were
identified. Fixes are grouped into two batches by priority.

Full diagnostic report: produced by Cursor agent on 2026-04-20.

---

### Batch 1 — ROI-Positive Fixes (ship together)

- [ ] **B1-1 — Fix `_RISK_PCT` phase ladder** (`backend/risk_engine.py`)
      Phase 1 and 2 have identical values — E1 auto-advance (12N) is a no-op on sizing.
      Fix: `2: {"core": 0.0075, "satellite": 0.00375}` — +50% at E1, 2× at E2.
      Phase 1 UNCHANGED (0.005/0.0025). Test: assert phase1 ≠ phase2 ≠ phase3.

- [ ] **B1-2 — Fix 12A EOD gate from 19 → 21 UTC** (`backend/polygon_feed.py`)
      Both VIX daily history AND SPX daily return gates use `now.hour >= 19` (= 3 PM ET).
      True NYSE close is 4 PM ET = 20:00 UTC (EDT) / 21:00 UTC (EST).
      Fix: change BOTH `now.hour >= 19` occurrences to `now.hour >= 21`.
      Ensures close-to-close daily returns, not mid-afternoon samples.
      VIX and SPX must stay in sync — both change together.

- [ ] **B1-3 — Add `earnings_proximity_score` writer** (`backend_agents/economic_calendar.py`)
      `calendar:earnings_proximity_score` Redis key is READ by prediction_engine but
      NEVER WRITTEN anywhere. Every prediction row has 0.0 permanently — phantom feature.
      Fix: in `write_intel_to_redis()`, compute and write score = min(1.0, max(0, 1 - days_to_next_earnings/5))
      based on upcoming earnings in the calendar intel. TTL 86400. Fail-open.

- [ ] **B1-4 — Drop `signal_weak` from 12K/12M feature vectors** (`backend/model_retraining.py`)
      `signal_weak` is always False in training (filter: no_trade_signal=False) and
      always False at inference (only reached when no_trade_signal=False).
      Constant column wastes a degree of freedom and adds noise to walk-forward comparison.
      Fix: remove from SELECT query, feature list, and _row_to_features() in both
      train_meta_label_model() and run_meta_label_champion_challenger(). 4 lines total.
      Update feature count comments from "10 features" to "9 features".

- [ ] **B1-5 — Wire feature flags for counterfactual and meta-label** (`backend/counterfactual_engine.py`, `backend/execution_engine.py`)
      `feedback:counterfactual:enabled` and `model:meta_label:enabled` flags exist in
      the UI but are never read by backend code. Operator has no kill-switch if either
      misbehaves in production without a code deploy.
      Fix: wrap label_counterfactual_outcomes() top with flag check (fail-open: missing
      row / read error / exception → feature ENABLED, today's behaviour preserved).
      Wrap meta-label inference block in execution_engine.py with same flag check.
      Semantics: flag=false → disabled; flag missing/error → enabled (fail-open).

**Batch 1 commit tag:** `feat(section-13): ROI fixes — risk ladder, EOD gates, earnings score, feature flags, feature hygiene`

---

### Batch 2 — Cleanup and Observability (ship together, after Batch 1)

- [ ] **B2-1 — Sync sizing phase to Supabase** (`backend/calibration_engine.py`)
      When evaluate_sizing_phase() advances the phase, it writes Redis only.
      ConfigPage.tsx reads sizing_phase from trading_operator_config (Supabase) — never updated.
      Operator UI shows stale phase indefinitely after auto-advance.
      Fix: also upsert trading_operator_config.sizing_phase on every advance.

- [ ] **B2-2 — Rename inline `_safe_float` → `_read_float_key`** (`backend/prediction_engine.py`)
      Module-level _safe_float(value, default) and an inline _safe_float(key, default)
      with a different signature coexist in the same function — name collision risk.
      Fix: rename inline helper. Purely defensive, zero behaviour change.

- [ ] **B2-3 — Add TODO to `drawdown_block` counter** (`backend/main.py`)
      `drawdown_block` is in butterfly_gate_daily_stats reasons list but has no writer
      anywhere in the codebase — reads 0 forever. Keep as placeholder, add comment.
      Fix: add `# TODO: wire drawdown_block counter in execution_engine` comment.

- [ ] **B2-4 — Document phase 4 as manual-only** (`src/pages/admin/trading/ConfigPage.tsx`)
      Phase 4 exists in _RISK_PCT and the UI but is never reached by auto-advance (max=3).
      Operator reading only the UI would expect auto-advance to handle it.
      Fix: add comment in ConfigPage.tsx that phase 4 requires manual activation.

- [ ] **B2-5 — Return None from _annualised_sharpe on negative mean** (`backend/calibration_engine.py`)
      Currently returns 0.0 when mean_pnl <= 0. This is correct for the gate logic
      (0 < 1.2 → no advance) but the payload shows "sharpe": 0.0 which is
      indistinguishable from a genuinely computed very-bad Sharpe.
      Fix: return None and add "reason": "negative_mean_pnl" to the payload. 2 lines.

**Batch 2 commit tag:** `chore(section-13): observability + cleanup fixes`

---

### Deferred (conscious decision, not forgotten)

- **Item 8** — Counterfactual spread width hardcoded to 5pt iron_condor win band.
  Real 0DTE condors wing 20-50pts. Simulated P&L skews negative.
  Defer: needs real strategy_hint data per no-trade cycle before fixing is meaningful.
  Revisit after 30+ sessions of counterfactual data exists.

- **Item 11** — No UI surfaces for 12A–12L observability data (realized vol, butterfly
  counters, matrix cell values, drift alert banner, sizing phase ribbon).
  Defer: separate UI sprint after paper trading validates the data is meaningful.

---

### Status

- [ ] Batch 1 shipped
- [ ] Batch 2 shipped

*Section 13 opened: 2026-04-20 | Owner: tesfayekb*

---

*Task Register v1.0 — April 2026 — tesfayekb*
