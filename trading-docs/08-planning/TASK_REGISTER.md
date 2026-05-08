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

### LightGBM v1 Activation Chain — 2026-04-30 (5 sequential Fix PRs)
- [x] T-ACT-040 / PR #82 (`94edb9a`) — AI synthesis output unblock (TTL coupling + schema migration)
- [x] T-ACT-041 / PR #83 (`a77195a`) — three-tier LightGBM model loader + Supabase storage fallback + `lightgbm` 4.6.0 bump
- [x] T-ACT-042 / PR #84 (`eaa7aa8`) — `trading_system_health` CHECK constraint expansion for `direction_model` (the `nixpacks.toml` portion of this PR was subsequently confirmed inert; superseded by T-ACT-043)
- [x] T-ACT-043 / PR #85 (`8094eff`) — `railpack.json` `deploy.aptPackages: ["libgomp1"]` + `nixpacks.toml` deletion — **LightGBM activated in production at this commit**
- [x] T-ACT-044 / PR #86 (`5162020`) — `scikit-learn==1.5.2` exact pin + training-environment metadata capture + `preflight_training_env.py` validator
- [x] System flipped from hardcoded 0.35/0.30/0.35 placeholder probabilities to real ML conviction signals at holdout-validated 52.9% win rate across 23,668 samples
- [x] 4 governance-grade lessons-learned (HANDOFF NOTE Appendix A.1-A.4) ratified

**Full per-PR detail and audit trail:** `trading-docs/06-tracking/action-tracker.md` T-ACT-040 through T-ACT-044 entries. **Cross-references:** `trading-docs/08-planning/MASTER_ROI_PLAN.md` §1.8 (activation narrative) + §7 F-38 (findings register milestone) + `trading-docs/06-tracking/HANDOFF_NOTE_2026-04-28_POST_P1-3-7.md` Appendix A (cumulative DIAGNOSE-FIRST discipline additions).

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

**2026-04-20 Railway deploy scope fix (this commit):**
The `abspath` pattern shipped in `3cd1c8c` correctly resolves
sibling-dir paths at runtime, but the sibling directories
themselves (`backend_agents/`, `backend_earnings/`) were never
entering the Railway container. Operator confirmed Railway
Root Directory was set to `/backend`, which only copies the
`backend/` subtree into the image — everything else in the repo
was excluded, producing `ModuleNotFoundError: No module named
'flow_agent'` (and `synthesis_agent`, `feedback_agent`,
`main_earnings`, ...) on every scheduled tick. The health-write
column fix in `fd34c3c` exposed these failures; they had been
silently swallowed before.

- **Infra change.** Moved `backend/nixpacks.toml` → `./nixpacks.toml`
  (repo root) and rewrote the file to anchor the install/start
  commands to the new build root:

  ```
  [phases.install]
  cmds = ["pip install -r backend/requirements.txt"]
  [start]
  cmd = "cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT"
  ```
  No Python code change — the existing `abspath(dirname(__file__)/..
  /backend_agents)` pattern correctly resolves to
  `/app/backend_agents` once those dirs are in the container.
- **Operator step (manual, not in code).** Change Railway service
  Root Directory from `/backend` to `/` (root) and trigger a
  manual redeploy. This cannot be automated from the repo.
- **Regression guard.** Added `backend/tests/test_nixpacks_location.py`
  — 4 assertions: nixpacks.toml at repo root, not inside backend/,
  install cmd references `backend/requirements.txt`, start cmd
  contains both `cd backend` and `uvicorn main:app`.
- **Verification after redeploy.** Watch Railway logs for
  `macro_agent_job_complete`, `flow_agent_job_complete`,
  `synthesis_agent_job_complete`, `feedback_agent_job_complete`,
  `surprise_detector_job_complete`, `sentiment_agent_job_complete`,
  and `earnings_scan_job_complete` on the next cycle.

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

- [x] **B1-1 — Fix `_RISK_PCT` phase ladder** (`backend/risk_engine.py`) ✅ COMPLETE (2026-04-20, fc64840)
      Phase 1 and 2 have identical values — E1 auto-advance (12N) is a no-op on sizing.
      Fix: `2: {"core": 0.0075, "satellite": 0.00375}` — +50% at E1, 2× at E2.
      Phase 1 UNCHANGED (0.005/0.0025). Test: assert phase1 ≠ phase2 ≠ phase3.

- [x] **B1-2 — Fix 12A EOD gate from 19 → 21 UTC** (`backend/polygon_feed.py`) ✅ COMPLETE (2026-04-20, fc64840)
      Both VIX daily history AND SPX daily return gates use `now.hour >= 19` (= 3 PM ET).
      True NYSE close is 4 PM ET = 20:00 UTC (EDT) / 21:00 UTC (EST).
      Fix: change BOTH `now.hour >= 19` occurrences to `now.hour >= 21`.
      Ensures close-to-close daily returns, not mid-afternoon samples.
      VIX and SPX must stay in sync — both change together.

- [x] **B1-3 — Add `earnings_proximity_score` writer** (`backend_agents/economic_calendar.py`) ✅ COMPLETE (2026-04-20, fc64840)
      `calendar:earnings_proximity_score` Redis key is READ by prediction_engine but
      NEVER WRITTEN anywhere. Every prediction row has 0.0 permanently — phantom feature.
      Shipped Option B (full gradient): extended `_fetch_major_earnings()` to query a
      5-day window and annotate each event with `date` + `days_until`; added
      `_compute_earnings_proximity_score()` (linear decay 1.0→0.0 across 0..5 days)
      called from `write_intel_to_redis()`. Independent try/except so an intel-write
      or proximity-write failure can't cross-contaminate. TTL 86400. Fail-open.

- [x] **B1-4 — Drop `signal_weak` from 12K/12M feature vectors** (`backend/model_retraining.py`, `backend/execution_engine.py`) ✅ COMPLETE (2026-04-20, fc64840)
      `signal_weak` is always False in training (filter: no_trade_signal=False) and
      always False at inference (only reached when no_trade_signal=False).
      Constant column wastes a degree of freedom and adds noise to walk-forward comparison.
      Fix: remove from SELECT query, feature list, and `_row_to_features()` in both
      `train_meta_label_model()` and `run_meta_label_champion_challenger()` — AND
      from the `execution_engine` meta-label inference `_feat` builder so all three
      sites stay in lockstep at 9 features (otherwise `.predict_proba()` crashes on
      a shape mismatch once `meta_label_v1.pkl` ships). Feature-count comments updated
      from "10 features" to "9 features".

- [x] **B1-5 — Wire feature flags for counterfactual and meta-label** (`backend/counterfactual_engine.py`, `backend/execution_engine.py`) ✅ COMPLETE (2026-04-20, fc64840)
      `feedback:counterfactual:enabled` and `model:meta_label:enabled` flags exist in
      the UI but are never read by backend code. Operator has no kill-switch if either
      misbehaves in production without a code deploy.
      Implemented using the Redis-authoritative pattern that matches
      `strategy_selector._check_feature_flag` (15+ existing call sites) instead of
      a fresh Supabase round-trip on the hot path — keeps the operator toggle
      instantaneous and eliminates the stale-read risk from a failed Redis→Supabase
      mirror write. `label_counterfactual_outcomes()` short-circuits before any
      Supabase query when the flag is false; `execution_engine` gates the meta-label
      inference `if _meta_label_enabled and _model_path.exists():`. Fail-open:
      missing key / client-None / read error → feature ENABLED (today's behaviour
      preserved).

**Batch 1 commit tag:** `feat(section-13): ROI fixes — risk ladder, EOD gates, earnings score, feature flags, feature hygiene`
**Shipped as commit:** `fc64840` on 2026-04-20. Full suite: 718 passed (vs 704 baseline, +14 new tests in `backend/tests/test_section_13_batch_1.py`). `tsc --noEmit`: 0 errors.

---

### Batch 2 — Cleanup and Observability (ship together, after Batch 1)

- [x] **B2-1 — Sync sizing phase to Supabase** COMPLETE (2026-04-20, 41bb1ab)
      Implemented `_sync_sizing_phase(redis_client, new_phase)` in
      `backend/calibration_engine.py`. Called from both E1 and E2 advance
      branches. Two parallel fail-open writes:
        * Redis audit key `capital:sizing_phase_advanced_at` ←
          `"<phase>|<iso_timestamp>"` with matching 1-year TTL.
        * Supabase `trading_operator_config.sizing_phase` via service-role
          `.update()` with a `sizing_phase >= 0` filter (single-tenant,
          user_id-agnostic bulk update — table has UNIQUE(user_id) with
          exactly one row in practice, and no scheduler-time user context).
      Neither sync failure blocks the primary `capital:sizing_phase` write.
      Logs `sizing_phase_synced` with phase + rows_updated for observability.

- [x] **B2-2 — Rename inline `_safe_float` → `_read_float_key`** COMPLETE (2026-04-20, 41bb1ab)
      Renamed the inline helper inside `run_cycle()` in
      `backend/prediction_engine.py` (signature: key, default) to
      `_read_float_key`. Module-level `_safe_float(value, default)` is
      now the only function by that name in the file. Five call sites
      updated. Pure defensive rename; zero behaviour change.

- [x] **B2-3 — Add TODO to `drawdown_block` counter** COMPLETE (2026-04-20, 41bb1ab)
      Added inline comment on the `"drawdown_block"` entry of the
      butterfly_gate_daily_stats reasons list in `backend/main.py`:
      `TODO (Section 13 Batch 2): wire writer in execution_engine when
      same-strategy drawdown gate fires`. Kept in the list so the counter
      surfaces (as 0) in EOD stats without a schema change once the
      writer ships. Regression guard `test_drawdown_block_in_reasons_list`
      prevents accidental removal.

- [x] **B2-4 — Document phase 4 as manual-only** COMPLETE (2026-04-20, 41bb1ab)
      `src/pages/admin/trading/ConfigPage.tsx`:
        * Extended `SIZING_PHASES` with `manualOnly?: boolean` flag.
        * Phase 4 description: "Never reached by auto-advance — requires
          operator action in trading_operator_config."
        * Added a "manual" badge next to the Phase 4 label with a tooltip.
        * Added a leading comment documenting that MAX_PHASE is capped at
          3 in the backend auto-advance.
      Also refreshed phase 2 + 3 descriptions to match the Batch 1
      `_RISK_PCT` ladder (0.75/0.375 and 1.0/0.5) — pure observability
      fix; the stale phase 2 copy was otherwise misleading post-Batch-1.

- [x] **B2-5 — Return None from _annualised_sharpe on negative mean** COMPLETE (2026-04-20, 41bb1ab)
      `_annualised_sharpe` in `backend/calibration_engine.py` now returns
      `None` (not 0.0) when mean P&L is non-positive. Downstream gate
      check `sharpe is not None and sharpe >= gate` already short-circuits
      correctly on None — no gate logic change. The return payload from
      `evaluate_sizing_phase` distinguishes `E1_negative_mean_pnl` from
      `E1_sharpe_below_gate` (and symmetric for E2) so structured logs
      separate "cohort is losing" from "cohort is just low-Sharpe".

**Batch 2 commit tag:** `chore(section-13): observability + cleanup fixes`

---

### Section 13 — UI Observability Sprint (Item 11)

Previously deferred. Build now — annotated with activation state so operators
understand which panels show live data vs "warming up" data.

All panels are READ-ONLY — no trade decisions are affected. Every panel shows
"warming up" state until enough data exists.

---

#### UI-1 — Learning Dashboard Page (`/trading/learning`)
**New page — surface all Section 12 observability data in one place**
**Activation note: shows "warming up" for most panels until 10+ sessions**

- [x] **UI-1 COMPLETE** (2026-04-20, 0149877) — `src/pages/trading/LearningPage.tsx`
      Ships all seven panels below. Uses `useLearningStats()` hook
      (`src/hooks/trading/useLearningStats.ts`) which calls the Supabase
      Edge Function `get-learning-stats` (see CHANGE 0 below). Every panel
      renders an explicit warmup state — operator never sees null/undefined.
      Route: `/trading/learning` (NOT `/admin/trading/learning` as in the
      original spec — matches the Phase 4C convention where every other
      trading sidebar entry lives under `/trading/*`).
      Sidebar entry uses `GraduationCap` icon to avoid colliding with the
      existing AI Intelligence `Brain` icon.

Panels shipped:

- [x] **IV/RV Ratio panel** — realized_vol_20d vs vix_current with
      calculated ratio. Green >1.10, red <=1.10, grey when null.
      Warmup: "Collecting daily returns — realized volatility needs
      20 daily samples before it stabilises."

- [x] **Butterfly Gate Counters panel** — horizontal bar chart of all
      6 reasons (regime_mismatch, time_gate, failed_today,
      low_concentration, wall_unstable, drawdown_block) plus "Allowed"
      green bar. `drawdown_block` greyed out with "wiring pending"
      annotation (matches the TODO in backend/main.py from Batch 2).
      Warmup: "No butterfly attempts today — counters reset each session."

- [x] **Regime × Strategy Matrix panel** — table with regime, strategy,
      win rate, avg P&L, profit factor, trade count. Rows with
      trade_count >= 10 AND win_rate < 0.40 tinted red (active reduction).
      Rows with 5 <= trade_count < 10 tinted yellow (building data).
      Warmup: "Collecting trades — each cell needs 10 closed paper trades
      before it starts influencing sizing."

- [x] **Model Drift (live) panel** — green "No drift detected" badge
      normally; red alert card when `model_drift_alert=true`. Always
      visible (no warmup state — bool is always defined).

- [x] **Sizing Phase panel** — current phase number + label with
      Batch 1 risk ladder copy ("Paper trading", "E1 Active",
      "E2 Active", "Manual override"). Shows `sizing_phase_advanced_at`
      timestamp when phase > 1.

- [x] **Adaptive Halt Threshold panel** — calibrated value in green
      when `halt_threshold_source=adaptive`; -3.0% (default) in grey
      otherwise. Warmup: "Using default — adaptive calibration
      activates after 100 closed trades."

- [x] **Calibrated Butterfly Thresholds panel** — 3-row table comparing
      default vs calibrated for GEX Confidence, Wall Distance,
      Concentration. Rows where calibrated differs from default
      tinted green. Warmup: "Using defaults — calibration activates
      after 20 butterfly trades."

---

#### CHANGE 0 — Supabase Edge Function proxy (`get-learning-stats`)
**New function — Lovable frontend cannot reach Railway directly (CSP) and
shipping RAILWAY_ADMIN_KEY in the browser bundle would leak the secret.**

- [x] **CHANGE 0 COMPLETE** (2026-04-20, 0149877) —
      `supabase/functions/get-learning-stats/index.ts`
      Authenticates the Supabase session (Bearer token), enforces
      `trading.view` permission, and forwards to Railway
      `GET /admin/trading/learning-stats` with `X-Api-Key:
      RAILWAY_ADMIN_KEY` stored as a Supabase edge secret (server-side
      only). Fail-open: if Railway is unreachable or the proxy is
      mis-configured, returns a 200 warmup skeleton so the UI renders
      every panel in its "collecting data" state rather than erroring.
      Same pattern as `set-feature-flag`, `kill-switch`,
      `subscription-key-status`.

      **Operator actions required before the UI shows live data:**
        1. `supabase secrets set RAILWAY_ADMIN_KEY=<value> RAILWAY_API_URL=<https://...>`
        2. `supabase functions deploy get-learning-stats`

      Until both are run, the Edge function returns warmup defaults
      and the UI renders cleanly with no errors — zero trading impact.

---

#### UI-2 — Backend endpoint (`GET /trading/learning-stats`)
**New FastAPI endpoint to serve all observability data to the Learning Dashboard**

- [x] **UI-2 COMPLETE** (2026-04-20, 709a3db) — `GET /admin/trading/learning-stats`
      Reads all Redis keys listed in UI-1 in a single handler.
      Returns JSON with all values + warmup states.
      Requires `RAILWAY_ADMIN_KEY` authentication (via `Depends(_require_admin_key)` — same as other admin endpoints).
      Fail-open: missing Redis keys return null/default, never 500.
      Path deviation from the doc: real route is `/admin/trading/learning-stats`
      (not `/trading/learning-stats`) to stay consistent with the six other
      admin GETs and keep RAILWAY_ADMIN_KEY gating uniform. UI-1 fetch calls
      must target `/admin/trading/learning-stats`.
      Field deviation: `realized_vol_daily_days` renamed to
      `realized_vol_last_date` — polygon_feed only persists the last EOD date
      string (not a sample count). UI infers warmth from `realized_vol_20d`
      non-null, which proxies the writer's `daily_len >= 5` gate.
      +9 tests in `backend/tests/test_learning_stats_endpoint.py` covering
      shape contract, iv/rv math, fail-open, and auth enforcement.

---

#### UI-3 — Drift alert banner on War Room and Performance pages
**Elevate model drift to highest-visibility pages**

- [x] **UI-3 COMPLETE** (2026-04-20, 0149877) —
      `src/pages/admin/trading/WarRoomPage.tsx` and
      `src/pages/admin/trading/PerformancePage.tsx` each now render a
      destructive-colored drift banner sourced from
      `useLearningStatsBanner()` (120s refetch, separate cache key
      from the full Learning Dashboard query so it does not cause
      cascade invalidation). Banner includes an inline `<Link>` to
      `/trading/learning` for immediate operator triage.
      On PerformancePage the banner is labeled **"Live model drift"**
      so it is clearly distinct from the existing
      `modelPerf.drift_status` "Drift Status" badge in the Model
      Performance card (that one is the historical session-level
      drift; this one is the live 10-day rolling Redis alert).

---

#### UI-4 — Missed Opportunity Summary on Performance page
**Surface counterfactual engine weekly report**

- [x] **UI-4 COMPLETE** (2026-04-20, 0149877) —
      `src/pages/admin/trading/PerformancePage.tsx` now renders a
      "Missed Opportunities (This Week)" card at the bottom. Reads
      directly from Supabase (`trading_prediction_outputs` with
      `no_trade_signal=true`, `counterfactual_pnl IS NOT NULL`, last
      7 days). Groups by `no_trade_reason`, sorts by absolute total
      P&L, shows top 3 with cycles / avg / total columns. Uses
      `formatPnl()` for consistent coloring. Empty state: "No
      counterfactual data yet — collecting from no-trade cycles."
      `counterfactual_pnl` is not yet in the generated Supabase
      types (column added in `20260421_add_counterfactual_pnl.sql`),
      so the row shape is widened via `as unknown as Array<...>` —
      same cast-around-missing-types pattern used by `useFeatureFlags`
      for `trading_feature_flags`.

---

**Build order:** UI-2 (endpoint) → UI-1 (Learning Dashboard) → UI-3 (banners) → UI-4 (counterfactual)
**Commit tag:** `feat(ui): learning dashboard + observability panels`
**Activation note:** Every panel shows warmup state until its data threshold is met.
No panel affects any trade decision — pure read-only observability.

---

### Deferred (conscious decision, not forgotten)

- **Item 8** — Counterfactual spread width hardcoded to 5pt iron_condor win band.
  Real 0DTE condors wing 20-50pts. Simulated P&L skews negative.
  Defer: needs real strategy_hint data per no-trade cycle before fixing is meaningful.
  Revisit after 30+ sessions of counterfactual data exists.

- **Item 11** — ~~No UI surfaces for 12A–12L observability data~~
  **COMPLETE.** Phase 1 (UI-2 backend endpoint) shipped 2026-04-20 in
  commit `709a3db`; Phase 2 frontend panels (UI-1 Learning Dashboard,
  UI-3 live-drift banners, UI-4 Missed Opportunity panel, plus the
  `get-learning-stats` Supabase Edge proxy) shipped 2026-04-20 in
  commit `0149877`. UI Observability Sprint fully closed.

- **Item 12** — ~~`VIX_SPREAD_WIDTH_TABLE` under-scaled for SPX 7000
  price levels.~~
  **COMPLETE (2026-04-20).** Two-commit landing:
  `fix(strike): widen VIX spread width table for SPX 7000 price levels`
  (table values 2.5/5/7.5/10 → 10/15/20/30, `DEFAULT_SPREAD_WIDTH`
  5→15) and `fix(risk): double Phase 1 risk_pct to preserve
  contracts>=1 under widened SPX wings` (Phase 1 core 0.005→0.010,
  satellite 0.0025→0.005, iron_butterfly 0.004→0.008). Paired
  commits because narrow-wing → wide-wing alone would produce
  contracts=0 on core+full without the risk_pct bump. Full sizing
  matrix verified — core+full produces contracts>=1 at every VIX
  regime including stress. Satellite+moderate is intentionally
  blocked at width>=15pt ("fewer, better trades"); satellite+full
  and satellite+moderate are blocked at VIX>20 (elevated/crisis
  regime discipline). C4 constraint (0.5-sigma survival) relaxed to
  0.25-sigma survival — strict 0.5-sigma is infeasible at $100k
  within the 2× risk_pct ceiling. Pinned by
  `backend/tests/test_risk_engine.py::test_core_full_produces_contract_
  at_all_operating_widths` + 5 companion tests + 3 new width-table
  guards in `test_phase_b1.py`.

- **Item 13** — Sizing-phase ladder non-monotonic after Item 12.
  The 2026-04-20 Phase 1 doubling was approved and shipped as a
  Phase-1-only change. Phases 2 and 3 were **not** rescaled, which
  leaves the ladder as:
    Phase 1 core = 0.010
    Phase 2 core = 0.0075 (lower than Phase 1 — advancement demotes)
    Phase 3 core = 0.010 (equal to Phase 1 — advancement no-op)
  A trader who passes the E1 gate (45+ live days, rolling 45d Sharpe
  ≥ 1.2) would currently see their risk_pct **decrease**, which is
  the opposite of the gate's intent. Phase 3 would leave risk
  unchanged vs Phase 1.
  Defer rationale: zero current impact — we are ~2 live days in, and
  the earliest E1 gate fires at 45 days. The system is provably safe
  at today's phase. Decision of whether to rescale phases 2/3 in
  proportion (the natural +50%/2× interpretation would give 0.015 /
  0.020 core) or to re-examine the gate thresholds themselves is
  deferred to the first pre-advancement review. Existing
  `test_section_13_batch_1.py::test_phase1_phase2_phase3_distinct`
  still passes (adjacent phases differ) so this does not break the
  existing guards, but the ladder semantics are broken and MUST be
  resolved before any Phase-2 advancement fires. Flagged inline in
  `backend/risk_engine.py::_RISK_PCT` docstring.
  Revisit trigger: 40 live days (first warning bell, 5 days before
  potential advancement).

---

### Status

