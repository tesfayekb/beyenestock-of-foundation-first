-- Enable pg_trgm extension for trigram-based ILIKE search
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Composite indexes for audit_logs: filtered + sorted queries
CREATE INDEX IF NOT EXISTS idx_audit_logs_actor_created
  ON public.audit_logs (actor_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_audit_logs_action_created
  ON public.audit_logs (action, created_at DESC);

-- GIN trigram index for profiles.display_name ILIKE search
CREATE INDEX IF NOT EXISTS idx_profiles_display_name_trgm
  ON public.profiles USING GIN (display_name gin_trgm_ops);
