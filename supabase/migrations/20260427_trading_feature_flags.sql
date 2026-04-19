-- CSP fix migration #1: trading_feature_flags
--
-- Mirrors the Redis flag state into Supabase so the frontend can read
-- it via direct supabase-js queries instead of fetching from Railway
-- (which the Lovable-hosted CSP blocks).
--
-- Redis remains AUTHORITATIVE for the trading engine. The backend
-- writes Redis first, then upserts here in the same try/except block;
-- a Supabase failure must never prevent a flag from taking effect.
--
-- Polarity is preserved verbatim: `enabled` reflects the operator's
-- intended state. Strategy/agent flags default OFF (absent row = OFF);
-- signal flags default ON (absent row = ON) — the frontend applies
-- this polarity using the static signal-flag set.
--
-- OPERATOR ACTION: apply this migration manually in the Supabase SQL
-- editor before deploying the CSP-fix code. The application never
-- runs migrations from code.

CREATE TABLE trading_feature_flags (
    flag_key    TEXT PRIMARY KEY,
    enabled     BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by  TEXT
);

CREATE INDEX idx_trading_feature_flags_updated_at
    ON trading_feature_flags(updated_at DESC);

ALTER TABLE trading_feature_flags ENABLE ROW LEVEL SECURITY;

CREATE POLICY "service_role_full" ON trading_feature_flags
    FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY "authenticated_read" ON trading_feature_flags
    FOR SELECT TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM user_roles ur
            JOIN role_permissions rp ON rp.role_id = ur.role_id
            JOIN permissions p ON p.id = rp.permission_id
            WHERE ur.user_id = auth.uid() AND p.key = 'trading.view'
        )
    );
