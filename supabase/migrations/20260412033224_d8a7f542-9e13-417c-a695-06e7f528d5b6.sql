-- Remove the permissive INSERT policy that allowed any authenticated user to write audit_logs
DROP POLICY IF EXISTS "audit_logs_insert_policy" ON public.audit_logs;
