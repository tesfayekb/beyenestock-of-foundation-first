-- RPC function for feedback agent temporal lateral join.
-- Called by feedback_agent._fetch_closed_trades() as primary path.
-- Falls back to Python join if this fails.

CREATE OR REPLACE FUNCTION get_feedback_trades()
RETURNS TABLE (
  id                    UUID,
  session_id            UUID,
  strategy_type         TEXT,
  entry_at              TIMESTAMPTZ,
  exit_at               TIMESTAMPTZ,
  net_pnl               NUMERIC,
  entry_regime          TEXT,
  entry_credit          NUMERIC,
  contracts             INTEGER,
  prediction_direction  TEXT,
  prediction_confidence NUMERIC,
  prediction_regime     TEXT
)
LANGUAGE SQL
STABLE
AS $$
  SELECT
    pos.id,
    pos.session_id,
    pos.strategy_type,
    pos.entry_at,
    pos.exit_at,
    pos.net_pnl,
    pos.entry_regime,
    pos.entry_credit,
    pos.contracts,
    p.direction   AS prediction_direction,
    p.confidence  AS prediction_confidence,
    p.regime      AS prediction_regime
  FROM trading_positions pos
  LEFT JOIN LATERAL (
    SELECT direction, confidence, regime
    FROM trading_prediction_outputs pred
    WHERE pred.session_id = pos.session_id
      AND pred.predicted_at <= pos.entry_at
    ORDER BY pred.predicted_at DESC
    LIMIT 1
  ) p ON TRUE
  WHERE pos.status = 'closed'
    AND pos.position_mode = 'virtual'
    AND pos.net_pnl IS NOT NULL
  ORDER BY pos.exit_at DESC
  LIMIT 60;
$$;
