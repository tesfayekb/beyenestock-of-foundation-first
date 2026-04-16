-- ============================================================
-- T-MIG-001: Initial Trading Schema
-- Source: MARKETMUSE_MASTER.md v4.0, Part 4 (sections 4.1–4.13)
-- ============================================================

-- 4.1 Profiles Extension (ALTER, not new table)
ALTER TABLE public.profiles
  ADD COLUMN IF NOT EXISTS trading_tier     TEXT DEFAULT 'operator',
  ADD COLUMN IF NOT EXISTS tradier_connected BOOLEAN DEFAULT false,
  ADD COLUMN IF NOT EXISTS tradier_account_id TEXT;

-- 4.4 trading_operator_config
CREATE TABLE public.trading_operator_config (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id               UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  tradier_account_id    TEXT,
  tradier_key_preview   TEXT,
  encrypted_key         TEXT,
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

-- 4.5 trading_sessions
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

-- 4.6 trading_prediction_outputs
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

-- 4.7 trading_signals
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

-- 4.8 trading_positions
CREATE TABLE public.trading_positions (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  signal_id             UUID REFERENCES public.trading_signals(id),
  session_id            UUID REFERENCES public.trading_sessions(id),
  position_mode         TEXT NOT NULL CHECK (position_mode IN ('virtual','live')),
  instrument            TEXT NOT NULL,
  strategy_type         TEXT NOT NULL,
  position_type         TEXT CHECK (position_type IN ('core','satellite')),
  entry_at              TIMESTAMPTZ NOT NULL,
  entry_credit          NUMERIC(8,4),
  entry_slippage        NUMERIC(8,4),
  entry_spx_price       NUMERIC(10,4),
  entry_regime          TEXT,
  entry_rcs             NUMERIC(5,2),
  entry_cv_stress       NUMERIC(5,2),
  entry_touch_prob      NUMERIC(5,4),
  entry_greeks          JSONB,
  short_strike          NUMERIC(10,2),
  long_strike           NUMERIC(10,2),
  short_strike_2        NUMERIC(10,2),
  long_strike_2         NUMERIC(10,2),
  expiry_date           DATE,
  contracts             INTEGER,
  tradier_order_id      TEXT,
  tradier_fill_price    NUMERIC(8,4),
  current_state         INTEGER DEFAULT 1 CHECK (current_state BETWEEN 1 AND 5),
  current_pnl           NUMERIC(10,4) DEFAULT 0,
  peak_pnl              NUMERIC(10,4) DEFAULT 0,
  current_touch_prob    NUMERIC(5,4),
  current_cv_stress     NUMERIC(5,2),
  last_updated_at       TIMESTAMPTZ DEFAULT now(),
  exit_at               TIMESTAMPTZ,
  exit_credit           NUMERIC(8,4),
  exit_slippage         NUMERIC(8,4),
  exit_reason           TEXT CHECK (exit_reason IN (
    'profit_target','stop_loss','time_stop_230pm','time_stop_345pm',
    'touch_prob_threshold','cv_stress_trigger','state4_degrading',
    'portfolio_stop','circuit_breaker','capital_preservation','manual'
  )),
  exit_spx_price        NUMERIC(10,4),
  gross_pnl             NUMERIC(10,4),
  slippage_cost         NUMERIC(8,4),
  commission_cost       NUMERIC(8,4),
  net_pnl               NUMERIC(10,4),
  attribution_direction BOOLEAN,
  attribution_structure BOOLEAN,
  attribution_timing    BOOLEAN,
  attribution_vol       BOOLEAN,
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

-- 4.9 trading_system_health
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
  tradier_ws_connected  BOOLEAN,
  databento_connected   BOOLEAN,
  cboe_connected        BOOLEAN,
  last_data_at          TIMESTAMPTZ,
  data_lag_seconds      INTEGER,
  gex_confidence        NUMERIC(5,4),
  gex_staleness_seconds INTEGER,
  slippage_model_age_hours NUMERIC(8,2),
  slippage_model_observations INTEGER,
  details               JSONB,
  created_at            TIMESTAMPTZ DEFAULT now(),
  updated_at            TIMESTAMPTZ DEFAULT now()
);
ALTER TABLE public.trading_system_health ENABLE ROW LEVEL SECURITY;
CREATE POLICY "authenticated_read_trading_health" ON public.trading_system_health
  FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "service_write_trading_health" ON public.trading_system_health
  FOR ALL USING (auth.role() = 'service_role');

-- 4.10 trading_model_performance
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
  cv_stress_fp_rate     NUMERIC(5,4),
  cv_stress_fn_rate     NUMERIC(5,4),
  touch_prob_brier      NUMERIC(8,6),
  touch_prob_observations INTEGER,
  slippage_mae          NUMERIC(8,4),
  slippage_observations INTEGER,
  regime_agreement_rate NUMERIC(5,4),
  preservation_triggers_this_week INTEGER DEFAULT 0,
  created_at            TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_model_perf_time ON public.trading_model_performance(recorded_at DESC);
ALTER TABLE public.trading_model_performance ENABLE ROW LEVEL SECURITY;
CREATE POLICY "authenticated_read_model_perf" ON public.trading_model_performance
  FOR SELECT USING (auth.role() = 'authenticated');
CREATE POLICY "service_write_model_perf" ON public.trading_model_performance
  FOR ALL USING (auth.role() = 'service_role');

-- 4.11 trading_calibration_log
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
  FOR ALL USING (auth.role() = 'service_role');

-- Updated_at triggers for tables with updated_at columns
CREATE TRIGGER update_trading_operator_config_updated_at
  BEFORE UPDATE ON public.trading_operator_config
  FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_trading_sessions_updated_at
  BEFORE UPDATE ON public.trading_sessions
  FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_trading_system_health_updated_at
  BEFORE UPDATE ON public.trading_system_health
  FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

-- 4.2 Seed trading permissions
INSERT INTO public.permissions (key, description) VALUES
  ('trading.view',         'View trading signals, positions, and performance'),
  ('trading.admin',        'Full trading system administration'),
  ('trading.execute',      'Allow system to execute trades on connected account'),
  ('trading.kill_switch',  'Activate emergency trading halt'),
  ('trading.configure',    'Configure trading parameters and thresholds')
ON CONFLICT (key) DO NOTHING;

-- 4.3 Assign trading permissions to admin role
INSERT INTO public.role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM public.roles r, public.permissions p
WHERE r.key = 'admin'
  AND p.key IN ('trading.view','trading.admin','trading.kill_switch','trading.configure')
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- 4.12 Trading job registry entries
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

-- 4.13 Trading alert configs
INSERT INTO public.alert_configs (
  metric_key, severity, threshold_value, comparison, enabled, cooldown_seconds, created_by
) VALUES
  ('trading.daily_drawdown_pct',   'warning',  -2.0,  'lte',true, 300, '00000000-0000-0000-0000-000000000000'),
  ('trading.daily_drawdown_pct',   'critical', -2.5,  'lte',true, 60,  '00000000-0000-0000-0000-000000000000'),
  ('trading.daily_drawdown_pct',   'emergency',-3.0,  'lte',true, 0,   '00000000-0000-0000-0000-000000000000'),
  ('trading.vvix_z_score',         'warning',  2.0,   'gte',true, 600, '00000000-0000-0000-0000-000000000000'),
  ('trading.vvix_z_score',         'critical', 2.5,   'gte',true, 0,   '00000000-0000-0000-0000-000000000000'),
  ('trading.vvix_z_score',         'emergency',3.0,   'gte',true, 0,   '00000000-0000-0000-0000-000000000000'),
  ('trading.vix_spike_pct',        'critical', 15.0,  'gte',true, 300, '00000000-0000-0000-0000-000000000000'),
  ('trading.spx_drop_30m_pct',     'critical', -2.0,  'lte',true, 0,   '00000000-0000-0000-0000-000000000000'),
  ('trading.cv_stress_score',      'warning',  60.0,  'gte',true, 300, '00000000-0000-0000-0000-000000000000'),
  ('trading.cv_stress_score',      'critical', 70.0,  'gte',true, 60,  '00000000-0000-0000-0000-000000000000'),
  ('trading.cv_stress_score',      'emergency',85.0,  'gte',true, 0,   '00000000-0000-0000-0000-000000000000'),
  ('trading.win_rate_20d',         'warning',  0.58,  'lt', true, 3600,'00000000-0000-0000-0000-000000000000'),
  ('trading.win_rate_20d',         'critical', 0.54,  'lt', true, 1800,'00000000-0000-0000-0000-000000000000'),
  ('trading.heartbeat_age_seconds','critical', 120.0, 'gte',true, 60,  '00000000-0000-0000-0000-000000000000'),
  ('trading.gex_confidence',       'warning',  0.5,   'lt', true, 300, '00000000-0000-0000-0000-000000000000'),
  ('trading.gex_confidence',       'critical', 0.4,   'lt', true, 60,  '00000000-0000-0000-0000-000000000000'),
  ('trading.slippage_degraded',    'warning',  1.25,  'gte',true, 300, '00000000-0000-0000-0000-000000000000'),
  ('trading.regime_disagreement',  'warning',  0.3,   'gte',true, 300, '00000000-0000-0000-0000-000000000000'),
  ('trading.consecutive_losses',   'warning',  3.0,   'gte',true, 0,   '00000000-0000-0000-0000-000000000000'),
  ('trading.consecutive_losses',   'critical', 5.0,   'gte',true, 0,   '00000000-0000-0000-0000-000000000000');