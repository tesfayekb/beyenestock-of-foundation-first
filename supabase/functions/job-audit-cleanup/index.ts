/**
 * job-audit-cleanup — Scheduled job: archives audit records older than 90 days.
 *
 * Invoked by pg_cron weekly (Sunday 03:00 UTC) via pg_net HTTP POST.
 * Uses executeWithRetry() for retry, backoff, telemetry, and audit trail.
 * Deletes audit_logs records where created_at < now() - 90 days (DEC-007).
 *
 * Owner: audit-logging module
 * Job ID: audit_cleanup
 * Classification: maintenance
 * Schedule: 0 3 * * 0 (weekly, Sunday 3am UTC)
 */
import { createHandler, apiSuccess } from '../_shared/handler.ts'
import { supabaseAdmin } from '../_shared/supabase-admin.ts'
import { executeWithRetry } from '../_shared/job-executor.ts'

const JOB_ID = 'audit_cleanup'
const RETENTION_DAYS = 90

Deno.serve(createHandler(async (req: Request): Promise<Response> => {
  let scheduledTime: string | undefined
  let scheduleWindowId: string | undefined
  try {
    const body = await req.json()
    if (body.time) {
      scheduledTime = body.time
      // Weekly bucket dedup: ISO week
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

      // Count records to be deleted (pre-condition validation)
      const { count, error: countError } = await supabaseAdmin
        .from('audit_logs')
        .select('id', { count: 'exact', head: true })
        .lt('created_at', cutoffIso)

      if (countError) {
        throw new Error(`Pre-count failed: ${countError.message}`)
      }

      const recordsToDelete = count ?? 0

      if (recordsToDelete === 0) {
        return {
          affectedRecords: 0,
          resourceUsage: { db_queries: 1, records_deleted: 0 },
        }
      }

      // Delete in batches to avoid oversized transactions
      // Supabase REST API doesn't support LIMIT on DELETE, so we delete all matching
      const { error: deleteError } = await supabaseAdmin
        .from('audit_logs')
        .delete()
        .lt('created_at', cutoffIso)

      if (deleteError) {
        throw new Error(`Audit cleanup delete failed: ${deleteError.message}`)
      }

      return {
        affectedRecords: recordsToDelete,
        resourceUsage: {
          db_queries: 2, // 1 count + 1 delete
          records_deleted: recordsToDelete,
          cutoff_date: cutoffIso,
          retention_days: RETENTION_DAYS,
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
