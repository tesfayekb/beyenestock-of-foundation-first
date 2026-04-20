-- 12E / D4: counterfactual engine columns.
-- Stores the simulated P&L, simulated-strategy label, and simulation
-- timestamp for every no-trade prediction that gets labeled by the
-- counterfactual_engine EOD job. Pure observability — never read by
-- any trading-decision path.

ALTER TABLE public.trading_prediction_outputs
    ADD COLUMN IF NOT EXISTS counterfactual_pnl NUMERIC(10,2);

ALTER TABLE public.trading_prediction_outputs
    ADD COLUMN IF NOT EXISTS counterfactual_strategy TEXT;

ALTER TABLE public.trading_prediction_outputs
    ADD COLUMN IF NOT EXISTS counterfactual_simulated_at TIMESTAMPTZ;

COMMENT ON COLUMN public.trading_prediction_outputs.counterfactual_pnl IS
    'Simulated P&L (1-contract basis, USD) had the no-trade signal '
    'instead opened a position. Populated by counterfactual_engine '
    'EOD job at 4:25 PM ET.';

COMMENT ON COLUMN public.trading_prediction_outputs.counterfactual_strategy IS
    'Strategy type used for the counterfactual simulation. Currently '
    'defaults to iron_condor since trading_prediction_outputs does not '
    'persist a per-prediction strategy hint.';

COMMENT ON COLUMN public.trading_prediction_outputs.counterfactual_simulated_at IS
    'UTC timestamp when the counterfactual simulation wrote this row. '
    'Used to skip already-labeled rows on retries / backfills.';

-- Partial index accelerates the "no-trade rows not yet simulated"
-- query that the labeler runs every weekday at 4:25 PM ET. Without
-- this index the job degrades to a full scan once the table grows
-- past ~10k rows.
CREATE INDEX IF NOT EXISTS idx_prediction_counterfactual_pending
    ON public.trading_prediction_outputs (predicted_at DESC)
    WHERE no_trade_signal = true AND counterfactual_pnl IS NULL;
