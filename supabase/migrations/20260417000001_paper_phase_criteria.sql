-- Paper phase go-live criteria tracker
-- Tracks all 12 GLC criteria defined in D-013
-- One row per criterion, upserted daily by the criteria evaluator job

CREATE TABLE IF NOT EXISTS public.paper_phase_criteria (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  criterion_id          TEXT NOT NULL UNIQUE,  -- 'GLC-001' through 'GLC-012'
  criterion_name        TEXT NOT NULL,
  target_description    TEXT NOT NULL,
  current_value_text    TEXT,                  -- human-readable current value
  current_value_numeric NUMERIC,               -- numeric for comparison logic
  status                TEXT NOT NULL DEFAULT 'not_started'
                        CHECK (status IN ('not_started','in_progress','passed','failed','pending','blocked')),
  observations_count    INTEGER DEFAULT 0,     -- data points measured so far
  target_numeric        NUMERIC,               -- numeric target for comparison
  is_manual             BOOLEAN DEFAULT false, -- true for criteria that need human verification
  last_evaluated_at     TIMESTAMPTZ,
  notes                 TEXT,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- RLS
ALTER TABLE public.paper_phase_criteria ENABLE ROW LEVEL SECURITY;

CREATE POLICY "trading_view_paper_criteria" ON public.paper_phase_criteria
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM public.user_roles ur
      JOIN public.roles r ON ur.role_id = r.id
      JOIN public.role_permissions rp ON r.id = rp.role_id
      JOIN public.permissions p ON rp.permission_id = p.id
      WHERE ur.user_id = auth.uid()
      AND p.key = 'trading.view'
    )
  );

-- Updated_at trigger
CREATE TRIGGER paper_phase_criteria_updated_at
  BEFORE UPDATE ON public.paper_phase_criteria
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Seed all 12 criteria with initial not_started status
INSERT INTO public.paper_phase_criteria
  (criterion_id, criterion_name, target_description, target_numeric, is_manual, status)
VALUES
  ('GLC-001', 'Aggregate Prediction Accuracy',
   'Prediction accuracy >= 58% over full 45 days',
   58.0, false, 'not_started'),

  ('GLC-002', 'Per-Regime Accuracy',
   'Each day type with >= 8 observations achieves >= 55% accuracy',
   55.0, false, 'not_started'),

  ('GLC-003', 'Training Examples Per Cell',
   'Minimum 50 training examples per regime-strategy combination',
   50.0, false, 'not_started'),

  ('GLC-004', 'Under-Sampled Cell Handling',
   'Under-sampled cells flagged and sized at 25% until 50 examples',
   NULL, false, 'not_started'),

  ('GLC-005', 'Paper Sharpe Ratio',
   'Paper trading Sharpe ratio >= 1.5 over 45-day period',
   1.5, false, 'not_started'),

  ('GLC-006', 'Zero Unhandled Exceptions',
   'Zero unhandled exceptions in the final 20 paper sessions',
   0.0, false, 'not_started'),

  ('GLC-007', 'Circuit Breaker Scenarios',
   'All 6 circuit breaker scenarios tested in Tradier sandbox',
   6.0, true, 'not_started'),

  ('GLC-008', 'Kill-Switch Response Time',
   'Kill-switch response confirmed < 5 seconds from mobile',
   5.0, true, 'not_started'),

  ('GLC-009', 'Sentinel Operational',
   'Independent Sentinel verified operational on GCP',
   NULL, true, 'not_started'),

  ('GLC-010', 'WebSocket Heartbeat Failover',
   'Disconnect triggers degraded mode within 3 seconds',
   3.0, true, 'not_started'),

  ('GLC-011', 'Slippage Model Calibration',
   'Minimum 200 fill observations for predictive slippage model',
   200.0, false, 'not_started'),

  ('GLC-012', 'GEX Tracking Error',
   'GEX tracking error <= 15% vs OCC actuals (CBOE DataShop)',
   15.0, false, 'not_started')

ON CONFLICT (criterion_id) DO NOTHING;
