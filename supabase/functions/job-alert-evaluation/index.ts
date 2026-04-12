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
import { verifyCronSecret } from '../_shared/cron-auth.ts'

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
  const authError = verifyCronSecret(req)
  if (authError) return authError
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

      // Bulk-fetch: latest metric for every unique metric_key in one query
      const uniqueKeys = [...new Set(configs.map(c => c.metric_key))]
      const { data: allMetrics } = await supabaseAdmin
        .from('system_metrics')
        .select('metric_key, value, recorded_at')
        .in('metric_key', uniqueKeys)
        .order('recorded_at', { ascending: false })

      // Build map: metric_key → latest value
      const latestMetricMap = new Map<string, { value: number; recorded_at: string }>()
      if (allMetrics) {
        for (const m of allMetrics) {
          if (!latestMetricMap.has(m.metric_key)) {
            latestMetricMap.set(m.metric_key, { value: Number(m.value), recorded_at: m.recorded_at })
          }
        }
      }

      // Evaluate thresholds first pass — find breached configs
      const now = new Date()
      const breachedConfigs: Array<{ config: typeof configs[0]; metricValue: number }> = []

      for (const config of configs) {
        const latest = latestMetricMap.get(config.metric_key)
        if (!latest) continue

        const breached = evaluateThreshold(
          latest.value,
          Number(config.threshold_value),
          config.comparison,
        )
        if (breached) {
          breachedConfigs.push({ config, metricValue: latest.value })
        }
      }

      if (breachedConfigs.length === 0) {
        return {
          affectedRecords: 0,
          resourceUsage: { db_queries: 2, configs_evaluated: configs.length, alerts_triggered: 0 },
        }
      }

      // Bulk-fetch: recent alerts for all breached config IDs
      const breachedIds = breachedConfigs.map(b => b.config.id)
      const earliestCooldown = new Date(
        now.getTime() - Math.max(...breachedConfigs.map(b => b.config.cooldown_seconds)) * 1000
      )

      const { data: recentAlerts } = await supabaseAdmin
        .from('alert_history')
        .select('alert_config_id, created_at')
        .in('alert_config_id', breachedIds)
        .gte('created_at', earliestCooldown.toISOString())

      // Build cooldown map: config_id → latest alert time
      const cooldownMap = new Map<string, string>()
      if (recentAlerts) {
        for (const a of recentAlerts) {
          const existing = cooldownMap.get(a.alert_config_id)
          if (!existing || a.created_at > existing) {
            cooldownMap.set(a.alert_config_id, a.created_at)
          }
        }
      }

      let alertsTriggered = 0

      for (const { config, metricValue } of breachedConfigs) {
        // Per-config cooldown check
        const lastAlertTime = cooldownMap.get(config.id)
        if (lastAlertTime) {
          const cooldownCutoff = new Date(now.getTime() - config.cooldown_seconds * 1000)
          if (new Date(lastAlertTime) >= cooldownCutoff) continue // Still in cooldown
        }

        // Fire alert
        const { error: alertError } = await supabaseAdmin
          .from('alert_history')
          .insert({
            alert_config_id: config.id,
            metric_key: config.metric_key,
            metric_value: metricValue,
            threshold_value: Number(config.threshold_value),
            severity: config.severity,
          })

        if (alertError) {
          console.error(`[ALERT-EVAL] Failed to insert alert for ${config.metric_key}:`, alertError.message)
          continue
        }

        alertsTriggered++

        await logAuditEvent({
          actorId: null,
          action: 'health.alert_triggered',
          targetType: 'alert_config',
          targetId: config.id,
          metadata: {
            metric_key: config.metric_key,
            metric_value: metricValue,
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
          db_queries: 3 + alertsTriggered, // configs + metrics + recent_alerts + inserts
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
