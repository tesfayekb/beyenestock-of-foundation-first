# MARKETMUSE — Master Specification
**Version:** 4.0 — FINAL SINGLE SOURCE OF TRUTH  
**Date:** 2026-04-16  
**Owner:** tesfayekb  
**Repo:** https://github.com/tesfayekb/beyenestock-of-foundation-first.git  
**Foundation repo:** https://github.com/tesfayekb/beyenestock-of-foundation-first.git  
**Status:** PLANNING COMPLETE — BUILD BEGINS FROM THIS DOCUMENT

> This is the only document needed. All prior planning files (DECISIONS.md, FINAL_SPEC.md,
> MARKETMUSE_PROJECT_PLAN.md, SYNTHESIS.md) are superseded by this document.
> Feed this file to Lovable and Cursor directly.

---

## PART 1 — MISSION AND SCOPE

### What We Are Building
An AI-powered options trading system for a single operator. The system watches the market every trading day, runs institutional-grade AI prediction, selects optimal options strategies, and executes trades automatically on the operator's Tradier account. Every decision, signal, position, and outcome is recorded and visible in a War Room admin dashboard built on the existing foundation.

### What We Are NOT Building (V1)
- No multi-user mirroring — single operator only
- No user enrollment or tier system
- No subscription pricing
- No social or copy-trading features
- No futures, crypto, or international instruments

Multi-user mirroring is explicitly V2. The entire edge and profitability of the system is captured in V1 with a single account. Build the edge first. Add users once it is proven.

### The Prime Directive
Every architectural decision, every feature, every line of code must answer: **does this make the system more profitable or better protect capital?** If the answer is not a clear yes, it does not belong in V1.

---

## PART 2 — EXISTING FOUNDATION (DO NOT REBUILD)

The foundation at `beyenestock-of-foundation-first` is production-grade and must be preserved exactly as built.

### Existing Database Tables (DO NOT MODIFY)
```
alert_configs          alert_history          audit_logs
invitations            job_executions         job_idempotency_keys
job_registry           mfa_recovery_attempts  mfa_recovery_codes
permissions            profiles               role_permissions
roles                  system_config          system_health_snapshots
system_metrics         user_roles
```

### Profiles Table — Current Columns
`id, display_name, last_name, email, email_verified, avatar_url, status, created_at, updated_at`

**Add only:** `trading_tier TEXT DEFAULT 'operator'`, `tradier_connected BOOLEAN DEFAULT false`, `tradier_account_id TEXT`

### Existing Roles
`superadmin` (full access), `admin` (all except emergency/permission assign), `user` (self-scope only)

### Existing Permission Keys (Naming Convention to Follow)
```
roles.*     permissions.*    users.*      profile.*
mfa.*       session.*        admin.*      audit.*
monitoring.* jobs.*
```

### Existing Frontend Architecture Patterns
Every new page and component must follow these patterns exactly:

**Navigation:** Config-driven via `src/config/admin-navigation.ts` → `adminNavigation` array
**Routes:** Centralized in `src/config/routes.ts`
**Layout:** `AdminLayout` → `DashboardLayout` → `RequirePermission` with permission gate
**Lazy loading:** All admin pages use `lazy(() => import('./pages/admin/PageName'))`
**Data fetching:** `useQuery` from TanStack Query, single combined query where possible
**Components:** `PageHeader`, `StatCard`, `LoadingSkeleton`, `ErrorState`, `Card`, `Badge`, `Tabs`
**Auth guard:** `RequirePermission` with `fallback={<AccessDenied />}`
**Error handling:** Every query has loading and error states

**CRITICAL: Trading health monitoring uses `trading_*` prefixed tables.
`system_health_snapshots` and `system_metrics` are INFRASTRUCTURE health.
Trading engine health is SEPARATE. Never mix the two.**

---

## PART 3 — ALL LOCKED DECISIONS (22 TOTAL)

| ID | Decision | Value |
|---|---|---|
| D-001 | Instruments | SPX, XSP, NDX, RUT only (Section 1256) |
| D-002 | Primary mode | 0DTE |
| D-003 | Secondary mode | 1–5 day swing, regime-gated, system decides |
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

## PART 4 — TRADING DATABASE SCHEMA

All trading tables use `trading_` prefix to be completely isolated from foundation tables.
All follow the same conventions: UUID PKs, timestamptz, snake_case, RLS enabled.

### 4.1 Profiles Extension (ALTER, not new table)
```sql
ALTER TABLE public.profiles
  ADD COLUMN IF NOT EXISTS trading_tier     TEXT DEFAULT 'operator',
  ADD COLUMN IF NOT EXISTS tradier_connected BOOLEAN DEFAULT false,
  ADD COLUMN IF NOT EXISTS tradier_account_id TEXT;
```

### 4.2 New Trading Permissions to Seed
```sql
INSERT INTO public.permissions (key, description) VALUES
  ('trading.view',         'View trading signals, positions, and performance'),
  ('trading.admin',        'Full trading system administration'),
  ('trading.execute',      'Allow system to execute trades on connected account'),
  ('trading.kill_switch',  'Activate emergency trading halt'),
  ('trading.configure',    'Configure trading parameters and thresholds');
```

### 4.3 New Admin Route Permissions — Add to Admin Role
```sql
INSERT INTO public.role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM public.roles r, public.permissions p
WHERE r.key = 'admin'
  AND p.key IN ('trading.view','trading.admin','trading.kill_switch','trading.configure');
```

### 4.4 trading_operator_config
Stores the single operator's Tradier credentials and sizing phase.
```sql
CREATE TABLE public.trading_operator_config (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id               UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  tradier_account_id    TEXT,
  tradier_key_preview   TEXT,       -- last 4 chars only, for display
  encrypted_key         TEXT,       -- pgcrypto encrypted, never exposed to frontend
  account_type          TEXT CHECK (account_type IN ('margin','cash','sandbox')),
  is_sandbox            BOOLEAN DEFAULT true,
  sizing_phase          INTEGER DEFAULT 1 CHECK (sizing_phase BETWEEN 1 AND 4),
  live_trading_enabled  BOOLEAN DEFAULT false,
  created_at            TIMESTAMPTZ DEFAULT now(),
  updated_at            TIMESTAMPTZ DEFAULT now(),
  UNIQUE(user_id)
);
ALTER TABLE public.trading_operator_config ENABLE ROW LEVEL SECURITY;
CREATE POLICY "operator_own_config" ON public.trading_operator_config
  FOR ALL USING (user_id = auth.uid());
```

### 4.5 trading_sessions
One record per trading day. Created by Python at 9:00 AM, closed at 4:30 PM.
```sql
CREATE TABLE public.trading_sessions (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_date          DATE NOT NULL UNIQUE,
  day_type              TEXT CHECK (day_type IN ('trend','open_drive','range','reversal','event','unknown')),
  day_type_confidence   NUMERIC(5,4),
  regime                TEXT CHECK (regime IN ('quiet_bullish','volatile_bullish','quiet_bearish','crisis','pin_range','panic','unknown')),
  rcs                   NUMERIC(5,2),
  allocation_tier       TEXT CHECK (allocation_tier IN ('full','moderate','low','pre_event','danger','cash')),
  vix_open              NUMERIC(8,4),
  vvix_open             NUMERIC(8,4),
  vvix_20d_mean         NUMERIC(8,4),
  vvix_20d_std          NUMERIC(8,4),
  spx_open              NUMERIC(10,4),
  session_status        TEXT DEFAULT 'pending' CHECK (session_status IN ('pending','active','halted','closed')),
  halt_reason           TEXT,
  capital_preservation_active BOOLEAN DEFAULT false,
  consecutive_losses_today    INTEGER DEFAULT 0,
  consecutive_loss_sessions   INTEGER DEFAULT 0,
  virtual_pnl           NUMERIC(12,4) DEFAULT 0,
  virtual_trades_count  INTEGER DEFAULT 0,
  virtual_wins          INTEGER DEFAULT 0,
  virtual_losses        INTEGER DEFAULT 0,
  actual_pnl            NUMERIC(12,4),
  market_open_at        TIMESTAMPTZ,
  market_close_at       TIMESTAMPTZ,
  created_at            TIMESTAMPTZ DEFAULT now(),
  updated_at            TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_trading_sessions_date ON public.trading_sessions(session_date DESC);
ALTER TABLE public.trading_sessions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "authenticated_read_sessions" ON public.trading_sessions
  FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "service_write_sessions" ON public.trading_sessions
  FOR ALL USING (auth.role() = 'service_role');
```

