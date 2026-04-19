-- Phase 3B: A/B Shadow Infrastructure
-- shadow_predictions: one row per shadow cycle (Portfolio A)
-- ab_session_comparison: one row per trading day (Portfolio A vs B)
--
-- OPERATOR ACTION: apply this migration manually in the Supabase
-- SQL editor before deploying the Phase 3B code. The application
-- never runs migrations from code.

CREATE TABLE shadow_predictions (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id        UUID REFERENCES trading_sessions(id),
  predicted_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  -- Portfolio A prediction (rule-based only, no AI synthesis)
  direction         TEXT CHECK (direction IN ('bull','bear','neutral')),
  confidence        NUMERIC(5,4),
  regime            TEXT,
  rcs               NUMERIC(5,2),
  no_trade_signal   BOOLEAN DEFAULT false,
  no_trade_reason   TEXT,
  -- Context at time of prediction
  vix               NUMERIC(8,4),
  vvix_z_score      NUMERIC(8,4),
  gex_net           NUMERIC(15,2),
  spx_price         NUMERIC(10,4)
);

CREATE INDEX idx_shadow_session ON shadow_predictions(session_id, predicted_at DESC);
CREATE INDEX idx_shadow_date    ON shadow_predictions(predicted_at DESC);

ALTER TABLE shadow_predictions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "service_role_full" ON shadow_predictions
  FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "authenticated_read" ON shadow_predictions
  FOR SELECT TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM user_roles ur
      JOIN role_permissions rp ON rp.role_id = ur.role_id
      JOIN permissions p ON p.id = rp.permission_id
      WHERE ur.user_id = auth.uid() AND p.key = 'trading.view'
    )
  );

-- One row per trading day comparing Portfolio A vs Portfolio B
CREATE TABLE ab_session_comparison (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_date        DATE NOT NULL UNIQUE,
  -- Portfolio A (rule-based shadow)
  a_no_trade          BOOLEAN DEFAULT false,
  a_direction         TEXT,
  a_confidence        NUMERIC(5,4),
  a_regime            TEXT,
  a_synthetic_pnl     NUMERIC(10,4),  -- computed synthetic P&L
  a_would_have_traded BOOLEAN DEFAULT false,
  -- Portfolio B (real paper system)
  b_session_pnl       NUMERIC(10,4),  -- actual session virtual_pnl
  b_trades_count      INTEGER,
  b_no_trade          BOOLEAN DEFAULT false,
  -- Actual market outcome
  spx_open            NUMERIC(10,4),
  spx_close           NUMERIC(10,4),
  move_pct            NUMERIC(8,6),
  -- Metadata
  computed_at         TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_ab_date ON ab_session_comparison(session_date DESC);

ALTER TABLE ab_session_comparison ENABLE ROW LEVEL SECURITY;
CREATE POLICY "service_role_full" ON ab_session_comparison
  FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY "authenticated_read" ON ab_session_comparison
  FOR SELECT TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM user_roles ur
      JOIN role_permissions rp ON rp.role_id = ur.role_id
      JOIN permissions p ON p.id = rp.permission_id
      WHERE ur.user_id = auth.uid() AND p.key = 'trading.view'
    )
  );
