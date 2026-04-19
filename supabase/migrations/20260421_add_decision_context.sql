-- Migration: Add decision_context and prediction_id to trading_positions
-- decision_context: JSONB snapshot of active flags/model at trade entry
--   → enables A/B analysis of flag changes over time
-- prediction_id: FK to the prediction that drove this trade
--   → required for Loop 2 (meta-label model) — NULL for existing rows is fine

ALTER TABLE trading_positions
  ADD COLUMN IF NOT EXISTS decision_context JSONB,
  ADD COLUMN IF NOT EXISTS prediction_id UUID
    REFERENCES trading_prediction_outputs(id);

CREATE INDEX IF NOT EXISTS idx_position_prediction
  ON trading_positions(prediction_id)
  WHERE prediction_id IS NOT NULL;

COMMENT ON COLUMN trading_positions.decision_context IS
  'JSON snapshot of active feature flags and model config when trade fired.
   Used for A/B analysis. Example: {"synthesis_enabled": true, "flow_enabled": false,
   "ai_provider": "anthropic", "ai_model": "claude-sonnet-4-5"}';

COMMENT ON COLUMN trading_positions.prediction_id IS
  'FK to trading_prediction_outputs. NULL for positions opened before this migration.
   Required for Loop 2 meta-label model training.';