### 4.6 trading_prediction_outputs
Every 5-minute prediction cycle output, every trading day.
```sql
CREATE TABLE public.trading_prediction_outputs (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id            UUID REFERENCES public.trading_sessions(id),
  predicted_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  p_bull                NUMERIC(5,4),
  p_bear                NUMERIC(5,4),
  p_neutral             NUMERIC(5,4),
  direction             TEXT CHECK (direction IN ('bull','bear','neutral')),
  confidence            NUMERIC(5,4),
  expected_move_pts     NUMERIC(8,4),
  expected_move_pct     NUMERIC(8,6),
  gex_net               NUMERIC(15,2),
  gex_nearest_wall      NUMERIC(10,4),
  gex_flip_zone         NUMERIC(10,4),
  gex_confidence        NUMERIC(5,4),
  cv_stress_score       NUMERIC(5,2),
  charm_velocity        NUMERIC(12,8),
  vanna_velocity        NUMERIC(12,8),
  regime                TEXT,
  rcs                   NUMERIC(5,2),
  regime_hmm            TEXT,
  regime_lgbm           TEXT,
  regime_agreement      BOOLEAN DEFAULT true,
  no_trade_signal       BOOLEAN DEFAULT false,
  no_trade_reason       TEXT,
  capital_preservation_mode BOOLEAN DEFAULT false,
  execution_degraded    BOOLEAN DEFAULT false,
  spx_price             NUMERIC(10,4),
  vix                   NUMERIC(8,4),
  vvix                  NUMERIC(8,4),
  vvix_z_score          NUMERIC(6,3),
  job_execution_id      UUID REFERENCES public.job_executions(id),
  created_at            TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_prediction_session ON public.trading_prediction_outputs(session_id, predicted_at DESC);
CREATE INDEX idx_prediction_time    ON public.trading_prediction_outputs(predicted_at DESC);
ALTER TABLE public.trading_prediction_outputs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "authenticated_read_predictions" ON public.trading_prediction_outputs
  FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "service_write_predictions" ON public.trading_prediction_outputs
  FOR ALL USING (auth.role() = 'service_role');
```

### 4.7 trading_signals
The system's decision to open a virtual or real trade.
```sql
CREATE TABLE public.trading_signals (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id            UUID REFERENCES public.trading_sessions(id),
  prediction_id         UUID REFERENCES public.trading_prediction_outputs(id),
  signal_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
  instrument            TEXT NOT NULL CHECK (instrument IN ('SPX','XSP','NDX','RUT')),
  strategy_type         TEXT NOT NULL CHECK (strategy_type IN (
    'put_credit_spread','call_credit_spread','iron_condor','iron_butterfly',
    'debit_put_spread','debit_call_spread','long_put','long_call'
  )),
  position_type         TEXT CHECK (position_type IN ('core','satellite')),
  short_strike          NUMERIC(10,2),
  long_strike           NUMERIC(10,2),
  short_strike_2        NUMERIC(10,2),
  long_strike_2         NUMERIC(10,2),
  expiry_date           DATE,
  target_credit         NUMERIC(8,4),
  target_debit          NUMERIC(8,4),
  predicted_slippage    NUMERIC(8,4),
  ev_net                NUMERIC(8,4),
  stop_loss_level       NUMERIC(8,4),
  profit_target         NUMERIC(8,4),
  touch_prob_at_entry   NUMERIC(5,4),
  sigma_effective       NUMERIC(10,8),
  regime_at_signal      TEXT,
  rcs_at_signal         NUMERIC(5,2),
  cv_stress_at_signal   NUMERIC(5,2),
  gex_wall_distance_pct NUMERIC(8,4),
  gex_confidence_at_signal NUMERIC(5,4),
  contracts             INTEGER,
  position_size_pct     NUMERIC(5,4),
  signal_status         TEXT DEFAULT 'pending' CHECK (signal_status IN (
    'pending','executed','expired','rejected','cancelled'
  )),
  rejection_reason      TEXT,
  job_execution_id      UUID REFERENCES public.job_executions(id),
  correlation_id        TEXT,
  created_at            TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_signal_session ON public.trading_signals(session_id, signal_at DESC);
CREATE INDEX idx_signal_status  ON public.trading_signals(signal_status, created_at DESC);
ALTER TABLE public.trading_signals ENABLE ROW LEVEL SECURITY;
CREATE POLICY "authenticated_read_signals" ON public.trading_signals
  FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "service_write_signals" ON public.trading_signals
  FOR ALL USING (auth.role() = 'service_role');
```

### 4.8 trading_positions
Open and closed positions — both virtual (paper) and actual (live).
```sql
CREATE TABLE public.trading_positions (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  signal_id             UUID REFERENCES public.trading_signals(id),
  session_id            UUID REFERENCES public.trading_sessions(id),
  position_mode         TEXT NOT NULL CHECK (position_mode IN ('virtual','live')),
  instrument            TEXT NOT NULL,
  strategy_type         TEXT NOT NULL,
  position_type         TEXT CHECK (position_type IN ('core','satellite')),
  -- Entry
  entry_at              TIMESTAMPTZ NOT NULL,
  entry_credit          NUMERIC(8,4),
  entry_slippage        NUMERIC(8,4),
  entry_spx_price       NUMERIC(10,4),
  entry_regime          TEXT,
  entry_rcs             NUMERIC(5,2),
  entry_cv_stress       NUMERIC(5,2),
  entry_touch_prob      NUMERIC(5,4),
  entry_greeks          JSONB,
  -- Strikes
  short_strike          NUMERIC(10,2),
  long_strike           NUMERIC(10,2),
  short_strike_2        NUMERIC(10,2),
  long_strike_2         NUMERIC(10,2),
  expiry_date           DATE,
  contracts             INTEGER,
  -- Live execution (null for virtual)
  tradier_order_id      TEXT,
  tradier_fill_price    NUMERIC(8,4),
  -- Active management
  current_state         INTEGER DEFAULT 1 CHECK (current_state BETWEEN 1 AND 5),
  current_pnl           NUMERIC(10,4) DEFAULT 0,
  peak_pnl              NUMERIC(10,4) DEFAULT 0,
  current_touch_prob    NUMERIC(5,4),
  current_cv_stress     NUMERIC(5,2),
  last_updated_at       TIMESTAMPTZ DEFAULT now(),
  -- Exit
  exit_at               TIMESTAMPTZ,
  exit_credit           NUMERIC(8,4),
  exit_slippage         NUMERIC(8,4),
  exit_reason           TEXT CHECK (exit_reason IN (
    'profit_target','stop_loss','time_stop_230pm','time_stop_345pm',
    'touch_prob_threshold','cv_stress_trigger','state4_degrading',
    'portfolio_stop','circuit_breaker','capital_preservation','manual'
  )),
  exit_spx_price        NUMERIC(10,4),
  -- P&L
  gross_pnl             NUMERIC(10,4),
  slippage_cost         NUMERIC(8,4),
  commission_cost       NUMERIC(8,4),
  net_pnl               NUMERIC(10,4),
  -- Attribution
  attribution_direction BOOLEAN,
  attribution_structure BOOLEAN,
  attribution_timing    BOOLEAN,
  attribution_vol       BOOLEAN,
  -- Status
  status                TEXT DEFAULT 'open' CHECK (status IN ('open','closed')),
  created_at            TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_position_session ON public.trading_positions(session_id, entry_at DESC);
CREATE INDEX idx_position_status  ON public.trading_positions(status, entry_at DESC);
CREATE INDEX idx_position_mode    ON public.trading_positions(position_mode, status);
ALTER TABLE public.trading_positions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "authenticated_read_positions" ON public.trading_positions
  FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "service_write_positions" ON public.trading_positions
  FOR ALL USING (auth.role() = 'service_role');
```

