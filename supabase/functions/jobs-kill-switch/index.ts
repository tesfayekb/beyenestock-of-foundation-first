/**
 * jobs-kill-switch — Global or class-level emergency job halt.
 *
 * POST /jobs-kill-switch
 * Body: { activate: boolean, scope?: 'global' | 'class', class?: string, reason: string }
 *
 * When activated globally, sets __kill_switch__.enabled = false.
 * When activated per-class, sets __class_pause:{class}__.enabled = false.
 * system_critical jobs can ONLY be stopped via the global kill switch.
 *
 * Requires: jobs.emergency permission + requireRecentAuth()
 * Audit: job.kill_switch_activated / job.kill_switch_deactivated
 *
 * Owner: jobs-and-scheduler module
 */
import { createHandler, apiSuccess } from '../_shared/handler.ts'
import { authenticateRequest } from '../_shared/authenticate-request.ts'
import { checkPermissionOrThrow } from '../_shared/authorization.ts'
import { requireRecentAuth } from '../_shared/authorization.ts'
import { validateRequest, z } from '../_shared/validate-request.ts'
import { supabaseAdmin } from '../_shared/supabase-admin.ts'
import { logAuditEvent } from '../_shared/audit.ts'

const BodySchema = z.object({
  activate: z.boolean(),
  scope: z.enum(['global', 'class']).default('global'),
  class: z.string().optional(),
  reason: z.string().min(1).max(500),
})

Deno.serve(createHandler(async (req: Request): Promise<Response> => {
  const ctx = await authenticateRequest(req)
  await checkPermissionOrThrow(ctx.user.id, 'jobs.emergency')
  requireRecentAuth(ctx.user.lastSignInAt, undefined, ctx.user.id)

  const body = validateRequest(BodySchema, await req.json())

  if (body.scope === 'class' && !body.class) {
    return apiSuccess({ error: 'class field required when scope is class' }, 400)
  }

  const validClasses = ['system_critical', 'operational', 'maintenance', 'analytics', 'user_triggered']
  if (body.scope === 'class' && !validClasses.includes(body.class!)) {
    return apiSuccess({ error: `Invalid class. Must be one of: ${validClasses.join(', ')}` }, 400)
  }

  let targetId: string
  if (body.scope === 'global') {
    targetId = '__kill_switch__'
  } else {
    targetId = `__class_pause:${body.class}__`
  }

  // activate = true → enabled = false (jobs stop)
  // activate = false → enabled = true (jobs resume)
  const newEnabled = !body.activate

  const { error: updateError } = await supabaseAdmin
    .from('job_registry')
    .update({ enabled: newEnabled, updated_at: new Date().toISOString() })
    .eq('id', targetId)

  if (updateError) {
    throw new Error(`Failed to update kill switch: ${updateError.message}`)
  }

  const action = body.activate ? 'job.kill_switch_activated' : 'job.kill_switch_deactivated'
  await logAuditEvent({
    actorId: ctx.user.id,
    action,
    targetType: 'job',
    targetId,
    metadata: {
      scope: body.scope,
      class: body.class ?? null,
      reason: body.reason,
      new_enabled: newEnabled,
    },
    ipAddress: ctx.ipAddress,
    userAgent: ctx.userAgent,
    correlationId: ctx.correlationId,
  })

  return apiSuccess({
    target: targetId,
    activated: body.activate,
    scope: body.scope,
    class: body.class ?? null,
    reason: body.reason,
  })
}, { rateLimit: 'sensitive' }))
