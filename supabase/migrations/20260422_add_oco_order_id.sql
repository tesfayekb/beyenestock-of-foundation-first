-- Migration 12I (C1): persist the Tradier OCO bracket order ID
-- returned by execution_engine._submit_oco_bracket() when a position
-- is opened in real-capital mode. NULL in sandbox/paper mode and NULL
-- when OCO_BRACKET_ENABLED is false — the column is an observability
-- handle, not a trading decision input.
--
-- Idempotent via IF NOT EXISTS. Safe to apply before or after the
-- corresponding code deploy.

ALTER TABLE public.trading_positions
  ADD COLUMN IF NOT EXISTS oco_order_id TEXT;

COMMENT ON COLUMN public.trading_positions.oco_order_id IS
  'Tradier OCO bracket order ID. Only populated when TRADIER_SANDBOX=false AND OCO_BRACKET_ENABLED=true. NULL in paper trading mode or when OCO is disabled.';
