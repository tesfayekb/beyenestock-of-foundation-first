-- Migration: expand trading_system_health service_name allowlist to
-- include the 12D + 12E EOD batch jobs (strategy_matrix and
-- counterfactual_engine). Without this their health writes are
-- rejected silently by the CHECK constraint and the Engine Health
-- admin page shows them as offline even after a successful run.
--
-- Idempotent: DROP CONSTRAINT IF EXISTS + re-add with the full list.
-- Preserves every name from the prior 20260419 migration and appends
-- the two new EOD services.

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
    'counterfactual_engine'
  ));
