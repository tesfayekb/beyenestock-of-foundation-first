-- Migration: Add long_straddle and calendar_spread to strategy_type constraint
-- Phase 2B shipped long_straddle to the selector but missed the DB constraint.
-- Phase 3C adds calendar_spread.
-- Must run before Monday market open.

ALTER TABLE trading_positions
  DROP CONSTRAINT IF EXISTS trading_positions_strategy_type_check;

ALTER TABLE trading_positions
  ADD CONSTRAINT trading_positions_strategy_type_check
  CHECK (strategy_type IN (
    'put_credit_spread',
    'call_credit_spread',
    'iron_condor',
    'iron_butterfly',
    'debit_put_spread',
    'debit_call_spread',
    'long_put',
    'long_call',
    'long_straddle',
    'calendar_spread'
  ));

-- Add far_expiry_date column for calendar spread
-- (near leg = expiry_date, far leg = far_expiry_date)
ALTER TABLE trading_positions
  ADD COLUMN IF NOT EXISTS far_expiry_date DATE;

COMMENT ON COLUMN trading_positions.far_expiry_date IS
  'Far leg expiry for calendar spreads (near leg uses expiry_date). NULL for all other strategies.';
