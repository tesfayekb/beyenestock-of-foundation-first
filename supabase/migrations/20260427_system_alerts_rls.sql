-- CSP fix migration #4: system_alerts RLS read policy
--
-- The system_alerts table already exists in production (created
-- manually outside of migrations). This migration ONLY adds the RLS
-- read policy needed for the activation-page hook to read alerts
-- directly from Supabase. The table itself is NOT (re)created — only
-- the policy is added (idempotently) so the migration is safe to
-- re-apply if needed.
--
-- OPERATOR ACTION: apply this migration manually in the Supabase SQL
-- editor. Verify system_alerts already exists first; if it does not,
-- create it via the activation-dashboard rollout migration (not this
-- one).

ALTER TABLE system_alerts ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "service_role_full" ON system_alerts;
CREATE POLICY "service_role_full" ON system_alerts
    FOR ALL TO service_role USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "authenticated_read" ON system_alerts;
CREATE POLICY "authenticated_read" ON system_alerts
    FOR SELECT TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM user_roles ur
            JOIN role_permissions rp ON rp.role_id = ur.role_id
            JOIN permissions p ON p.id = rp.permission_id
            WHERE ur.user_id = auth.uid() AND p.key = 'trading.view'
        )
    );
