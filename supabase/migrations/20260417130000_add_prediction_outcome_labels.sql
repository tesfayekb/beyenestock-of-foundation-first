-- Phase A1: Add outcome label columns to trading_prediction_outputs
-- These columns enable real directional accuracy measurement for GLC-001/002.
-- Populated daily by label_prediction_outcomes() in model_retraining.py.

ALTER TABLE public.trading_prediction_outputs
  ADD COLUMN IF NOT EXISTS outcome_direction  TEXT
    CHECK (outcome_direction IN ('bull', 'bear', 'neutral')),
  ADD COLUMN IF NOT EXISTS outcome_correct    BOOLEAN,
  ADD COLUMN IF NOT EXISTS spx_return_30min   NUMERIC(8,6);

COMMENT ON COLUMN public.trading_prediction_outputs.outcome_direction IS
  'Actual SPX direction 30 minutes after prediction (bull/bear/neutral)';
COMMENT ON COLUMN public.trading_prediction_outputs.outcome_correct IS
  'True when predicted direction matched realized SPX direction';
COMMENT ON COLUMN public.trading_prediction_outputs.spx_return_30min IS
  'SPX decimal return (e.g. 0.0019 = +0.19%) from predicted_at to predicted_at + 30 minutes';

CREATE INDEX IF NOT EXISTS idx_prediction_outcome
  ON public.trading_prediction_outputs(outcome_correct, no_trade_signal);
