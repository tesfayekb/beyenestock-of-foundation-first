-- Fix: expand trading_system_health_service_name_check constraint
-- to include HARD-A circuit breaker services, agents, and earnings scanner.
-- Applied manually to production on 2026-04-19 after health_write_failed errors.
-- This migration is idempotent — safe to re-run.

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
    'earnings_scanner'
  ));
