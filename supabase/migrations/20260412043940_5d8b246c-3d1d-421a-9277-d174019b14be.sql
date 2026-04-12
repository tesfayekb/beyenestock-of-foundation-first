-- Stage 5A: system_health_snapshots table
-- Stores periodic health check results for monitoring dashboard

CREATE TABLE public.system_health_snapshots (
  id uuid NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  status text NOT NULL CHECK (status IN ('healthy', 'degraded', 'unhealthy')),
  checks jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- RLS: SELECT only for users with monitoring.view permission
-- No INSERT/UPDATE/DELETE via client — edge functions use service role
ALTER TABLE public.system_health_snapshots ENABLE ROW LEVEL SECURITY;

CREATE POLICY "monitoring_view_select"
  ON public.system_health_snapshots
  FOR SELECT
  TO authenticated
  USING (public.has_permission(auth.uid(), 'monitoring.view'));

COMMENT ON TABLE public.system_health_snapshots IS 'Periodic health check snapshots for system monitoring (Stage 5A)';