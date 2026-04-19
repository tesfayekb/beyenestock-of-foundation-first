-- S4 / D-1: Tighten RLS on core trading tables.
--
-- The original migration (20260416172751_*.sql) and the paper-phase
-- migration (20260417000001_paper_phase_criteria.sql) granted SELECT
-- to anyone with role = 'authenticated' — that's any signed-in user
-- of any tenant role, regardless of whether they have the trading
-- module enabled. The trading_feature_flags table (20260427) already
-- uses the correct pattern: check the 'trading.view' permission via
-- user_roles → role_permissions → permissions. Apply that same
-- pattern here.
--
-- Tables tightened:
--   trading_positions
--   trading_sessions
--   trading_prediction_outputs
--   trading_system_health
--   paper_phase_criteria
--
-- Service-role writes (used by the Railway backend) are unaffected —
-- the existing service_write_* policies remain in place.
--
-- OPERATOR ACTION REQUIRED before applying:
--   1. Confirm 'trading.view' exists in the permissions table:
--        SELECT key FROM permissions WHERE key = 'trading.view';
--   2. Confirm at least one user is granted 'trading.view' via a role
--      (otherwise no human will be able to read these tables after
--      this migration applies):
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
-- trading_positions
-- ──────────────────────────────────────────────────────────────────
DROP POLICY IF EXISTS "authenticated_read_positions"
    ON public.trading_positions;

CREATE POLICY "trading_view_read_positions"
    ON public.trading_positions
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
-- trading_sessions
-- ──────────────────────────────────────────────────────────────────
DROP POLICY IF EXISTS "authenticated_read_sessions"
    ON public.trading_sessions;

CREATE POLICY "trading_view_read_sessions"
    ON public.trading_sessions
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
-- trading_prediction_outputs
-- ──────────────────────────────────────────────────────────────────
DROP POLICY IF EXISTS "authenticated_read_predictions"
    ON public.trading_prediction_outputs;

CREATE POLICY "trading_view_read_predictions"
    ON public.trading_prediction_outputs
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
-- trading_system_health
-- ──────────────────────────────────────────────────────────────────
DROP POLICY IF EXISTS "authenticated_read_trading_health"
    ON public.trading_system_health;

CREATE POLICY "trading_view_read_trading_health"
    ON public.trading_system_health
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
-- paper_phase_criteria
-- ──────────────────────────────────────────────────────────────────
DROP POLICY IF EXISTS "authenticated_read_paper_criteria"
    ON public.paper_phase_criteria;

CREATE POLICY "trading_view_read_paper_criteria"
    ON public.paper_phase_criteria
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
