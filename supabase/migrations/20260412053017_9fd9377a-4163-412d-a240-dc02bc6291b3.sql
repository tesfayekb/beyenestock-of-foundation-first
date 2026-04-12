-- Unschedule existing insecure cron jobs
SELECT cron.unschedule('job-health-check');
SELECT cron.unschedule('job-alert-evaluation');
SELECT cron.unschedule('job-metrics-aggregate');
SELECT cron.unschedule('job-audit-cleanup');