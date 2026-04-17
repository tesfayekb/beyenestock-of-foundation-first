-- Add partial_exit_done flag to trading_positions
-- Prevents partial exit from firing more than once per position.
-- P0.6: partial exit at 25% profit (30% of contracts closed early).

ALTER TABLE public.trading_positions
  ADD COLUMN IF NOT EXISTS partial_exit_done BOOLEAN DEFAULT false;

COMMENT ON COLUMN public.trading_positions.partial_exit_done IS
  'True after 30% of contracts have been closed at 25% of max profit (P0.6)';
