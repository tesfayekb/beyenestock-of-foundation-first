-- MIG-033: MFA recovery codes table
-- Stores bcrypt-hashed single-use recovery codes for MFA bypass

CREATE TABLE public.mfa_recovery_codes (
  id uuid NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  code_hash text NOT NULL,
  used_at timestamp with time zone,
  created_at timestamp with time zone NOT NULL DEFAULT now()
);

-- Index for fast user lookup
CREATE INDEX idx_mfa_recovery_codes_user_id ON public.mfa_recovery_codes(user_id);

-- Enable RLS — no client read access, all operations via service-role
ALTER TABLE public.mfa_recovery_codes ENABLE ROW LEVEL SECURITY;

-- No RLS policies = no client access. Service-role bypasses RLS.
-- This is intentional: recovery codes are security-critical and must never
-- be readable from the client. All operations go through edge functions.