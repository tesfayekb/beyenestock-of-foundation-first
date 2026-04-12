-- Stage 5D: Seed job_registry with 4 core jobs
INSERT INTO public.job_registry (id, version, owner_module, description, schedule, trigger_type, class, priority, execution_guarantee, timeout_seconds, max_retries, retry_policy, concurrency_policy, replay_safe, enabled, status)
VALUES
  ('health_check', '1.0.0', 'health-monitoring', 'Run subsystem health checks (DB, auth, audit)', '* * * * *', 'scheduled', 'system_critical', 'highest', 'at_least_once', 10, 3, 'aggressive', 'forbid', true, true, 'registered'),
  ('metrics_aggregate', '1.0.0', 'health-monitoring', 'Aggregate health snapshots into system_metrics', '*/5 * * * *', 'scheduled', 'operational', 'high', 'at_least_once', 20, 3, 'standard', 'forbid', true, true, 'registered'),
  ('alert_evaluation', '1.0.0', 'health-monitoring', 'Evaluate alert thresholds against system_metrics', '* * * * *', 'scheduled', 'system_critical', 'highest', 'at_least_once', 10, 3, 'aggressive', 'forbid', true, true, 'registered'),
  ('audit_cleanup', '1.0.0', 'audit-logging', 'Archive audit records older than 90 days (DEC-007)', '0 3 * * 0', 'scheduled', 'maintenance', 'normal', 'at_least_once', 25, 3, 'standard', 'forbid', true, true, 'registered')
ON CONFLICT (id) DO NOTHING;