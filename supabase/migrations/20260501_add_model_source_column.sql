-- 2026-05-01 — emergency fix: add model_source column referenced by
-- backend/prediction_engine.py:883 (LightGBM v1 path) but omitted from
-- the 2026-04-30 schema migration (20260430_add_ai_synthesis_columns.sql).
--
-- INCIDENT BACKGROUND:
-- PR #83 (T-ACT-041, commit a77195a, "three-tier LightGBM model loader")
-- introduced a code-level dependency on a `model_source` column without
-- shipping a corresponding schema migration. The companion PR #82
-- (T-ACT-040) had shipped a migration adding `source` + `strategy_hint`
-- + `sizing_modifier` — but `source` and `model_source` are NOT the
-- same column. PR #83 author appears to have assumed they were.
--
-- SYMPTOM:
-- Every prediction cycle from LightGBM v1 activation (2026-04-30 21:33 UTC,
-- T-ACT-044 commit 5162020) through this fix (2026-05-01 ~13:55 UTC) failed
-- at the trading_prediction_outputs insert with:
--   PGRST204: "Could not find the 'model_source' column of
--             'trading_prediction_outputs' in the schema cache"
--
-- The outer try/except in prediction_engine.py:run_cycle() silently caught
-- the error, so cycles produced log events without persisting any row.
-- Unit tests at backend/tests/test_phase_a3.py:95-96 check dict-level value
-- only, not database insert — the gap escaped 5 PRs of DIAGNOSE discipline
-- (T-ACT-040 through T-ACT-044) and was only caught by post-deployment
-- empirical validation on 2026-05-01.
--
-- SCOPE:
-- This migration was first applied directly to Supabase production via SQL
-- Editor on 2026-05-01 ~13:55 UTC by operator. This file is the repo-sync
-- record of that fix — committing it ensures any fresh environment built
-- from supabase/migrations/ will have the column. Idempotent
-- (IF NOT EXISTS); safe to re-run on the production instance where it has
-- already been applied.
--
-- COLUMN SEMANTICS:
--   model_source: Provenance of direction probabilities specifically.
--                 Values: 'lgbm_v1' | 'placeholder' | 'regime_fallback'.
--                 NULL for legacy rows pre-2026-04-30 LightGBM v1 activation.
--
--   Distinct from the existing `source` column added by PR #82, which
--   covers the broader prediction-pipeline provenance
--   ('ai_synthesis' | 'lgbm_v1' | 'gex_zg_classifier' | 'regime_fallback').
--   Column-consolidation between `source` and `model_source` is a
--   deferred follow-up; flagged for post-validation T-ACT assignment.
--
-- LESSON-LEARNED:
-- Recorded as HANDOFF_NOTE Appendix A.5 in trading-docs/06-tracking/.
-- Future schema-touching PRs must include integration-test verification
-- of database persistence (not just dict-level unit tests) and must NOT
-- rely on outer try/except to mask schema errors.

ALTER TABLE public.trading_prediction_outputs
  ADD COLUMN IF NOT EXISTS model_source TEXT;

COMMENT ON COLUMN public.trading_prediction_outputs.model_source IS
  'Provenance of direction probabilities specifically (lgbm_v1 | placeholder | regime_fallback). '
  'Distinct from the broader `source` column which covers the full prediction pipeline provenance. '
  'Column-consolidation between source and model_source is a deferred follow-up — see T-ACT-NNN '
  '(to be assigned post-validation).';

-- No CHECK constraint on model_source — leaving open for future model
-- versions (lgbm_v2, lgbm_v3, etc.) and A/B variants. If/when the
-- canonical set stabilises, add a CHECK in a follow-up migration.