- [x] Batch 1 shipped (2026-04-20, fc64840)
- [x] Batch 2 shipped (2026-04-20, 41bb1ab)
- [x] UI Observability Sprint shipped (2026-04-20, 709a3db + 0149877)
- [x] T0-7 floor unblock shipped (2026-04-20, 167d7cd)

*Section 13 opened: 2026-04-20 | Owner: tesfayekb*

---

## SECTION 14 — POST-2026-05-01 DIAGNOSTIC FIXES + FOLLOW-UPS

Tasks surfaced during the 2026-05-01 trading session validation. See HANDOFF NOTE Appendix A.6 for the canonical post-mortem context. Track B PR `docs/track-b-silent-staleness-and-governance` (2026-05-03) added the empirical-validation update to A.6 and ratified A.7 (silent-failure-class family convention pointer); see also the cv_stress design memo 2026-05-03 for T-ACT-054 design rationale.

**Numbering note (2026-05-03):** T-ACT-049 was originally proposed as a separate entry for the `polygon_feed.py:174-184` silent-staleness fix, sibling to T-ACT-046 (`tradier_feed.py:282-283`). Per Cursor's recommendation 2026-05-03, both fixes are bundled into an expanded T-ACT-046 (same root pattern, single PR — Track B). T-ACT-049 is therefore subsumed and not assigned. The next available T-ACT number after the 2026-05-03 batch (T-ACT-048, T-ACT-050, T-ACT-051, T-ACT-054) is T-ACT-055.

**Numbering note (2026-05-04 evening, amended late evening):** Numbers T-ACT-056, T-ACT-058, T-ACT-059 are RESERVED placeholders, not yet assigned to delivered work. T-ACT-056 is reserved for the exhaustive persist-site audit (gate for A.7 family re-closure on database-persistence subclass) per T-ACT-055 entry. T-ACT-058 is reserved for the Option B `.replace(" ", "")` defensive whitespace strip code-change PR per T-ACT-057 entry. T-ACT-059 is reserved for the exhaustive infrastructure-config audit (gate for A.7 family re-closure on infrastructure-config subclass) per T-ACT-057 entry. T-ACT-060 was assigned to the stale `_upsert_criterion` test references fix (Option Bravo per T-ACT-060 plan-review) executed 2026-05-04. T-ACT-061..T-ACT-064 were added in PR #100 `docs/post-incident-indices-advanced-2026-05-04` (governance closure for the 2026-05-01 → 2026-05-04 prediction outage). T-ACT-065 was added 2026-05-04 evening alongside the T-ACT-062 EXECUTE PR `feat/t-act-062-vix-vvix-freshness-guard` to formalize the 7-day post-T-ACT-062-merge evaluation (decision matrix for hard-gate-flip on VIX/VVIX/VIX9D per SD-1 Option β). **T-ACT-062 closed 2026-05-04 late evening via the EXECUTE PR (Option β shipped per SD-1; T-ACT-061 §7.1 gate waived per SD-5).** **T-ACT-072 added 2026-05-06 mid-RTH via PR `fix/t-act-072-databento-ts-event-age-filter` (producer-side ts_event age filter on Databento OPRA trades; CRITIQUE-FIRST Q1-Q8 + YELLOW-authorized implementation per markets-open risk discipline). T-ACT-066..T-ACT-071 and T-ACT-073 remain RESERVED placeholders for the diagnostic-derived follow-ups identified across the 2026-05-05 / 2026-05-06 handoff notes (`HANDOFF_NOTE_2026-05-05_RTH_DAY1_ANOMALIES.md`, `HANDOFF_NOTE_2026-05-05_FIRST_POST_DEPLOY_TRADE.md`, `HANDOFF_NOTE_2026-05-06_GEX_QUOTE_MISSING.md`, `HANDOFF_NOTE_2026-05-06_DATABENTO_PUSH_LIFECYCLE.md`); they will be assigned as those follow-ups are scoped.** **Next available T-ACT is T-ACT-074.**

### T-ACT-045 — Post-PR-#90 empirical SPX real-time validation

**Severity:** HIGH (validation-blocking)
**Owner:** operator
**Estimated time:** 10 minutes

**Description:** PR #90 routed SPX through Polygon real-time and added a freshness guard. The pre-PR-#90 LightGBM v1 "empirical validation" (declared 2026-05-01 morning) was made on 15-min-stale Tradier sandbox SPX data. After PR #90 deploy and ~10 minutes of stable cycle execution, operator must re-run the validation comparing system-recorded `entry_spx_price` to Polygon's contemporaneous 1-minute SPX bar.

**2026-05-03 update — independent review verdict:** Operator's first attempt to run T-ACT-045 used data from 2026-05-01 13:35-19:55 UTC compared to Polygon real-time 1-min bars. Cursor's independent review (2026-05-03) determined the data is entirely pre-PR-#90-merge (PR #90 squash-merged 19:59:22 UTC; last cycle 19:55 UTC). The verdict was reversed from VALIDATED to NOT-YET-VALIDATED. T-ACT-045 must be re-run against post-deploy data — target Monday 2026-05-04 ≥10 min after Railway deploy is confirmed stable.

**Acceptance criteria (refined 2026-05-03 per N-1 finding):**

1. Run the SQL query — but with a hard floor: `predicted_at >= [PR #90 Railway deploy timestamp] + INTERVAL '10 minutes'`. Operator must look up the actual deploy timestamp from Railway's deployments dashboard before running the SQL. Rows with `predicted_at` BEFORE that floor MUST be excluded; the validation operates ONLY on post-deploy data.
   ```sql
   SELECT predicted_at, spx_price
   FROM trading_prediction_outputs
   WHERE predicted_at >= '<PR-#90-deploy-ts>'::timestamptz + INTERVAL '10 minutes'
     AND predicted_at <= NOW()
   ORDER BY predicted_at DESC;
   ```

2. Pull contemporaneous Polygon real-time SPX 1-min bars for the same window via `https://api.polygon.io/v2/aggs/ticker/I:SPX/range/1/minute/{date}/{date}` API:
   ```bash
   curl -s "https://api.polygon.io/v2/aggs/ticker/I:SPX/range/1/minute/$(date +%Y-%m-%d)/$(date +%Y-%m-%d)?apiKey=$POLYGON_API_KEY&adjusted=true&sort=asc"
   ```

