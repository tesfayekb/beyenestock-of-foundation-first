-- Migration 12H (Phase A): persist additional features to
-- trading_prediction_outputs so that by the time we have 90+ labeled
-- sessions we already have a full column of training data for the
-- Phase A LightGBM direction model.
--
-- All columns NULL-able — missing values must stay NULL rather than
-- silently coerce to 0, otherwise the model learns on a fake signal
-- during any Redis outage / feed gap. IF NOT EXISTS keeps this
-- migration idempotent and safe to apply before or after the
-- corresponding code deploy.

ALTER TABLE public.trading_prediction_outputs
  ADD COLUMN IF NOT EXISTS prior_session_return     NUMERIC(8,6),
  ADD COLUMN IF NOT EXISTS vix_term_ratio           NUMERIC(6,4),
  ADD COLUMN IF NOT EXISTS spx_momentum_4h          NUMERIC(8,6),
  ADD COLUMN IF NOT EXISTS gex_flip_proximity       NUMERIC(8,6),
  ADD COLUMN IF NOT EXISTS earnings_proximity_score NUMERIC(5,4);

COMMENT ON COLUMN public.trading_prediction_outputs.prior_session_return
  IS 'Previous session SPX return. Feature for Phase A LightGBM direction model.';
COMMENT ON COLUMN public.trading_prediction_outputs.vix_term_ratio
  IS 'VIX9D / VIX ratio. Contango vs backwardation signal. NULL when either leg missing.';
COMMENT ON COLUMN public.trading_prediction_outputs.spx_momentum_4h
  IS 'SPX 4-hour log return. Medium-term momentum feature.';
COMMENT ON COLUMN public.trading_prediction_outputs.gex_flip_proximity
  IS 'abs(gex_flip_zone - spx_price) / spx_price. Pin stability signal. NULL when flip_zone or price missing.';
COMMENT ON COLUMN public.trading_prediction_outputs.earnings_proximity_score
  IS 'Score 0-1 for proximity to next major earnings event. Sourced from calendar:earnings_proximity_score Redis key.';
