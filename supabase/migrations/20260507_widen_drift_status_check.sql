-- Migration: widen trading_model_performance.drift_status CHECK
-- constraint to include 'ok' and 'unknown' (T-ACT-076 / F-068-A,
-- 2026-05-07).
--
-- Symptom: every Sunday weekly job at 22:05 UTC silently fails to
-- write a trading_model_performance row whenever
-- model_retraining.detect_drift returns drift_status='ok' or
-- drift_status='unknown'. The original schema migration
-- (20260416172751_0ef832ac-fab6-4da7-a0d0-050df61b399f.sql:270)
-- declared:
--
--   drift_status TEXT DEFAULT 'normal'
--     CHECK (drift_status IN ('normal','warning','critical'))
--
-- but model_retraining.detect_drift (backend/model_retraining.py
-- lines 478-517) returns one of: 'ok' | 'warning' | 'critical' |
-- 'unknown'. The two value spaces do NOT match. Postgres rejects
-- inserts with 'ok' / 'unknown' via error 23514 (check_violation)
-- but the broad except Exception in run_weekly_model_performance
-- (model_retraining.py line ~695) swallows the PostgrestAPIError,
-- producing only a generic ERROR log with no schema-specific
-- detail. The dashboard then falls back to a stale row from the
-- 22:00 UTC sibling writer in calibration_engine.write_model_
-- performance, which writes drift_status='normal' with NULL
-- accuracies. This dual-writer pattern is logged as F-068-H.
--
-- This migration widens the CHECK to match the function's actual
-- return values, preserving diagnostic granularity (we keep 'ok'
-- distinct from 'normal' rather than remapping at the function
-- layer). The function-layer remap was the runner-up option
-- considered in T-ACT-076 critique Q10 sub-decision; CHECK
-- widening was preferred for ROI-grounds reasons (no information
-- loss, smaller diff, no risk of changing the daily
-- check_prediction_drift contract which also returns 'ok').
--
-- Companion code change: backend/model_retraining.py lines
-- ~677-697 narrow the broad except Exception around the insert
-- to surface PostgrestAPIError distinctly with structured
-- pgrst_code/pgrst_details/pgrst_hint logging + write_health_
-- status('error') + send_alert(CRITICAL, ...). This follows the
-- T-ACT-047 Choice C pattern from prediction_engine.py:1641-1690.
--
-- Idempotent: DROP CONSTRAINT IF EXISTS + re-add with the full
-- five-value allowlist. Preserves every existing accepted value
-- ('normal','warning','critical') and appends the two missing
-- values from detect_drift's actual return space.
--
-- Cross-references:
--   - T-ACT-076 (HANDOFF_NOTE_2026-05-06_F068I_BINARY_LABELER_FIX.md)
--   - F-068-A (silent schema-CHECK rejection — A.7 family
--     subclass)
--   - F-068-G (threshold-metric mismatch from S15 — dissolved
--     by T-ACT-076 Position 1a labeler fix once 'ok' rows
--     can persist)
--   - T-ACT-047 Choice C pattern (prediction_engine.py:1641-1690)

ALTER TABLE trading_model_performance
  DROP CONSTRAINT IF EXISTS trading_model_performance_drift_status_check;

ALTER TABLE trading_model_performance
  ADD CONSTRAINT trading_model_performance_drift_status_check
  CHECK (drift_status IN (
    -- Original allowlist from
    -- 20260416172751_0ef832ac-fab6-4da7-a0d0-050df61b399f.sql:270:
    'normal',
    'warning',
    'critical',
    -- Added 2026-05-07 to align with
    -- model_retraining.detect_drift return values:
    'ok',
    'unknown'
  ));
