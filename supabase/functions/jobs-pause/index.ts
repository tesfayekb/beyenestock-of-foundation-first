/**
 * jobs-pause — Pause individual jobs or all jobs of a class.
 *
 * POST /jobs-pause
 * Body: { job_id?: string, class?: string, reason: string }
 *
 * system_critical jobs cannot be paused individually — use kill switch.
 * Requires: jobs.pause permission
 * Audit: job.paused
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
  job_id: z.string().optional(),
  class: z.string().optional(),
  reason: z.string().min(1).max(500),
}).refine(d => d.job_id || d.class, { message: 'Either job_id or class is required' })

Deno.serve(createHandler(async (req: Request): Promise<Response> => {
  const ctx = await authenticateRequest(req)
  await checkPermissionOrThrow(ctx.user.id, 'jobs.pause')
  requireRecentAuth(ctx.user.lastSignInAt, 30 * 60 * 1000, ctx.user.id)

  const body = validateRequest(BodySchema, await req.json())
  const paused: string[] = []

  if (body.job_id) {
    // Per-job pause — block system_critical
    const { data: job } = await supabaseAdmin
      .from('job_registry')
      .select('id, class, status')
      .eq('id', body.job_id)
      .not('id', 'like', '__%__') // exclude reserved rows
      .single()

    if (!job) {
      return apiSuccess({ error: 'Job not found' }, 404)
    }
    if (job.class === 'system_critical') {
      return apiSuccess({ error: 'system_critical jobs can only be stopped via the global kill switch' }, 403)
    }

    await supabaseAdmin
      .from('job_registry')
      .update({ status: 'paused', enabled: false, updated_at: new Date().toISOString() })
      .eq('id', body.job_id)

    paused.push(body.job_id)
  } else if (body.class) {
    // Class-level pause — update all non-reserved jobs of that class
    if (body.class === 'system_critical') {
      return apiSuccess({ error: 'system_critical jobs can only be stopped via the global kill switch' }, 403)
    }

    const { data: jobs } = await supabaseAdmin
      .from('job_registry')
      .select('id')
      .eq('class', body.class)
      .not('id', 'like', '__%__')

    if (jobs && jobs.length > 0) {
      const ids = jobs.map(j => j.id)
      await supabaseAdmin
        .from('job_registry')
        .update({ status: 'paused', enabled: false, updated_at: new Date().toISOString() })
        .in('id', ids)
      paused.push(...ids)
    }
  }

  await logAuditEvent({
    actorId: ctx.user.id,
    action: 'job.paused',
    targetType: 'job',
    metadata: {
      job_id: body.job_id ?? null,
      class: body.class ?? null,
      reason: body.reason,
      paused_jobs: paused,
    },
    ipAddress: ctx.ipAddress,
    userAgent: ctx.userAgent,
    correlationId: ctx.correlationId,
  })

  return apiSuccess({ paused, reason: body.reason })
}, { rateLimit: 'strict' }))
