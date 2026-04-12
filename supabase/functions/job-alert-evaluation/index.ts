/**
 * job-alert-evaluation — Scheduled job: evaluates alert thresholds against system_metrics.
 *
 * Invoked by pg_cron every 1 minute via pg_net HTTP POST.
 * Uses executeWithRetry() for retry, backoff, telemetry, and audit trail.
 * Reads enabled alert_configs, checks latest metric values against thresholds,
 * writes to alert_history and emits health.alert_triggered when breached.
 * Respects cooldown_seconds to prevent duplicate alerts.
 *
 * Owner: health-monitoring module
 * Job ID: alert_evaluation
 * Classification: system_critical
 * Schedule: * * * * * (every 1 min)
 */
import { createHandler, apiSuccess } from '../_shared/handler.ts'
import { supabaseAdmin } from '../_shared/supabase-admin.ts'
import { logAuditEvent } from '../_shared/audit.ts'
import { executeWithRetry } from '../_shared/job-executor.ts'

const JOB_ID = 'alert_evaluation'

function evaluateThreshold(value: number, threshold: number, comparison: string): boolean {
  switch (comparison) {
    case 'gt': return value > threshold
    case 'lt': return value < threshold
    case 'gte': return value >= threshold
    case 'lte': return value <= threshold
    case 'eq': return value === threshold
    default: return false
  }
}

Deno.serve(createHandler(async (req: Request): Promise<Response> => {
  let scheduledTime: string | undefined
  let scheduleWindowId: string | undefined
  try {
    const body = await req.json()
    if (body.time) {
      scheduledTime = body.time
      const d = new Date(body.time)
      scheduleWindowId = `${JOB_ID}:${d.toISOString().slice(0, 16)}`
    }
  } catch {
    // Manual trigger
  }

  const correlationId = crypto.randomUUID()

  const result = await executeWithRetry(
    async () => {
      // Fetch all enabled alert configs
      const { data: configs, error: configError } = await supabaseAdmin
        .from('alert_configs')
        .select('*')
        .eq('enabled', true)

      if (configError) {
        throw new Error(`Failed to fetch alert configs: ${configError.message}`)
      }

      if (!configs || configs.length === 0) {
        return { affectedRecords: 0, resourceUsage: { db_queries: 1, configs_evaluated: 0, alerts_triggered: 0 } }
      }

      let alertsTriggered = 0
      const now = new Date()

      for (const config of configs) {
        // Get the latest metric value for this config's metric_key
        const { data: latestMetric, error: metricError } = await supabaseAdmin
          .from('system_metrics')
          .select('value, recorded_at')
          .eq('metric_key', config.metric_key)
          .order('recorded_at', { ascending: false })
          .limit(1)
          .maybeSingle()

        if (metricError || !latestMetric) continue

        // Check threshold
        const breached = evaluateThreshold(
          Number(latestMetric.value),
          Number(config.threshold_value),
          config.comparison,
        )

        if (!breached) continue

        // Check cooldown: skip if an alert was fired within cooldown_seconds
        const cooldownCutoff = new Date(now.getTime() - config.cooldown_seconds * 1000)
        const { data: recentAlert } = await supabaseAdmin
          .from('alert_history')
          .select('id')
          .eq('alert_config_id', config.id)
          .gte('created_at', cooldownCutoff.toISOString())
          .limit(1)
          .maybeSingle()

        if (recentAlert) continue // Still in cooldown

        // Fire alert — insert into alert_history
        const { error: alertError } = await supabaseAdmin
          .from('alert_history')
          .insert({
            alert_config_id: config.id,
            metric_key: config.metric_key,
            metric_value: Number(latestMetric.value),
            threshold_value: Number(config.threshold_value),
            severity: config.severity,
          })

        if (alertError) {
          console.error(`[ALERT-EVAL] Failed to insert alert for ${config.metric_key}:`, alertError.message)
          continue
        }

        alertsTriggered++

        // Emit health.alert_triggered audit event
        await logAuditEvent({
          actorId: null,
          action: 'health.alert_triggered',
          targetType: 'alert_config',
          targetId: config.id,
          metadata: {
            metric_key: config.metric_key,
            metric_value: Number(latestMetric.value),
            threshold_value: Number(config.threshold_value),
            comparison: config.comparison,
            severity: config.severity,
          },
          correlationId,
        })
      }

      return {
        affectedRecords: alertsTriggered,
        resourceUsage: {
          db_queries: 1 + configs.length * 3, // 1 config fetch + per-config: metric + cooldown + insert
          configs_evaluated: configs.length,
          alerts_triggered: alertsTriggered,
        },
      }
    },
    {
      jobId: JOB_ID,
      correlationId,
      scheduleWindowId,
      scheduledTime,
      userAgent: 'system/job-alert-evaluation',
    },
  )

  return apiSuccess({
    jobId: JOB_ID,
    executionId: result.executionId,
    state: result.state,
    attempt: result.attempt,
    durationMs: result.durationMs,
    success: result.success,
    error: result.error,
  })
}, { rateLimit: 'relaxed' }))