### 4.9 trading_system_health
**COMPLETELY SEPARATE from system_health_snapshots and system_metrics.**
One row per module, upserted every 10 seconds by Python backend.
```sql
CREATE TABLE public.trading_system_health (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  service_name          TEXT NOT NULL UNIQUE CHECK (service_name IN (
    'prediction_engine','gex_engine','strategy_selector','risk_engine',
    'execution_engine','learning_engine','data_ingestor','sentinel',
    'tradier_websocket','databento_feed','cboe_feed'
  )),
  status                TEXT NOT NULL CHECK (status IN ('healthy','degraded','error','offline')),
  last_heartbeat_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  is_market_hours       BOOLEAN DEFAULT false,
  current_session_id    UUID REFERENCES public.trading_sessions(id),
  latency_ms            INTEGER,
  error_count_1h        INTEGER DEFAULT 0,
  last_error_message    TEXT,
  -- Data feed specific
  tradier_ws_connected  BOOLEAN,
  databento_connected   BOOLEAN,
  cboe_connected        BOOLEAN,
  last_data_at          TIMESTAMPTZ,
  data_lag_seconds      INTEGER,
  -- GEX specific
  gex_confidence        NUMERIC(5,4),
  gex_staleness_seconds INTEGER,
  -- Slippage model
  slippage_model_age_hours NUMERIC(8,2),
  slippage_model_observations INTEGER,
  -- Extra detail
  details               JSONB,
  created_at            TIMESTAMPTZ DEFAULT now(),
  updated_at            TIMESTAMPTZ DEFAULT now()
);
ALTER TABLE public.trading_system_health ENABLE ROW LEVEL SECURITY;
CREATE POLICY "authenticated_read_trading_health" ON public.trading_system_health
  FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "service_write_trading_health" ON public.trading_system_health
  FOR ALL USING (auth.role() = 'service_role');
```

### 4.10 trading_model_performance
Rolling accuracy, drift detection, champion/challenger status. Updated EOD.
```sql
CREATE TABLE public.trading_model_performance (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  recorded_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
  session_id            UUID REFERENCES public.trading_sessions(id),
  accuracy_5d           NUMERIC(5,4),
  accuracy_20d          NUMERIC(5,4),
  accuracy_60d          NUMERIC(5,4),
  accuracy_range_day    NUMERIC(5,4),
  accuracy_trend_day    NUMERIC(5,4),
  accuracy_reversal_day NUMERIC(5,4),
  accuracy_event_day    NUMERIC(5,4),
  win_rate_5d           NUMERIC(5,4),
  win_rate_20d          NUMERIC(5,4),
  win_rate_60d          NUMERIC(5,4),
  profit_factor_20d     NUMERIC(8,4),
  sharpe_20d            NUMERIC(8,4),
  drift_status          TEXT DEFAULT 'normal' CHECK (drift_status IN ('normal','warning','critical')),
  drift_z_score         NUMERIC(8,4),
  samples_since_retrain INTEGER,
  champion_model_id     TEXT,
  challenger_model_id   TEXT,
  challenger_active     BOOLEAN DEFAULT false,
  -- CV_Stress calibration
  cv_stress_fp_rate     NUMERIC(5,4),
  cv_stress_fn_rate     NUMERIC(5,4),
  -- Touch probability calibration
  touch_prob_brier      NUMERIC(8,6),
  touch_prob_observations INTEGER,
  -- Slippage model
  slippage_mae          NUMERIC(8,4),
  slippage_observations INTEGER,
  -- Regime disagreement rate
  regime_agreement_rate NUMERIC(5,4),
  -- Capital preservation
  preservation_triggers_this_week INTEGER DEFAULT 0,
  created_at            TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_model_perf_time ON public.trading_model_performance(recorded_at DESC);
ALTER TABLE public.trading_model_performance ENABLE ROW LEVEL SECURITY;
CREATE POLICY "authenticated_read_model_perf" ON public.trading_model_performance
  FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "service_write_model_perf" ON public.trading_model_performance
  FOR ALL USING (auth.role() = 'service_role');
```

### 4.11 trading_calibration_log
Append-only. Every 5-min CV_Stress and touch prob reading per position.
```sql
CREATE TABLE public.trading_calibration_log (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ts                    TIMESTAMPTZ NOT NULL DEFAULT now(),
  position_id           UUID REFERENCES public.trading_positions(id),
  signal_type           TEXT CHECK (signal_type IN ('cv_stress','touch_prob','slippage')),
  strategy_type         TEXT,
  regime                TEXT,
  cv_stress_score       NUMERIC(5,2),
  charm_velocity        NUMERIC(12,8),
  vanna_velocity        NUMERIC(12,8),
  z_vanna               NUMERIC(8,4),
  z_charm               NUMERIC(8,4),
  exit_triggered        BOOLEAN DEFAULT false,
  exit_reason           TEXT,
  touch_prob_put        NUMERIC(5,4),
  touch_prob_call       NUMERIC(5,4),
  touch_prob_max        NUMERIC(5,4),
  sigma_realized        NUMERIC(12,8),
  sigma_implied         NUMERIC(12,8),
  sigma_effective       NUMERIC(12,8),
  t_years_to_exit       NUMERIC(12,10),
  predicted_slippage    NUMERIC(8,4),
  actual_slippage       NUMERIC(8,4),
  slippage_delta        NUMERIC(8,4),
  position_state        INTEGER,
  unrealized_pnl        NUMERIC(10,4),
  pct_max_profit        NUMERIC(5,4),
  spx_price             NUMERIC(10,4),
  vix                   NUMERIC(8,4),
  vvix                  NUMERIC(8,4),
  -- Post-session outcome labels (reconciliation job fills these)
  put_touched_by_exit   BOOLEAN,
  call_touched_by_exit  BOOLEAN,
  forward_pnl_20m       NUMERIC(10,4),
  was_correct_exit      BOOLEAN,
  fp_flag               BOOLEAN,
  fn_flag               BOOLEAN,
  created_at            TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_calib_position ON public.trading_calibration_log(position_id, ts DESC);
CREATE INDEX idx_calib_type     ON public.trading_calibration_log(signal_type, regime, ts DESC);
ALTER TABLE public.trading_calibration_log ENABLE ROW LEVEL SECURITY;
CREATE POLICY "service_only_calib" ON public.trading_calibration_log
  USING (auth.role() = 'service_role');
```

