-- T1-13: Tighten RLS on trading_signals and trading_model_performance.
--
-- Both tables currently use auth.role() = 'authenticated' which allows
-- any signed-in user to read every trading signal and model performance
-- row regardless of whether they have the trading module enabled.
-- This is the same gap 20260420_tighten_core_table_rls.sql closed on
-- trading_positions / trading_sessions / trading_prediction_outputs /
-- trading_system_health / paper_phase_criteria — this migration
-- applies the identical pattern to the two remaining tables.
--
-- Pattern: replace the permissive authenticated_read_* policy with a
-- trading_view_read_* policy that checks the `trading.view` permission
-- via user_roles -> role_permissions -> permissions.
--
-- Service-role writes (used by the Railway backend) are unaffected —
-- service_write_* policies remain in place.
--
-- OPERATOR ACTION REQUIRED before applying:
--   1. Confirm `trading.view` exists in the permissions table:
--        SELECT key FROM permissions WHERE key = 'trading.view';
--   2. Confirm at least one user is granted `trading.view`:
--        SELECT u.email, p.key
--        FROM auth.users u
--        JOIN user_roles ur ON ur.user_id = u.id
--        JOIN role_permissions rp ON rp.role_id = ur.role_id
--        JOIN permissions p ON p.id = rp.permission_id
--        WHERE p.key = 'trading.view';
--   3. Run this migration in the Supabase SQL editor.
--
-- Idempotent — safe to re-run. DROP POLICY IF EXISTS guards every
-- replacement.

-- ──────────────────────────────────────────────────────────────────
-- trading_signals
-- ──────────────────────────────────────────────────────────────────
DROP POLICY IF EXISTS "authenticated_read_signals"
    ON public.trading_signals;

CREATE POLICY "trading_view_read_signals"
    ON public.trading_signals
    FOR SELECT TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.user_roles ur
            JOIN public.role_permissions rp ON rp.role_id = ur.role_id
            JOIN public.permissions p ON p.id = rp.permission_id
            WHERE ur.user_id = auth.uid()
              AND p.key = 'trading.view'
        )
    );

-- ──────────────────────────────────────────────────────────────────
-- trading_model_performance
-- ──────────────────────────────────────────────────────────────────
DROP POLICY IF EXISTS "authenticated_read_model_perf"
    ON public.trading_model_performance;

CREATE POLICY "trading_view_read_model_perf"
    ON public.trading_model_performance
    FOR SELECT TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.user_roles ur
            JOIN public.role_permissions rp ON rp.role_id = ur.role_id
            JOIN public.permissions p ON p.id = rp.permission_id
            WHERE ur.user_id = auth.uid()
              AND p.key = 'trading.view'
        )
    );
