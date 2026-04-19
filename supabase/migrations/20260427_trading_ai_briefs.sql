-- CSP fix migration #2: trading_ai_briefs
--
-- Mirrors the AI agent brief Redis keys into Supabase so the frontend
-- War Room and Intelligence pages can read them via direct supabase-js
-- queries instead of fetching from Railway (which the Lovable-hosted
-- CSP blocks).
--
-- One row per brief kind. Agents upsert on `brief_kind` so there is at
-- most one row per kind at any time — the same shape that the
-- /admin/trading/intelligence endpoint returned. Redis remains
-- AUTHORITATIVE for the trading engine; the upsert here is purely a
-- read-mirror for the dashboard.
--
--   brief_kind values written by the backend:
--     'calendar'  — economic_calendar    (calendar:today:intel)
--     'macro'     — macro_agent          (ai:macro:brief)
--     'flow'      — flow_agent           (ai:flow:brief)
--     'sentiment' — sentiment_agent      (ai:sentiment:brief)
--     'synthesis' — synthesis_agent      (ai:synthesis:latest)
--                   surprise_detector also updates 'synthesis'
--
-- OPERATOR ACTION: apply this migration manually in the Supabase SQL
-- editor before deploying the CSP-fix code.

CREATE TABLE trading_ai_briefs (
    brief_kind    TEXT PRIMARY KEY,
    payload       JSONB NOT NULL,
    generated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_trading_ai_briefs_generated_at
    ON trading_ai_briefs(generated_at DESC);

ALTER TABLE trading_ai_briefs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "service_role_full" ON trading_ai_briefs
    FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY "authenticated_read" ON trading_ai_briefs
    FOR SELECT TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM user_roles ur
            JOIN role_permissions rp ON rp.role_id = ur.role_id
            JOIN permissions p ON p.id = rp.permission_id
            WHERE ur.user_id = auth.uid() AND p.key = 'trading.view'
        )
    );
