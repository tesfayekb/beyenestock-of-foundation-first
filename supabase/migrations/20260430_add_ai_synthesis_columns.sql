-- 2026-04-30 schema-discipline + AI synthesis output unblock.
--
-- The AI synth path at backend/prediction_engine.py:498-510 has been
-- emitting strategy_hint, sizing_modifier, and source keys since the
-- Phase 2A initial implementation. These keys had no corresponding
-- columns in trading_prediction_outputs, causing every AI-synth-driven
-- prediction insert to fail with PGRST204 ("Could not find column").
-- The outer try/except in run_cycle silently caught the error, so AI
-- synth cycles produced log events without persisting any row.
--
-- Empirical confirmation: Apr 30 13:30-13:45 UTC had 4
-- `prediction_from_ai_synthesis` log events but 0 rows in
-- trading_prediction_outputs for that window.
--
-- Why these columns matter:
--   strategy_hint   — consumed by strategy_selector.py:1019-1075
--                     (strategy:ai_hint_override:enabled feature flag).
--   source          — consumed by strategy_selector.py:1517
--                     (telemetry "ai_hint" vs "regime" routing).
--   sizing_modifier — forward-compat pass-through (reserved for
--                     Action-8-adjacent sizing-modifier consumers).
--
-- All three columns NULLABLE so non-AI-synth prediction paths
-- (LightGBM, GEX/ZG, regime fallback) which omit these keys continue
-- to insert cleanly — every NULL on those rows is correct.
--
-- Idempotent (IF NOT EXISTS); safe to re-run.

ALTER TABLE public.trading_prediction_outputs
  ADD COLUMN IF NOT EXISTS strategy_hint   TEXT,
  ADD COLUMN IF NOT EXISTS sizing_modifier NUMERIC(8,4),
  ADD COLUMN IF NOT EXISTS source          TEXT;

COMMENT ON COLUMN public.trading_prediction_outputs.strategy_hint IS
  'AI synthesis recommended strategy hint. Consumed by '
  'strategy_selector.py:1019-1075 when strategy:ai_hint_override:enabled '
  'feature flag is on. NULL for non-AI-synth prediction paths.';

COMMENT ON COLUMN public.trading_prediction_outputs.sizing_modifier IS
  'AI synthesis sizing recommendation (clamped 0.25-1.2 per '
  'synthesis_agent.py validation). Forward-compat for Action-8-adjacent '
  'sizing-modifier consumers. NULL for non-AI-synth prediction paths.';

COMMENT ON COLUMN public.trading_prediction_outputs.source IS
  'Provenance of the prediction: ai_synthesis | lgbm_v1 | gex_zg_classifier '
  '| regime_fallback. Consumed by strategy_selector.py:1517 telemetry '
  'routing (ai_hint vs regime). NULL for legacy rows pre-Apr-30.';

-- No CHECK constraint on `source` — leaving open for future paths
-- (e.g., new model versions, A/B variants) that may write this field.
-- If/when the canonical set stabilises, add a CHECK in a follow-up
-- migration.
