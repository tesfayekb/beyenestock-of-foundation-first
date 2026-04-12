/**
 * job-audit-cleanup — Scheduled job: deletes audit records older than 90 days.
 *
 * Invoked by pg_cron weekly (Sunday 03:00 UTC) via pg_net HTTP POST.
 * Uses executeWithRetry() for retry, backoff, telemetry, and audit trail.
 *
 * DW-029 resolved: Uses rpc_batch_delete_audit_logs() to delete in batches
 * of 1000, looping until zero remaining or 25s timeout budget consumed.
 * This prevents unbounded DELETE statements that could exceed edge function
 * timeout limits on large datasets.
 *
 * Owner: audit-logging module
 * Job ID: audit_cleanup
 * Classification: maintenance
 * Schedule: 0 3 * * 0 (weekly, Sunday 3am UTC)
 */
import { createHandler, apiSuccess } from '../_shared/handler.ts'
import { supabaseAdmin } from '../_shared/supabase-admin.ts'
import { executeWithRetry } from '../_shared/job-executor.ts'
import { verifyCronSecret } from '../_shared/cron-auth.ts'

const JOB_ID = 'audit_cleanup'
const RETENTION_DAYS = 90
const BATCH_SIZE = 1000
const TIMEOUT_BUDGET_MS = 25_000 // Leave 5s headroom from 30s limit

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
      const weekStart = new Date(d)
      weekStart.setDate(d.getDate() - d.getDay())
      scheduleWindowId = `${JOB_ID}:${weekStart.toISOString().slice(0, 10)}`
    }
  } catch {
    // Manual trigger
  }

  const correlationId = crypto.randomUUID()

  const result = await executeWithRetry(
    async () => {
      const cutoffDate = new Date()
      cutoffDate.setDate(cutoffDate.getDate() - RETENTION_DAYS)
      const cutoffIso = cutoffDate.toISOString()

      let totalDeleted = 0
      const startTime = Date.now()

      // Batched delete loop
      while (Date.now() - startTime < TIMEOUT_BUDGET_MS) {
        const { data: deletedCount, error } = await supabaseAdmin.rpc(
          'rpc_batch_delete_audit_logs',
          { cutoff: cutoffIso, batch_size: BATCH_SIZE }
        )

        if (error) {
          throw new Error(`Batch delete failed: ${error.message}`)
        }

        const count = deletedCount as number
        totalDeleted += count

        // No more records to delete
        if (count < BATCH_SIZE) break
      }

      return {
        affectedRecords: totalDeleted,
        resourceUsage: {
          records_deleted: totalDeleted,
          cutoff_date: cutoffIso,
          retention_days: RETENTION_DAYS,
          batch_size: BATCH_SIZE,
          elapsed_ms: Date.now() - startTime,
        },
      }
    },
    {
      jobId: JOB_ID,
      correlationId,
      scheduleWindowId,
      scheduledTime,
      userAgent: 'system/job-audit-cleanup',
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
