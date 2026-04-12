-- MIG-035: Batched audit cleanup RPC function (DW-029)
-- Deletes audit_logs older than cutoff in batches to avoid timeout

CREATE OR REPLACE FUNCTION public.rpc_batch_delete_audit_logs(
  cutoff TIMESTAMPTZ,
  batch_size INT DEFAULT 1000
)
RETURNS INT
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  deleted_count INT;
BEGIN
  -- Safety: enforce max batch size
  IF batch_size > 5000 THEN
    batch_size := 5000;
  END IF;
  IF batch_size < 1 THEN
    batch_size := 1;
  END IF;

  DELETE FROM public.audit_logs
  WHERE id IN (
    SELECT id FROM public.audit_logs
    WHERE created_at < cutoff
    ORDER BY created_at ASC
    LIMIT batch_size
  );

  GET DIAGNOSTICS deleted_count = ROW_COUNT;
  RETURN deleted_count;
END;
$$;

-- Restrict to service role only (no anon/authenticated)
REVOKE ALL ON FUNCTION public.rpc_batch_delete_audit_logs(TIMESTAMPTZ, INT) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.rpc_batch_delete_audit_logs(TIMESTAMPTZ, INT) FROM anon;
REVOKE ALL ON FUNCTION public.rpc_batch_delete_audit_logs(TIMESTAMPTZ, INT) FROM authenticated;