### 4.12 Trading Job Registry Entries
Insert into the EXISTING `job_registry` table — do not create a new one.
```sql
INSERT INTO public.job_registry (
  id, version, owner_module, description, schedule, trigger_type,
  class, priority, execution_guarantee, timeout_seconds,
  max_retries, retry_policy, concurrency_policy, replay_safe,
  enabled, status, circuit_breaker_threshold
) VALUES
  ('trading_pre_market_scan',  '1.0.0','trading','Pre-market regime + day type','0 9 * * 1-5',    'scheduled','PreMarketScanJob',     'high',    'at_least_once',60,  3,'exponential','single',  true, true,'active',2),
  ('trading_prediction_cycle', '1.0.0','trading','5-min prediction engine',    '*/5 9-14 * * 1-5','scheduled','PredictionCycleJob',   'critical','at_least_once',30,  2,'exponential','single',  false,true,'active',5),
  ('trading_gex_computation',  '1.0.0','trading','Intraday GEX from Databento', '*/5 9-16 * * 1-5','scheduled','GEXComputationJob',    'critical','at_least_once',20,  2,'immediate',  'single',  false,true,'active',10),
  ('trading_position_monitor', '1.0.0','trading','Open position state machine', '*/1 9-15 * * 1-5','scheduled','PositionMonitorJob',   'critical','at_least_once',25,  1,'immediate',  'single',  false,true,'active',10),
  ('trading_time_stop_230pm',  '1.0.0','trading','Mandatory 2:30 PM close',    '30 14 * * 1-5',   'scheduled','TimeStop230pmJob',     'critical','exactly_once', 60,  3,'exponential','single',  false,true,'active',1),
  ('trading_time_stop_345pm',  '1.0.0','trading','Mandatory 3:45 PM close',    '45 15 * * 1-5',   'scheduled','TimeStop345pmJob',     'critical','exactly_once', 60,  3,'exponential','single',  false,true,'active',1),
  ('trading_session_close',    '1.0.0','trading','EOD cleanup and P&L summary', '30 16 * * 1-5',   'scheduled','SessionCloseJob',      'high',    'at_least_once',300, 2,'exponential','single',  true, true,'active',2),
  ('trading_learning_fast',    '1.0.0','trading','Daily fast calibration loop', '15 16 * * 1-5',   'scheduled','LearningFastLoopJob',  'normal',  'at_least_once',600, 2,'exponential','single',  true, true,'active',3),
  ('trading_learning_slow',    '1.0.0','trading','Weekly model retrain',        '0 20 * * 0',      'scheduled','LearningSlowLoopJob',  'normal',  'at_least_once',3600,1,'exponential','single',  true, true,'active',2),
  ('trading_heartbeat_check',  '1.0.0','trading','Sentinel heartbeat monitor',  '*/1 * * * *',     'scheduled','HeartbeatCheckJob',    'critical','at_least_once',10,  0,'immediate',  'single',  false,true,'active',3)
ON CONFLICT (id) DO NOTHING;
```

### 4.13 Trading Alert Configs
Insert into the EXISTING `alert_configs` table.
```sql
INSERT INTO public.alert_configs (
  id, metric_key, severity, threshold_value, comparison, enabled, cooldown_seconds, created_at, updated_at
) VALUES
  (gen_random_uuid(),'trading.daily_drawdown_pct',   'warning',  -2.0,  'lte',true, 300, now(),now()),
  (gen_random_uuid(),'trading.daily_drawdown_pct',   'critical', -2.5,  'lte',true, 60,  now(),now()),
  (gen_random_uuid(),'trading.daily_drawdown_pct',   'emergency',-3.0,  'lte',true, 0,   now(),now()),
  (gen_random_uuid(),'trading.vvix_z_score',         'warning',  2.0,   'gte',true, 600, now(),now()),
  (gen_random_uuid(),'trading.vvix_z_score',         'critical', 2.5,   'gte',true, 0,   now(),now()),
  (gen_random_uuid(),'trading.vvix_z_score',         'emergency',3.0,   'gte',true, 0,   now(),now()),
  (gen_random_uuid(),'trading.vix_spike_pct',        'critical', 15.0,  'gte',true, 300, now(),now()),
  (gen_random_uuid(),'trading.spx_drop_30m_pct',     'critical', -2.0,  'lte',true, 0,   now(),now()),
  (gen_random_uuid(),'trading.cv_stress_score',      'warning',  60.0,  'gte',true, 300, now(),now()),
  (gen_random_uuid(),'trading.cv_stress_score',      'critical', 70.0,  'gte',true, 60,  now(),now()),
  (gen_random_uuid(),'trading.cv_stress_score',      'emergency',85.0,  'gte',true, 0,   now(),now()),
  (gen_random_uuid(),'trading.win_rate_20d',         'warning',  0.58,  'lt', true, 3600,now(),now()),
  (gen_random_uuid(),'trading.win_rate_20d',         'critical', 0.54,  'lt', true, 1800,now(),now()),
  (gen_random_uuid(),'trading.heartbeat_age_seconds','critical', 120.0, 'gte',true, 60,  now(),now()),
  (gen_random_uuid(),'trading.gex_confidence',       'warning',  0.5,   'lt', true, 300, now(),now()),
  (gen_random_uuid(),'trading.gex_confidence',       'critical', 0.4,   'lt', true, 60,  now(),now()),
  (gen_random_uuid(),'trading.slippage_degraded',    'warning',  1.25,  'gte',true, 300, now(),now()),
  (gen_random_uuid(),'trading.regime_disagreement',  'warning',  0.3,   'gte',true, 300, now(),now()),
  (gen_random_uuid(),'trading.consecutive_losses',   'warning',  3.0,   'gte',true, 0,   now(),now()),
  (gen_random_uuid(),'trading.consecutive_losses',   'critical', 5.0,   'gte',true, 0,   now(),now())
ON CONFLICT DO NOTHING;
```

---

## PART 5 — THE TRADING ENGINE (Python/Railway/Cursor)

### 5.1 Architecture Overview
```
Python backend (Railway — persistent process, NOT serverless)
│
├── data_ingestor.py       — WebSocket feeds, heartbeat, GEX pipeline
├── prediction_engine.py   — 3-layer prediction (Layer A/B/C)
├── strategy_selector.py   — Stage 0-4 selection + walk-the-book
├── risk_engine.py         — Sizing, Greeks, circuit breakers
├── execution_engine.py    — Tradier orders, OCO, state machine
├── learning_engine.py     — Fast/slow/intraday calibration loops
└── sentinel.py            — Independent monitoring (deploy on GCP)

Storage: Supabase (permanent) + Redis (intraday cache, sub-ms) + QuestDB (feature store)
```

### 5.2 Pillar 1 — Prediction Engine

**Layer A — Regime Engine (9:00 AM pre-market):**
LightGBM Day Type Classifier → 5 types (trend, open_drive, range, reversal, event). Gates entire session strategy universe.

HMM (6 states) + LightGBM ensemble every 60 seconds. Six states: quiet_bullish, volatile_bullish, quiet_bearish, crisis, pin_range, panic.

**Regime Disagreement Guard (D-021):**
```python
if regime_hmm != regime_lgbm:
    apply_penalty(size_reduction=0.50, rcs_adjustment=-15)
    log_to_audit(action='trading.regime_disagreement', ...)
```

**Adaptive VVIX Circuit Breakers (D-018):**
```python
vvix_z = (vvix_current - vvix_20d_mean) / vvix_20d_std
# Warning: z > 2.0 → reduce new sizes 50%
# Critical: z > 2.5 → close all short-gamma
# Emergency: z > 3.0 → 100% reserve, halt
```
Fallback to fixed thresholds (120/140/160) until 20-day history available.

**Layer B — Path & Distribution Engine (every 5 min):**
LightGBM ensemble, 93 features:
- Price/Volume (15): OHLCV 1/5/15/30-min, VWAP deviation, opening range
- GEX (12): Net GEX, sign, wall/zero-line/flip distances, change rate, confidence
- Volatility Surface (18): ATM IV 0DTE/1DTE/7DTE, term slope, skew, RV 5/10d, VIX, VVIX
- Options Flow (20): Net premium delta, unusual activity, dark pool, 0DTE P/C ratio
- Cross-Asset (14): TLT, DXY, /ES premium, sector rotation, gold/oil
- Calendar/Time (8): Time of day sin/cos, day of week, days to Fed/CPI
- Charm/Vanna (6): CV_Stress_Score, charm_velocity, vanna_velocity, distances