3. For each row in the SQL output, the system's `spx_price` MUST fall within ±$5 of Polygon's 1-min bar [low, high] envelope containing that timestamp. Allow small drift up to ±$5 to account for poll cadence (TTL=600s, freshness threshold=330s per PR #90 design).

4. **Validation-artifact requirement (per N-2 finding):** Operator commits the SQL output + Polygon bars + gap analysis + verdict reasoning to a new file at `trading-docs/06-tracking/T-ACT-045-validation-artifact-2026-05-XX.md` (replace XX with the validation date). Action 6 prerequisite explicitly requires this file to exist.

5. Verdict logic:
   - All rows within ±$5 → **VALIDATED**. Action 6 unblocks. Mark this T-ACT done.
   - 1+ rows deviate >$5 systematically aligned with Polygon's price 15 min earlier → **NOT-VALIDATED** — Polygon Indices Starter is empirically 15-min-delayed; operator must decide subscription upgrade ($249-299/mo Indices Advanced) or architectural rerouting (SPY×10 proxy via Stocks Advanced, real-time on equities tier).
   - Mixed signal → INVESTIGATE further; do not declare verdict until clear.

**Status:** [ ] PENDING-RE-RUN — operator action required Monday 2026-05-04 ≥10 min post-deploy

---

### T-ACT-046 — Fix silent-staleness pattern in `tradier_feed.py:282-283` AND `polygon_feed.py:174-184` (bundled — same root pattern)

**Severity:** MEDIUM (now fallback-only concern post-PR-#90 for Tradier; primary concern for Polygon SPX path until T-ACT-045 re-validates)
**Owner:** Cursor — implemented in Track B PR `docs/track-b-silent-staleness-and-governance` 2026-05-03 (Edit Group A)
**Estimated time (actual):** ~75 min Cursor (DIAGNOSE-FIRST + bundled scope + observability instrumentation)

**Description:** Both `tradier_feed.py:282-283` and `polygon_feed.py:174-184` wrote the cache timestamp using `datetime.now(timezone.utc).isoformat()` as the fallback when the upstream API response lacked an explicit timestamp. This meant downstream freshness checks based on the Redis-stored timestamp were blind to upstream-side staleness — the cache always looked "fresh" because the timestamp was stamped at write time, not at upstream-quote time. Cursor's audit identified both vectors as the same root pattern; bundled per Cursor's recommendation 2026-05-03 (subsumes the previously-proposed T-ACT-049 polygon-side fix).

**Why it matters now:** Post-PR-#90, Tradier is fallback-only for SPX. But the silent-staleness vector still affects `tradier:quotes:{SPXW…}` (option chain quotes) which remain Tradier-primary per the OPRA-exception. The Polygon-side vector affects `polygon:spx:current.fetched_at`, which is consumed by the freshness guard at `prediction_engine.run_cycle` — wall-clock-now stamping made the guard blind to upstream-Polygon delays.

**Implemented in Track B PR `docs/track-b-silent-staleness-and-governance` (2026-05-03):**

1. **`tradier_feed.py` `process_quote`:** Defensive field-name chain (F2-c): `trade_date → bid_date → ask_date → timestamp → None`. New `timestamp_source` payload field marks "upstream" vs "missing." One-time WARN log `tradier_quote_fields_observed` per process startup capturing actual field set in upstream quotes for empirical refinement of the priority chain. `__init__` adds `_quote_fields_logged: bool = False` marker.

2. **`polygon_feed.py` `_fetch_spx_price` + setex at L173-184:** F1-c side-channel — `_fetch_spx_price` extracts upstream timestamp via defensive chain (`session.last_updated → value.last_updated → result.last_updated`), normalizes via new `_normalize_polygon_timestamp` helper (handles ns/ms/s epoch + ISO 8601), stores in `self._last_spx_upstream_ts`. The setex at L173-184 reads the side-channel attribute. New `fetched_at_source` payload field marks "polygon_upstream" vs "missing." One-time WARN log `polygon_spx_snapshot_fields_observed` per process startup capturing actual field set in indices snapshot for empirical refinement. `__init__` adds `_last_spx_upstream_ts: Optional[str]` and `_spx_fields_logged: bool` markers. Side-channel cleared on fetch failure to prevent stale-ts re-use.

3. **`prediction_engine.run_cycle` freshness guard (L1192-1230, observability amendment per F6):** Existing guard already gracefully degraded on null `fetched_at` (TypeError caught by outer try/except, cycle skipped). Amendment makes the new contract explicit: distinct `spx_price_upstream_timestamp_missing` WARN log when upstream-stamped null, separate from generic `spx_freshness_check_failed`. `spx_fresh = False` semantics unchanged — conservative skip preserved.

4. **Consumer audit (DIAGNOSE 4.1, 4.2):** No Tradier-quote consumer reads `timestamp` from `tradier:quotes:*` (verified across `mark_to_market.py`, `strike_selector.py`, `strategy_selector.py`, `shadow_engine.py`, `gex_engine.py`, `prediction_engine.py`, `databento_feed.py`); blast radius is zero. Polygon-`fetched_at` has exactly one consumer (the freshness guard); blast radius is one.

**Acceptance criteria:**

- ✅ `tradier_feed.py` no longer writes wall-clock-now as a fallback timestamp.
- ✅ `polygon_feed.py` no longer writes wall-clock-now in the SPX setex.
- ✅ Freshness guard handles null `fetched_at` with conservative skip and explicit observability log.
- ✅ Defensive field-name chains + one-time observability logs land in production for empirical refinement.

**Status:** [x] DONE — implemented in Track B PR (Edit Group A complete)

**Cross-references:** HANDOFF A.5 (silent-failure family precedent — `model_source` schema/code drift), HANDOFF A.6 (Tradier sandbox SPX delay — same family, distinct surface), HANDOFF A.7 (silent-failure-class family convention pointer ratified by this PR), T-ACT-054 (sibling — same family, derived-feature surface; cv_stress NULL-on-degenerate-input remediation pending separate PR), T-ACT-047 (sibling — same family, try/except discipline mitigation)

---

### T-ACT-047 — Try/except discipline mitigation in `prediction_engine.run_cycle` (Choice C: inner-block scoped at persist site)

**Severity:** MEDIUM (silent-failure surface — closed by this PR; family A.7 fully closed)
**Owner:** Cursor — implemented 2026-05-02
**Estimated time:** 1.5-2 hours actual

**Description:** Per HANDOFF NOTE Appendix A.5 mitigation #3: the outer `try/except` in `backend/prediction_engine.py` `run_cycle()` silenced `PostgrestAPIError` and similar schema-class errors. This is the surface that hid the `model_source` bug for ~16 hours on 2026-04-30 to 2026-05-01 (PR #82 → PR #89).

Schema errors are fundamentally different from transient DB connectivity errors and should NOT be silenced by the same handler. Examples:

- Schema cache miss (PGRST204) — code-vs-DB drift; permanent until migration applied
- RLS policy violation — permission misconfiguration; permanent until fixed
- Unique constraint violation — usually a logic bug; not a transient issue
- Connection refused / timeout — transient; retry semantics appropriate

**Fix selected: Choice C — inner-block-specific try/except** (per Cursor 2026-05-02 design memo + plan review):

Wrap ONLY the supabase insert site at `prediction_engine.py:1495-1500` (post-Track B + T-ACT-054 line numbers) with a narrow `try/except PostgrestAPIError` block. Catch the persistent class via the canonical `from postgrest.exceptions import APIError as PostgrestAPIError` import. Non-postgrest exceptions fall through to the existing outer `except Exception` handler unchanged.

**Why Choice C over Choices A/B (per design memo):**

- **Choice A (class-based routing):** Requires refactoring `run_cycle` into multiple stages with class-based dispatch. Out of scope for a discipline PR; over-engineered for a single-site fix.
- **Choice B (error-class taxonomy + dispatcher):** Adds a global error-classification module. Operationally clean but reaches well beyond the A.5 incident's actual surface. Defer to v2.
- **Choice C (inner-block-specific):** Surgical scope (ONE site touched: the persist site that was the A.5 trigger). Consistent with existing inner-try patterns at L1280 (calendar fail-open), L1329-1372 (SPX freshness guard, T-ACT-046), L1389-1393 (vvix parse defensive). Clear evolution path: if more sites need the same discipline later, the pattern is already established and can be extracted to a helper.

**Per-error escalation (Choice C scope):**

| Error class | Caught at | Logged at | Health status | Alert |
|---|---|---|---|---|
| `PostgrestAPIError` (PGRST204, RLS violations, unique constraint) | NEW inner block at L1500 | WARN with structured `pgrst_code/details/hint` | `error` + `PERSISTENT[<code>]:` prefix in `last_error_message` | `alerting.send_alert(CRITICAL, ...)` with hint in body |
| `httpx.ConnectError`, `RuntimeError`, generic `Exception` | EXISTING outer block at L1518 (line shifts post-edit) | ERROR `prediction_cycle_failed` (unchanged) | `error` (no PERSISTENT prefix; unchanged) | None (unchanged — accumulated escalation via `error_count_1h` counter only) |

**Critical disciplines applied (per design memo + plan review):**

- DB `service_health.status` stays in the existing CHECK-constraint allowlist (`'healthy'/'degraded'/'error'/'offline'/'idle'`). Writing `'critical'` would violate the constraint at `supabase/migrations/20260420_add_idle_health_status.sql:11` per HANDOFF A.1 lesson. Critical severity is expressed via `alerting.send_alert(CRITICAL, ...)` channel instead.
- The `error_count_1h` auto-increment at `db.py:233-249` fires automatically when `write_health_status` is called with `status="error"`. This is the sustained-error escalation channel, independent of the per-cycle alert. Both fire together; they detect different patterns (per-cycle observability vs. accumulated-pattern escalation).
- Alert-pipeline failure must NOT mask the original error: the `send_alert(...)` call is wrapped in a defensive `try/except` that logs an `alert_failed` WARN and continues without re-raising.
- `R3 (hint in alert body):` the alert body explicitly includes `code=...`, `detail=...`, `hint=...` for operator triage. Hint is the most actionable field for schema-drift incidents (typically points at the missing column / required migration).

**Acceptance criteria:**

1. ✅ `PostgrestAPIError` is caught at the new inner block and surfaces at WARN with `event="prediction_cycle_persistent_error"` (structured `pgrst_code`, `pgrst_details`, `pgrst_hint` fields).
2. ✅ Non-postgrest exceptions fall through to the outer `except Exception` handler unchanged (verified by Tests 4a + 4b for `httpx.ConnectError` and `RuntimeError`).
3. ✅ `alerting.send_alert(CRITICAL, ...)` fires once per persistent-error cycle with code/detail/hint in the body. Defensive: alert-pipeline failure does not mask the original error.
4. ✅ `write_health_status("prediction_engine", "error", ...)` is called with `last_error_message` carrying the `PERSISTENT[<code>]:` prefix. The `error_count_1h` auto-increment at `db.py:233-249` fires on this code path (verified by db.py code-path inspection; not directly asserted in unit test since `write_health_status` is mocked).

**Status:** [x] DONE — implemented 2026-05-02 via PR `fix/t-act-047-postgrest-error-classification` (branch from main @ `575e79d` post-T-ACT-054 merge).

**Implementation summary (2026-05-02):**

*Scope:* 1 modified file (`backend/prediction_engine.py`) + 1 new test file + 3 doc updates (TASK_REGISTER, action-tracker, HANDOFF) = 5 files total. ~22 logical edits. 5 tests.

*Files modified:*

1. `backend/prediction_engine.py` — Edit Group A: hard import `from postgrest.exceptions import APIError as PostgrestAPIError` placed after the redis defensive-import try-block (F1-a per operator authorization 2026-05-02; PEP 8 third-party group alignment). Edit Group B: ~70-line `try/except PostgrestAPIError` block wrapping the supabase insert at L1495-1500 (post-edit) — extracts `code/details/hint` via `getattr`, logs WARN with structured fields (R3: hint included), calls `write_health_status` with `PERSISTENT[<code>]:` prefix (R2: comment documenting `error_count_1h` auto-increment dependency at db.py:233-249), fires `send_alert(CRITICAL, ...)` with hint in body (R3), defensively wraps the alert call so alert failure does not mask the original error, returns None.

2. `backend/tests/test_t_act_047_persistent_error_classification.py` — **NEW** — 5 tests:
   - Test 1: `test_persistent_error_logged_at_warn_with_structured_fields` — verifies WARN log fires with `event="prediction_cycle_persistent_error"`, `error_class="postgrest_api_error"`, `pgrst_code/details/hint` extracted via `getattr`, `exc_info=True`. Verifies outer ERROR log does NOT fire.
   - Test 2: `test_persistent_error_writes_health_error_with_persistent_prefix` — verifies `write_health_status("prediction_engine", "error", last_error_message="PERSISTENT[PGRST204]: ...")`. Acceptance criterion #4 (R2 dependency on db.py:233-249 documented in code comment).
   - Test 3: `test_persistent_error_fires_critical_alert_with_hint_in_body` — verifies `send_alert("critical", "prediction_engine_persistent_error", body)` with `code=...`, `detail=...`, `hint=...` in body (R3 explicit assertion).
   - Test 4a (R5 split): `test_4a_httpx_connect_error_falls_through_to_outer_except` — verifies `httpx.ConnectError` (transient network) falls through to outer `except Exception` handler (logs `prediction_cycle_failed` at ERROR, no persistent WARN, no CRITICAL alert).
   - Test 4b (R5 split): `test_4b_runtime_error_falls_through_to_outer_except` — verifies `RuntimeError` (generic) falls through identically. Confirms inner block's catch is narrowly scoped to `PostgrestAPIError`.
   - R4 tightening: `pytest.importorskip("postgrest.exceptions", reason="...")` (forward-defensive against partial-install edge case; production cost zero).

*Plan-review refinements incorporated (7 total, per Cursor's READ-ONLY plan review 2026-05-02):*

- **R1**: Canonical full path `from postgrest.exceptions import APIError as PostgrestAPIError` (rather than colloquial `PostgrestAPIError` symbol).
- **R2**: Comment above `write_health_status` call documenting the `error_count_1h` auto-increment dependency at `db.py:233-249`.
- **R3**: `hint=` field included in the alert email body (operator's most actionable field for schema-drift incidents).
- **R4 (NON-NEGOTIABLE)**: `pytest.importorskip("postgrest.exceptions", ...)` at top of test file. Tightened from `"postgrest"` per F4 (defensive against partial-install edge case).
- **R5**: Test 4 split into Test 4a (`httpx.ConnectError`) + Test 4b (`RuntimeError`). Net 5 tests.
- **R6**: Post-deploy step 0 verifies `ALERT_EMAIL` + `ALERT_GMAIL_APP_PASSWORD` env vars on Railway BEFORE any trigger. If unset, surface as separate T-ACT entry.
- **R7**: Concrete operator-facing PGRST trigger SQL + 3 deterministic expected outcomes for the supplementary email-pipeline validation path.

*DIAGNOSE-round flag resolutions (4 flags surfaced 2026-05-02):*

- **F1-a**: Postgrest import placed AFTER redis defensive try-block (PEP 8 third-party group alignment; postgrest is not stdlib).
- **F2 REFINE**: Smoke 4 uses unique outer-except marker grep (`logger\.error\("prediction_cycle_failed"`) instead of fragile line-number assertion.
- **F3 REVISE (Option C documented limitation)**: Replaced original §2.6 Step 1 manual-trigger framing (which was non-deterministic — the `output` dict at L1467-1493 contains only schema-valid columns; running `run_cycle()` manually does not produce PGRST204) with: Step 0 (env-var precondition) → Step 1 (pytest in dev/staging is the PRIMARY validation of acceptance criteria 1-4) → Step 2 (OPTIONAL operator-chosen path A passive or path B temp throwaway branch with forced wrong column name; deploys to dev/staging only, NEVER production). Cursor explicitly rejected Option B from §3.5 (feature-flag env var) as A.1-class precedent risk — shipping backdoor code into production binary violates the very discipline T-ACT-047 establishes.
- **F4 TIGHTEN**: `pytest.importorskip("postgrest.exceptions", reason="...")` (submodule-level guard) over `pytest.importorskip("postgrest", ...)` (package-level only).

**Post-deploy verification (per Cursor's revised §2.6 protocol per F3):**

- **Step 0 (PRECONDITION):** Operator confirms `ALERT_EMAIL` + `ALERT_GMAIL_APP_PASSWORD` env vars are set on Railway BEFORE any trigger. If unset, surface as separate T-ACT entry — NOT a T-ACT-047 EXECUTE blocker (the code path is correct; only the email pipeline gates on these vars).

- **Step 1 (PRIMARY VALIDATION via pytest):** In dev/staging:
   ```bash
   cd backend && PYTHONDONTWRITEBYTECODE=1 PYTHONPYCACHEPREFIX=/tmp/pyc_t_act_047 \
     .venv/bin/python -m pytest tests/test_t_act_047_persistent_error_classification.py \
     -v --tb=short
   ```
   Expected: 5/5 PASS. If 5/5 PASS, T-ACT-047 acceptance criteria #1, #2, #3, #4 are validated at the code level.

- **Step 2 (OPTIONAL SUPPLEMENTARY — email pipeline validation):** Two operator-choice paths:
   - **Path A (passive, zero code change):** Wait for an organic schema-drift incident in production. When one occurs, observe whether the email arrives within ≤5 min and contains the expected `code=...`, `detail=...`, `hint=...` fields. No timeline; depends on next real incident.
   - **Path B (active, operator-controlled temp throwaway branch):** On a throwaway branch (e.g., `verify/t-act-047-pgrst-trigger-DELETE-AFTER`), add ONE line in `run_cycle`'s `output` dict construction (e.g., `output["nonexistent_t_act_047_test_col"] = "test"`) just before the L1495 insert. Deploy to dev/staging ONLY (NEVER production). Wait for one cycle to fire (≤5 min). Verify: (1) email arrives at `ALERT_EMAIL` with subject `[CRITICAL] prediction_engine_persistent_error` and body containing `code=PGRST204`, `detail=...`, `hint=...`; (2) Railway log contains structured WARN entry with `event="prediction_cycle_persistent_error"`, `pgrst_code="PGRST204"`; (3) `trading_system_health` row for `prediction_engine` shows `status="error"`, `last_error_message` starting with `PERSISTENT[PGRST204]:`, `error_count_1h` incremented by ≥1. Delete the throwaway branch after validation. Zero production code shipped with the trigger; full reversibility.

- **Step 3 (verdict):**
   - Step 1 = 5/5 PASS → Acceptance criteria #1, #2, #3, #4 VALIDATED at code level. T-ACT-047 status → DONE.
   - Step 2 = email arrives within ≤5 min (whichever path operator chooses) → email pipeline empirically VALIDATED. Optional but recommended.
   - Step 2 NOT performed OR email does NOT arrive → surface specifically; depends on infrastructure (likely `ALERT_EMAIL` env var per Step 0). NOT a T-ACT-047 EXECUTE blocker.

**Cross-references:** HANDOFF A.5 mitigation #3 (original lesson — try/except discipline at the persist site), HANDOFF A.6 (post-mortem context), HANDOFF A.7 (silent-failure-class family convention pointer — T-ACT-047 closes the family as the 5th and final member), T-ACT-046 (sibling — same family, distinct surface — silent-staleness in feed timestamps), T-ACT-054 (sibling — same family, derived-feature surface — cv_stress NULL semantics), Cursor 2026-05-02 design memo §SQ4 (DB schema constraint vs. alert-channel separation per A.1), Cursor 2026-05-02 plan review §1.3 / §2.2 / §4.2-4.3 / §6.2-6.3 (the 7 refinements).

**Step 0 closure footnote (added 2026-05-02 via T-ACT-057 discovery):** §R6 step 0 ("verify ALERT_EMAIL + ALERT_GMAIL_APP_PASSWORD env vars are set on Railway BEFORE manual PGRST trigger") was operator-completed 2026-05-02 21:28 ET; verification surfaced that the env vars were SET but the App Password was malformed (display-format spaces; Gmail SMTP rejecting with 535). T-ACT-057 filed as discrete entry covering the partial-failure mode + 14-day production-alerting blackout. T-ACT-047 §2.6 Path B trigger validation closure: T-ACT-057 §1.2 smoke test PASSED 2026-05-02 21:52 ET (`alert_email_sent` log fired + email arrived in operator's inbox), confirming the alerting pipeline is now end-to-end functional. Discipline-meta-lesson surfaced: convention pointer ≠ exhaustive audit (the §R6 verification asked "are env vars SET" but not "are env vars CORRECTLY FORMATTED"; an exhaustive audit would have asked all three of SET / CORRECT FORMAT / END-TO-END VALIDATED). Sharpened at T-ACT-057 entry to "3-question exhaustive verification" applied to ALL infrastructure-config surfaces.

---

### T-ACT-055 — `paper_phase_criteria` upsert NOT NULL violation regression (HIGH; 2026-04-17 to 2026-05-02; 6th member of A.7 silent-failure-class family — REOPENS A.7)

- **Status:** DONE (2026-05-02)
- **Severity:** HIGH (regression — 8 of 12 GLC paper-phase criteria silently frozen at seed values for ~16 days, blocking go-live)
- **Vintage:** Regression introduced 2026-04-17 in commit `836a83c` (PR #17). NOT a long-standing bug. Same-day reversal of T-ACT-047's "A.7 FULLY CLOSED" claim from earlier on 2026-05-02.
- **Root cause:** PR #17 changed `_upsert_criterion` body from `.update(...).eq('criterion_id', X)` to `.upsert(..., on_conflict='criterion_id')`. The `paper_phase_criteria` schema requires `criterion_name TEXT NOT NULL` and `target_description TEXT NOT NULL` (per `supabase/migrations/20260417000001_paper_phase_criteria.sql:8-9`), neither of which is in the payload. PostgreSQL's INSERT-phase NOT NULL check fires with code 23502 BEFORE `ON CONFLICT` engages. The outer `try/except Exception` at the original L35-36 swallowed the failure with `logger.error("criterion_upsert_failed", ...)`, masking the silent freeze.
- **Discovery:** Operator surfaced via `criterion_upsert_failed` errors in Railway logs for GLC-001 through GLC-004 on 2026-05-02. Cursor's verification report identified all 12 GLCs were affected (not just 4) and pinpointed the regression vintage via `git log --follow` on `criteria_evaluator.py`.
- **Remediation (Choice B per design memo):** Direct revert to `.update().eq()` form + function rename `_upsert_criterion` → `_update_criterion` (semantic correctness; body uses `.update()`, not `.upsert()`) + defensive WARN log on empty `result.data` (surfaces the row-deleted edge case that `.update()` silently no-ops on). Event name `criterion_upsert_failed` preserved at the `logger.error` line for dashboard/log-search continuity (deliberate; see inline code comment in `criteria_evaluator.py`). 12 production caller sites + 6 test references renamed mechanically.
- **Acceptance criteria:**
  - [x] `_update_criterion` function uses `.update().eq()` form, NOT `.upsert(...)` — verified S4/S6/S7
  - [x] All 12 production caller sites in `criteria_evaluator.py` updated to call `_update_criterion(...)` — verified S4 (0 callable matches of old name) + S7 (12 callable matches of new name)
  - [x] All 6 test references updated; new test file has 8 tests total (3 renamed existing + 5 new) — verified S3
  - [x] HANDOFF A.7 amended to reflect REOPENED status (6 members; over-confident "FULLY CLOSED" claim preserved as discipline-meta-lesson per R6 stop-condition) — 6 amendment sites: L1253 header, L1259 claim, L1269+ member 6 append, L1285 closure verdict, L1287 ratification footer (added per F2-a), L1297 appendix footer
  - [x] `pytest backend/tests/test_criteria_evaluator.py` passes 8/8 — verified S8
- **Post-deploy verification protocol:**
  1. Confirm next nightly evaluation updates `last_evaluated_at` for all 12 GLC rows in `paper_phase_criteria`.
  2. Confirm no `criterion_upsert_failed` errors in Railway logs for ≥24h after merge.
  3. Spot-check 2-3 GLC rows: `current_value_text` reflects current data, NOT seed values.
- **Files modified:** `backend/criteria_evaluator.py`, `backend/tests/test_criteria_evaluator.py`, `trading-docs/08-planning/TASK_REGISTER.md`, `trading-docs/06-tracking/action-tracker.md`, `trading-docs/06-tracking/HANDOFF_NOTE_2026-04-28_POST_P1-3-7.md`.
- **Related entries:** T-ACT-047 (try/except discipline at `prediction_engine` persist site — same-day "FULLY CLOSED" claim was empirically over-confident; T-ACT-055 reopens A.7 as 6th member). T-ACT-056 reserved for future formal exhaustive persist-site audit before A.7 may be formally re-closed.
- **Discipline-meta-lesson:** "Convention pointer ≠ exhaustive audit." T-ACT-047 closed A.7 based on remediation of 5 known members but did not perform an exhaustive audit of all persist sites in the codebase. T-ACT-055 surfaced a 6th member (`criteria_evaluator` persist site) on the SAME DAY (2026-05-02) that was OUTSIDE T-ACT-047's audit scope and therefore not caught by the convention pointer. Future "family closed" claims must explicitly distinguish (a) convention-establishment closure (which T-ACT-047 achieved) from (b) exhaustive-audit closure (which is reserved as T-ACT-056 follow-up). Original "FULLY CLOSED" claim is preserved verbatim in HANDOFF A.7 (L1253/L1259/L1269/L1285/L1287/L1297) as discipline-meta-lesson — sanitizing it would lose the lesson.
- **Cross-references:** HANDOFF A.7 (REOPENED 2026-05-02 same-day reversal — 6th member, T-ACT-055 cited as canonical example for regression-vintage discipline applied to database-persistence surface). T-ACT-047 (sibling — same family, same surface (DB persist), but different vintage class — long-standing bug vs. regression). T-ACT-054 (sibling — same family, derived-feature surface). T-ACT-046 (sibling — same family, silent-staleness in feed timestamps). Cursor 2026-05-02 verification report (DIAGNOSE finding + git archaeology to commit 836a83c). Cursor 2026-05-02 plan review §R1-R8 (8 refinements; R3 sharpened to MEDIUM with rename, R8 reconfirmed annotation correct).

---

### T-ACT-057 — `ALERT_GMAIL_APP_PASSWORD` whitespace silent-rejection at SMTP layer (HIGH; 2026-04-19 to 2026-05-03 01:28 UTC; 7th member of A.7 silent-failure-class family — infrastructure-config surface, NEW SUBCLASS)

- **Status:** DONE-VALIDATED (env-var fix applied 2026-05-02 21:28 ET; end-to-end smoke test PASSED 2026-05-02 21:52 ET; Option B code-change PR DEFERRED to separate PR)
- **Severity:** HIGH (14-day production-alerting blackout 2026-04-19 → 2026-05-03 01:28 UTC; ALL 8 `send_alert(...)` callsites silently rejected by Gmail SMTP including 4 CRITICAL: `prediction_engine_persistent_error`, `emergency_backstop_triggered`, `prediction_watchdog_triggered`, `daily_halt_triggered`)
- **Vintage:** Long-standing infrastructure config defect — `alerting.py` introduced 2026-04-19 commit `082bdc0` ("HARD-B: External alerting via Gmail"). Operator wired Railway env vars at unspecified date during the 2026-04-19 to 2026-05-02 window; copy-pasted `ALERT_GMAIL_APP_PASSWORD` value with Google's display-format spaces (`xxxx xxxx xxxx xxxx` = 19 chars including 3 spaces).
- **Root cause:** `backend/alerting.py:170-172` calls `srv.login(config.ALERT_FROM_EMAIL, config.ALERT_GMAIL_APP_PASSWORD)` with NO whitespace stripping. Google's App Password UI displays passwords as four 4-char groups separated by spaces for readability; the actual credential is the 16-char continuous concatenation. Operators copy-pasting from the UI naturally include spaces. Gmail SMTP rejects the spaced version with `535 5.7.8 Username and Password not accepted`, raising `smtplib.SMTPAuthenticationError`, caught at `alerting.py:181-188` and logged as `alert_email_auth_failed` with hint "Check ALERT_GMAIL_APP_PASSWORD in Railway env vars. Must be a Gmail App Password, not your account password." The hint TEXT is technically correct but did not help because the operator HAD pasted a Gmail App Password — just with display-format spaces. The L82-88 silent no-op gate did NOT trip because the env var was non-empty.
- **Discovery:** Operator self-discovered 2026-05-02 21:28 ET while diagnosing why no T-ACT-047 alert validation email arrived. Inspection of Railway env var revealed display-format spaces; stripped to 16-char continuous; redeployed. Per pre-fix Railway deploy logs, the partial-failure log path `alert_email_auth_failed` was firing at ERROR level — operator hadn't filtered Railway logs for it because the convention pointer at T-ACT-047 §R6 had asked only "are env vars SET" not "are env vars CORRECTLY FORMATTED."
- **Remediation (env-var fix; operator-executed 2026-05-02 21:28 ET):** Stripped 3 display-format spaces from `ALERT_GMAIL_APP_PASSWORD` Railway env var, saved, redeployed. New container healthy at 2026-05-03 01:28:28 UTC.
- **Remediation (end-to-end smoke test; operator-executed 2026-05-02 21:52 ET):** Ran `railway shell` + `python3 -c "from alerting import send_alert, INFO; send_alert(INFO, 'test_t_act_057_validation', 'T-ACT-057 ALERT_GMAIL_APP_PASSWORD whitespace fix validation 2026-05-03 — if you receive this email the SMTP login is working.', _blocking=True); print('send_alert returned synchronously')"`. Observed: `alert_email_sent` log fired at 2026-05-03 01:52:33 UTC; email arrived in operator's inbox within typical Gmail SMTP window (~10-30 sec). End-to-end pipeline confirmed working.
- **Remediation (code-change PR; DEFERRED to separate PR):** Add `.replace(" ", "")` defensive whitespace strip at `config.py:103`. 1-line change + 2 unit tests. Prevents recurrence on App Password rotation. Provably safe (`.replace(" ", "")` on no-spaces input is a no-op; App Password format is 16-char alphanumeric continuous per Google's generation grammar, so cannot legitimately contain spaces). DEFERRED to separate PR after this governance closure PR ships; not blocking T-ACT-057 closure (env-var fix + smoke test PASS are sufficient).
- **Acceptance criteria:**
  - [x] Env-var fix applied; Railway redeployed (2026-05-03 01:28:28 UTC)
  - [x] Smoke test PASSED 2026-05-03 01:52:33 UTC (railway shell + `python3 -c "send_alert(INFO, 'test_t_act_057_validation', ..., _blocking=True)"` → `alert_email_sent` log fired + email arrived in operator's inbox)
  - [ ] Option B code-change PR (DEFERRED to separate PR; not blocking — env-var fix + smoke test are sufficient for T-ACT-057 closure)
  - [x] T-ACT-047 §R6 step 0 footnote added closing the verification gap (this PR)
- **Files modified (governance-only; this PR):** `trading-docs/08-planning/TASK_REGISTER.md` (NEW T-ACT-057 entry + T-ACT-047 step-0-closure footnote), `trading-docs/06-tracking/action-tracker.md` (NEW T-ACT-057 stub), `trading-docs/06-tracking/HANDOFF_NOTE_2026-04-28_POST_P1-3-7.md` (A.7 amendments at 6 sites). NO code changes, NO new test files.
- **Related entries:** T-ACT-047 (the trigger event for discovery — alert pipeline tested as part of Path B trigger validation; T-ACT-047 §R6 step 0 closure footnote added in this PR). T-ACT-055 (sibling — same A.7 family, REOPENED verdict from earlier 2026-05-02; T-ACT-057 expands family to 7 members, adding the third subclass). T-ACT-058 reserved for the Option B code-change PR. T-ACT-059 reserved for exhaustive-config-audit (parallel to T-ACT-056 reserved for exhaustive persist-site audit; both must complete before A.7 may be formally re-closed).
- **Cross-references:** HANDOFF A.7 (REOPENED 2026-05-02 via T-ACT-055; 2026-05-02 (same day, second expansion) further expanded to 7 members via T-ACT-057 with new "infrastructure-config silent-failure" subclass). T-ACT-056 reserved (exhaustive persist-site audit). T-ACT-059 reserved (exhaustive-config-audit). Cursor 2026-05-02 T-ACT-057 verification report §1-§5 (validation protocol + historical impact assessment + Option B code-change recommendation + disposition recommendation + A.7 amendment recommendation).
- **Discipline-meta-lesson (sharpened from T-ACT-055):** This finding is the canonical instance of "convention pointer ≠ exhaustive audit" predicted at T-ACT-055. T-ACT-047 §R6 asked operator to verify env vars were SET — a convention-pointer-style verification. An exhaustive audit would have asked: SET, of CORRECT FORMAT, AND end-to-end SMTP login validated. The convention pointer caught 1 of 3. **Sharpened discipline-meta-lesson: "3-question exhaustive verification (SET / CORRECT FORMAT / END-TO-END VALIDATED) must be applied to ALL infrastructure-config surfaces"**, not just code/data semantics ones. Future similar verifications must ask all three questions explicitly.
- **Sub-class designation:** **Infrastructure-config silent-failure surface** — third subclass of A.7 family (alongside derived-feature surface from T-ACT-054/A.5/A.6/T-ACT-046, and database-persistence surface from T-ACT-047/T-ACT-055). Subclass scope: env vars, secrets, deploy config, Railway/Supabase/external-service configuration where format-incorrect input gets accepted at the load layer but rejected at the use layer with the rejection caught/swallowed/logged-only-at-low-priority. T-ACT-059 reserved for exhaustive-config-audit before A.7 may be formally re-closed.

---

### T-ACT-048 — SUBSCRIPTION_REGISTRY.md + `prediction_engine.py` docstring corrections (doc-only)

**Severity:** LOW (documentation discipline)
**Owner:** Cursor — partially implemented in Track B PR (docstring fix per Edit Group B); SUBSCRIPTION_REGISTRY row addition deferred to a separate doc-only PR
**Estimated time:** 30 min total; ~10 min remaining

**Description:** Two related doc-discipline issues surfaced in Cursor's audit on 2026-05-03 morning:

- `SUBSCRIPTION_REGISTRY.md` is missing a row for Polygon Indices Starter ($49/mo) — registry-vs-runtime drift surfaced by HANDOFF A.6 mitigation #2 (subscription-vs-runtime audit).
- `backend/prediction_engine.py:425-432` docstring incorrectly cited "Polygon Stocks Advanced" subscription for I:SPX recency. The `/v3/snapshot?ticker.any_of=I:SPX` endpoint is served by Polygon Indices product line, not Stocks Advanced (different products).

**Status this PR:** Docstring fix implemented as Track B Edit Group B. SUBSCRIPTION_REGISTRY row addition deferred — when added, must reflect Cursor's recommendation that recency-class is empirically TBD pending T-ACT-045 re-run, NOT the false claim of "real-time confirmed."

**Acceptance criteria:**

- ✅ `prediction_engine.py:425-432` docstring updated (Track B PR, 2026-05-03)
- [ ] `SUBSCRIPTION_REGISTRY.md` gains row for Polygon Indices Starter $49/mo with recency note "TBD pending T-ACT-045 re-run; per Polygon published policy 15-min delayed for I:* indices, but `/v3/snapshot` may serve real-time despite policy"
- [ ] No false "verified real-time" claims committed to the registry

**Status:** [x] Docstring fix DONE (Track B PR); [ ] SUBSCRIPTION_REGISTRY row addition PENDING (separate doc-only PR or bundled with cv_stress remediation PR)

**Status amendment (2026-05-02 night via T-ACT-050 PR closure):** Acceptance criterion #2 (`SUBSCRIPTION_REGISTRY.md` gains row for Polygon Indices Starter $49/mo) NOW CLOSED via T-ACT-050 PR Edit Group C.2 — row added at `SUBSCRIPTION_REGISTRY.md` §1 row 8 with recency note pending T-ACT-045 Monday re-run. T-ACT-048 fully closed.

---

### T-ACT-050 — Polygon Stocks Advanced ($199/mo) underutilization audit

**Severity:** LOW (cost optimization; -$149/mo savings identified)
**Owner:** Operator (audit DONE 2026-05-02 night; downgrade execution DEFERRED Monday 2026-05-04 post-T-ACT-045)
**Estimated time:** ~20 min audit (DONE); ~15 min Polygon dashboard subscription change Monday post-T-ACT-045 closure

**Description:** Cursor's morning audit (S-7) initially identified that Polygon Stocks Advanced ($199/mo) is consumed primarily by the Polygon News bundle in production code; no equity quotes (SPY/HYG/TLT/DXY) appear to be consumed in the live decision path. **2026-05-02 night operator audit + Cursor's 10-callsite codebase analysis sharpened the finding:** ZERO Polygon News API calls anywhere in `backend/`; ZERO equity/ETF/options API calls; the codebase consumes ONLY CBOE indices (`I:SPX`, `I:VIX`, `I:VVIX`, `I:VIX9D`) via `/v3/snapshot` + `/v2/aggs/ticker/I:.../range/...` endpoints. These index endpoints are served by Polygon's Indices product line, not Stocks Advanced (different products). Stocks Advanced was overprovisioned for actual usage.

**Audit findings (2026-05-02 night):**

- **Current Polygon subscriptions on operator's account (verified via Polygon dashboard):**
  - Polygon Stocks Advanced: $199/mo (real-time indices included; current path for live decision)
  - Polygon Options Developer: $79/mo (15-min delayed quotes; historical/reference layer; NOT in live decision path)
  - Polygon Indices Starter: $49/mo (15-min delayed)
  - Subtotal Polygon: $327/mo

- **Polygon Indices product line tiers (verified via Polygon dashboard):**
  - Basic: $0/mo — 15-min delayed
  - Starter: $49/mo — 15-min delayed (current operator subscription)
  - **Advanced: $99/mo — REAL-TIME** ← target replacement tier

- **Codebase consumer analysis (Cursor 2026-05-02 verification report Task C):**
  - 10 Polygon API consumer sites in `backend/`; ALL use `I:` prefix (CBOE indices) ONLY
  - Tickers consumed: `I:SPX`, `I:VIX`, `I:VVIX`, `I:VIX9D`
  - Endpoints: `/v3/snapshot` (real-time index reads) + `/v2/aggs/ticker/I:.../range/...` (historical aggregates)
  - ZERO stocks, ZERO ETFs, ZERO options API, ZERO Polygon News API calls

- **Critical finding — hidden double-pay:** Operator is currently paying for BOTH Stocks Advanced ($199/mo, includes real-time indices) AND Indices Starter ($49/mo, 15-min delayed). The Indices Starter subscription provides nothing the Stocks Advanced doesn't already cover (and at lower fidelity). The two subscriptions overlap on indices coverage with no incremental value from Indices Starter.

- **Optimal restructure (Scenario Z):**
  - CANCEL: Stocks Advanced ($199/mo) + Indices Starter ($49/mo) = -$248/mo
  - ADD: Indices Advanced ($99/mo) = +$99/mo
  - **Net savings: $149/mo = $1,788/yr**

- **Why this is safe:**
  1. Indices Advanced covers 100% of actual codebase usage (all I:* tickers, both endpoints)
  2. Real-time preserved (Indices Advanced serves real-time same as Stocks Advanced for indices)
  3. No code changes required (same endpoint URLs, same API key flow)
  4. Eliminates the redundant Indices Starter line item

- **Forward-coverage trade-offs (acceptable):**
  - LOSE Polygon News bundle (Item 15A) → NewsAPI.org free tier provides redundant coverage; Item 15A activation 90+ days out per `AI_BUILD_ROADMAP.md` §6
  - LOSE cross-asset HYG/TLT/DXY (Item 15D) → un-defer eligibility 120+ days out per `AI_BUILD_ROADMAP.md` §6; re-upgrade-when-needed pattern
  - LOSE Stocks endpoints (`/v2/aggs/ticker/AAPL`, etc.) → not consumed in codebase; no functional impact

**Why downgrade execution is DEFERRED to Monday (per discipline recommendation):**

Per Cursor's earlier T-ACT-050 verification round: operator delays the actual subscription change until after T-ACT-045 Monday closure to avoid compounding capability changes with active validation work. T-ACT-045 (Monday RTH actual re-run, post-PR-#90 deploy) validates whether Polygon real-time data is reaching the system. If subscription change happens BEFORE T-ACT-045, two capability changes compound (subscription/account-level + already-deployed PR #90 architectural fix). If T-ACT-045 fails Monday, bug attribution is murky — was it PR #90 not working OR was it the new subscription serving stale data? Better: complete T-ACT-045 first, then change subscription with clean attribution if anything goes wrong post-change.

**Sequence:**

1. **Tonight (this PR):** Document audit findings; update SUBSCRIPTION_REGISTRY; status = CONDITIONALLY-CLOSED-DOWNGRADE-DEFERRED-MONDAY
2. **Monday RTH:** Execute T-ACT-045 actual re-run
3. **After T-ACT-045 = VALIDATED:** Operator pulls trigger on Polygon subscription restructure; brief HANDOFF amendment captures the actual change date + verifies real-time still works post-change
4. **If T-ACT-045 fails:** Subscription restructure stays parked until T-ACT-045 closes (one capability change at a time)

**Acceptance criteria:**

- [x] Operator verified Polygon News is NOT the SOLE consumer (correction to original AC #1 — News not consumed at all per codebase audit; News-only-tier framing was irrelevant; revised finding: Indices Advanced is the optimal target)
- [x] Operator identified Polygon Indices product tier table (Basic $0 / Starter $49 / Advanced $99 with real-time)
- [x] Operator confirmed Items 15A/15D 90-120+ day activation timeline; re-upgrade-when-needed pattern acceptable
- [/] Operator decision documented in `SUBSCRIPTION_REGISTRY.md` §1 (this PR Edit Groups C.1/C.2/C.3 + §3 Items 15A/15D forward-coverage notes via D.1/D.2) — pending downgrade execution Monday
- [ ] DEFERRED to Monday: actual subscription change on Polygon dashboard (operator action; not in this PR scope per §1.4 sequencing)

**Post-Monday operator action items:**

After T-ACT-045 = VALIDATED Monday:

1. Cancel Polygon Stocks Advanced ($199/mo)
2. Cancel Polygon Indices Starter ($49/mo)
3. Subscribe to Polygon Indices Advanced ($99/mo)
4. Verify real-time `/v3/snapshot` still works post-change (one-shot test query — `python3 -c "from polygon_feed import _fetch_index_snapshot; print(_fetch_index_snapshot('I:SPX'))"` or equivalent; confirm `last_updated` timestamp is recent, NOT 15-min stale)
5. Brief HANDOFF amendment capturing actual change date + verification result + post-restructure state in SUBSCRIPTION_REGISTRY (§1 Stocks Advanced row strikethrough + Indices Advanced row promoted from "TARGET" to active + §1 Total math reconciliation + §10 Summary list update)

**Status:** [/] CONDITIONALLY-CLOSED-DOWNGRADE-DEFERRED-MONDAY (audit complete 2026-05-02 night; downgrade execution gated on T-ACT-045 Monday closure)

**Cross-references:** T-ACT-045 (Monday gating dependency — actual re-run validates Polygon real-time reaches system before subscription change). T-ACT-048 (partial-PARTIAL closure — `SUBSCRIPTION_REGISTRY.md` Indices Starter $49/mo row added in this PR via Edit Group C.2, closing T-ACT-048 acceptance criterion #2 opportunistically). HANDOFF A.6 mitigation #2 (subscription-vs-runtime audit precedent — same discipline class as T-ACT-050 Polygon-line-items audit). Cursor 2026-05-02 verification report Task C (10-callsite codebase analysis confirming I:* indices only; zero Polygon News API consumption).

---

### T-ACT-051 — Consolidate duplicate I:SPX direct fetches (DEFERRED)

**Severity:** LOW (code hygiene)
**Owner:** Cursor (when next file-touch trigger occurs)
**Estimated time:** ~30 min

**Description:** `backend/counterfactual_engine.py:61` and `backend/model_retraining.py:118` both directly hit Polygon `/v2/aggs/ticker/I:SPX/range/1/minute` aggregates. Neither is in the live decision path (counterfactual is post-trade analysis; retraining is offline). Consolidation into a shared helper would reduce the redundant API call surface and make future endpoint changes single-touch.

**Acceptance criteria:** Single shared helper used by both call sites; behavior identical for both consumers.

**Status:** [ ] DEFERRED — not blocking. Defer until next file-touch on either site.

---

### T-ACT-054 — Investigate and fix `charm_velocity` / `vanna_velocity` / `cv_stress_score` silent-zero pattern (Choice A: NULL-on-degenerate-input)

**Severity:** MEDIUM (silent-failure-class; same family as A.5, A.6, T-ACT-046)
**Owner:** Cursor (separate follow-up PR after Track B merges)
**Estimated time:** 2-3 hours including DIAGNOSE-FIRST + ~3 consumer patches + tests

**Description:** Empirical confirmation 2026-05-03 (per disambiguating SQL run after Cursor's first-pass review): 103 of 353 cycles (~29.2%) in the last 7 days persisted exact-zero `cv_stress_score`, `charm_velocity`, `vanna_velocity` due to degenerate inputs (`vvix_z=0` AND `gex_conf=1.0`). The formula at `prediction_engine.py:691-694` correctly translates these inputs to zero, but downstream consumers cannot distinguish "real no-stress signal" from "missing/saturated input artifact."

**Active downstream consumers (verified 2026-05-03):**

1. `prediction_engine.py:1008` — `if cv_stress > 85: no_trade("cv_stress_critical")` — emergency no-trade gate (active in all paths).
2. `strategy_selector.py:176` — `if cv_stress > 70: long_gamma_only` — defensive strategy override (active in all paths).
3. `prediction_engine.py:938/949` — rule-based direction tilt (DORMANT when LightGBM v1 is loaded; active only if model unavailable).

When `cv_stress` is silently 0, the system loses (a) emergency stop, (b) defensive strategy override; the rule-based tilt is also silenced but is dormant in normal operation. **Live ROI clamp footprint is the 2 active consumers, not 4** (per Cursor design memo §6.1 correction).

**Root cause (Hypothesis E, locked 2026-05-03):**

- `gex:confidence` saturates at exactly `1.0` via `min(1.0, len(trades)/1000)` at `gex_engine.py:175` whenever OPRA flow exceeds 1000 trades/5min — normal RTH steady-state for SPX options.
- `polygon:vvix:z_score` resolves to `0.0` in `_compute_cv_stress` whenever (a) the key is absent and the default `"0.0"` cast fires, OR (b) `polygon_feed._compute_vvix_baseline` writes literal `"0.0"` because `pstdev(self.history) == 0` (warmup or flat VVIX). VVIX history is in-memory only with no daily-aggregate seed (asymmetric with VIX); cold-start warmup is **20 polls × 300s = 100 min** per Polygon feed restart (per Cursor design memo §6.2 correction; earlier "~25 min" framing was wrong).

**Remediation: Choice A — NULL-on-degenerate-input** (selected per Cursor design memo 2026-05-03):

1. Modify `_compute_cv_stress` at `prediction_engine.py:674-700` to detect degenerate inputs (`baseline_ready=False` OR `vvix_z_raw is None` OR `gex_conf == 1.0`) and return `{"cv_stress_score": None, "charm_velocity": None, "vanna_velocity": None}` instead of computing arithmetic on degenerate inputs.
2. Patch the 2 active downstream consumers (`prediction_engine.py:1008` and `strategy_selector.py:176`) AND the dormant rule-based tilt at `prediction_engine.py:938/949` to handle `None` cv_stress conservatively: `if cv_stress is not None and cv_stress > 70:` (or 85). NULL semantics: skip the cycle's branch with a structured log entry.
3. Add tests verifying NULL semantics across the 3 consumer paths.
4. Verify any audit/monitoring SQL queries do not break under NULL semantics (none identified in 2026-05-03 audit; verify before ship).

**Choice rationale:** Choice A fully restores all 3 downstream cv_stress safety gates across the 103-row population. Choice B (warmup gate) only handles warmup-and-missing-key subset; zero-variance subset remains broken. Choice C (formula redesign) is correct as Phase-4 follow-up after operator+analyst design call but does not on its own address missing-VVIX cases. See cv_stress design memo (Cursor 2026-05-03) §3 for full reasoning.

**Acceptance criteria:**

1. `_compute_cv_stress` returns NULL triple under degenerate inputs (verified by unit test).
2. All 3 active+dormant consumers handle NULL gracefully with structured log + skip-branch behavior.
3. After merge + 7 days of cycles: re-run the disambiguating SQL; the `both_at_extremes ≈ triple_zeros` pattern should disappear (replaced by NULL rows where degenerate inputs occurred).
4. Action 6 not affected by this T-ACT (cv_stress is independent of T-ACT-045 SPX delay question).

**Status:** [x] DONE — implemented 2026-05-02 via PR `fix/t-act-054-cv-stress-null-on-degenerate` (branch from main @ `e887c39` post-Track B merge).

**Implementation summary (2026-05-02):**

*Scope:* 8 modified files + 1 new test file = 9 files total. ~17-18 logical edits. 14 tests.

*Files modified:*

1. `backend/prediction_engine.py` — `__init__` instance marker (`_cv_stress_degenerate_logged`); `_compute_cv_stress` rewritten with **AND-logic degenerate-input gate** (vvix_z_degenerate AND gex_conf_degenerate; OR-logic was a critical defect identified in plan review — gex_conf=1.0 is normal RTH steady-state); `_compute_direction` and `_evaluate_no_trade` signatures updated to `cv_stress: Optional[float]`; consumer guards at L1050/L1061/L1120 patched with `is not None`.
2. `backend/strategy_selector.py` — `__init__` instance marker (`_strategy_selector_null_cv_stress_logged`); `_stage0_time_gate` and `_check_time_window` signatures updated to `cv_stress: Optional[float]` (`_check_time_window` default now `None`); long-gamma override patched with `is not None`; propagation site (formerly L994) preserves None and emits one-time INFO log on first observation.
3. `backend/position_monitor.py` — D-017 cv_stress exit gate (formerly L773-778) patched: dropped `or 0.0` coercion (preserves NULL contract end-to-end) + added `is not None` guard. Conservative semantics: do NOT exit on absence-of-signal.
4. `backend/model_retraining.py` — Meta-3 NaN sentinel applied at training site (formerly L817) and champion-challenger `_row_to_features` (formerly L1071); feature-contract docstring (L727-733) updated with full Meta-3 lockstep contract.
5. `backend/execution_engine.py` — Meta-3 NaN sentinel at meta-label inference (formerly L388); `current_cv_stress` propagation patched (dropped `0.0` default, preserves None into position dict); `entry_cv_stress` site augmented with documenting comment.
6. `tests/test_t_act_054_cv_stress_null_semantics.py` — **NEW** — 14 tests covering AND-logic gate correctness (including critical regression test `test_gex_saturation_alone_does_not_null_cv_stress`), NULL contract preservation, NaN sentinel propagation in 3 lockstep meta-label sites, type contract, healthy paths, direct consumer NULL handling, D-017 exit, propagation/integration, calibration engine NULL-aware behavior, and meta-label NaN sentinel training/inference.

*Schema verification:* All 8 affected DB columns confirmed NULL-permissive in `supabase/migrations/20260416172751_*.sql` (`trading_prediction_outputs.cv_stress_score / charm_velocity / vanna_velocity`, `trading_positions.entry_cv_stress / current_cv_stress`, `trading_calibration_log.cv_stress_score / charm_velocity / vanna_velocity`). NO migration required.

*Plan-review modifications incorporated (10 total, all from Cursor's READ-ONLY review of Claude's draft plan):*

1. **CRITICAL** — AND-logic degenerate gate (replaced Claude's OR-logic which would have NULLed majority of healthy RTH cycles).
2. Added missing D-017 consumer (`position_monitor.py`) — Claude's plan missed this active production gate.
3. Adopted Meta-3 NaN sentinel (vs. Claude's Meta-2 row-filter); preserves training data volume and leverages LightGBM native missing-value handling.
4-6. Three propagation-boundary silent-coercion fixes (`strategy_selector.py:994`, `execution_engine.py:463`, `position_monitor.py:773`).
7. File path attribution fix (Claude cited `prediction_engine.py:449/463` which are actually in `execution_engine.py`).
8. Test surface expanded from 5 → 14 (added regression test for AND-logic that would have caught the OR-logic defect).
9-10. Added 3 type-signature updates flagged as F1/F2/F3 in DIAGNOSE round (`_evaluate_no_trade`, `_stage0_time_gate`, `_check_time_window`) for full NULL-contract type-system consistency.

**Post-deploy verification (operator action, ≥7 days post-merge):**

1. Re-run the disambiguating SQL from cv_stress design memo §3 — the `both_at_extremes ≈ triple_zeros` pattern should be replaced by NULL rows in `trading_prediction_outputs` where degenerate inputs occurred.
2. Verify `cv_stress_degenerate_first_cycle` INFO log appears once per `prediction_engine` process restart in production logs.
3. Verify `strategy_selector_observed_null_cv_stress` INFO log appears once per `strategy_selector` process restart when degenerate cycles propagate.
4. Confirm meta-label retrain (auto-triggered after ≥7 days of NULL/NaN-bearing data accumulates) produces a model with non-trivial split on the cv_stress NaN-missing direction.
5. Verify D-017 exit fires correctly in cycles where `current_cv_stress` is genuinely > 70 (NOT silently disabled when None).

**Cross-references:** HANDOFF A.5 (precedent — same silent-failure class), HANDOFF A.7 (silent-failure-class family convention pointer ratified by Track B PR; T-ACT-054 implementation now serves as the canonical example for derived-feature surface), T-ACT-046 (sibling — same family, distinct surface — silent-staleness in feed timestamps; bundled tradier+polygon fixes), T-ACT-047 (sibling — same family, try/except discipline)

---

### T-ACT-061 — Polygon Indices subscription upgrade Starter→Advanced (post-incident closure of 2026-05-01 → 2026-05-04 prediction outage)

**Severity:** HIGH (operationally critical — 76-hour zero-prediction outage; loss of training data; lessons-learned ratified in HANDOFF A.8)
**Owner:** Operator (subscription change executed 2026-05-04 evening); Cursor (governance closure this PR)
**Estimated time:** 0 (operator action complete); pending §7.1 probe verification

**Description:** Operator upgraded Polygon Indices subscription from **Starter $49/m** (15-min delayed indices) → **Indices Advanced $99/m** (real-time indices) on 2026-05-04 evening. The upgrade resolves the structural cause of the 2026-05-01 15:55 ET → 2026-05-04 PM prediction outage diagnosed in `trading-docs/06-tracking/HANDOFF_NOTE_2026-05-04_INDICES_OUTAGE.md`: Indices Starter's 15-min delay was correctly rejected by the codebase's 330s freshness guard at `prediction_engine.py:1366/1373`, producing `spx_price_stale_or_unavailable` early-return on every RTH cron cycle. Outage trigger was PR #92 (T-ACT-046, 2026-05-02 12:00 ET) flipping `polygon:spx:current.fetched_at` from `datetime.now(utc)` (wall-clock-now) to upstream Polygon timestamp via `_normalize_polygon_timestamp` — the change made the structural 15-min delay visible to the guard, where pre-PR-#92 the wall-clock-now stamp had silently masked it.

**Operator action taken (DONE 2026-05-04 evening):**
1. Polygon billing dashboard: cancel Indices Starter subscription.
2. Polygon billing dashboard: subscribe Indices Advanced ($99/mo).
3. Confirm dashboard "Subscribed" state for Indices Advanced (operator confirmed).

**Verification gate (pending operator action — RTH window, ideally Tuesday 2026-05-05 ~10:00 ET if not Monday evening):**

§7.1 manual API probe from `HANDOFF_NOTE_2026-05-04_INDICES_OUTAGE.md`:

```bash
curl -sH "Authorization: Bearer ${POLYGON_API_KEY}" \
  "https://api.polygon.io/v3/snapshot?ticker.any_of=I:SPX" \
  | python3 -c '
import json, sys, time
data = json.load(sys.stdin)
r = data["results"][0]
session = r.get("session", {})
last_upd = session.get("last_updated")
now_ns   = time.time_ns()
if last_upd:
    age_s = (now_ns - last_upd) / 1e9
    print(f"session.last_updated = {last_upd} (age: {age_s:.1f}s = {age_s/60:.1f} min)")
print(f"session keys: {sorted(session.keys())}")
print(f"result keys:  {sorted(r.keys())}")
print(f"close:        {session.get(\"close\")}")'
```

**Expected outcome (CONFIRMS upgrade efficacy + closes T-ACT-061):** `age_seconds < 60s` during RTH.
**Refutation outcome (BLOCKS T-ACT-061 closure):** `age_seconds > 800s` — would indicate (a) dashboard upgrade has not propagated to API entitlement, (b) different code-path bug, or (c) tier description mismatch; requires additional diagnosis before closure.

**Acceptance criteria:**
1. §7.1 probe shows `age_seconds < 60s` during RTH (operator-executed).
2. First successful post-upgrade RTH prediction cycle writes a row to `trading_prediction_outputs` (verifiable via Supabase SQL: `SELECT MAX(created_at) FROM trading_prediction_outputs WHERE created_at > '2026-05-04 12:00:00'::timestamptz;` returning a timestamp post-Monday-RTH-open; current state shows max rows from 2026-05-01 15:55 ET).
3. SUBSCRIPTION_REGISTRY.md §1 reflects Indices Starter cancelled + Indices Advanced active (DONE in this PR).
4. HANDOFF NOTE A.8 lessons-learned entry ratified (DONE in this PR).
5. `HANDOFF_NOTE_2026-05-04_INDICES_OUTAGE.md` relocated to `trading-docs/06-tracking/` (DONE in this PR).

**Status:** [~] PENDING-VERIFICATION — operator subscription change DONE 2026-05-04 evening; awaiting §7.1 probe + first post-upgrade prediction cycle write. Will close to [x] DONE on operator confirmation (next session) of probe `age_seconds < 60s` AND first successful prediction write post-2026-05-04 evening.

**Files modified (governance-only; this PR `docs/post-incident-indices-advanced-2026-05-04`):**
- `trading-docs/08-planning/SUBSCRIPTION_REGISTRY.md` — §1 row 8 marked CANCELLED, row 9 flipped to ACTIVE with Non-pros only restriction; new §1A tier comparison matrix; §1 monthly burn updated; §5 forward-looking entry expanded; §10 summary updated.
- `trading-docs/08-planning/TASK_REGISTER.md` — this entry T-ACT-061 + sibling entries T-ACT-062/063/064.
- `trading-docs/06-tracking/HANDOFF_NOTE_2026-04-28_POST_P1-3-7.md` — Appendix A.8 added (lessons-learned for the outage).
- `trading-docs/06-tracking/HANDOFF_NOTE_2026-05-04_INDICES_OUTAGE.md` — relocated from repo root + post-script appended (operator action + closure cross-references).

**Cross-references:** HANDOFF A.8 (canonical lessons-learned for the 2026-05-04 outage; subscription tier mismatch outage). T-ACT-046 (PR #92 — outage trigger, fixed silent-staleness in `polygon_feed.py` `fetched_at`; correct fix that exposed the underlying tier mismatch). T-ACT-045 (operator-pending Monday re-run; original diagnostic context). T-ACT-050 (sibling — Polygon Stocks Advanced underutilization audit; full restructure to cancel Stocks Advanced still pending separate operator decision after T-ACT-061 verification). T-ACT-062 (sibling — VVIX/VIX/VIX9D freshness guard + 330s constant extraction; queued post-T-ACT-061-verification). T-ACT-063 (sibling — email egress investigation). T-ACT-064 (sibling — post-upgrade retraining decision tracking). HANDOFF NOTE 2026-05-04 §7.1 (the manual API probe defining the verification gate).

---

### T-ACT-062 — VVIX / VIX / VIX9D freshness guard + extract 330s constant to module-level (post-T-ACT-061-verification follow-up)

**Severity:** MEDIUM (silent-staleness-class; same A.7 family, derived-feature/feed surface; was a contributor to the 2026-05-04 outage diagnosis surface area but not the trigger)
**Owner:** Cursor (separate PR after operator confirms T-ACT-061 §7.1 probe + first post-upgrade prediction cycle)
**Estimated time:** medium — ~150-250 lines, 3-5 files; DIAGNOSE-FIRST + plan-review + EXECUTE

**Description:** Mirror the SPX freshness pattern (introduced in PR #90 / T-ACT-045 + made truthful in PR #92 / T-ACT-046) for the remaining three Polygon index feeds: VVIX, VIX, VIX9D. Currently `polygon_feed.py` writes these as raw float strings to Redis (`polygon:vvix:current` / `polygon:vix:current` / `polygon:vix9d:current` per L130-132 / L152-156 — actual line numbers must be re-verified at DIAGNOSE-time as the file evolves) with no JSON envelope, no `fetched_at`, no `fetched_at_source`, no `source` field. Consumer-side derived features (`vvix_z_score`, `vvix_close`, `vix_term_ratio` and the cv_stress family at `prediction_engine.py:691-694`) compute on these raw floats with NO freshness guard.

Pre-T-ACT-061 (Indices Starter era): all three feeds were silently 15-min stale every cycle (same structural cause as the SPX outage). Post-T-ACT-061 (Indices Advanced era): all three feeds should be real-time, but absence of a guard means no defensive coverage against future Polygon hiccups, parsing regressions, or accidental subscription downgrade. Likely contributor to the Sunday 2026-05-03 accuracy investigation findings (`vvix_z_score`, `vvix_close`, `vix_term_ratio` features derived from 15-min-delayed data during much of the LightGBM training window — see T-ACT-064 for retraining decision tracking).

**Scope (refined at DIAGNOSE-time before EXECUTE):**

1. **Producer side (`backend/polygon_feed.py`):** Convert VVIX / VIX / VIX9D Redis writes from raw float strings to JSON payloads matching the SPX pattern post-PR-#92: `{"price": <float>, "fetched_at": <ISO8601>, "fetched_at_source": "polygon_session_last_updated" | "wall_clock_fallback", "source": "polygon_v3_snapshot"}`. Use the `_normalize_polygon_timestamp` helper introduced in PR #92 to derive `fetched_at` from the upstream Polygon `session.last_updated` field (with defensive null-sentinel fallback per HANDOFF A.7 contract).

2. **Consumer side (`backend/prediction_engine.py` and any other VVIX/VIX/VIX9D readers — re-grep at DIAGNOSE-time):** Add freshness checks mirroring SPX guard at L1366/1373. Skip cycle (or branch with conservative semantics) on stale-or-missing data with structured WARN log naming the field.

3. **Constant extraction:** Replace inline `330` literal at `prediction_engine.py:1366` and `:1373` (line numbers as of HANDOFF A.8 timestamp; re-verify at DIAGNOSE-time) with module-level constant `POLYGON_FRESHNESS_THRESHOLD_SECONDS = 330`. Reuse for SPX + VIX + VVIX + VIX9D guards introduced in this T-ACT. Eliminates the drift-between-comparison-and-log-message future-bug-class noted in `HANDOFF_NOTE_2026-05-04_INDICES_OUTAGE.md` §8.3.

4. **Tests:** Unit tests for new VVIX/VIX/VIX9D guards (one happy-path, one stale-input-skip, one missing-input-skip per feed). Per-feed verification that `_normalize_polygon_timestamp` is correctly invoked.

**Pre-conditions / gating (HARD GATE — do NOT start before these are met):**
1. T-ACT-061 §7.1 probe confirms `age_seconds < 60s` for `I:SPX` post-upgrade (operator action).
2. First successful post-upgrade RTH prediction cycle writes a row to `trading_prediction_outputs` (Supabase SQL verification).
3. Operator approval to proceed (since this is the FIRST code change touching `polygon_feed.py` after the 2026-05-04 outage; defensive operator-confirmation step prevents compounding capability changes per the same discipline as T-ACT-050's Monday-after-T-ACT-045 gating).

**Acceptance criteria:**
1. All four index feeds (SPX, VIX, VVIX, VIX9D) write JSON envelopes with consistent `fetched_at`/`fetched_at_source`/`source` fields.
2. Consumer-side freshness guards in place at all derived-feature compute sites.
3. `POLYGON_FRESHNESS_THRESHOLD_SECONDS = 330` extracted to module-level; all four guards reference it (no inline literals).
4. Test surface: ≥6 unit tests (1 happy + 2 skip per feed × 3 feeds).
5. After 7 days post-merge: re-run accuracy investigation SQL; no `*_stale_or_unavailable` patterns observed during RTH on any index feed.

**Status:** [x] DONE — shipped 2026-05-04 evening via PR `feat/t-act-062-vix-vvix-freshness-guard` (commit hash recorded post-merge).

**Design decisions resolved at DIAGNOSE-time (2026-05-04 evening):**

- **SD-1 (BLOCKING — gating semantic, operator decision):** Hard-gating VIX/VVIX/VIX9D would have been a behavioural regression — all three feeds today have graceful default semantics at every consumer site (e.g. ``float(_read_redis(...) or "18.0")``). Hard-gate would have starved cycles where they previously proceeded with a slightly stale value. Operator selected **Option β `beta_hard_spx_only_soft_others`**: hard-gate SPX only (preserves existing T-ACT-046 contract); soft-warn VIX/VVIX/VIX9D when stale. WARN log keys (``vix_price_stale`` / ``vvix_price_stale`` / ``vix9d_price_stale``) are the telemetry consumed by **T-ACT-065** for a 7-day evaluation window (due 2026-05-12) deciding whether to flip to hard-gate.

- **SD-2 (Empirical risk — operator probe):** Real-time delivery for VIX/VVIX/VIX9D on Indices Advanced was unverified at DIAGNOSE-time. Operator selected **probe before merge**: ran §7.1-style curl probes for I:VIX, I:VVIX, I:VIX9D and confirmed all three are real-time post-2026-05-04 evening upgrade — `last_updated` ages of ~5-7 minutes (post-close), explicit `timeframe: "REAL-TIME"` field present at every result level, response shape matches SPX. Decision matrix output: **Pattern A (all feeds real-time)** — proceed with Option β as planned. No follow-up tier-mismatch investigation T-ACT needed.

- **SD-3 (informational — constants location):** ``backend/constants.py`` does not exist in the repo. Default selected: place the new ``POLYGON_FRESHNESS_THRESHOLD_SECONDS = 330`` constant at module level inside ``backend/prediction_engine.py`` adjacent to the existing ``_safe_float`` and ``_is_market_hours`` helpers — same convention as the surrounding code.

- **SD-4 (informational — scope refinement):** initial estimate (60-90 min / 150-250 lines, 3-5 files) was revised at DIAGNOSE-time after surfacing 13 production consumer sites + 13 test files. Actual delivered scope: ~370 lines net additions across **13 files** (1 new module ``backend/polygon_index_helpers.py`` (89 lines); 8 production files modified; 1 new test file ``backend/tests/test_t_act_062_freshness_guard.py`` (19 tests, ~330 lines); 1 brittle existing test ``test_consolidation_s5.py::test_vvix_writes_use_setex_not_bare_set`` updated to a regex-tolerant assertion to accept the multi-line setex form post-rewrite; 2 docs files: this TASK_REGISTER amendment + footer).

- **SD-5 (self-amendment of T-ACT-062 entry):** the T-ACT-062 entry shipped in PR #100 explicitly gated this work on the T-ACT-061 §7.1 probe + first post-upgrade prediction cycle. The 2026-05-04 evening operator instruction explicitly waived that gate ("Independent of: the SPX subscription verification probe") on the basis that the SPX probe results were already in hand and the §1A tier comparison matrix in SUBSCRIPTION_REGISTRY.md confirmed the upgrade had landed. Recorded here so the audit trail is complete: **gate waived per operator instruction 2026-05-04 evening; new semantic = "ship after empirical VIX/VVIX/VIX9D probe confirms Pattern A"** (which it did, per SD-2).

- **Optional enhancement (operator's belt-and-suspenders note):** included `polygon_tier_mismatch` once-per-process detector in ``polygon_feed._extract_index_upstream_ts``. Fires a single WARN per feed per process if `result.timeframe` is present but != ``"REAL-TIME"`` — catches a future accidental subscription downgrade BEFORE the freshness guard does (the guard only fires once age accumulates past 330s; tier_mismatch fires on the FIRST stale response). Same A.8 L8.1 discipline (verify subscription claims as present-day factual questions) applied to runtime detection.

**Acceptance criteria — verification status:**

1. ✅ All four index feeds (SPX, VIX, VVIX, VIX9D) write JSON envelopes with consistent `fetched_at`/`fetched_at_source`/`source` fields. SPX path unchanged from PR #92; VIX/VVIX/VIX9D producer rewrite mirrors it via the new shared `_extract_index_upstream_ts` helper at `polygon_feed.py:_extract_index_upstream_ts`.
2. ✅ Consumer-side freshness guards in place. SPX = hard-gate (existing T-ACT-046 behaviour preserved via the new `_check_index_freshness` helper). VIX/VVIX/VIX9D = soft-warn (Option β). All consumer sites that read these keys use the shared `parse_polygon_index_value` helper (`polygon_index_helpers.py`) which is backward-compatible with legacy raw float values still in cache during the 1-hour rollover window.
3. ✅ `POLYGON_FRESHNESS_THRESHOLD_SECONDS = 330` extracted to module-level in `prediction_engine.py`; the SPX guard at `prediction_engine.run_cycle` and the new `_check_index_freshness` helper both reference it. No inline literal `330` remains for any of the four index-feed freshness checks.
4. ✅ Test surface: 19 new unit tests in `backend/tests/test_t_act_062_freshness_guard.py` covering parser backward compatibility (7 tests), envelope shape (2 tests), freshness threshold semantics (5 tests including pinned WARN log key names for T-ACT-065 telemetry), and threshold arithmetic (3 tests). Plus the regex-tolerance fix at `test_consolidation_s5.py::test_vvix_writes_use_setex_not_bare_set`.
5. ⏳ 7-day post-merge stale-event audit: tracked under **T-ACT-065** with due date 2026-05-12. Decision matrix already drafted in T-ACT-065's entry below.

**Cross-references:** HANDOFF A.7 (silent-failure-class family convention pointer — T-ACT-062 closes the exhaustive-coverage milestone for the derived-feature surface). HANDOFF A.8 (this T-ACT was identified as the natural follow-up in `HANDOFF_NOTE_2026-05-04_INDICES_OUTAGE.md` §8.3). T-ACT-046 (sibling — same family, established the SPX pattern; T-ACT-062 mirrors it to VVIX/VIX/VIX9D). T-ACT-061 (predecessor — gate originally specified, waived per SD-5 operator instruction). T-ACT-064 (downstream — VVIX freshness now contributes to the retraining decision tracking; "confirmed-fresh data" is now well-defined at all four index feeds). T-ACT-065 (immediate successor — 7-day post-merge soft-warn evaluation window deciding whether to flip to hard-gate).

---

### T-ACT-063 — Email alert egress failure on Railway (`alert_email_failed [Errno 101] Network is unreachable`)

**Severity:** MEDIUM-HIGH (operator detection-without-notification — watchdog correctly fires, but no alert reaches operator; same blast-radius class as T-ACT-057 14-day alerting blackout but with a different proximate cause)
**Owner:** Cursor (DIAGNOSE-FIRST + recommendation; operator decides remediation path)
**Estimated time:** small-medium — ~30 min DIAGNOSE; 1-2 hours EXECUTE depending on chosen path

**Description:** During the 2026-05-04 RTH window of the prediction outage, the watchdog at `backend/main.py` (or wherever the watchdog lives — confirm at DIAGNOSE-time) correctly detected `prediction_engine_silent` and attempted to fire an alert via the SMTP path established post-T-ACT-057 (env-var fix DONE 2026-05-02). However, every `send_alert(...)` call during the RTH window logged `alert_email_failed [Errno 101] Network is unreachable` — a Linux errno code indicating no IPv4 route to the SMTP host. The operator received NO alert during the 76-hour outage despite the watchdog correctly classifying the silent-state.

**Hypothesis (DIAGNOSE-pending):** Railway's container egress to public SMTP (smtp.gmail.com:587) is structurally flaky or actively blocked. SMTP egress from cloud containers is well-known to be unreliable due to (a) ISP-style abuse-prevention egress filtering (Railway may block port 25/587 by default), (b) IPv6-vs-IPv4 routing surprises, (c) cloud-provider DNS resolution differences, (d) ephemeral container network re-initialization on cold-start vs. warm-cycle.

**Investigation needed (DIAGNOSE-FIRST scope):**
1. Confirm error class — is `[Errno 101]` consistent across all watchdog fires during the outage window? Search Railway logs for the date range 2026-05-04 09:30-15:55 ET.
2. Confirm Railway egress policy on SMTP ports — check Railway docs / support; some plans/regions block SMTP outbound by default.
3. Test connectivity from Railway shell during a non-incident window: `python3 -c "import socket; s = socket.create_connection(('smtp.gmail.com', 587), 5); print('ok')"`.
4. Inventory candidate replacements:
   - **Slack webhook** (HTTP POST to `hooks.slack.com`; outbound HTTP/443 reliably egressed from Railway).
   - **Telegram bot API** (HTTP POST; same).
   - **HTTP transactional email API** (Resend, Postmark, SendGrid — HTTP/443 egress; transactional reliability; ~$0-15/mo for low-volume MarketMuse cadence).
   - **PagerDuty / Opsgenie** (heavier; not warranted at current scale).

**Recommendation pending DIAGNOSE (anticipated):** switch from SMTP transport to webhook-based or HTTP-API-based alerting. SMTP from cloud containers is structurally fragile; an HTTP-based path eliminates the egress class of failure entirely. Slack webhook is likely the lowest-friction option (operator already uses Slack for personal/team comms; one-time webhook URL setup; <50 lines of code change in `backend/alerting.py`).

**Acceptance criteria (TBD post-DIAGNOSE):**
1. Watchdog firing during a smoke-test outage window successfully reaches the operator within 60 seconds.
2. Failure mode for the new transport is observable (e.g., HTTP 4xx/5xx response logged at WARN, not silently swallowed) — same A.7 discipline applied to alerting transport.
3. No regression in alert latency vs. the post-T-ACT-057 SMTP baseline (smoke test 2026-05-02 21:52 ET arrived in operator's inbox within ~30 sec).

**Status:** [ ] OPEN — queued, lower urgency than T-ACT-062. Operator can prioritize among T-ACT-062 vs T-ACT-063 based on which provides higher governance value first.

**Cross-references:** T-ACT-057 (ALERT_GMAIL_APP_PASSWORD whitespace silent-rejection; T-ACT-063 is the SECOND distinct alerting blackout root-cause discovered after T-ACT-057's whitespace fix; reinforces the discipline-meta-lesson "infrastructure-config silent-failure surfaces require 3-question exhaustive verification: SET / CORRECT FORMAT / END-TO-END VALIDATED" — T-ACT-063 demonstrates that even with all three questions answered correctly, a fourth-class issue (transport-layer egress reliability) can still produce detection-without-notification). HANDOFF A.7 (silent-failure-class family — T-ACT-063 may surface a 4th subclass: alerting-transport reliability surface). HANDOFF A.8 (this T-ACT was identified during the 2026-05-04 outage diagnosis when operator noted no email arrived during the 76-hour silent window despite watchdog firing correctly).

---

### T-ACT-064 — Post-upgrade LightGBM retraining decision tracking (informational; no immediate action)

**Severity:** INFORMATIONAL (decision-deferred; tracked only)
**Owner:** Operator (decision); Cursor (data-availability monitoring + decision-support analysis when threshold reached)
**Estimated time:** 0 (no work now); 4-8 hours when triggered (training run + accuracy investigation re-run + decision memo)

**Description:** The Sunday 2026-05-03 accuracy investigation (per session HANDOFF) identified critically degraded directional accuracy in the production LightGBM v1 model. The investigation surfaced a metric mismatch (2-class binary training vs. 3-class labeling at evaluation with `±0.1%` neutral threshold) as the dominant explanatory factor, but the investigation also flagged that input-data quality may have been silently compromised during the training window:

- **VVIX features (`vvix_z_score`, `vvix_close`, `vix_term_ratio`):** silently 15-min stale every cycle pre-T-ACT-061 (Indices Starter era — entire training window through 2026-05-04). Will become real-time post-T-ACT-061 verification + T-ACT-062 freshness-guard rollout.
- **SPX features:** real-time with PR #82-#86 chain (LightGBM v1 activation 2026-04-30) until PR #90/T-ACT-045 introduced Polygon-first chain on 2026-04-30; then in the brief Saturday-only window 2026-05-02 12:00 ET → 2026-05-04 evening, post-PR-#92 SPX features were "correctly stale" (guard rejected) which is the OPPOSITE of stale-and-used. So SPX features in training are mostly OK pending T-ACT-045 actual re-run analysis.
- **Cv_stress family (T-ACT-054 fixed 2026-05-02):** ~29.2% of cycles in pre-fix window persisted silent-zero artifacts. Now NULL-on-degenerate-input.
- **Model_source schema-code drift (A.5, fixed 2026-05-01):** ~16+ hours of zero-row persistence pre-fix. Resolved.

**Decision deferred until threshold:**
- **Threshold:** ~50-100 closed paper trades on confirmed-fresh data (post-T-ACT-061 verification + post-T-ACT-062 freshness guards rolled out).
- **At threshold:** re-run accuracy investigation (Sunday 2026-05-03 SQL pack + holdout backtest). Compare to current model's performance on confirmed-fresh data.
- **Decision points:**
  - **(a) Retrain on known-fresh window:** if confirmed-fresh-data accuracy is materially better than current model's confirmed-fresh-data performance — retrain LightGBM on the post-T-ACT-061+T-ACT-062 window only; update `model_metadata.json` with new training-window range.
  - **(b) Accept current model:** if confirmed-fresh-data accuracy is statistically indistinguishable from current model's confirmed-fresh-data performance — keep current model; update governance docs to record that the metric mismatch was the dominant explanation for low-accuracy framing.
  - **(c) Investigate further:** if neither path is clearly indicated.

**No action now. Tracked only.** Future Cursor sessions reasoning about model performance, retraining urgency, or activation-gate sufficiency must:
1. Check this T-ACT's status before recommending retraining.
2. Verify the closed-trade-count threshold has been reached (Supabase SQL: `SELECT COUNT(*) FROM trading_positions WHERE status='closed' AND closed_at > '<post-T-ACT-061-verification timestamp>';`).
3. Check `data freshness audit` per T-ACT-062 acceptance criterion #5 has run cleanly for ≥7 days.
4. Surface this T-ACT in the recommendation chain rather than re-deriving the question from first principles.

**Acceptance criteria (when triggered):**
1. ≥50 closed paper trades on confirmed-fresh data (data-availability gate).
2. Re-run accuracy investigation produces a recommendation ((a), (b), or (c)).
3. Decision memo logged in TASK_REGISTER §14 with reasoning.

**Status:** [ ] OPEN — informational, no immediate action. Will reactivate at threshold.

**Cross-references:** HANDOFF A.6 (paper-trading-P&L-meaningless-if-inputs-stale lesson; T-ACT-064 is the same discipline applied to ML training-data freshness). HANDOFF A.8 (post-upgrade retraining as a tracked decision was identified during the 2026-05-04 outage diagnosis; included in that file's "Open question" closing section). T-ACT-061 (gating dependency — must verify SPX real-time entitlement first). T-ACT-062 (gating dependency — must roll out VVIX/VIX/VIX9D freshness guards before "confirmed-fresh data" is well-defined). Sunday 2026-05-03 accuracy investigation HANDOFF (referenced in session continuity; if not yet committed to repo, it should be committed in a separate governance PR — flag to operator).

---

### T-ACT-065 — Evaluate flip to hard-gate on VIX / VVIX / VIX9D (7-day post-T-ACT-062 evaluation)

**Severity:** INFORMATIONAL (decision-only; no code change required at trigger; closes regardless of which path chosen)
**Owner:** Operator (pulls log + SQL evidence); Cursor (decision-matrix analysis + decision memo)
**Estimated time:** ~30 min at trigger
**Status:** [ ] SCHEDULED
**Due date:** 2026-05-12 (7 days post-T-ACT-062 merge)
**Predecessor:** T-ACT-062 (VVIX/VIX/VIX9D freshness guard with Option β soft-warn — see SD-1 below)
**Trigger:** scheduled date OR T-ACT-062 merged + 7 calendar days elapsed (whichever later)

**Why this T-ACT exists (governance discipline):** T-ACT-062 ships SD-1 Option β (hard-gate SPX only; soft-warn VIX/VVIX/VIX9D when stale) per the operator's design choice 2026-05-04 evening. The 7-day evaluation window is a first-class tracked item with a due date and a decision matrix — NOT buried in T-ACT-062's success criteria — so that "everything looks fine, flip it" cannot ship without checking the actual data. Cursor or future-Claude can execute T-ACT-065 mechanically when the date arrives.

**Action:**

1. Pull `vix_price_stale`, `vvix_price_stale`, `vix9d_price_stale` event counts from Railway logs over the 7-day window since T-ACT-062 merge.
2. SQL: count cycles where any VIX-family stale event fired vs. total RTH cycles in the window.
3. Decision matrix:
   - **Zero stale events across all three feeds:** flip to hard-gate (Option α). Open follow-up PR.
   - **Rare-and-transient (< 1% of cycles, no clusters > 3 consecutive):** flip to hard-gate. Open follow-up PR.
   - **Common (> 1% of cycles) OR clustered (> 3 consecutive in any window):** investigate root cause before flipping. Do NOT flip yet. Open diagnostic task.
   - **VIX9D-only stale events:** consider Option γ (hard-gate VIX + VVIX, soft-warn VIX9D) as intermediate.

**Success criterion:** decision documented in TASK_REGISTER §14 with evidence (event counts + cycle counts + decision rationale). T-ACT-065 closes regardless of which path chosen.

**Reference:** SD-1 from T-ACT-062 PR review, 2026-05-04 evening (operator selected Option β `beta_hard_spx_only_soft_others`; this T-ACT formalizes the 7-day evaluation that informs whether to flip).

**Cross-references:** T-ACT-062 (predecessor — establishes the soft-warn telemetry that this T-ACT consumes). T-ACT-061 §7.1 probe (independent verification — confirms SPX real-time entitlement; T-ACT-065 measures the analogous post-deploy reality for VIX/VVIX/VIX9D via produced log signal rather than a one-shot probe). HANDOFF NOTE Appendix A.8 L8.1 ("subscription/entitlement claims as present-day factual questions" — T-ACT-065 generalizes the discipline from "verify tier description" to "verify production log evidence over a window before flipping a behavioral guard").

---

### T-ACT-072 — Producer-side `ts_event` age filter on Databento OPRA trades (frankenstein-record protection)

**Severity:** HIGH (corrupts GEX outputs that feed regime classification, strategy selection, and strike selection)
**Owner:** Cursor — implemented 2026-05-06 mid-RTH via PR `fix/t-act-072-databento-ts-event-age-filter`
**Estimated time (actual):** ~75 min Cursor (CRITIQUE-FIRST + Q1-Q8 + EXECUTE + tests + governance)
**Status:** [x] DONE (pending operator review/merge — markets-open critique-first discipline observed)

**Description:** `databento_feed._handle_trade` accepted any `ts_event` and pushed via `_push_trade` regardless of age. Server-side Databento replay (most plausibly a gateway-level snapshot/preamble delivered on subscribe, possibly amplified by our outer reconnect loop after overnight idle) was delivering Tuesday-stamped `TradeMsg` records during Wednesday pre-market. `_get_underlying_price` reads `polygon:spx:current` at wall-clock-now, producing **frankenstein records**: OLD `ts_event` + OLD strike + OLD time-to-expiry paired with CURRENT `underlying_price` + floored `T=0.0001`. Downstream `compute_gex` ran Black-Scholes against this and wrote corrupted `gex:by_strike` / `gex:nearest_wall` / `gex:flip_zone` / `gex:confidence` to Redis, feeding `prediction_engine._compute_regime`, `strategy_selector`, and `strike_selector`.

Symptom signature observed 2026-05-06 06:30 ET (pre-RTH): nine consecutive `gex_quote_missing_after_rest` warnings referencing yesterday's expired option symbols; `databento:opra:trades` re-filling at ~500 trades/min after manual `DEL`; all replayed records bore Tuesday-aligned `ts_event` while `underlying_price` was the live Wednesday SPX value.

**Fix shipped (single-scope PR):**

1. **Module-level constant** `DATABENTO_TRADE_MAX_AGE_SECONDS = 300` and `_STALE_TRADE_REJECT_LOG_INTERVAL = 100` in `backend/databento_feed.py`. Threshold rationale: wide enough that legitimate live-trade delivery delays never hit it (sub-second normal), narrow enough that any cross-day record is always rejected (>> 300s old). Library docstring at `databento/live/client.py:450` documents the live `start` parameter as bounded at 24 hours, supporting the choice as well-separated from both extremes.
2. **Per-instance counter** `self._stale_trade_reject_count` initialized in `__init__` (NOT module-global, to keep tests that instantiate multiple feeds isolated — see Q5 critique). Process-cumulative; resets on process restart.
3. **Filter block** inserted in `_handle_trade` after the existing `event_date` derivation (immediately before `raw_symbol = None`). Computes age from `ts_ns` against `time.time_ns()`, rejects when `age_seconds > DATABENTO_TRADE_MAX_AGE_SECONDS`. Logs every Nth rejection (default N=100) at WARNING with structured fields `age_seconds`, `threshold_seconds`, `cumulative_rejections`, `ts_event_iso`. Fail-open on `ts_ns <= 0` (consistent with existing `event_date` fallback at the top of `_handle_trade`).
4. **Filter location discipline** documented inline: filter is applied at `_handle_trade`, not at `_push_trade`, because the only other caller of `_push_trade` is `process_trade` — a back-compat shim used exclusively by `tests/test_fix_group7a.py:71`. A code comment at the filter site warns that future production callers of `_push_trade` or `process_trade` MUST add their own filter or move this one.
5. **Test fixture update** in `backend/tests/test_databento_feed.py`: `_mk_trade_mock` default `ts_event` changed from the hardcoded `datetime(2026, 4, 15, ...)` (3+ weeks old) to `time.time_ns()`. Without this, three pre-existing tests would have broken when the filter rejected the stale fixture default — surfaced in Q6 critique as a hard requirement before merge.
6. **Four new tests** added in the same file: (a) fresh trade (1ms old) reaches `_push_trade`; (b) stale trade (10 min old) is rejected and emits the structured warning on the first rejection of the process; (c) edge — trade exactly 1s past threshold (301s) is rejected; (d) edge — `ts_event = 0` falls through and reaches `_push_trade` (fail-open consistency check).

**Acceptance criteria:**

- ✅ Producer-side filter rejects trades whose `ts_event` is more than 300 seconds old.
- ✅ Structured `databento_stale_trade_rejected` event emitted at WARNING (batched: every Nth rejection of the process).
- ✅ Filter is fail-open on `ts_ns == 0` (consistent with existing semantics).
- ✅ Pre-existing tests in `test_databento_feed.py` continue to pass (fixture updated).
- ✅ Four new tests pass (fresh, stale, threshold edge, zero-ts edge).
- 🟡 Post-deploy validation (operator-observed): on subsequent mornings, `LLEN databento:opra:trades` does NOT grow during pre-market reconnect bursts; `gex_quote_missing_after_rest` warnings cease for cross-day expired symbols.

**Critique-first discipline (markets-open mid-RTH context):** Operator imposed an explicit "do not cause further break / degradation of ROI" mandate for any code change shipped during live trading. Cursor responded to the operator's draft fix prompt with a Q1-Q8 critique BEFORE implementation. The critique surfaced one **STOP-class** issue (Q6 — fixture default would break pre-existing tests) and two **modification-needed** items (Q5 instance variable; variable-name correction `ts_ns` not `ts_event_ns`). Operator authorized YELLOW (proceed with the three modifications); implementation followed exactly. No silent workarounds; the critique document is referenced from the PR body.

**Why this design over alternatives:**

- **Consumer-side filtering in `compute_gex`** would also work but adds complexity to a per-cycle hot path, doesn't prevent `LTRIM` from evicting good data to make room for stale-but-just-pushed bad data, and doesn't suppress the `gex_quote_missing_after_rest` warning emission.
- **Daily-flush cron on `databento:opra:trades`** (Option A from the predecessor diagnostic) would be defense-in-depth at the boundary; redundant given the producer-side filter, deferrable indefinitely or as a separate small belt-and-suspenders PR.
- **Hard-coded fail-closed on `ts_event = 0`** would protect against a future bug that bypasses the filter via zeroed timestamps but would break compatibility with the existing `event_date` fallback semantic. Q4 critique resolved this fail-open per existing convention.

**Cross-references:**

- HANDOFF_NOTE_2026-05-06_DATABENTO_PUSH_LIFECYCLE.md (predecessor diagnostic — establishes the bug surface and the producer-side-filter recommendation; pre-existing condition, no recent merge identified as cause).
- HANDOFF_NOTE_2026-05-06_GEX_QUOTE_MISSING.md (sibling diagnostic — `gex_quote_missing_after_rest` warnings are a symptom of the same root issue addressed by this PR).
- T-ACT-062 (predecessor — established the freshness-guard discipline; T-ACT-072 generalizes the discipline from per-cycle index reads to per-trade producer-side ingestion).
- HANDOFF NOTE Appendix A.7 (silent-failure-class family — T-ACT-072 closes a producer-side instance: trades with degenerate-but-current `underlying_price` corrupting downstream Black-Scholes silently).
- T-ACT-073 (queued — `gex:confidence` redefine; informational follow-up identified by both the GEX-quote-missing and Databento-push-lifecycle diagnostics, not bundled here per single-scope discipline).

---

### T-ACT-076 — F-068-I binary labeler fix (Position 1a) + F-068-A schema-CHECK widening (bundled scope)

**Severity:** HIGH (Scope A: structural collapse of `outcome_correct` — accuracy reads ~6.1% post-hygiene because every `actual_direction='neutral'` row is scored false against a binary-trained LightGBM. Blocks GLC-001/002 milestone gates. Scope B: every Sunday 22:05 UTC weekly run silently fails to write a `trading_model_performance` row whenever `detect_drift` returns `'ok'` or `'unknown'`; dashboard falls back to a stale row from `calibration_engine.write_model_performance` at 22:00 UTC.)
**Owner:** Cursor — implemented 2026-05-07 via PR `fix/t-act-076-binary-labeler-position-1a`
**Estimated time (actual):** ~90 min Cursor (DIAGNOSE-FIRST F-068-I recommendation review + Q1-Q12 critique + bundled-scope EXECUTE + tests + governance)
**Status:** [x] DONE (pending operator review/merge)

**Description (Scope A — F-068-I dissolution):** `backend/scripts/train_direction_model.py:323-325` labels training data as binary (`bull` if `r > 0` else `bear`) — this is the deliberate post-"model-collapse" revert from the original ternary attempt (commit `84617a1`, 2026-04-17 16:22 ET). The production labeler at `backend/model_retraining.py:140-145` was missed in the same-day revert and remained ternary (`bull`/`bear`/`neutral` with a ±0.1% `DIRECTION_THRESHOLD` band). The inference engine (`prediction_engine.py:1116-1124`, LightGBM path) has effectively no way to emit `direction='neutral'` because `p_neutral` is hardcoded to `0.35` while `max(p_bull, p_bear) >= 0.5`. Net effect: every prediction cycle whose realized SPX move falls inside the ±0.1% band gets `pred_direction ∈ {bull, bear}` paired with `actual_direction='neutral'`, so `outcome_correct=False` deterministically — structurally collapsing measured accuracy to the bands of the ternary distribution that the model architecturally cannot hit. Forensic and recommendation in `HANDOFF_NOTE_2026-05-06_F068I_BINARY_LABELER_FIX.md`.

**Description (Scope B — F-068-A silent schema rejection):** `supabase/migrations/20260416172751_0ef832ac-fab6-4da7-a0d0-050df61b399f.sql:270` declares `drift_status TEXT DEFAULT 'normal' CHECK (drift_status IN ('normal','warning','critical'))` but `model_retraining.detect_drift` (L478-517) returns one of `{'ok','warning','critical','unknown'}`. Postgres rejects `'ok'` and `'unknown'` inserts via 23514 check_violation; the broad `except Exception` at `model_retraining.py:695-699` swallows the `PostgrestAPIError` with a generic ERROR log. The dashboard then falls back to a stale row written at 22:00 UTC by `calibration_engine.write_model_performance` (with NULL accuracies and `drift_status='normal'`). This is the F-068-H "dual-writer dashboard identity-switch" pattern.

**Fix shipped (bundled single-PR scope per T-ACT-076 Q10):**

1. **Scope A — `backend/model_retraining.py:140-147`** — replace ternary classifier with binary (`actual_direction = "bull" if spx_return > 0 else "bear"`). Strict `> 0` matches `train_direction_model.py:323-325` byte-for-byte; `spx_return == 0.0` → `"bear"` (vanishingly rare under float division). Removes the `DIRECTION_THRESHOLD = 0.001` constant from the labeler entirely (any future re-introduction of a band would re-trip the regression test below).
2. **Scope B — `supabase/migrations/20260507_widen_drift_status_check.sql`** — new idempotent `DROP CONSTRAINT IF EXISTS` + `ADD CONSTRAINT` widens the CHECK to `('normal','warning','critical','ok','unknown')`. Preserves the existing three values; appends the two missing values from `detect_drift`'s actual return space. CHECK-widening was preferred over function-layer remap on ROI grounds (no information loss; smaller diff; doesn't change the daily `check_prediction_drift` contract which also returns `'ok'`).
3. **Scope B — `backend/model_retraining.py:677-697`** — narrow inner `try/except` around the `.insert(payload).execute()` call surfaces `PostgrestAPIError` distinctly. Pattern is byte-for-byte aligned with the T-ACT-047 Choice C precedent at `prediction_engine.py:1641-1690` to keep the two A.7-family persist sites in lock-step. Logs structured `weekly_model_performance_persistent_error` event at WARN with `pgrst_code` / `pgrst_details` / `pgrst_hint` / `drift_status_attempted`. Calls `write_health_status('prediction_engine', 'error')` with a `PERSISTENT[<code>]:` prefix on `last_error_message`. Fires `send_alert(CRITICAL, ...)` with the hint and `drift_status_attempted` in the body. Returns `{"error": "persistent_postgrest:<code>"}` instead of collapsing to `str(e)`. Outer broad `except Exception` preserved for non-postgrest failure classes (compute helpers, network errors, audit-log failures).
4. **Tests — `backend/tests/test_phase_a1.py`** — re-purposes `test_label_prediction_outcomes_neutral_within_threshold` → `test_label_prediction_outcomes_tiny_positive_move_is_bull` (asserts the OLD ternary-band case is now classified `'bull'`). Adds `test_label_prediction_outcomes_zero_move_is_bear` (boundary contract: strict `> 0`). Adds `test_label_prediction_outcomes_never_emits_neutral` regression-guard via `inspect.getsource(...)` — defends against future accidental re-introduction of a ternary band.
5. **Tests — `backend/tests/test_t_act_076_weekly_perf_persistent_error.py`** (new file, 5 tests) — mirrors the T-ACT-047 test structure for the second A.7-family persist site: structured-fields logging, health-write `PERSISTENT[]` prefix, CRITICAL alert with hint + `drift_status_attempted`, non-postgrest fall-through to outer handler, happy-path no-warning regression guard.

**Acceptance criteria:**

- ✅ `model_retraining.label_prediction_outcomes` writes `outcome_direction ∈ {'bull','bear'}` exclusively (never `'neutral'`).
- ✅ `train_direction_model.py:323-325` and `model_retraining.py:147` are byte-for-byte aligned (`r > 0` → `"bull"`, else `"bear"`).
- ✅ `trading_model_performance.drift_status` CHECK constraint accepts `'ok'`, `'normal'`, `'warning'`, `'critical'`, `'unknown'` after migration applied.
- ✅ `PostgrestAPIError` on the weekly insert is caught at the inner WARN-class classifier with structured fields; outer ERROR-class fall-through preserved for non-postgrest exceptions.
- ✅ Targeted tests pass (14 total: 9 pre-existing + 2 amended + 3 new in `test_phase_a1.py`; 5 new in `test_t_act_076_weekly_perf_persistent_error.py`).
- ✅ Full backend test suite shows zero regressions: baseline `38 failed + 10 errors + 784 passed` → post-merge `38 failed + 10 errors + 791 passed` (+7 new passes match exactly: 5 + 2). Pre-existing failures are tracked under T-ACT-074/T-ACT-075 (test pollution + suite-wide triage) and unaffected by this PR.
- 🟡 Post-deploy validation (operator-observed, see §A.7 below): post-deploy `outcome_direction` value-distribution shows zero `'neutral'` rows on labeler-runs after merge; first Sunday weekly run after migration successfully writes a `trading_model_performance` row when `detect_drift` returns `'ok'` (no `weekly_model_performance_persistent_error` event); §11.1-style `pred_direction × outcome_direction` crosstab shows the post-fix accuracy distribution.

**Q5 regime-dependent confound — explicit documentation (per operator's Phase 2 amendment #1):** The Position 1a binary labeler dissolves F-068-G on average but exposes a regime-dependent risk surface. Two inference paths can still emit `direction='neutral'` after this fix: (a) the AI-synthesis path at `prediction_engine.py:974,978` (passes through `'neutral'` if AI agent returns it with `confidence >= 0.55`), and (b) the regime-fallback at `prediction_engine.py:1178-1192` when `cv_stress > 70` (deterministically produces `p_neutral = 0.40` as argmax — this is the LARGER of the two; the default-regime branch at L1188 has `p_neutral = 0.35` tied with `p_bull = 0.35` and Python's `max()` returns the first equal-valued tuple = `'bull'`, so default is binary-correct). Under the binary labeler, both paths produce `pred_direction='neutral'` rows that get scored `outcome_correct=False` against a `'bull'`/`'bear'` actual. **Expected post-deploy accuracy is ~47-50% on average but regime-dependent; on high-cv_stress weeks the regime-fallback path will produce more `pred='neutral'` rows that get scored false against binary labels. F-068-G's dissolution is conditional on `cv_stress` distribution being typical.** A high-stress week with `cv_stress > 70` firing on, say, 30% of cycles could pull weekly accuracy below `RETRAIN_THRESHOLD = 0.45` and correctly trigger drift — but for the WRONG reason (structural class-mismatch on neutral preds, not model degradation). T-ACT-081 is queued to address this via a labeler guard once post-deploy data quantifies the actual magnitude. Do NOT pre-emptively expand T-ACT-076 scope to include the guard — operator's scope discipline rule (#3) invoked.

**T-ACT-077 status (re-checked per Q11 critique):** F-068-B (data-window contamination from the Indices-Starter-stale era) is **DEFERRED, NOT CLOSED** by T-ACT-076. F-068-B concerns input-quality contamination (rows whose `spx_price` fields were captured during the 2026-05-01 → 2026-05-04 outage / pre-ratification window when `polygon:spx:current.fetched_at` semantics were in flux); T-ACT-076 fixes labeler class-space, which is orthogonal to input-row hygiene. T-ACT-077 re-evaluation due 2026-05-25 (post-21-day clean-data window).

**Critique-first discipline (DIAGNOSE-FIRST applied):** Operator imposed a critique-first Q1-Q12 review before authorizing implementation. Cursor's Phase 1 critique came back GREEN with two flags: Q5 (regime-dependent neutral-emission paths — two real cases verified by operator; non-blocking, queued as T-ACT-081), Q11 (T-ACT-077 status — DEFERRED not CLOSED, operator agreed). Operator authorized YELLOW (proceed) with three governance amendments: (1) handoff note must explicitly document Q5 confound; (2) add T-ACT-081 to bundle; (3) expand §A.7 post-deploy SQL to include `pred_direction × outcome_direction` crosstab. All three are documentation/governance amendments, not scope expansions.

**Why bundled (Q10 BUNDLE decision):** Activation-risk asymmetry. If Scope A shipped alone before the next Sunday cron, the first weekly run after the labeler fix would still silently fail on `'ok'` drift_status. Sequencing the migration as a separate later PR creates a window during which the F-068-A silent rejection would re-fire weekly. Marginal review burden of bundling (~30 LOC + one trivial migration) is trivial vs. the activation-risk avoidance. Operator agreed dispositively in Phase 1 critique.

**Why CHECK-widening over function-layer remap (Q10 sub-decision):** Diagnostic granularity preservation. `'ok'` and `'unknown'` are semantically distinct from `'normal'` (`'ok'` = computed-and-healthy; `'unknown'` = insufficient-observations); collapsing them at the function layer would lose A.7-family observability. Migration is a one-line ALTER TABLE.

**Cross-references:**

- HANDOFF_NOTE_2026-05-06_F068I_BINARY_LABELER_FIX.md (forensic + recommendation + Q1-Q12 critique + Phase 2 amendments)
- F-068-I (training-inference class-space mismatch — dissolved by Scope A)
- F-068-A (schema-CHECK silent rejection — closed by Scope B; A.7-family second persist-site instance after T-ACT-047)
- F-068-G (S15 threshold-metric mismatch — DISSOLVED by Scope A on average; conditional on `cv_stress` regime distribution per Q5)
- F-068-H (dual-writer dashboard identity-switch via `calibration_engine.write_model_performance` 22:00 UTC sibling — surfaced by Scope B inner-classifier observability; informational follow-up, not closed by this PR)
- T-ACT-047 Choice C (precedent pattern for `PostgrestAPIError` classification at persist sites — `prediction_engine.py:1641-1690`; T-ACT-076 Scope B keeps the two A.7-family persist sites in lock-step)
- T-ACT-077 (data-window hygiene — DEFERRED 2026-05-25 per Q11 re-evaluation, not closed)
- T-ACT-081 (labeler guard against `pred_direction='neutral'` inputs — queued, defer pending post-deploy magnitude quantification)
- HANDOFF NOTE Appendix A.7 (silent-failure-class family — T-ACT-076 closes a fifth subclass: training-inference class-space mismatch; complements T-ACT-067 "schema-CHECK constraint mismatch" which Scope B addresses for the second persist site)

---

### T-ACT-081 — Labeler guard against `pred_direction='neutral'` inputs (queued, defer pending post-deploy magnitude data)

**Severity:** MEDIUM (regime-dependent confound on accuracy metrics; not a correctness bug per se — see Q5 in T-ACT-076)
**Owner:** Cursor — to be authorized after post-deploy magnitude data is in
**Estimated time:** ~30 min Cursor (small additive change in `model_retraining.label_prediction_outcomes` to filter or distinguish `pred_direction='neutral'` rows before computing `outcome_correct`)
**Status:** [ ] QUEUED / DEFERRED — re-evaluate after first 7 days post-T-ACT-076 deploy

**Description:** Two inference paths in `prediction_engine.py` can emit `direction='neutral'` even after T-ACT-076's binary-labeler fix: (a) the AI-synthesis path at L974,978 (passes through `'neutral'` if AI agent returns it with `confidence >= 0.55`); (b) the regime-fallback at L1178-1192 when `cv_stress > 70` (`p_neutral = 0.40` is unambiguous argmax). Under the new binary labeler, both paths produce `pred_direction='neutral'` rows that are scored `outcome_correct=False` against `'bull'`/`'bear'` actuals — structurally driving accuracy down on cycles where the prediction engine deliberately chose the neutral option. This is a **regime-dependent confound**: on calm `cv_stress < 50` weeks the impact is bounded by the AI-synth share (small); on stressed `cv_stress > 70` weeks the impact can be material (e.g., 30% of cycles → ~37% weekly accuracy, below `RETRAIN_THRESHOLD = 0.45`).

**Why DEFERRED, not bundled with T-ACT-076:** Operator scope discipline (rule #3). Bundling would expand T-ACT-076 past the "complete the same-day fix" framing and would touch code paths (AI-synth + regime fallback) beyond `model_retraining.py:140-145`. Defer until post-deploy data quantifies the actual magnitude — if impact materially exceeds 10% of labeled rows we'll prioritize; otherwise lower priority.

**Decision matrix (re-evaluate 2026-05-14, one week post-T-ACT-076 deploy):**

- **Path A (impact <= 10%):** Park indefinitely. Document as a known regime-dependent confound in `function-index.md` once that index exists; no further action.
- **Path B (10% < impact <= 25%):** Schedule a small fix — labeler skips (does not write `outcome_*` columns) when `pred_direction='neutral'` so neither dataset shape nor accuracy metric is contaminated. Adds NULLs to `outcome_correct` for those rows; GLC-001/002 evaluators must filter NULL.
- **Path C (impact > 25%):** Treat as acceptance-criterion-impacting; escalate to a labeler+evaluator coordinated change; require operator review.

**Acceptance criterion (when this T-ACT moves to DONE):** Post-deploy SQL crosstab from §A.7 confirms ≤ 10% of labeled rows have `pred_direction='neutral'` (Path A), OR a coordinated fix is shipped per Path B/C above.

**Reference:** Q5 critique flag in T-ACT-076 Phase 1 review; HANDOFF_NOTE_2026-05-06_F068I_BINARY_LABELER_FIX.md §Q5 + §A.7 SQL.

**Cross-references:** T-ACT-076 (predecessor — establishes the binary-labeler contract that creates the surface); T-ACT-068 (drift-detector context — F-068-G dissolution from T-ACT-076 is conditional on this confound's magnitude staying typical); HANDOFF NOTE Appendix A.7 (silent-failure-class family lens — distinct from a silent-failure since the neutral-emission is logged, but the SCORING outcome is silently degraded).

---

### T-ACT-082 — Feature pipeline completion (Path Alpha subset: bb_pct_b + macd_signal + vix_5d_change + rv_20d 5-min basis with B.1.iii backfill)

**Severity:** HIGH (six of the model's 25 input features were silently constant in production: `vwap_distance` #1 importance, `rv_20d` #2, `macd_signal` #6, `morning_range` #7, `bb_pct_b`, `overnight_gap`, `vix_5d_change` #10 — plus the semantically-mismatched daily-vs-realtime `vix_close`/`vvix_close` shifts. LightGBM was effectively running on ~15 of 25 features, materially explaining the production-vs-training accuracy gap (31% live vs 52.92% holdout). T-ACT-082 closes 4 of the 6 unwritten keys plus the `rv_20d` semantic shift; the remaining three OHLC-dependent features defer to T-ACT-085.)
**Owner:** Cursor — implemented 2026-05-07 via PR `fix/t-act-082-feature-pipeline-completion`
**Estimated time (actual):** ~120 min Cursor (DIAGNOSE-FIRST model-quality investigation + Q1-Q14 critique + Path Alpha subset implementation + tests + governance + handoff)
**Status:** [x] DONE (pending operator review/merge)

**Description:** Audit of the T-ACT-076 post-deploy operator-data revealed that the LightGBM inference site (`prediction_engine.py:1085-1110`) reads 25 features from Redis but six of them have no producer in the codebase — specifically `polygon:spx:overnight_gap`, `polygon:spx:macd_signal`, `polygon:spx:bb_pct_b`, `polygon:spx:vwap_distance`, `polygon:spx:morning_range`, and `polygon:vix:5d_change`. The Python `_read_redis(..., default)` fallbacks return constant values (typically 0.0) for every cycle, so the LightGBM tree-splits these features encode are never exercised. Additionally, `polygon:spx:realized_vol_20d` was being written under the 12A daily-basis formula (`std(daily_returns) * sqrt(252) * 100`), semantically mismatching the training pipeline's 5-min-basis formula (`std(5m_returns) * sqrt(252 * 78) * 100` per `train_direction_model.py:292-298`).

**Path Alpha (operator-authorized 2026-05-07 after Cursor's Phase 1 critique surfaced three STOP-class issues):** subset T-ACT-082 to the byte-for-byte-alignable features and defer the OHLC-dependent / data-class-shifting work to follow-up T-ACTs (T-ACT-084, T-ACT-085, T-ACT-086).

**Fix shipped:**

1. **Scope A subset — three new live writers in `polygon_feed.py:_compute_spx_features` / `_store_vix_baseline`:**
   - `polygon:spx:bb_pct_b` (training L242-244 byte-aligned: `(close - (sma20 - 2*std20)) / (4*std20)` with `ddof=1` sample std; 20-bar warmup; 300s TTL)
   - `polygon:spx:macd_signal` (training L237-240 byte-aligned: MACD histogram = `(ema12 - ema26)[-1] - ewm9(ema12 - ema26)[-1]` with `adjust=False` recurrence; 35-bar warmup chosen to bring the 9-bar smoothing transient below ~0.03%; 300s TTL). New static helper `PolygonFeed._ewm_adjust_false(values, span)` matches `pandas.Series.ewm(span=N, adjust=False).mean()` to <1e-9 numerical noise (locked by `test_ewm_adjust_false_matches_pandas`).
   - `polygon:vix:5d_change` (training L274-276 byte-aligned: `(daily_vix[-1] - daily_vix[-6]) / daily_vix[-6]`; 6-day warmup satisfied immediately on poll cycle 1 thanks to `_backfill_vix_history`; 7200s TTL matching sibling daily VIX keys).

2. **Scope B — `rv_20d` 5-min basis writer in `_compute_spx_features`:** new buffer `_spx_5m_returns_history` (cap 1560 = 20 trading days × 78 5-min bars/day), per-cycle append, computes `std(window) * sqrt(252 * 78) * 100` exactly per training (`ddof=1` sample std, matching pandas `.rolling(20*78).std()`). Replaces the 12A daily-basis writer in `_append_spx_daily_return_if_due` (which is now no-op for `realized_vol_20d` but retains the date-guard infrastructure for any future daily-basis sibling).

3. **Scope B.1.iii — `_backfill_spx_5m_history` startup backfill** (~110 LOC): one Polygon `/v2/aggs/ticker/I:SPX/range/5/minute/{30d_ago}/{today}` call seeds 1560 returns + 60 closes (the latter to warm `spx_history` for `safe_return(48)` and the EMA recurrence). Without this, production would run with `rv_20d` falling back to `prediction_engine` default 15.0 for ~21 trading days — operationally activating the same regression T-ACT-082 fixes (workflow rule #11 ROI watch-list "without backfill" rejection branch from Phase 1 critique Q9).

4. **Test churn — `test_spx_daily_rv.py` deleted, replaced with `test_spx_5m_basis_rv.py` (8 tests):** the original file's 7 tests explicitly locked in the daily-basis `sqrt(252)` annualization with a docstring saying "catches accidental re-introduction of intraday annualization factors (sqrt(252 * 78) etc.)" — directly anti-Scope-B by design. Replaced with 5-min-basis invariants: 1560-bar warmth threshold; 5-min-basis annualization math (`sqrt(252 * 78)`) with a hard regression guard against `sqrt(252)` re-introduction; FIFO buffer cap; backfill populates buffer; regression guard that `_append_spx_daily_return_if_due` no longer writes the realized-vol key; date-guard preservation for the future-sibling case. Approved as ~150 LOC churn per Phase 1 critique Q7 / Path Alpha authorization.

5. **New tests — `test_t_act_082_feature_writers.py` (10 tests):** byte-for-byte alignment verification for `bb_pct_b`, `macd_signal`, `vix_5d_change` against the closed-form training formulas, plus warmth-threshold regression guards (no premature writes), TTL contracts, and `_ewm_adjust_false` ↔ `pandas.ewm(adjust=False)` numerical equivalence (catches accidental drift in the recursive helper).

6. **Comment hygiene:** updated 4 outdated "12A garbage values" / "intraday 5-min buffer is garbage" / "polygon:spx:realized_vol_20d written EOD" comments in `polygon_feed.py:43-58`, `polygon_feed.py:316-324`, `polygon_feed.py:519-524`, `prediction_engine.py:1264-1275`, and `tests/test_iron_butterfly_safety_gates.py:235-241` so future readers are not misled by superseded narrative.

**Acceptance criteria:**

- ✅ `polygon:spx:bb_pct_b` written every 5-min cycle (>= 20 closes); value matches training formula to <1e-5 noise.
- ✅ `polygon:spx:macd_signal` written every 5-min cycle (>= 35 closes); value matches training EMA chain to <1e-5 noise.
- ✅ `polygon:vix:5d_change` written when daily VIX history >= 6 samples (immediate post-backfill); 7200s TTL.
- ✅ `polygon:spx:realized_vol_20d` written every 5-min cycle (>= 1560 returns); annualized via `sqrt(252 * 78)`; 300s TTL.
- ✅ `_backfill_spx_5m_history` populates buffer to 1560 within first cycle (when Polygon API key is set); fail-open on Polygon error.
- ✅ `_append_spx_daily_return_if_due` no longer writes `polygon:spx:realized_vol_20d` (regression guard test explicitly fails any future re-introduction).
- ✅ Targeted tests pass: 18 new (8 in `test_spx_5m_basis_rv.py` + 10 in `test_t_act_082_feature_writers.py`); plus 43 nearby tests (`test_iron_butterfly_safety_gates.py`, `test_consolidation_s13.py`, `test_consolidation_s14.py`) all pass — comment-only changes confirmed safe.
- ✅ Full backend test suite shows zero regressions vs T-ACT-076 baseline.
- 🟡 Post-deploy validation (operator-observed): post-deploy `model_metadata`-style audit of inference-time feature distributions confirms `bb_pct_b`, `macd_signal`, `rv_20d`, `vix_5d_change` are no longer constant; LightGBM directional accuracy on labeled rows recovers materially toward the 52.92% training holdout floor (full closure deferred to T-ACT-085 / OHLC-dependent features still constant).

**Why subset over fully-original-prompt scope (Path Alpha consensus):** Cursor's Phase 1 Q1-Q14 critique surfaced three STOP-class issues in the original "populate all 6 unwritten keys" framing: (1) `self.spx_history` is `List[float]` of spot CLOSES capped at 60, not OHLC bars — `vwap_distance` (typical-price-based), `morning_range` (high/low/open), and `overnight_gap` (day-boundary anchored on first-bar-of-session) require an entire new data class the live pipeline does not maintain; (2) the `rv_20d` 5-min-basis buffer requires 1560 bars but `spx_history` holds only 60, implying either a 3-week cold-start or the new backfill mechanism added in this PR; (3) `tests/test_spx_daily_rv.py` was anti-Scope-B by docstring design and required ~150 LOC re-write. Operator independently verified all three findings against HEAD and authorized Path Alpha (subset to byte-for-byte-alignable features + B.1.iii backfill) over Path Beta (bundle OHLC fetch, ~570 LOC) and Path Gamma (close-only OHLC approximations, rejected per workflow rule #11 — feeding the model approximated distributions trained on real ones may be worse than constants). Three follow-up T-ACTs (T-ACT-084, T-ACT-085, T-ACT-086) opened to track the deferred work. Per workflow rule #16 (priority by consequential improvement), shipping 4 of the top-10 importance features now (macd_signal #6, rv_20d #2, partial fixes to iv_rv_ratio #4 and vix_term_ratio #8 via correct `rv_20d`, plus `vix_5d_change` #10 and `bb_pct_b`) is the high-value subset.

**Critique-first discipline (DIAGNOSE-FIRST applied):** Operator imposed a critique-first Q1-Q14 review before authorizing implementation. Cursor's Phase 1 critique came back YELLOW with three STOP-class issues (Q1: cache-class insufficiency for OHLC features; Q2: `rv_20d` buffer feasibility; Q7: anti-Scope-B test file); operator independently verified all three against HEAD code citations. Phase 2 was authorized as Path Alpha (subset) with the B.1.iii backfill amendment, T-ACT-083 governance bundled, and ~150 LOC test churn approved. Three follow-up T-ACTs queued for the deferred work.

**Why bundle T-ACT-083 governance into this PR (Q11 BUNDLE decision):** F-068-G reclassification + T-ACT-064 dependency note are governance changes that explain WHY this T-ACT exists. Shipping them in a separate later PR creates a window during which the action tracker / risk register narrative is incoherent with the merged code. Marginal review burden trivial vs. narrative-coherence preservation.

**Cross-references:**

- HANDOFF_NOTE_2026-05-07_T_ACT_082_FEATURE_PIPELINE.md (`trading-docs/06-tracking/`) — Q1-Q14 critique trace, Phase 2 implementation log, Path Alpha vs Beta vs Gamma comparison, B.1.iii backfill rationale
- F-068 model-quality investigation (`HANDOFF_NOTE_2026-05-06_*.md` series) — establishes the 31%-live vs 52.92%-training-holdout gap that motivated the T-ACT-082 candidate scoping
- F-068-G (S15 threshold-metric mismatch — initially DISSOLVED by T-ACT-076 conditionally, now RECLASSIFIED to feature-pipeline-incompleteness root cause per T-ACT-083 governance scope; the regime-dependent confound from T-ACT-076 Q5 remains a separate concern tracked under T-ACT-081)
- T-ACT-064 (post-upgrade LightGBM retraining decision tracking — newly BLOCKED on T-ACT-082 ship + 7 days of post-deploy production accuracy data; updated dependency note in T-ACT-083 governance bundle)
- T-ACT-077 (data-window hygiene — DEFERRED 2026-05-25; orthogonal to T-ACT-082, both targeting the production-quality gap from different angles)
- T-ACT-084 (NEW — daily-aligned VIX series, fixes `vix_close`/`vvix_close` daily-vs-realtime semantic shift)
- T-ACT-085 (NEW — SPX OHLC fetch + day-boundary state, fixes `vwap_distance`/`morning_range`/`overnight_gap`)
- T-ACT-086 (NEW — `polygon:spx:open` writer, fixes the new A.7-class instance Cursor caught at `shadow_engine.py:318`; this is the 8th A.7-family subclass)
- HANDOFF NOTE Appendix A.7 (silent-failure-class family — T-ACT-082 closes a sixth subclass: feature-pipeline-incompleteness, where consumer reads but no producer writes; complements T-ACT-076's class-space mismatch and T-ACT-067's schema-CHECK constraint mismatch)
- HANDOFF NOTE Appendix A.8 (post-upgrade retraining-decision discipline; T-ACT-082 ship + post-deploy data is the gating event for T-ACT-064's eventual decision)

---

### T-ACT-083 — F-068-G governance reclassification + T-ACT-064 dependency note (governance-only, bundled with T-ACT-082)

**Severity:** GOVERNANCE-ONLY (no code change; reclassifies F-068-G root cause and updates T-ACT-064 dependency to reflect the post-T-ACT-082 information state)
**Owner:** Cursor — implemented 2026-05-07 (bundled into PR `fix/t-act-082-feature-pipeline-completion`)
**Estimated time (actual):** ~10 min Cursor (drafting + cross-reference updates)
**Status:** [x] DONE — bundled

**Description:** F-068-G ("S15 threshold-metric mismatch — drift detector emitted `Critical + Z=0.00` against a structurally-collapsed `outcome_correct` distribution") was initially marked as conditionally DISSOLVED by T-ACT-076 Position 1a (binary-labeler fix) — under the assumption that the labeler class-space mismatch was the SOLE structural driver of the 6.1% post-hygiene accuracy reading. The 2026-05-07 model-quality investigation revealed a SECOND structural driver — feature-pipeline incompleteness — that was masked by the labeler bug. T-ACT-083 reclassifies F-068-G's primary root cause from "labeler class-space mismatch only" to "labeler class-space mismatch + feature-pipeline-incompleteness (compounding contributors)". Both T-ACT-076 and T-ACT-082 are needed to fully dissolve F-068-G's dual root causes; either fix shipped alone leaves a residual contributor.

T-ACT-064 (post-upgrade LightGBM retraining decision tracking) had previously listed T-ACT-061/T-ACT-062 as gating dependencies. T-ACT-083 adds T-ACT-082 ship + 7 days of post-deploy production-accuracy data as a NEW gating dependency: any retraining-decision SQL run before T-ACT-082's deploy would conflate "labeler-fixed feature-pipeline-incomplete distribution" with the eventual "labeler-fixed feature-pipeline-complete distribution" the retrained model would inherit. Operator must wait for both T-ACT-082's ship and the 7-day post-deploy window before invoking T-ACT-064's decision matrix.

**Bundled with T-ACT-082 (Q11 BUNDLE):** Governance changes that contextualize a code PR ride with that PR (workflow precedent established under T-ACT-076 / T-ACT-081 bundle 2026-05-07 morning).

**Cross-references:** T-ACT-082 (predecessor — surfaces the second structural driver of F-068-G that motivates the reclassification); T-ACT-076 / T-ACT-081 (predecessor — first structural driver of F-068-G + queued labeler-guard for the regime-dependent residual); T-ACT-064 (downstream — newly-blocked retraining decision); F-068 (parent finding); HANDOFF_NOTE_2026-05-07_T_ACT_082_FEATURE_PIPELINE.md.

---

### T-ACT-084 — Daily-aligned VIX/VVIX series for training-distribution alignment (queued; deferred from T-ACT-082)

**Severity:** MEDIUM (training uses `vix_close`/`vvix_close` from end-of-day Polygon daily aggregates, while live `polygon:vix:current`/`polygon:vvix:current` are real-time intraday quotes — same NAME, different statistical distribution. The model's tree-splits learned on EOD-aligned values are not exercised by the same-named real-time values. Affected derived features include `vix_z_score`, `vvix_z_score`, and the `vix_term_ratio` denominator.)
**Owner:** Cursor — to be authorized after T-ACT-082 + 7 days of post-deploy data
**Estimated time:** ~150 min Cursor (~100-150 LOC code: separate `vix_close_eod` / `vvix_close_eod` keys derived from `vix_daily_history[-1]` / `vvix_daily_history[-1]` updated only at the 21:00 UTC EOD gate, plus `prediction_engine.py:1085-1110` reader update + tests)
**Status:** [ ] QUEUED / DEFERRED — re-evaluate after T-ACT-082 post-deploy window

**Description:** Cursor's T-ACT-082 Phase 1 critique Q14 surfaced a daily-vs-realtime semantic shift on the `vix_close` and `vvix_close` features. Training (per `train_direction_model.py:271-272, 283-284`) uses `vix_close` / `vvix_close` from the daily aggregates parquet (one EOD value per session). The live inference site (`prediction_engine.py:1085-1110`) reads `polygon:vix:current` / `polygon:vvix:current` — JSON envelopes carrying real-time intraday quotes. Same key NAME, different statistical population. The fix requires a separate daily-aligned series in `polygon_feed.py` (sourced from the 21:00 UTC EOD append in `_store_vix_baseline`'s daily branch) under distinct keys `polygon:vix:close_eod` / `polygon:vvix:close_eod`, plus a reader-site change to consume those instead of `:current` for the model-feature path. Operator's original prompt suggested "<50 LOC" for this; Cursor's honest read is ~100-150 LOC including tests.

**Why DEFERRED, not bundled with T-ACT-082:** Path Alpha boundary (Phase 1 critique Q14 deferral). Bundling would push T-ACT-082's PR past the reviewable-in-one-sitting target (~370 + 150 LOC); separating it preserves T-ACT-082's narrow framing and lets the operator review the new VIX series as its own diff with explicit before/after distribution comparison.

**Decision matrix (re-evaluate post-T-ACT-082 deploy + 7 days):**

- **Path A (T-ACT-082 alone closes the production-vs-training accuracy gap to within 5%):** Park indefinitely. Document the daily-vs-realtime semantic shift as an accepted residual confound; no further action.
- **Path B (residual gap 5-15%):** Schedule T-ACT-084 as MEDIUM priority; closes the gap further.
- **Path C (residual gap > 15%):** Escalate to HIGH priority; bundle with T-ACT-085 (OHLC fetch) as a coordinated Phase 2 of T-ACT-082's Path Beta.

**Cross-references:** T-ACT-082 Phase 1 critique Q14; F-068 (parent finding); T-ACT-064 (downstream — gating dependency on T-ACT-084's ship if Path B/C selected).

---

### T-ACT-085 — SPX OHLC fetch + day-boundary state for vwap_distance / morning_range / overnight_gap (queued; deferred from T-ACT-082)

**Severity:** HIGH (these are the LARGEST feature-importance gaps remaining in production: `vwap_distance` is the #1-importance feature in the trained LightGBM model per `model_metadata.json`, `morning_range` is #7, and `overnight_gap` is also a top-quartile contributor. All three remain pinned at 0.0 in production until T-ACT-085 ships.)
**Owner:** Cursor — to be authorized after T-ACT-082 + post-deploy data confirms the residual gap
**Estimated time:** ~240 min Cursor (~200 LOC code + ~80 LOC tests: new SPX 5-min OHLC fetcher hitting `/v2/aggs/ticker/I:SPX/range/5/minute/today/today` per cycle + new `spx_5m_bars: List[dict]` buffer + day-boundary state for `prev_session_close`/`day_open`/`morning_high_low` + three new feature writers byte-aligned with `train_direction_model.py:249-264`)
**Status:** [ ] QUEUED / DEFERRED — re-evaluate after T-ACT-082 post-deploy window

**Description:** The live `polygon_feed.py` maintains `self.spx_history: List[float]` (60 spot CLOSES, no OHLC) and has no day-boundary state for `day_open` / `morning_high` / `morning_low`. Three of the model's high-importance features require this missing data class:

1. **`vwap_distance`** (training L249-253): `(close - vwap_typical_price) / vwap_typical_price` where `vwap_typical_price = expanding-day mean of (high+low+close)/3`. Requires 5-min OHLC + day-boundary reset at session open.
2. **`morning_range`** (training L255-264): `(morning_high - morning_low) / day_open` where `morning_high`/`morning_low` are computed over the first 30 minutes after the open (`minutes_from_open <= 30`). Requires high/low per bar + day-boundary anchor.
3. **`overnight_gap`** (training L220-227): `(first_bar_open - prev_session_close) / prev_session_close`, gated on `hour == 9` (only written on the open bar). Requires `day_open` (first 5-min bar's open) and `prev_session_close` (separate from `spx_prev_session_close` already maintained).

T-ACT-085 introduces the OHLC fetcher + buffer + day-boundary state + three writers. Tests must verify byte-for-byte alignment with training under cold-start, mid-session, and end-of-session conditions. Workflow rule #11 forbids approximations (close-only `vwap_distance` is REJECTED per Phase 1 critique Q3 because the model's tree-splits learned on true-typical-price distribution may behave worse on close-only than on the constant 0.0 it currently sees).

**Why DEFERRED, not bundled with T-ACT-082:** Path Alpha boundary. Bundling would push T-ACT-082's PR to ~570 LOC code + ~200 LOC tests (Path Beta) — past the reviewable-in-one-sitting target. Separating it preserves Path Alpha's narrow framing while keeping the highest-impact feature deferred to its own focused review.

**Decision matrix (re-evaluate post-T-ACT-082 deploy + 7 days):** Same Path A/B/C as T-ACT-084, with T-ACT-085 prioritized HIGHER (top-quartile feature importance > daily-vs-realtime confound) under any non-Path-A outcome.

**Cross-references:** T-ACT-082 Phase 1 critique Q1 (cache-class insufficiency for OHLC features); F-068 (parent finding); T-ACT-064 (downstream — gating dependency on T-ACT-085's ship if Path B/C selected); T-ACT-086 (sibling — `polygon:spx:open` writer is a strict subset of the day-boundary state added here, so could be subsumed if T-ACT-085 ships first).

---

### T-ACT-086 — polygon:spx:open writer (A.7-family 8th subclass, surfaced by T-ACT-082 Phase 1 critique)

**Severity:** MEDIUM (silent feature gap at `shadow_engine.py:318` — `polygon:spx:open` is read for shadow-mode comparisons but never written by any producer in the codebase. The shadow engine reads it via `_read_redis(..., None)` and presumably falls through to a default; the affected shadow-comparison logic is silently degraded but not broken. This is the 8th A.7-family subclass instance identified in the past 7 days.)
**Owner:** Cursor — to be authorized any time (independent of T-ACT-082 outcomes)
**Estimated time:** ~30 min Cursor (~20 LOC: `polygon_feed.py` writes `polygon:spx:open` once per session at the open-minute branch in `_poll_loop`, sourced from the first 5-min bar's open price returned by Polygon snapshot or the existing prev-session-close fetcher's open-of-current-day field)
**Status:** [ ] QUEUED — independent of T-ACT-082 critical-path

**Description:** Cursor's T-ACT-082 Phase 1 critique Q1 grep for unwritten Redis keys surfaced a NEW silent feature gap not previously in any T-ACT scope: `shadow_engine.py:318` reads `polygon:spx:open` but no producer writes that key. Polygon's `/v3/snapshot?ticker.any_of=I:SPX` response already carries `session.open` per upstream docs; the existing `_fetch_spx_price` (`polygon_feed.py:971-1076`) extracts only `session.close` / `session.last`. Adding a single setex with the response's `session.open` field at the once-per-session open-minute branch closes the gap.

This is the 8th A.7-family subclass instance counted in the past 7 days (alongside T-ACT-046 SPX `fetched_at`, T-ACT-047 `PostgrestAPIError`, T-ACT-055 persist-site audit, T-ACT-057 `.replace(" ", "")` whitespace strip, T-ACT-061 subscription-tier mismatch, T-ACT-067 schema-CHECK family, T-ACT-076 / T-ACT-082 themselves, etc.). The cumulative pattern is sufficient evidence for Section 14's "A.7 silent-failure-class family" framing to be re-elevated to a first-order architectural concern in the next governance review cycle.

**Why DEFERRED, not bundled with T-ACT-082:** A.7-family scope (small, independent fix); bundling would dilute T-ACT-082's narrow Path Alpha framing. Independent of T-ACT-082's success criteria; can ship any time.

**Cross-references:** T-ACT-082 Phase 1 critique Q1 (originating finding); HANDOFF NOTE Appendix A.7 (silent-failure-class family — T-ACT-086 = 8th subclass instance); `shadow_engine.py:318` (consumer site).

---

### T-ACT-087 — Railway deploy unblock via `railway.json` field reorder + `0.22.0` pin reaffirmation (recurrence of `2236558` regression triggered by PR #104 merge)

**Severity:** HIGH (production deploy fully blocked: PR #102 / #103 / #104 merged tonight but none are live because the post-merge Railway redeploy fails twice with `< failed to solve: frontend grpc server closed unexpectedly >`. Build log explicitly shows `using build driver railpack-v0.23.0` despite `railway.json` pinning `railpackVersion: "0.22.0"`. Same regression class that motivated `2236558` (Apr 23): Railway runner silently overrides the pin under specific cache states.)
**Owner:** Cursor — implemented 2026-05-07 ~22:00 ET via PR `fix/t-act-087-railway-cache-bust-pin-reaffirmation`
**Estimated time (actual):** ~90 min Cursor (DIAGNOSE-FIRST read-only investigation + Phase 1 critique with two STOP-class catches + Path 4-A implementation)
**Status:** [x] DONE — pushed (pending operator merge + post-deploy verification)

**Description:** Tonight's deploy of T-ACT-082 + T-ACT-083 (`7567551`, PR #104) failed twice with the BuildKit grpc-frontend crash. Operator-pulled Railway dashboard data confirmed: (1) the previous successful deploy was T-ACT-076 (`1ac7209`, PR #103) ~14 hours earlier on Railpack 0.22.0; (2) `RAILPACK_VERSION` is unset in dashboard variables (no env-var override fighting the file pin); (3) the failure correlates exactly with the PR #104 merge event. Diagnosis verdict: PR #104 merge invalidated Railway's cached build plan; cache regeneration somewhere in the runner stack stopped honoring the `railpackVersion: "0.22.0"` pin in `railway.json`; Railpack 0.23.0 was used instead and crashed at the LLB-emit / BuildKit-frontend layer. Code/config-as-checked-in is structurally identical to the deploy state that worked for 14 days — the platform-side runner's Railpack binary acquisition path has changed under us, mirroring the original `2236558` regression pattern.

**Fix shipped:**

1. **`railway.json` field reorder (Commit 1, `374f7f0`):** moved `deploy` block above `build` block. All four fields (`$schema`, `deploy.startCommand`, `build.builder`, `build.railpackVersion`) preserved with original values. Diff is pure reorder (3 insertions / 3 deletions). File content hash changes (`a4b7f9d → e9b5bc0`) — sufficient to invalidate any cache keyed on byte-level file hash. Pin value held at `0.22.0`. Builder held at `RAILPACK`. No new fields added; no schema-validation risk.

2. **`TASK_REGISTER.md` T-ACT-087 entry (Commit 2, this commit):** governance entry mirroring T-ACT-072 / T-ACT-082 format; bundled per Phase 1 critique Q4 (1+1+1 split: railway.json + TASK_REGISTER in this PR; handoff note as a separate documentation PR within the week to avoid diluting the surgical 1-line config fix with 200-400 lines of post-mortem narrative).

**Acceptance criteria:**

- ✅ `railway.json` is valid JSON (verified via `python3 -c "import json; json.load(open('railway.json'))"`).
- ✅ All four fields preserved with original values (`$schema`, `deploy.startCommand`, `build.builder`, `build.railpackVersion`).
- ✅ Pin value remains `0.22.0` (workflow rule #11 ROI preservation gate; §3 forbidden-changes list).
- ✅ Builder remains `RAILPACK`; no switch to nixpacks/Dockerfile.
- 🟡 Post-deploy validation (operator-observed at T+0 to T+5 min): build log shows `using build driver railpack-v0.22.0` (NOT `0.23.0`); Railpack proceeds through `pip install` and uvicorn startup without grpc crash; service comes up green; `/health` returns 200.
- 🟡 If F1 fails at deploy time (build log still shows `railpack-v0.23.0` OR same grpc error): **HALT** per §0 hard rule #8 — do NOT auto-escalate to F1-secondary (`RAILPACK_VERSION` env var) or F2-F4 (schema migration / nixpacks revert / Dockerfile). Operator decides next step with fresh context.

**Mechanism uncertainty (Phase 1 critique Q2 — flagged in PR body verbatim):** The `24fd7ba` cache-bust precedent (Apr 22) was followed by 9 additional deploy-fix commits before stability returned (`55c8cc5` Dockerfile attempt → `46ec071` builder pin → `17e6d6a` shell-form CMD → `63c7ed8` PORT default → `b183858` revert to nixpacks → `1b6a38e` builder set → `d84f885` python -m pip → `f2c0b40` RAILPACK pin → `2236558` 0.22.0 pin). Whether `24fd7ba` itself unblocked deploys or whether downstream commits were the actual unblocker cannot be resolved from git history alone. T-ACT-087's success at unblocking tonight is best-effort, not high-confidence. Deploy success at T+5 min is the only definitive test.

**Path 4-A specific uncertainty:** This PR uses field reorder (move `deploy` above `build`) as the cache-bust mechanism. If Railway canonicalizes JSON (alphabetical key sort) before computing cache keys, this reorder is a no-op and provides no cache invalidation. If Railway uses byte-level content hash, the reorder works. We cannot determine which from outside Railway's runner. Accept that this is best-effort.

**Critique-first discipline (DIAGNOSE-FIRST applied):** Operator imposed a Phase 1 critique-first review before authorizing implementation. Cursor's Phase 1 critique surfaced two STOP-class issues:

- **Q1 STOP — `_cacheBust` field rejected by Railway schema.** I fetched `https://railway.app/railway.schema.json` and confirmed the root object has `additionalProperties: false` enclosing the four allowed top-level properties (`$schema`, `build`, `deploy`, `environments`). The originally-proposed `_cacheBust` field would have caused config-parse rejection, making the deploy WORSE than tonight (different error, same blocked state).
- **Q2 STOP — `watchPatterns: ["**/*"]` operational semantic divergence.** Railway docs explicitly state watchPatterns are gitignore-style **filters that conditionally trigger deploys** (`https://docs.railway.com/builds/build-configuration#configure-watch-paths`). The docs' canonical "match all" pattern is `**` (not `**/*`); `**/*` may exclude root files under strict gitignore semantics, introducing a silent deploy-trigger regression on root-file-only changes. This violated workflow rule #11 ROI watch-list "Disable/downgrade monitoring / logging / audit." Operator + Cursor consensus moved to Path 4-A (field reorder) — zero new schema fields, zero operational semantic changes, content hash still changes.

**Why bundle TASK_REGISTER but NOT handoff into this PR (Q4 BUNDLE decision):** TASK_REGISTER entry is governance-required (constitutional rule + ACT-012 phase-gate verification protocol) and ~25 LOC. Handoff note would be ~200-400 LOC, dwarfing the 1-line config fix at 200:1 reviewer ratio. 1+1+1 split: railway.json + TASK_REGISTER ship now; handoff note ships as separate documentation PR within the week (preserves narrow-PR-review discipline + governance completeness).

**Cross-references:**

- `2236558` (2026-04-23) — original 0.22.0 pin commit; verbatim body cites *"providers override regression in 0.23.0"* and the silent runner-side Railpack version upgrade pattern this T-ACT recurs against
- `24fd7ba` (2026-04-22) — cache-bust precedent (mechanism mirrored here for Railpack-instead-of-Nixpacks); verbatim body cites *"Railway can reuse a stale cached build plan even when new commits land"*
- `35c448c` (2026-04-30) — last deploy-config edit before tonight (T-ACT-043 libgomp1 fix); confirms zero root-file changes in PRs #102/#103/#104 since this commit (Railpack provider-detection surface unchanged)
- T-ACT-082 / T-ACT-083 (PR #104 merge — the cache-invalidation trigger; merging itself broke the deploy, not anything in the PR's code or config)
- T-ACT-076 (PR #103) — last successful deploy at Railpack 0.22.0 (~14h prior)
- T-ACT-072 (PR #102) — preceding Databento age filter; deployed successfully in same 14h window
- §3 forbidden-changes list from operator's Phase 2 prompt (pin value, builder value, startCommand, railpack.json, requirements.txt, application code, dashboard env vars — all preserved)
- HANDOFF_NOTE_2026-05-07_T_ACT_087_RAILWAY_CACHE_BUST.md (`trading-docs/06-tracking/`) — to be shipped as separate documentation PR within the week (forensic timeline, recurring-pattern documentation, tracked follow-up to re-validate Railpack pin every 2-3 weeks)

---

### Section 14 cross-references

- HANDOFF NOTE Appendix A.6 — full post-mortem context for the 2026-05-01 phantom-alpha incident (amended 2026-05-03 via Track B PR with T-ACT-045 PENDING-RE-RUN status + validation-artifact protocol)
- HANDOFF NOTE Appendix A.7 — silent-failure-class family convention pointer (ratified 2026-05-03 via Track B PR; bundles A.5/A.6/T-ACT-046/T-ACT-054 under a single discipline lens; reopened/expanded 2026-05-02 via T-ACT-055/057)
- HANDOFF NOTE Appendix A.8 — Subscription tier mismatch outage (76 hours; 2026-05-04 lessons-learned; ratified via this PR `docs/post-incident-indices-advanced-2026-05-04`)
- HANDOFF_NOTE_2026-05-04_INDICES_OUTAGE.md (`trading-docs/06-tracking/`) — full diagnostic record for the 2026-05-01 → 2026-05-04 prediction outage; §7.1 manual API probe defines the verification gate for T-ACT-061 closure
- PR #90 risks R-1 (T-ACT-046) and R-2 (T-ACT-047) — original risk identification
- PR #92 (T-ACT-046, 2026-05-02) — outage trigger via `polygon:spx:current.fetched_at` semantics flip (correct fix that exposed underlying tier mismatch)
- PR `feat/t-act-062-vix-vvix-freshness-guard` (T-ACT-062, 2026-05-04 late evening) — VVIX/VIX/VIX9D freshness guard + 330s constant extraction; closes the derived-feature freshness coverage gap identified in HANDOFF_NOTE_2026-05-04_INDICES_OUTAGE.md §8.3
- PR `fix/t-act-072-databento-ts-event-age-filter` (T-ACT-072, 2026-05-06 mid-RTH) — Producer-side `ts_event` age filter on Databento OPRA trades; closes the frankenstein-record surface identified in HANDOFF_NOTE_2026-05-06_DATABENTO_PUSH_LIFECYCLE.md and the symptomatic warnings identified in HANDOFF_NOTE_2026-05-06_GEX_QUOTE_MISSING.md
- HANDOFF_NOTE_2026-05-06_DATABENTO_PUSH_LIFECYCLE.md (`trading-docs/06-tracking/`) — diagnostic for the 2026-05-06 pre-RTH frankenstein-record / Databento backfill pattern; predecessor for T-ACT-072
- HANDOFF_NOTE_2026-05-06_GEX_QUOTE_MISSING.md (`trading-docs/06-tracking/`) — diagnostic for `gex_quote_missing_after_rest` warnings; same root cause addressed by T-ACT-072
- PR `fix/t-act-076-binary-labeler-position-1a` (T-ACT-076 + T-ACT-081 governance, 2026-05-07) — Position 1a binary labeler (F-068-I dissolution) + bundled `drift_status` CHECK widening + narrow `PostgrestAPIError` classifier (F-068-A closure); same A.7-family pattern as T-ACT-047; amends §A.7 post-deploy SQL with a `pred_direction × outcome_direction` crosstab to quantify Q5 magnitude
- HANDOFF_NOTE_2026-05-06_F068I_BINARY_LABELER_FIX.md (`trading-docs/06-tracking/`) — original-intent forensic + Q1-Q12 critique + Phase 2 amendments for T-ACT-076; Q5 regime-dependent confound; T-ACT-081 deferral rationale
- PR `fix/t-act-082-feature-pipeline-completion` (T-ACT-082 + T-ACT-083 governance, 2026-05-07) — Path Alpha subset feature-pipeline completion: 3 byte-for-byte writers (`bb_pct_b`, `macd_signal`, `vix_5d_change`) + `rv_20d` 5-min basis with B.1.iii startup backfill, byte-aligned with `train_direction_model.py`; supersedes 12A daily-basis writer; bundles F-068-G reclassification + T-ACT-064 dependency note. CRITIQUE-FIRST Q1-Q14 discipline applied; YELLOW authorization with B.1.iii backfill amendment + ~150 LOC test churn approved; three follow-up T-ACTs (T-ACT-084, T-ACT-085, T-ACT-086) opened for deferred work
- HANDOFF_NOTE_2026-05-07_T_ACT_082_FEATURE_PIPELINE.md (`trading-docs/06-tracking/`) — Q1-Q14 critique trace, Path Alpha vs Beta vs Gamma comparison, B.1.iii backfill rationale, deferred-work scoping for T-ACT-084/085/086
- PR `fix/t-act-087-railway-cache-bust-pin-reaffirmation` (T-ACT-087, 2026-05-07 ~22:00 ET) — Railway deploy unblock via `railway.json` field reorder + `0.22.0` pin reaffirmation. Recurrence of `2236558` regression triggered by PR #104 merge cache invalidation; mirrors `24fd7ba` cache-bust precedent (mechanism adapted from Nixpacks-comment-marker to JSON-key-reorder since JSON has no comment syntax). CRITIQUE-FIRST Phase 1 discipline applied; two STOP-class issues caught and resolved before ship: (1) `_cacheBust` schema rejection per `https://railway.app/railway.schema.json` root-level `additionalProperties: false`; (2) `watchPatterns: ["**/*"]` operational semantic divergence per `https://docs.railway.com/builds/build-configuration#configure-watch-paths` gitignore-style filter semantics. Path 4-A (field reorder, zero new fields, zero semantic change) shipped under both safety nets. Mechanism uncertainty (Phase 1 Q2: `24fd7ba` precedent's success unverified; followed by 9 deploy-fix commits) flagged in PR body verbatim. §0 hard rule #8 (no auto-escalate on F1 failure) explicitly affirmed in PR body. Handoff note (`HANDOFF_NOTE_2026-05-07_T_ACT_087_RAILWAY_CACHE_BUST.md`) deferred to separate documentation PR within the week (1+1+1 governance split). No tests required per §0 hard rule #7 — deploy success at T+5 min is the only definitive test
- HANDOFF NOTE Appendix A.5 mitigation #3 — original lesson surfacing the try/except discipline issue
- SUBSCRIPTION_REGISTRY.md — canonical reference for subscription-vs-runtime audit (mitigation #2 in A.6); §1A tier comparison matrix for Polygon Indices added 2026-05-04 evening
- T-ACT-054 cv_stress design memo (Cursor 2026-05-03) — Choice A NULL-on-degenerate-input selected; remediation DONE 2026-05-02

*Section 14 opened: 2026-05-01 | Owner: tesfayekb. Amended 2026-05-03 via Track B PR (T-ACT-045 status update; T-ACT-046 scope expansion; T-ACT-048/050/051/054 added; T-ACT-049 subsumed per numbering note above). Amended 2026-05-04 evening via PR `docs/post-incident-indices-advanced-2026-05-04` (T-ACT-061 closed-resolved subscription upgrade; T-ACT-062 queued VVIX/VIX/VIX9D freshness; T-ACT-063 queued email egress; T-ACT-064 informational retraining decision tracking; HANDOFF NOTE Appendix A.8 added; HANDOFF_NOTE_2026-05-04_INDICES_OUTAGE.md relocated from repo root). Amended 2026-05-04 late evening via PR `feat/t-act-062-vix-vvix-freshness-guard` (T-ACT-062 EXECUTE shipped — VVIX/VIX/VIX9D freshness guard via Option β soft-warn per SD-1, 330s constant extracted to `POLYGON_FRESHNESS_THRESHOLD_SECONDS`, new `polygon_index_helpers.py` shared parser module, 19 new unit tests, T-ACT-061 §7.1 gate waived per SD-5 operator instruction; T-ACT-065 evaluation window opened with due date 2026-05-12). Amended 2026-05-06 mid-RTH via PR `fix/t-act-072-databento-ts-event-age-filter` (T-ACT-072 EXECUTE shipped — producer-side `ts_event` age filter on Databento OPRA trades closes the frankenstein-record surface; CRITIQUE-FIRST Q1-Q8 discipline applied per markets-open / "do not cause further break" operator mandate; YELLOW authorization with three modifications: instance-variable counter, fixture-default refresh, variable-name correction `ts_ns`; four new tests; updated `_mk_trade_mock` default to `time.time_ns()` to keep three pre-existing tests passing). Amended 2026-05-07 via PR `fix/t-act-076-binary-labeler-position-1a` (T-ACT-076 EXECUTE shipped — F-068-I Position 1a binary-labeler fix matching `train_direction_model.py:323-325` byte-for-byte, bundled with F-068-A schema-CHECK widening on `trading_model_performance.drift_status` + narrow `PostgrestAPIError` classifier in `run_weekly_model_performance` per T-ACT-047 Choice C precedent. CRITIQUE-FIRST Q1-Q12 discipline applied; YELLOW authorization with three Phase 2 governance amendments: explicit Q5 regime-dependent confound documentation, T-ACT-081 added as queued-deferred entry, post-deploy verification SQL expanded with `pred_direction × outcome_direction` crosstab. Eight new tests (3 in `test_phase_a1.py` + 5 in `test_t_act_076_weekly_perf_persistent_error.py`); zero suite regressions confirmed via stash-and-baseline comparison. Amended 2026-05-07 via PR `fix/t-act-082-feature-pipeline-completion` (T-ACT-082 EXECUTE shipped — Path Alpha subset feature-pipeline completion: 3 new byte-for-byte writers (`polygon:spx:bb_pct_b`, `polygon:spx:macd_signal`, `polygon:vix:5d_change`) byte-aligned with `train_direction_model.py:237-298` + `polygon:spx:realized_vol_20d` migrated from 12A daily-basis (`sqrt(252)`) to 5-min basis (`sqrt(252*78)`) with new 1560-bar buffer + B.1.iii Polygon `/v2/aggs` startup backfill eliminating 3-week cold-start; T-ACT-083 governance reclassification of F-068-G + T-ACT-064 dependency note bundled; T-ACT-084 (daily-aligned VIX series), T-ACT-085 (SPX OHLC fetch + day-boundary state), T-ACT-086 (`polygon:spx:open` writer / 8th A.7-family subclass) opened as queued-deferred entries. CRITIQUE-FIRST Q1-Q14 discipline applied; YELLOW authorization after Phase 1 surfaced three STOP-class issues (cache-class insufficiency for OHLC features, 1560-bar buffer feasibility, anti-Scope-B test file) — operator independently verified all three then authorized Path Alpha subset over Path Beta (bundle OHLC, ~570 LOC) and Path Gamma (close-only approximations, rejected per workflow rule #11). 18 new tests (8 in `test_spx_5m_basis_rv.py` superseding `test_spx_daily_rv.py` + 10 in `test_t_act_082_feature_writers.py`); zero suite regressions confirmed. Amended 2026-05-07 ~22:00 ET via PR `fix/t-act-087-railway-cache-bust-pin-reaffirmation` (T-ACT-087 EXECUTE shipped — Railway deploy unblock via `railway.json` field reorder (`deploy` block moved above `build` block; 3+/3- diff; pure reorder, all four field values preserved at originals; content hash changes `a4b7f9d → e9b5bc0`). Recurrence of `2236558` regression triggered by PR #104 merge cache invalidation; mirrors `24fd7ba` cache-bust precedent (mechanism adapted for JSON since JSON has no comment syntax). CRITIQUE-FIRST Phase 1 discipline applied; two STOP-class issues caught and resolved before Phase 2 implementation: (1) `_cacheBust` field schema rejection — Cursor fetched `https://railway.app/railway.schema.json` and proved root-level `additionalProperties: false` would have caused config-parse failure; (2) `watchPatterns: ["**/*"]` operational semantic divergence — Railway docs explicitly define watchPatterns as gitignore-style filters that conditionally trigger deploys (canonical "match all" pattern is `**`, not `**/*`), introducing potential silent deploy-trigger regression on root-file-only changes. Operator-authorized Path 4-A (field reorder) consensus over Path 4-D (`watchPatterns`) and original `_cacheBust` proposal under both safety nets. Mechanism uncertainty (Phase 1 Q2: `24fd7ba` precedent's success unverified; followed by 9 additional deploy-fix commits before stability returned) flagged in PR body verbatim. §0 hard rule #8 (no auto-escalate on F1 failure to F1-secondary or F2-F4) explicitly affirmed in PR body and in T-ACT-087 acceptance criteria. Bundle decision: 1+1+1 split (railway.json + TASK_REGISTER in this PR; handoff note as separate documentation PR within the week to preserve narrow-PR-review discipline against 200:1 reviewer-ratio dilution). No tests required per §0 hard rule #7 — deploy success at T+5 min (build log shows `using build driver railpack-v0.22.0` AND service comes up green) is the only definitive test.*

---

*Task Register v1.0 — April 2026 — tesfayekb*
