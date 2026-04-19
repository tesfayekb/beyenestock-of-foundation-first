-- Migration: Add 'idle' status to trading_system_health
-- 'idle' means the service is not running because market is closed
-- (holiday, weekend, outside hours). Different from 'degraded' which
-- means broken during expected operating hours.

ALTER TABLE trading_system_health
  DROP CONSTRAINT IF EXISTS trading_system_health_status_check;

ALTER TABLE trading_system_health
  ADD CONSTRAINT trading_system_health_status_check
  CHECK (status IN ('healthy', 'degraded', 'error', 'offline', 'idle'));