No-trade signal is a first-class output — treated the same as a trade signal, logged always.

**CV_Stress Score:**
```python
z_vanna = (vanna_velocity - regime_vanna_mean) / regime_vanna_std
z_charm = (charm_velocity - regime_charm_mean) / regime_charm_std
raw = 0.6 * z_vanna + 0.4 * z_charm
cv_stress = min(100, max(0, (raw / P99_HISTORICAL) * 100))
```
Six separate regime calibration tables. Never cross-contaminate.

**Layer C — Volatility Surface:** Expected realized vs implied, skew regime, straddle implied move vs forecast.

### 5.3 Pillar 2 — Strategy Selection

**Stage 0 — Time + CV_Stress Gate:**
No entries before 10:00 AM. No short-gamma after 2:30 PM. CV_Stress > 70 blocks short-gamma.

**Trade Frequency Governor (D-020):**
```
Trend regime:   max 2 core positions per session
Range/Pin:      max 3 positions per session
Event regime:   max 1 position, reduced size
Volatile:       max 2 positions, reduced size
Panic:          0 positions
```

**Stage 1 — Day Type + Regime Eligibility:** Panic → all blocked. Trend → no IC/IB. RCS < 40 → all blocked.

**Stage 2 — GEX Strike Optimizer:** Short strikes at positive GEX walls. Hard veto: no short strike within 0.3% of negative GEX flip zone.

**Stage 3 — EV Utility (Monte Carlo, Numba JIT, 10,000 paths):**
```
Utility = EV_net_after_tax
        − λ1 × ExpectedShortfall
        − λ2 × PredictiveSlippagePenalty    ← LightGBM model (D-015)
        − λ3 × LiquidityPenalty
        + λ4 × CapitalEfficiency
        − λ5 × (0.12 × CV_Stress if > 60)
```

**Stage 4 — Liquidity Hard Veto:**
Bid/ask > $0.30, OI < 500 (RUT: 300), volume < 100 (RUT: 75) → veto.

**Walk-the-Book Execution (Gemini):**
Start at mid. Improve $0.02 every 5 seconds. Max 4 attempts, 30-second timeout. Max $0.08 improvement. Recovers ~$0.05/contract average.

### 5.4 Pillar 3 — Risk Management

**Position Sizing:**
```python
stressed_loss = max(
    spread_width * 100,
    adverse_move * 1.5 * 100 + spread_widening + predicted_slippage
)
position_size = int((account_value * risk_pct) / stressed_loss)
```

**Capital Preservation Mode (D-022):**
```python
if consecutive_losses_today == 3:
    risk_pct *= 0.50
    no_trade_threshold += 0.15
    
if consecutive_losses_today == 5:
    halt_new_entries_for_session()

if consecutive_loss_sessions == 3:
    risk_pct *= 0.70
    rcs_minimum = 75
```

**Intraday Execution Feedback (D-019):**
```python
if actual_slippage > predicted_slippage * 1.25:
    no_trade_threshold += 0.10
    position_size *= 0.70
    log_execution_degradation()
```
Resets at next session open.

**Hard Circuit Breakers:**
- SPX −2% in 30 min → halt entries
- VVIX Z > 2.0 → new sizes −50%
- VVIX Z > 2.5 → close all short-gamma
- VVIX Z > 3.0 → 100% reserve
- Drawdown −3% → close all, halt session
- Heartbeat lost > 120s → Sentinel closes all

### 5.5 Pillar 4 — Exit Strategy Engine

**Mandatory Exits:**
- Short-gamma: 2:30 PM EST — automated, no override
- Long-gamma: 3:45 PM EST — automated, no override

**Touch Probability (First-Passage Formula):**
```python
def touch_prob(S, K, mu, sigma, T):
    # First-passage barrier — NOT N(d2) terminal probability
    d1 = (log(S/K) + (mu + 0.5*sigma**2)*T) / (sigma*sqrt(T))
    d2 = d1 - sigma*sqrt(T)
    exponent = max(min((2*mu*log(K/S))/(sigma**2), 50), -50)
    return max(0.0, min(1.0, norm.cdf(-d2) + exp(exponent)*norm.cdf(-d1)))
```

**Hybrid Volatility (D-016):**
```python
sigma_effective = max(
    sigma_30m_realized,
    sigma_10m_realized * 0.85,
    sigma_5m_realized * 0.75,
    sigma_atm_implied * 0.70    # prevents regime-shift lag
)
if vvix_change_30m > 20% or spx_5m > 0.35%:
    sigma_effective = max(sigma_effective, sigma_5m)
```

**State-Based Exit Model:**

| State | Condition | Automated Action |
|---|---|---|
| 1 — Entry Validation | < 15 min | No action |
| 2 — Early Confirmation | Favorable, intact | Monitor |
| 3 — Mature Winner | > 40% max profit | Take 50% off, trail |
| 4 — Degrading Thesis | Any trigger below | Exit 50%, evaluate |
| 5 — Forced Exit | Hard stops/time stops | Exit 100% |

**State 3→4 Triggers:**
- Confidence drops > 15 points from entry
- GEX wall breached
- Touch probability > 25%
- CV_Stress > 70 **AND** unrealized_pnl ≥ 50% of max_profit (D-017)

### 5.6 Pillar 5 — Learning Engine

**Three-Speed Loop:**

Fast loop (daily 4:15 PM):
- Regime-conditioned isotonic recalibration (6 tables, never cross-contaminate)
- Predictive slippage model update (LightGBM regressor, rolling 30-day window)
- Z-test drift detection (min 30 trades)
- Counterfactual backtest (what if held longer? what if different strategy?)
- Session scorecard to `trading_model_performance`

Slow loop (weekly Sunday 8 PM):
- Full model retrain on rolling 90-day window
- Champion vs challenger (7 criteria — see Section 5.7)
- Fractional Kelly recalibration per strategy/regime
- Trade frequency governor review

Intraday micro-calibration (every 2 hours):
- Recalibrate confidence thresholds based on today's results only
- Does not retrain models — adjusts operational thresholds
- Prevents continued trading into confirmed adversity

**Minimum Samples Per Cell:** < 50 training examples per regime-strategy cell → live trading at 25% sizing until 50 live examples accumulate.

### 5.7 Champion/Challenger — 7 Criteria (ALL required)
1. Min 40 shadow sessions
2. Min 80 trade observations
3. ≥ 3 regime types covered
4. Z-test p < 0.05 in challenger's favor
5. Sharpe improvement ≥ 0.15 vs champion
6. Challenger max DD ≤ champion max DD
7. All circuit breaker scenarios pass in sandbox

### 5.8 Independent Sentinel
Deploy separately on GCP. Close-only Tradier permissions. Never shares Railway infrastructure.

Monitors independently:
- Drawdown from Tradier account balance (polled every 5s)
- SPX price every 2s
- Primary app heartbeat via Supabase read-only replica
- CV_Stress recomputed from its own Tradier option chain poll

Triggers close-all when:
- App heartbeat > 120 seconds stale
- Drawdown > 3%
- VVIX Z > 3.0 (independently computed)
- CV_Stress > 85 (independently computed)

Panic mode: LIFO market orders (most recent = 0DTE first), SMS alert, waits for fill confirmation.

---

## PART 6 — FRONTEND (Lovable — React/TypeScript)

### 6.1 New Routes to Add
Add to `src/config/routes.ts`:
```typescript
// Trading — Admin
ADMIN_TRADING:          '/admin/trading',
ADMIN_TRADING_WARROOM:  '/admin/trading/warroom',
ADMIN_TRADING_POSITIONS:'/admin/trading/positions',
ADMIN_TRADING_SIGNALS:  '/admin/trading/signals',
ADMIN_TRADING_PERFORMANCE: '/admin/trading/performance',
ADMIN_TRADING_HEALTH:   '/admin/trading/health',
ADMIN_TRADING_CONFIG:   '/admin/trading/config',
```

