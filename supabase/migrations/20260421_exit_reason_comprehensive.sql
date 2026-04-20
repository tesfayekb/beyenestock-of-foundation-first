-- Migration: comprehensive exit_reason CHECK constraint for
-- public.trading_positions.
--
-- Root cause this fixes:
--   The original CHECK constraint (baseline migration 20260416172751)
--   hardcoded 11 exit reasons. Since then, position_monitor.py has
--   emitted NEW exit_reason strings (tighter thresholds, new safety
--   backstops, new reconciliation paths) but the constraint was
--   never updated. Every close write with one of those strings is
--   silently REJECTED by Postgres (Supabase returns an error but
--   the monitor's outer try/except swallows it), leaving the row
--   status='open' forever and the position stuck.
--
-- Audit performed 2026-04-21 (Ctrl-F every `exit_reason=` in
-- backend/position_monitor.py + backend/execution_engine.py):
--
--   FROM position_monitor.py
--     take_profit_40pct              (L686  -- B3: 40% of max profit)
--     stop_loss_150pct_credit        (L726  -- B3: 150% of credit)
--     take_profit_debit_100pct       (L537  -- debit strategies TP)
--     stop_loss_debit_100pct         (L546  -- debit strategies SL)
--     cv_stress_exit_d017            (L702  -- D-017 CV_Stress guard)
--     time_stop_230pm_d010           (L95   -- D-010 2:30 PM short-gamma)
--     time_stop_345pm_d011           (L137  -- D-011 3:45 PM hard close)
--     emergency_backstop             (L188  -- runaway-loss backstop)
--     watchdog_engine_silent         (L300  -- engine heartbeat absent)
--     eod_reconciliation_stale_open  (L379  -- EOD reconcile sweep)
--     straddle_pre_event_exit        (L470  -- Phase 2B pre-event)
--
--   FROM execution_engine.py
--     (no hardcoded strings — exit_reason is a function parameter
--      that flows through from callers; line 720 references
--      'profit_target' and 'manual' in a read-only comparison.)
--
-- Policy going forward: adding a new exit_reason string in Python
-- code REQUIRES shipping a new migration to extend this constraint
-- in the same commit. The companion test
-- backend/tests/test_exit_reason_constraint.py parses both files'
-- AST and this migration's SQL and fails CI if the two drift apart.
--
-- Idempotent: DROP IF EXISTS + ADD, safe to replay.

ALTER TABLE public.trading_positions
  DROP CONSTRAINT IF EXISTS trading_positions_exit_reason_check;

ALTER TABLE public.trading_positions
  ADD CONSTRAINT trading_positions_exit_reason_check
  CHECK (exit_reason IS NULL OR exit_reason IN (
    -- ── Legacy values (baseline 20260416172751) ──────────────────
    -- Preserved even if no current code path emits them — historical
    -- rows and any future path that rediscovers the semantic name
    -- must remain valid. Dropping these would retroactively make
    -- closed positions fail re-validation during any table rewrite.
    'profit_target',
    'stop_loss',
    'time_stop_230pm',
    'time_stop_345pm',
    'touch_prob_threshold',
    'cv_stress_trigger',
    'state4_degrading',
    'portfolio_stop',
    'circuit_breaker',
    'capital_preservation',
    'manual',

    -- ── Hardcoded in backend/position_monitor.py (2026-04-21 audit) ──
    'take_profit_40pct',              -- B3 tighter TP trigger
    'stop_loss_150pct_credit',        -- B3 tighter SL trigger
    'take_profit_debit_100pct',       -- debit strategies: 100% gain
    'stop_loss_debit_100pct',         -- debit strategies: 100% loss
    'cv_stress_exit_d017',            -- D-017 CV_Stress override
    'time_stop_230pm_d010',           -- D-010 short-gamma 2:30 ET
    'time_stop_345pm_d011',           -- D-011 hard close 3:45 ET
    'emergency_backstop',             -- runaway-loss circuit
    'watchdog_engine_silent',         -- engine heartbeat absent
    'eod_reconciliation_stale_open',  -- EOD stale-open sweep
    'straddle_pre_event_exit'         -- Phase 2B pre-event exit
  ));

COMMENT ON CONSTRAINT trading_positions_exit_reason_check
  ON public.trading_positions IS
  '12-bug: comprehensive exit_reason allowlist rebuilt 2026-04-21 after silent rejects caused stuck-open positions. Source of truth for the companion AST test at backend/tests/test_exit_reason_constraint.py — update both in the same commit when adding a new exit reason.';
