-- GAP 2: Change audit_logs.actor_id FK to ON DELETE SET NULL
-- This preserves audit records when a user is deleted (GDPR right-to-erasure)
-- while maintaining the audit trail (the action still happened).
ALTER TABLE public.audit_logs
  DROP CONSTRAINT IF EXISTS audit_logs_actor_id_fkey;

ALTER TABLE public.audit_logs
  ADD CONSTRAINT audit_logs_actor_id_fkey
  FOREIGN KEY (actor_id)
  REFERENCES auth.users(id)
  ON DELETE SET NULL;