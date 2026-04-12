-- MIG-031: Secure Cron Job Schedule with X-Cron-Secret Authentication
--
-- PURPOSE: Schedules all 4 job edge functions via pg_cron + pg_net with
-- the X-Cron-Secret header for authenticated invocation.
--
-- PREREQUISITES:
--   1. pg_cron and pg_net extensions enabled
--   2. CRON_SECRET set as a Supabase Edge Function secret
--   3. MIG-030 applied (insecure jobs unscheduled)
--
-- MANUAL STEP: Before running, replace the two placeholders:
--   - YOUR_CRON_SECRET_VALUE → the actual CRON_SECRET value
--   - YOUR_ANON_KEY          → the Supabase anon/publishable key
--   - PROJECT_REF            → the Supabase project ref (e.g. wbmbsclrgcnqaxmdsgfc)
--
-- This file is in sql/ (not supabase/migrations/) because it contains
-- environment-specific secrets that must not be committed to version control.
-- Apply via the Supabase SQL Editor after deployment.

-- 1. health_check — every minute
SELECT cron.schedule(
  'job-health-check',
  '* * * * *',
  $$
  SELECT net.http_post(
    url := 'https://PROJECT_REF.supabase.co/functions/v1/job-health-check',
    headers := '{"Content-Type": "application/json", "Authorization": "Bearer YOUR_ANON_KEY", "X-Cron-Secret": "YOUR_CRON_SECRET_VALUE"}'::jsonb,
    body := concat('{"time": "', now(), '"}')::jsonb
  ) AS request_id;
  $$
);

-- 2. alert_evaluation — every minute
SELECT cron.schedule(
  'job-alert-evaluation',
  '* * * * *',
  $$
  SELECT net.http_post(
    url := 'https://PROJECT_REF.supabase.co/functions/v1/job-alert-evaluation',
    headers := '{"Content-Type": "application/json", "Authorization": "Bearer YOUR_ANON_KEY", "X-Cron-Secret": "YOUR_CRON_SECRET_VALUE"}'::jsonb,
    body := concat('{"time": "', now(), '"}')::jsonb
  ) AS request_id;
  $$
);

-- 3. metrics_aggregate — every 5 minutes
SELECT cron.schedule(
  'job-metrics-aggregate',
  '*/5 * * * *',
  $$
  SELECT net.http_post(
    url := 'https://PROJECT_REF.supabase.co/functions/v1/job-metrics-aggregate',
    headers := '{"Content-Type": "application/json", "Authorization": "Bearer YOUR_ANON_KEY", "X-Cron-Secret": "YOUR_CRON_SECRET_VALUE"}'::jsonb,
    body := concat('{"time": "', now(), '"}')::jsonb
  ) AS request_id;
  $$
);

-- 4. audit_cleanup — weekly Sunday 3am UTC
SELECT cron.schedule(
  'job-audit-cleanup',
  '0 3 * * 0',
  $$
  SELECT net.http_post(
    url := 'https://PROJECT_REF.supabase.co/functions/v1/job-audit-cleanup',
    headers := '{"Content-Type": "application/json", "Authorization": "Bearer YOUR_ANON_KEY", "X-Cron-Secret": "YOUR_CRON_SECRET_VALUE"}'::jsonb,
    body := concat('{"time": "', now(), '"}')::jsonb
  ) AS request_id;
  $$
);
