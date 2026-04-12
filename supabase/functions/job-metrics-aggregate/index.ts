/**
 * job-metrics-aggregate — Scheduled job: aggregates health snapshots into system_metrics.
 *
 * Invoked by pg_cron every 5 minutes via pg_net HTTP POST.
 * Uses executeWithRetry() for retry, backoff, telemetry, and audit trail.
 * Reads system_health_snapshots from the last 5 minutes and produces
 * aggregated metrics in system_metrics.
 *
 * Owner: health-monitoring module
 * Job ID: metrics_aggregate
 * Classification: operational
 * Schedule: *​/5 * * * * (every 5 min)
 */
import { createHandler, apiSuccess } from '../_shared/handler.ts'
import { supabaseAdmin } from '../_shared/supabase-admin.ts'
import { executeWithRetry } from '../_shared/job-executor.ts'

const JOB_ID = 'metrics_aggregate'

Deno.serve(createHandler(async (req: Request): Promise<Response> => {
  let scheduledTime: string | undefined
  let scheduleWindowId: string | undefined
  try {
    const body = await req.json()
    if (body.time) {
      scheduledTime = body.time
      // 5-minute bucket dedup
      const d = new Date(body.time)
      const bucket = Math.floor(d.getMinutes() / 5) * 5
      scheduleWindowId = `${JOB_ID}:${d.toISOString().slice(0, 11)}${String(d.getHours()).padStart(2, '0')}:${String(bucket).padStart(2, '0')}`
    }
  } catch {
    // Manual trigger
  }

  const correlationId = crypto.randomUUID()

  const result = await executeWithRetry(
    async () => {
      const now = new Date()
      const fiveMinAgo = new Date(now.getTime() - 5 * 60 * 1000)

      // Fetch recent health snapshots
      const { data: snapshots, error: fetchError } = await supabaseAdmin
        .from('system_health_snapshots')
        .select('status, checks, created_at')
        .gte('created_at', fiveMinAgo.toISOString())
        .order('created_at', { ascending: true })

      if (fetchError) {
        throw new Error(`Failed to fetch snapshots: ${fetchError.message}`)
      }

      if (!snapshots || snapshots.length === 0) {
        return { affectedRecords: 0, resourceUsage: { db_queries: 1, snapshots_processed: 0 } }
      }

      // Aggregate metrics from snapshots
      const metrics: Array<{ metric_key: string; value: number; metadata: Record<string, unknown> }> = []
      const recordedAt = now.toISOString()

      // 1. Health status counts
      const statusCounts = { healthy: 0, degraded: 0, unhealthy: 0 }
      for (const s of snapshots) {
        const status = s.status as keyof typeof statusCounts
        if (status in statusCounts) statusCounts[status]++
      }

      metrics.push(
        { metric_key: 'health.status_healthy_count', value: statusCounts.healthy, metadata: { window_minutes: 5 } },
        { metric_key: 'health.status_degraded_count', value: statusCounts.degraded, metadata: { window_minutes: 5 } },
        { metric_key: 'health.status_unhealthy_count', value: statusCounts.unhealthy, metadata: { window_minutes: 5 } },
      )

      // 2. Health rate (healthy / total)
      const total = snapshots.length
      const healthRate = total > 0 ? statusCounts.healthy / total : 0
      metrics.push({ metric_key: 'health.health_rate', value: Math.round(healthRate * 10000) / 10000, metadata: { window_minutes: 5, total_snapshots: total } })

      // 3. Per-subsystem average latency
      const subsystems = ['database', 'auth', 'audit_pipeline']
      for (const sub of subsystems) {
        const latencies: number[] = []
        for (const s of snapshots) {
          const checks = s.checks as Record<string, { latency_ms?: number }>
          if (checks?.[sub]?.latency_ms != null) {
            latencies.push(checks[sub].latency_ms)
          }
        }
        if (latencies.length > 0) {
          const avg = latencies.reduce((a, b) => a + b, 0) / latencies.length
          const max = Math.max(...latencies)
          metrics.push(
            { metric_key: `health.${sub}.avg_latency_ms`, value: Math.round(avg * 100) / 100, metadata: { window_minutes: 5, samples: latencies.length } },
            { metric_key: `health.${sub}.max_latency_ms`, value: max, metadata: { window_minutes: 5, samples: latencies.length } },
          )
        }
      }

      // Insert all metrics
      const metricsToInsert = metrics.map(m => ({
        metric_key: m.metric_key,
        value: m.value,
        metadata: m.metadata,
        recorded_at: recordedAt,
      }))

      const { error: insertError } = await supabaseAdmin
        .from('system_metrics')
        .insert(metricsToInsert)

      if (insertError) {
        throw new Error(`Metrics insert failed: ${insertError.message}`)
      }

      return {
        affectedRecords: metricsToInsert.length,
        resourceUsage: {
          db_queries: 2, // 1 select + 1 batch insert
          snapshots_processed: snapshots.length,
          metrics_produced: metricsToInsert.length,
        },
      }
    },
    {
      jobId: JOB_ID,
      correlationId,
      scheduleWindowId,
      scheduledTime,
      userAgent: 'system/job-metrics-aggregate',
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