### 6.2 Navigation Section to Add
Add to `src/config/admin-navigation.ts`:
```typescript
import { TrendingUp, Activity, BarChart2, Zap, Settings, Radio } from 'lucide-react';

{
  label: 'Trading System',
  items: [
    { title: 'War Room',     url: ROUTES.ADMIN_TRADING_WARROOM,   icon: TrendingUp,  permission: 'trading.view' },
    { title: 'Positions',    url: ROUTES.ADMIN_TRADING_POSITIONS, icon: BarChart2,   permission: 'trading.view' },
    { title: 'Signals',      url: ROUTES.ADMIN_TRADING_SIGNALS,   icon: Zap,         permission: 'trading.view' },
    { title: 'Performance',  url: ROUTES.ADMIN_TRADING_PERFORMANCE,icon: Activity,   permission: 'trading.view' },
    { title: 'Engine Health',url: ROUTES.ADMIN_TRADING_HEALTH,    icon: Radio,       permission: 'trading.view' },
    { title: 'Configuration',url: ROUTES.ADMIN_TRADING_CONFIG,    icon: Settings,    permission: 'trading.configure' },
  ],
},
```

### 6.3 New Admin Pages to Build

All pages follow the existing patterns exactly:
- Import `PageHeader`, `StatCard`, `LoadingSkeleton`, `ErrorState`
- Use `useQuery` with `refetchInterval`
- Use `supabase.from('trading_*')` for data
- Gate with `RequirePermission`
- Lazy loaded in `App.tsx`

---

#### Page 1: War Room (`/admin/trading/warroom`)
The primary operator view. Real-time during market hours.

**Top stat cards (4 cards, same as AdminDashboard pattern):**
- Today's virtual P&L (green/red)
- Today's actual P&L (green/red)
- Current drawdown % with −3% threshold indicator
- Active positions count

**Main panels:**

**Regime Panel:**
- Current regime badge (colour-coded by type)
- Day Type badge
- RCS score (0–100 gauge)
- HMM state vs LightGBM state — if they disagree, show amber "Regime Disagreement — Size Reduced 50%" banner
- VVIX Z-score with adaptive threshold display (current Z vs 2.0/2.5/3.0 thresholds)

**CV_Stress Panel:**
- Score 0–100 with colour: green <60, amber 60–70, red >70
- Velocity direction arrow (rising/stable/falling)
- Exit condition status: "Exit armed — position at X% of max profit" or "Exit standby — position below 50% of max profit"

**GEX Map:**
- Bar chart of GEX value by strike for nearest 20 strikes
- Current SPX price marker
- Positive (blue) and negative (red) GEX zones clearly visible
- GEX confidence percentage
- Staleness indicator (turns amber if > 10 minutes stale)

**Prediction Confidence:**
- Current P(bull) / P(bear) / P(neutral) — progress bars
- Top direction with confidence percentage
- No-trade signal displayed prominently if active with reason

**Capital Preservation Status:**
- Consecutive losses today (0/3/5 indicator)
- Current size reduction in effect
- Session trades used vs cap (e.g. "2 of 3 trades used — Range regime")

**Execution Quality:**
- Predicted vs actual slippage for today's fills
- "Execution Degraded" alert if feedback loop active

**Automation Activity Log:**
- Real-time stream of every decision with timestamp, reason, outcome

**Kill Switch button:**
- Red button, bottom right
- Requires 1.5-second hold to prevent accidental activation
- Shows confirmation with positions to be closed

**Refetch interval:** 5 seconds during market hours (9:30–4:00 PM ET), 60 seconds otherwise. WebSocket realtime subscription for positions table.

---

#### Page 2: Positions (`/admin/trading/positions`)
Table of open and closed positions.

**Tabs:** Open Positions | Today's Closed | Historical

**Columns per position:**
Instrument, Strategy, Type (Core/Satellite), Mode (Virtual/Live), Entry time, Entry credit, Current P&L, Current state (badge 1–5), CV_Stress, Touch Prob, Exit reason (if closed)

**Position detail drawer (click a row):**
Full attribution breakdown, Greeks at entry vs now, CV_Stress history chart, exit rationale from learning engine.

---

#### Page 3: Signals (`/admin/trading/signals`)
Log of all signals generated — executed, rejected, expired.

**Columns:** Time, Instrument, Strategy, Status badge, Regime, RCS, CV_Stress, EV, Rejection reason (if applicable)

**Filters:** Date range, instrument, strategy type, status

---

#### Page 4: Performance (`/admin/trading/performance`)
Rolling performance metrics, model accuracy, drift status.

**Stat cards:** Win rate (5d/20d/60d), Profit factor, Sharpe ratio, Max drawdown, Prediction accuracy by regime

**Charts:**
- Daily P&L over rolling 90 days (bar chart, green/red)
- Rolling win rate line
- Strategy distribution pie chart

**Model Health section:**
- Current model accuracy vs target (58%)
- Drift status badge (normal/warning/critical)
- Champion vs challenger status
- Last retrain date
- Samples per regime-strategy cell heatmap (highlights under-sampled cells)

---

#### Page 5: Engine Health (`/admin/trading/health`)
**SEPARATE from the existing System Health page at `/admin/health`**

This page monitors ONLY the trading engine components using `trading_system_health` table.

**Module cards (one per service):**
Each card shows: service name, status badge (healthy/degraded/error/offline), last heartbeat (relative time), latency, error count in last hour, relevant feed-specific metrics.

Services monitored:
- prediction_engine
- gex_engine (GEX confidence, staleness seconds)
- strategy_selector
- risk_engine
- execution_engine
- learning_engine (slippage model age, observations count)
- data_ingestor
- sentinel (GCP — shows as offline if primary app crashes)
- tradier_websocket (connected status, data lag)
- databento_feed (connected, data lag)
- cboe_feed (connected, last delivery time)

**Critical rule:** If any service shows `offline` for > 2 minutes during market hours → show full-page red CRITICAL banner at top of all admin pages. Not just on this page — everywhere in the admin console.

**Alert history from `alert_history`** filtered to `metric_key LIKE 'trading.%'` — shows last 20 trading-specific alerts with severity badges.

**Refetch interval:** 10 seconds always (health must always be current).

---

#### Page 6: Configuration (`/admin/trading/config`)
**Permission gate: `trading.configure`** (more restrictive than `trading.view`)

**Sections:**

**Tradier Connection:**
- Connect/disconnect button with OAuth flow
- Account type display (sandbox/live)
- Current balance (fetched from Tradier)
- Live trading toggle (disabled unless paper phase complete)

**Paper Phase Status:**
- All 12 go-live criteria with green/amber/red status
- Cannot enable live trading until all 12 are green

**Sizing Phase:**
- Current phase display (1/2/3/4)
- Advance/regress buttons (with confirmation dialog)
- Phase criteria checklist

**Alert Thresholds:**
- Edit VVIX Z-score thresholds
- Edit CV_Stress thresholds
- Edit drawdown limit display (read-only — cannot change the −3% hard stop)

---

### 6.4 Component Architecture Rules

All trading components live in:
```
src/components/trading/     — shared trading UI components
src/pages/admin/trading/    — page components
src/hooks/trading/          — trading-specific hooks
```

New hooks to create:
```typescript
useTradingSession()          — current session data, refetch 30s
useTradingPositions()        — positions with real-time updates
useTradingPrediction()       — latest prediction output
useTradingSystemHealth()     — trading_system_health, refetch 10s
useTradingPerformance()      — rolling model metrics
useKillSwitch()              — kill switch state and activation
```

