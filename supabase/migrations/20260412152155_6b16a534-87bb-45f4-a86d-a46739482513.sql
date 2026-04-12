CREATE TABLE IF NOT EXISTS public.mfa_recovery_attempts (
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  failed_count integer NOT NULL DEFAULT 0,
  locked_until timestamp with time zone,
  last_attempt_at timestamp with time zone NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id)
);

ALTER TABLE public.mfa_recovery_attempts ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE public.mfa_recovery_attempts IS 'Tracks failed MFA recovery code attempts per user. Service-role only — no client RLS policies.';
COMMENT ON COLUMN public.mfa_recovery_attempts.failed_count IS 'Number of consecutive failed recovery code attempts.';
COMMENT ON COLUMN public.mfa_recovery_attempts.locked_until IS 'If set and in the future, user is locked out from recovery code attempts.';
