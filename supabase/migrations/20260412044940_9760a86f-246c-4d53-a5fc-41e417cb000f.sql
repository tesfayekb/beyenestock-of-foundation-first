-- Stage 5B: Metrics & Alerting Infrastructure

-- ─── system_metrics ─────────────────────────────────────────────────
CREATE TABLE public.system_metrics (
  id uuid NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  metric_key text NOT NULL,
  value numeric NOT NULL,
  metadata jsonb DEFAULT '{}'::jsonb,
  recorded_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.system_metrics ENABLE ROW LEVEL SECURITY;

CREATE POLICY "monitoring_view_metrics"
  ON public.system_metrics
  FOR SELECT
  TO authenticated
  USING (public.has_permission(auth.uid(), 'monitoring.view'));

CREATE INDEX idx_system_metrics_key_time
  ON public.system_metrics(metric_key, recorded_at);

COMMENT ON TABLE public.system_metrics IS 'Time-series metric snapshots for system monitoring (Stage 5B)';

-- ─── alert_configs ──────────────────────────────────────────────────
CREATE TABLE public.alert_configs (
  id uuid NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  metric_key text NOT NULL,
  severity text NOT NULL CHECK (severity IN ('info', 'warning', 'critical')),
  threshold_value numeric NOT NULL,
  comparison text NOT NULL CHECK (comparison IN ('gt', 'lt', 'gte', 'lte', 'eq')),
  enabled boolean NOT NULL DEFAULT true,
  cooldown_seconds integer NOT NULL DEFAULT 300,
  created_by uuid NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.alert_configs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "monitoring_view_alert_configs"
  ON public.alert_configs
  FOR SELECT
  TO authenticated
  USING (public.has_permission(auth.uid(), 'monitoring.view'));

-- Trigger for updated_at
CREATE TRIGGER update_alert_configs_updated_at
  BEFORE UPDATE ON public.alert_configs
  FOR EACH ROW
  EXECUTE FUNCTION public.update_updated_at_column();

COMMENT ON TABLE public.alert_configs IS 'Configurable alert thresholds for metric monitoring (Stage 5B)';

-- ─── alert_history ──────────────────────────────────────────────────
CREATE TABLE public.alert_history (
  id uuid NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  alert_config_id uuid NOT NULL REFERENCES public.alert_configs(id) ON DELETE CASCADE,
  metric_key text NOT NULL,
  severity text NOT NULL CHECK (severity IN ('info', 'warning', 'critical')),
  metric_value numeric NOT NULL,
  threshold_value numeric NOT NULL,
  resolved_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.alert_history ENABLE ROW LEVEL SECURITY;

CREATE POLICY "monitoring_view_alert_history"
  ON public.alert_history
  FOR SELECT
  TO authenticated
  USING (public.has_permission(auth.uid(), 'monitoring.view'));

CREATE INDEX idx_alert_history_config
  ON public.alert_history(alert_config_id);

CREATE INDEX idx_alert_history_created
  ON public.alert_history(created_at);

COMMENT ON TABLE public.alert_history IS 'Triggered alert records for monitoring (Stage 5B)';