**WebSocket realtime subscriptions** (not just polling) for:
- `trading_positions` — open positions update in real time
- `trading_system_health` — health status changes immediately
- `trading_prediction_outputs` — new predictions appear live

Use `supabase.channel()` with `on('postgres_changes', ...)` — same pattern as any existing realtime subscription in the codebase.

---

## PART 7 — COMPREHENSIVE MONITORING STRATEGY

The core principle: **nothing in the trading engine should fail silently.** Every failure mode has a detection mechanism and a defined response.

### 7.1 Three-Layer Monitoring Architecture

```
Layer 1 — Database (always on, even if app crashes)
└── trading_system_health   — heartbeat table (10s upserts)
└── trading_calibration_log — every exit/entry decision logged
└── audit_logs              — every automated action
└── alert_history           — every threshold breach

Layer 2 — Primary Application (in-process)
└── Intraday execution feedback loop
└── Capital preservation counter
└── Regime disagreement guard
└── Circuit breaker cascade

Layer 3 — Independent Sentinel (separate GCP process)
└── Monitors Layer 1 independently
└── Backs up every critical circuit breaker
└── Acts even when Layer 1 and Layer 2 are both down
```

### 7.2 What Gets Monitored (Complete List)

**Market Data:**
- Tradier WebSocket connected (every 3 seconds)
- Databento OPRA feed alive (every 10 seconds)
- GEX data freshness (staleness in seconds, alert if > 600)
- VVIX 20-day baseline freshness (alert if > 24 hours stale)

**Prediction Quality:**
- Regime model agreement (alert if HMM ≠ LightGBM > 30% of predictions)
- Prediction confidence distribution (alert if persistently < 55%)
- No-trade rate (alert if > 80% of cycles, may indicate model stuck)
- CV_Stress level (real-time, three alert tiers)

**Execution Quality:**
- Actual vs predicted slippage per fill (every fill logged)
- Walk-the-book fill quality (fill vs mid at each attempt)
- Tradier order acknowledgement latency (alert if > 2 seconds)
- OCO order confirmation after every fill

**Position Management:**
- Open positions count vs limit (alert if approaching max)
- Time remaining to mandatory exits (alert at T-15 min)
- Portfolio delta and vega (check every 5 minutes)
- Capital preservation consecutive loss counter

**Learning Engine:**
- Slippage model age (alert if > 48 hours since last update)
- Slippage model observations (alert if < 200 = cold start mode)
- Drift z-score (alert if < −1.645 warning, < −2.326 critical)
- Champion/challenger promotion status

**Infrastructure:**
- Python backend heartbeat (10-second upsert to Supabase)
- Sentinel process heartbeat (separate from main heartbeat)
- Supabase connection health (query latency check)
- Railway process memory and CPU (Railway dashboard)

**Daily Reporting:**
- EOD session summary written to `trading_sessions`
- EOD model performance snapshot to `trading_model_performance`
- Weekly performance report (Sunday slow loop)

### 7.3 Alert Response Matrix

| Metric | Warning | Critical | Emergency |
|---|---|---|---|
| Daily drawdown | −2.0% | −2.5% | −3.0% → halt |
| VVIX Z-score | 2.0σ → size −50% | 2.5σ → close short-gamma | 3.0σ → 100% reserve |
| CV_Stress | 60 → monitor | 70 → exit (if P&L ≥ 50%) | 85 → Sentinel closes all |
| GEX confidence | 0.5 → watch | 0.4 → block entries | Trend day < 0.7 → block immediately |
| Heartbeat age | 60s → alert | 120s → Sentinel closes | — |
| Win rate 20d | 58% | 54% → reduce sizes | — |
| Consecutive losses | 3 → size −50% | 5 → halt session | — |
| Consecutive loss sessions | — | 3 → size −30%, RCS min 75 | — |
| Slippage degraded | Actual > predicted × 1.25 → tighten | — | — |

---

## PART 8 — DATA PROVIDERS

| Provider | Purpose | Cost | Status |
|---|---|---|---|
| Tradier API | Execution, streaming quotes, OCO orders | Commission | Active |
| Databento OPRA | Intraday trade-by-trade GEX synthesis | ~$150/mo | Subscribe |
| CBOE DataShop (Option EOD Summary) | EOD OI per strike — morning GEX baseline | ~$40–60/mo | Pending approval |
| Polygon.io (existing) | VVIX, breadth, dark pool, breadth | Already paid | Active |
| Unusual Whales (existing) | Options flow confirmation | Already paid | Active |
| Finnhub (existing) | Macro calendar events | Already paid | Active |

**VVIX source:** Polygon.io Indices Starter (already subscribed). No additional CBOE purchase needed.

---

## PART 9 — POSITION SIZING PHASES

| Phase | Core sizing | Satellite | Margin | Expected gross | Max drawdown target |
|---|---|---|---|---|---|
| 1 — Paper | 0.5% | 0.25% | None | N/A | N/A |
| 2 — Conservative live | 0.5% | 0.25% | None | ~24% | ~10% |
| 3 — Standard live | 1.0% | 0.50% | None | ~42% | ~16% |
| 4 — With margin | 1.0% | 0.50% | 2:1 | ~75% | ~27% |

**Advance criteria Phase 2 → 3:** 90+ live trading days, rolling 60d win rate ≥ 62%, max drawdown has not exceeded 12%.

**Advance criteria Phase 3 → 4:** 180+ live days, Phase 3 criteria sustained 6 months, conscious operator decision.

**Regression (automatic):** Phase 3 drawdown > 20% in one month → revert to Phase 2. Phase 4 drawdown > 28% in one month → revert to Phase 3 (margin off).

---

## PART 10 — 45-DAY PAPER PHASE — 12 GO-LIVE CRITERIA

All 12 required before live trading is enabled. Config page shows live status of all 12.

1. Aggregate prediction accuracy ≥ 58% over full 45 days
2. Per-regime accuracy ≥ 55% for every day type with ≥ 8 observations
3. Minimum 50 training examples per regime-strategy cell
4. Under-sampled cells flagged — live trading at 25% sizing until 50 examples
5. Paper Sharpe ≥ 1.5
6. Zero unhandled exceptions in final 20 paper sessions
7. All 6 circuit breaker scenarios tested and verified in Tradier sandbox
8. Kill-switch response confirmed < 5 seconds from mobile
9. Independent Sentinel verified operational on GCP
10. WebSocket heartbeat verified — disconnect triggers degraded mode within 3 seconds
11. Predictive slippage model calibrated — minimum 200 fill observations
12. GEX tracking error ≤ ±15% vs OCC actuals (CBOE DataShop validation)

---

## PART 11 — BUILD ORDER

### Phase 1 — Data Infrastructure (Weeks 1–2)
**Goal:** All feeds live, data flowing into Supabase, monitoring active.

Tasks:
- Subscribe to Databento OPRA (most critical — do first)
- Subscribe to CBOE DataShop Option EOD Summary (pending approval)
- Python: Tradier WebSocket connection + heartbeat monitor (3-second timeout)
- Python: Databento OPRA stream integration + Lee-Ready GEX synthesis
- Python: CBOE DataShop SFTP file pickup + morning OI baseline
- Python: VVIX 20-day baseline computation from Polygon
- Python: Write all data to Supabase tables + `trading_system_health` heartbeats
- Lovable: Run Supabase migration (all trading tables from Part 4)
- Lovable: Engine Health page (`/admin/trading/health`)

**Go/No-Go:** All feeds verified live. GEX computing at 8:30 AM. Heartbeat triggering degraded mode on disconnect. Engine Health page shows all services healthy.

---

### Phase 2 — Virtual Trade Engine (Weeks 3–5)
**Goal:** System generates signals from real data, records virtual positions.

