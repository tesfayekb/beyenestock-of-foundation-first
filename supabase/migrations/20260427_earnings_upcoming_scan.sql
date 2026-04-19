-- CSP fix migration #3: earnings_upcoming_scan
--
-- Mirrors the upcoming-earnings list (Redis key
-- earnings:upcoming_events) and the last_scan_at timestamp so the
-- /trading/earnings page can read them via direct supabase-js queries
-- instead of fetching from Railway. Redis stays AUTHORITATIVE for the
-- earnings system itself.
--
-- One INSERT per scan. The page reads the most recent row by
-- scanned_at; older rows form a small audit history of what the
-- 8:45 AM ET scan saw on each day.
--
-- OPERATOR ACTION: apply this migration manually in the Supabase SQL
-- editor before deploying the CSP-fix code.

CREATE TABLE earnings_upcoming_scan (
    scan_id     BIGSERIAL PRIMARY KEY,
    scanned_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    payload     JSONB NOT NULL
);

CREATE INDEX idx_earnings_upcoming_scanned_at
    ON earnings_upcoming_scan(scanned_at DESC);

ALTER TABLE earnings_upcoming_scan ENABLE ROW LEVEL SECURITY;

CREATE POLICY "service_role_full" ON earnings_upcoming_scan
    FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY "authenticated_read" ON earnings_upcoming_scan
    FOR SELECT TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM user_roles ur
            JOIN role_permissions rp ON rp.role_id = ur.role_id
            JOIN permissions p ON p.id = rp.permission_id
            WHERE ur.user_id = auth.uid() AND p.key = 'trading.view'
        )
    );
