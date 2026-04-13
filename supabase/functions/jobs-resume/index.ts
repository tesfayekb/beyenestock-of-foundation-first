/**
 * jobs-resume — Resume paused jobs (individual or class-level).
 *
 * POST /jobs-resume
 * Body: { job_id?: string, class?: string, reason: string }
 *
 * Does NOT resume poison jobs — those require manual investigation.
 * Requires: jobs.resume permission
 * Audit: job.resumed
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
  await checkPermissionOrThrow(ctx.user.id, 'jobs.resume')
  requireRecentAuth(ctx.user.lastSignInAt, 30 * 60 * 1000, ctx.user.id)

  const body = validateRequest(BodySchema, await req.json())
  const resumed: string[] = []

  if (body.job_id) {
    const { data: job } = await supabaseAdmin
      .from('job_registry')
      .select('id, status')
      .eq('id', body.job_id)
      .not('id', 'like', '__%__')
      .single()

    if (!job) {
      return apiSuccess({ error: 'Job not found' }, 404)
    }
    if (job.status === 'poison') {
      return apiSuccess({ error: 'Cannot resume poison job — requires manual investigation and reset' }, 409)
    }

    await supabaseAdmin
      .from('job_registry')
      .update({ status: 'registered', enabled: true, updated_at: new Date().toISOString() })
      .eq('id', body.job_id)

    resumed.push(body.job_id)
  } else if (body.class) {
    // Resume all paused (not poison) jobs of that class
    const { data: jobs } = await supabaseAdmin
      .from('job_registry')
      .select('id')
      .eq('class', body.class)
      .eq('status', 'paused')
      .not('id', 'like', '__%__')

    if (jobs && jobs.length > 0) {
      const ids = jobs.map(j => j.id)
      await supabaseAdmin
        .from('job_registry')
        .update({ status: 'registered', enabled: true, updated_at: new Date().toISOString() })
        .in('id', ids)
      resumed.push(...ids)
    }
  }

  await logAuditEvent({
    actorId: ctx.user.id,
    action: 'job.resumed',
    targetType: 'job',
    metadata: {
      job_id: body.job_id ?? null,
      class: body.class ?? null,
      reason: body.reason,
      resumed_jobs: resumed,
    },
    ipAddress: ctx.ipAddress,
    userAgent: ctx.userAgent,
    correlationId: ctx.correlationId,
  })

  return apiSuccess({ resumed, reason: body.reason })
}, { rateLimit: 'strict' }))
