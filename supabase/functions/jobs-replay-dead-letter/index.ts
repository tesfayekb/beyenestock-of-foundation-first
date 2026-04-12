/**
 * jobs-replay-dead-letter — Re-queue a dead-lettered execution.
 *
 * POST /jobs-replay-dead-letter
 * Body: { execution_id: string, reason: string }
 *
 * Creates a new execution record linked to the original via parent_execution_id.
 * Does NOT re-execute inline — sets state to 'scheduled' for the next cron cycle.
 *
 * Requires: jobs.deadletter.manage + requireRecentAuth()
 * Audit: job.replayed
 *
 * Owner: jobs-and-scheduler module
 */
import { createHandler, apiSuccess } from '../_shared/handler.ts'
import { authenticateRequest } from '../_shared/authenticate-request.ts'
import { checkPermissionOrThrow, requireRecentAuth } from '../_shared/authorization.ts'
import { validateRequest, z } from '../_shared/validate-request.ts'
import { supabaseAdmin } from '../_shared/supabase-admin.ts'
import { logAuditEvent } from '../_shared/audit.ts'

const BodySchema = z.object({
  execution_id: z.string().uuid(),
  reason: z.string().min(1).max(500),
})

Deno.serve(createHandler(async (req: Request): Promise<Response> => {
  const ctx = await authenticateRequest(req)
  await checkPermissionOrThrow(ctx.user.id, 'jobs.deadletter.manage')
  requireRecentAuth(ctx.user.lastSignInAt, undefined, ctx.user.id)

  const body = validateRequest(BodySchema, await req.json())

  // Fetch the dead-lettered execution
  const { data: deadLetter, error: fetchError } = await supabaseAdmin
    .from('job_executions')
    .select('*')
    .eq('id', body.execution_id)
    .eq('state', 'dead_lettered')
    .single()

  if (fetchError || !deadLetter) {
    return apiSuccess({ error: 'Dead-lettered execution not found' }, 404)
  }

  // Check the job is still registered and not poison
  const { data: job } = await supabaseAdmin
    .from('job_registry')
    .select('id, version, status, enabled')
    .eq('id', deadLetter.job_id)
    .single()

  if (!job) {
    return apiSuccess({ error: 'Job no longer exists in registry' }, 404)
  }
  if (job.status === 'poison') {
    return apiSuccess({ error: 'Cannot replay — job is marked as poison' }, 409)
  }

  // Create new execution record linked to original
  const { data: newExec, error: insertError } = await supabaseAdmin
    .from('job_executions')
    .insert({
      job_id: deadLetter.job_id,
      state: 'scheduled',
      job_version: job.version,
      attempt: 1,
      scheduled_time: new Date().toISOString(),
      parent_execution_id: deadLetter.id,
      root_execution_id: deadLetter.root_execution_id ?? deadLetter.id,
      correlation_id: ctx.correlationId,
      metadata: { replayed_by: ctx.user.id, reason: body.reason },
    })
    .select('id, execution_id')
    .single()

  if (insertError || !newExec) {
    throw new Error(`Failed to create replay execution: ${insertError?.message}`)
  }

  await logAuditEvent({
    actorId: ctx.user.id,
    action: 'job.replayed',
    targetType: 'job',
    targetId: deadLetter.job_id,
    metadata: {
      original_execution_id: body.execution_id,
      new_execution_id: newExec.id,
      job_id: deadLetter.job_id,
      reason: body.reason,
    },
    ipAddress: ctx.ipAddress,
    userAgent: ctx.userAgent,
    correlationId: ctx.correlationId,
  })

  return apiSuccess({
    replayed: true,
    original_execution_id: body.execution_id,
    new_execution_id: newExec.id,
    job_id: deadLetter.job_id,
  })
}, { rateLimit: 'strict' }))
