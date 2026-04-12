/**
 * job-health-check — Scheduled job: runs subsystem health checks.
 *
 * Invoked by pg_cron every 1 minute via pg_net HTTP POST.
 * Uses executeWithRetry() for retry, backoff, telemetry, and audit trail.
 * Stores snapshot in system_health_snapshots.
 * Emits health.status_changed on status transition.
 *
 * Owner: health-monitoring module
 * Job ID: health_check
 * Classification: system_critical
 * Schedule: * * * * * (every 1 min)
 */
import { createHandler, apiSuccess } from '../_shared/handler.ts'
import { supabaseAdmin } from '../_shared/supabase-admin.ts'
import { logAuditEvent } from '../_shared/audit.ts'
import {
  checkDatabase,
  checkAuth,
  checkAuditPipeline,
  deriveOverallStatus,
} from '../_shared/health-checks.ts'
import { executeWithRetry } from '../_shared/job-executor.ts'

const JOB_ID = 'health_check'

Deno.serve(createHandler(async (req: Request): Promise<Response> => {
  // Extract scheduled time from pg_cron body (if present)
  let scheduledTime: string | undefined
  let scheduleWindowId: string | undefined
  try {
    const body = await req.json()
    if (body.time) {
      scheduledTime = body.time
      // Minute-bucket dedup: truncate to minute
      const d = new Date(body.time)
      scheduleWindowId = `${JOB_ID}:${d.toISOString().slice(0, 16)}`
    }
  } catch {
    // Manual trigger or no body — use defaults
  }

  const correlationId = crypto.randomUUID()

  const result = await executeWithRetry(
    async () => {
      // Query previous snapshot BEFORE inserting new one (race condition prevention)
      const { data: previousSnapshot } = await supabaseAdmin
        .from('system_health_snapshots')
        .select('status')
        .order('created_at', { ascending: false })
        .limit(1)
        .maybeSingle()

      // Run all subsystem checks in parallel
      const [db, auth, audit] = await Promise.all([
        checkDatabase(),
        checkAuth(),
        checkAuditPipeline(),
      ])

      const checks = { database: db, auth, audit_pipeline: audit }
      const overallStatus = deriveOverallStatus(checks)

      // Store snapshot
      const { error: insertError } = await supabaseAdmin
        .from('system_health_snapshots')
        .insert({ status: overallStatus, checks })

      if (insertError) {
        throw new Error(`Snapshot insert failed: ${insertError.message}`)
      }

      // Emit health.status_changed if status transitioned
      if (previousSnapshot && previousSnapshot.status !== overallStatus) {
        await logAuditEvent({
          actorId: null,
          action: 'health.status_changed',
          targetType: 'system',
          metadata: {
            previous_status: previousSnapshot.status,
            new_status: overallStatus,
            checks,
          },
          correlationId,
        })
      }

      return {
        affectedRecords: 1,
        resourceUsage: {
          db_queries: 3, // 3 subsystem checks + 1 previous + 1 insert
          status: overallStatus,
        },
      }
    },
    {
      jobId: JOB_ID,
      correlationId,
      scheduleWindowId,
      scheduledTime,
      userAgent: 'system/job-health-check',
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
