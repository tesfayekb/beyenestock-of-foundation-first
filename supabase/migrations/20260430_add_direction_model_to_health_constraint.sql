-- Migration: expand trading_system_health service_name allowlist to
-- include 'direction_model' for the LightGBM model health probe
-- shipped in T-ACT-041 (Fix PR 2).
--
-- Without this entry, write_health_status('direction_model', ...)
-- raises Postgres error 23514 (check_violation) and the
-- _safe_write_health() wrapper at prediction_engine.py logs but
-- swallows the failure -- so the model load itself still succeeds
-- (per the Q-D10 fall-through design from PR 2's DIAGNOSE round)
-- but the Engine Health admin page shows the model state as
-- offline / never-seen, defeating the whole point of the probe.
--
-- Empirical confirmation post-T-ACT-041 deploy (commit a77195a):
--   Railway log: health_write_failed
--     error={'code': '23514', 'details': 'Failing row contains
--     (..., direction_model, error, ...)', 'message': 'new row
--     for relation "trading_system_health" violates check
--     constraint "trading_system_health_service_name_check"'}
--
-- Idempotent: DROP CONSTRAINT IF EXISTS + re-add with the full
-- list. Preserves every name from the prior 20260421 migration
-- and appends the one new entry. Same pattern as
-- 20260419_health_service_name_constraint.sql and
-- 20260421_health_service_name_eod_jobs.sql.

ALTER TABLE trading_system_health
  DROP CONSTRAINT IF EXISTS trading_system_health_service_name_check;

ALTER TABLE trading_system_health
  ADD CONSTRAINT trading_system_health_service_name_check
  CHECK (service_name IN (
    'prediction_engine',
    'gex_engine',
    'strategy_selector',
    'risk_engine',
    'execution_engine',
    'data_ingestor',
    'polygon_feed',
    'tradier_websocket',
    'databento_feed',
    'sentinel',
    'economic_calendar',
    'macro_agent',
    'synthesis_agent',
    'surprise_detector',
    'flow_agent',
    'sentiment_agent',
    'feedback_agent',
    'prediction_watchdog',
    'emergency_backstop',
    'position_reconciliation',
    'earnings_scanner',
    -- 12D: regime x strategy performance matrix EOD job (4:20 PM ET)
    'strategy_matrix',
    -- 12E: counterfactual engine daily labeler (4:25 PM ET)
    'counterfactual_engine',
    -- T-ACT-041: LightGBM direction model load probe (one-shot at
    -- PredictionEngine.__init__; states healthy/degraded/error per
    -- the three-tier loader at prediction_engine.py
    -- _load_direction_model). 'degraded' is the expected steady
    -- state on Railway cold start (Tier 2 Supabase fallback), NOT
    -- an error condition.
    'direction_model'
  ));
