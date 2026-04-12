-- Schedule health_check — every minute
SELECT cron.schedule(
  'job-health-check',
  '* * * * *',
  $$
  SELECT net.http_post(
    url := 'https://wbmbsclrgcnqaxmdsgfc.supabase.co/functions/v1/job-health-check',
    headers := '{"Content-Type": "application/json", "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndibWJzY2xyZ2NucWF4bWRzZ2ZjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzU3MjI1ODUsImV4cCI6MjA5MTI5ODU4NX0.mQnC6IatK3vRmz0R0nmS_tYi1G5cFRg-bRMOgn8UwiM"}'::jsonb,
    body := concat('{"time": "', now(), '"}')::jsonb
  ) AS request_id;
  $$
);

-- Schedule alert_evaluation — every minute
SELECT cron.schedule(
  'job-alert-evaluation',
  '* * * * *',
  $$
  SELECT net.http_post(
    url := 'https://wbmbsclrgcnqaxmdsgfc.supabase.co/functions/v1/job-alert-evaluation',
    headers := '{"Content-Type": "application/json", "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndibWJzY2xyZ2NucWF4bWRzZ2ZjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzU3MjI1ODUsImV4cCI6MjA5MTI5ODU4NX0.mQnC6IatK3vRmz0R0nmS_tYi1G5cFRg-bRMOgn8UwiM"}'::jsonb,
    body := concat('{"time": "', now(), '"}')::jsonb
  ) AS request_id;
  $$
);

-- Schedule metrics_aggregate — every 5 minutes
SELECT cron.schedule(
  'job-metrics-aggregate',
  '*/5 * * * *',
  $$
  SELECT net.http_post(
    url := 'https://wbmbsclrgcnqaxmdsgfc.supabase.co/functions/v1/job-metrics-aggregate',
    headers := '{"Content-Type": "application/json", "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndibWJzY2xyZ2NucWF4bWRzZ2ZjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzU3MjI1ODUsImV4cCI6MjA5MTI5ODU4NX0.mQnC6IatK3vRmz0R0nmS_tYi1G5cFRg-bRMOgn8UwiM"}'::jsonb,
    body := concat('{"time": "', now(), '"}')::jsonb
  ) AS request_id;
  $$
);

-- Schedule audit_cleanup — weekly on Sunday at 3 AM UTC
SELECT cron.schedule(
  'job-audit-cleanup',
  '0 3 * * 0',
  $$
  SELECT net.http_post(
    url := 'https://wbmbsclrgcnqaxmdsgfc.supabase.co/functions/v1/job-audit-cleanup',
    headers := '{"Content-Type": "application/json", "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndibWJzY2xyZ2NucWF4bWRzZ2ZjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzU3MjI1ODUsImV4cCI6MjA5MTI5ODU4NX0.mQnC6IatK3vRmz0R0nmS_tYi1G5cFRg-bRMOgn8UwiM"}'::jsonb,
    body := concat('{"time": "', now(), '"}')::jsonb
  ) AS request_id;
  $$
);