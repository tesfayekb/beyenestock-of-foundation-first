-- 2026-04-22 infra hotfix: guarantee the three Phase A1 outcome-label
-- columns exist on public.trading_prediction_outputs.
--
-- The original migration 20260417130000_add_prediction_outcome_labels.sql
-- already adds these same columns with IF NOT EXISTS, so this migration
-- is a no-op in any database where that one ran cleanly. It exists
-- purely to re-assert the invariant in environments where the earlier
-- migration failed to apply for any reason (partial apply, ordering
-- issue, operator-induced drift) — running it is safe because every
-- statement is idempotent.
--
-- Deliberately does NOT add any columns beyond the original three.
-- `outcome_labeled_at` and `spx_price_at_outcome` have zero consumers
-- anywhere in the Python / TypeScript / SQL tree (verified 2026-04-22
-- via ripgrep across the repo) — adding them here would be dead
-- schema and the kind of technical debt that silently costs review
-- time forever.

ALTER TABLE public.trading_prediction_outputs
  ADD COLUMN IF NOT EXISTS outcome_direction TEXT
    CHECK (outcome_direction IN ('bull', 'bear', 'neutral')),
  ADD COLUMN IF NOT EXISTS outcome_correct   BOOLEAN,
  ADD COLUMN IF NOT EXISTS spx_return_30min  NUMERIC(8,6);

CREATE INDEX IF NOT EXISTS idx_prediction_outcome
  ON public.trading_prediction_outputs(outcome_correct, no_trade_signal);
