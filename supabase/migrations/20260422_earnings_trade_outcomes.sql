-- Migration 12J: earnings_trade_outcomes — label store for the
-- Phase 5B earnings learning loop. Populated by
-- edge_calculator.label_earnings_outcome() on every closed earnings
-- straddle from trade #1; consumed by train_earnings_model()
-- once >= 50 rows exist.
--
-- SHIPPED DIVERGENCE from 12J spec:
--   position_id references public.earnings_positions(id), NOT
--   public.trading_positions(id). The spec named the wrong parent
--   table — earnings positions live in earnings_positions (see
--   20260426_earnings_system.sql). A FK to trading_positions would
--   reject every insert because the UUIDs come from a different
--   table. ON DELETE SET NULL keeps outcome rows queryable even
--   if a historical earnings position is ever purged.
--
-- Idempotent: CREATE TABLE IF NOT EXISTS + policy/index guards so
-- re-applying this migration on an already-bootstrapped database
-- is a no-op.

CREATE TABLE IF NOT EXISTS public.earnings_trade_outcomes (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    position_id         UUID REFERENCES public.earnings_positions(id)
                            ON DELETE SET NULL,
    ticker              TEXT NOT NULL,
    entry_at            TIMESTAMPTZ,
    exit_at             TIMESTAMPTZ,
    correct_direction   BOOLEAN,
    pnl_vs_expected     NUMERIC(8,4),
    iv_crush_captured   BOOLEAN,
    actual_move_pct     NUMERIC(8,6),
    expected_move_pct   NUMERIC(8,6),
    net_pnl             NUMERIC(10,2),
    created_at          TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE public.earnings_trade_outcomes ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = 'earnings_trade_outcomes'
          AND policyname = 'service_write_earnings_outcomes'
    ) THEN
        CREATE POLICY "service_write_earnings_outcomes"
            ON public.earnings_trade_outcomes
            FOR ALL
            USING (auth.role() = 'service_role');
    END IF;
END
$$;

CREATE INDEX IF NOT EXISTS idx_earnings_outcomes_ticker
    ON public.earnings_trade_outcomes(ticker);

COMMENT ON TABLE public.earnings_trade_outcomes IS
    '12J label store — one row per closed earnings straddle. Read by train_earnings_model() once 50+ rows exist to produce per-ticker edge weights that replace the hardcoded EARNINGS_HISTORY dict in edge_calculator.py.';