Tasks:
- Python: Day Type Classifier (pre-market LightGBM)
- Python: Regime detection (HMM + LightGBM 6-state)
- Python: CV_Stress computation from options chain
- Python: Layer B prediction pipeline (93 features)
- Python: Strategy selection Stages 0–4 with trade frequency governor
- Python: Walk-the-book order simulation (virtual mode)
- Python: Virtual position recorder → `trading_positions` with mode='virtual'
- Python: Regime disagreement guard (D-021)
- Python: Capital preservation counter (D-022)
- Python: Static slippage as fallback (predictive model trains during paper phase)

**Go/No-Go:** ≥ 3 virtual signals per day. All signals, positions, predictions in Supabase. No unhandled exceptions over 5 consecutive days.

---

### Phase 3 — Admin Console (Weeks 6–7)
**Goal:** Full War Room operational for operator.

Tasks (all Lovable):
- Run Supabase migration for trading tables
- Add trading navigation section to `admin-navigation.ts`
- Add trading routes to `routes.ts`
- War Room page (`/admin/trading/warroom`)
- Positions page (`/admin/trading/positions`)
- Signals page (`/admin/trading/signals`)
- Performance page (`/admin/trading/performance`)
- Configuration page (`/admin/trading/config`)
- Kill-switch button in War Room header
- Global CRITICAL banner for trading engine failures
- WebSocket realtime subscriptions for positions + health

**Go/No-Go:** Operator can see live predictions, virtual positions, regime state, CV_Stress, GEX map, engine health — all in real time. Kill-switch renders and is hold-to-activate.

---

### Phase 4 — Paper Phase (Weeks 8–14)
**Goal:** 45 days of automated paper trading, all 12 criteria tracked.

Tasks:
- Python: All 12 go-live criteria tracked and written to Supabase
- Python: Predictive slippage model training (accumulate fills, train LightGBM)
- Python: CV_Stress threshold calibration (weekly, CWER metric)
- Python: Touch probability calibration (grid search weekly)
- Python: GEX vs OCC validation (CBOE DataShop vs predicted OI)
- Python: Regime model retraining and champion/challenger infrastructure
- Lovable: Paper phase progress dashboard on Config page (12 criteria live status)
- Kill-switch tested against Tradier sandbox (Day 10 deadline)
- Sentinel deployed to GCP and tested weekly
- Intraday execution feedback loop tested

**Go/No-Go:** All 12 criteria green. Slippage model trained (≥ 200 observations). System operator signs off.

---

### Phase 5 — Live Execution (Week 15+)
**Goal:** Real trades executing on operator's Tradier account.

Tasks:
- Lovable: Tradier OAuth connection flow on Config page
- Python: Live order execution engine (position_mode='live')
- Python: OCO orders pre-submitted at every fill
- Python: Actual slippage tracking vs predicted
- Python: Intraday execution feedback loop active
- Sentinel: Live on GCP with actual account monitoring
- Kill-switch: Live (not sandbox)

**Start at Phase 2 sizing (0.5% per trade).**

---

### Phase 6 — Learning Engine (Parallel with Phase 5)
Runs in background from Phase 2 onward, matures over time.

- Python: Daily fast loop (isotonic recalibration, slippage model update, drift z-test)
- Python: Weekly slow loop (model retrain, champion/challenger)
- Python: Intraday micro-calibration (every 2 hours)
- Python: Counterfactual backtest (daily, post-session)

---

### Phase 7 — Phase 3 Sizing (Month 6+)
After 90 live days + ≥ 62% win rate sustained.

System auto-detects when criteria are met. Operator notified. Operator manually advances on Config page with confirmation dialog.

---

## PART 12 — SECURITY REQUIREMENTS

**Follow all existing foundation patterns exactly:**

1. **RLS on every trading table** — service_role writes, authenticated reads
2. **Never expose Tradier keys** — store encrypted, display only last 4 chars
3. **Permission gates on all pages** — `trading.view` minimum, `trading.configure` for config
4. **Kill-switch requires `trading.kill_switch` permission** — separate from trading.admin
5. **All automated actions logged to `audit_logs`** — every trade entry, exit, circuit breaker, with correlation_id linking to job_execution
6. **Audit log is append-only** — no deletes, 2-year retention minimum
7. **Calibration log is append-only** — write-only for service_role, read-only for admin
8. **API keys never in frontend code** — Python backend only, Railway environment variables
9. **Sentinel has close-only Tradier permissions** — separate API key with restricted scope
10. **MFA required for admin** — already enforced by existing `RequireMfaForAdmin` — trading admin inherits this

**New admin trading pages automatically get MFA enforcement because they are children of `AdminLayout` which already requires MFA.**

---

## PART 13 — PERFORMANCE REQUIREMENTS

**Follow existing patterns:**

1. **Single combined query per page** — same pattern as `AdminHealthPage` which combines 4 queries in one `Promise.all`
2. **Polling intervals matched to data change rate:**
   - War Room: 5-second refetch during market hours, 60-second otherwise
   - Engine Health: always 10-second
   - Performance: 60-second
   - Positions: WebSocket realtime subscription (not polling)
3. **Lazy loading all trading pages** — same as existing admin pages
4. **LoadingSkeleton on every data fetch** — same as existing pages
5. **refetchIntervalInBackground: false** — do not refetch when tab is not active
6. **TanStack Query caching** — `staleTime: 30_000` for trading data, `staleTime: 10_000` for health data
7. **Python backend: Redis for intraday state** — Supabase for permanent storage only, Redis for sub-millisecond intraday lookups
8. **QuestDB for feature store** — 93-feature LightGBM queries must be sub-millisecond, not Supabase queries

---

## PART 14 — V2 FEATURES (EXPLICITLY DEFERRED)

Do not build these in V1. Document here so nothing is forgotten.

- Multi-user trade mirroring (async fan-out, per-user Tradier, enrollment flow)
- User tier system (Free/Paper/Live/Premium)
- Subscription pricing
- Mirror fill risk score per user
- User-side slippage model (separate from virtual)
- Mirror health dashboard per user
- Feature-level input drift monitoring
- Black swan Monte Carlo scenario injection
- GEX-lite fallback mode (IV skew + VWAP when Databento drops)
- Calendar and diagonal spreads
- Futures hedging
- Multi-broker routing

---

## PART 15 — GLOSSARY

**CV_Stress:** Composite volatility stress score (0–100). 60% vanna velocity + 40% charm velocity, regime z-score normalised. Detects charm/vanna degradation 10–15 minutes before price shows it.

**GEX (Gamma Exposure):** Net dealer gamma exposure per strike. Positive GEX = dealers long gamma = price pinning. Negative GEX = dealers short gamma = price acceleration.

**RCS (Regime Confidence Score):** 0–100 composite score driving capital allocation tier. Higher = more certainty about current regime = more capital deployed.

**0DTE:** Zero days to expiration. Options that expire the same trading day.

**Section 1256:** IRS contract classification giving 60% long-term / 40% short-term tax treatment regardless of actual holding period. Applies to SPX/NDX/RUT/XSP options.

**Walk-the-book:** Limit order improvement strategy. Start at mid-price, improve by $0.02 every 5 seconds until filled or timeout (30s max).

**Touch probability:** First-passage barrier probability — the probability that SPX touches the short strike before the position exits. Computed with the correct first-passage formula (not the simpler but wrong N(d2)).

**Stressed loss:** Conservative position sizing denominator = max(spread_width × 100, adverse_move × 1.5 × 100 + spread_widening + predicted_slippage).

---

*MARKETMUSE Master Specification v4.0 — FINAL*  
*Single source of truth. Supersedes all prior documents.*  
*Owner: tesfayekb | Repo: https://github.com/tesfayekb/beyenestock-of-foundation-first.git*  
*Foundation: https://github.com/tesfayekb/beyenestock-of-foundation-first.git*  
*Build begins from this document.*
