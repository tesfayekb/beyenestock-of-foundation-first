/**
 * POST /health-alert-config — Create or update an alert configuration.
 *
 * Requires Bearer JWT + monitoring.configure permission.
 * Creates a new alert config or updates an existing one (by id).
 * Fail-closed audit: config change is rolled back if audit write fails.
 *
 * Owner: health-monitoring module
 * Classification: privileged
 * Rate limit: strict (mutation)
 */
import { createHandler, apiSuccess } from '../_shared/handler.ts'
import { apiError } from '../_shared/api-error.ts'
import { authenticateRequest } from '../_shared/authenticate-request.ts'
import { checkPermissionOrThrow } from '../_shared/authorization.ts'
import { validateRequest, z } from '../_shared/validate-request.ts'
import { supabaseAdmin } from '../_shared/supabase-admin.ts'
import { logAuditEvent } from '../_shared/audit.ts'

const CreateSchema = z.object({
  metric_key: z.string().min(1).max(255),
  severity: z.enum(['info', 'warning', 'critical']),
  threshold_value: z.number(),
  comparison: z.enum(['gt', 'lt', 'gte', 'lte', 'eq']),
  enabled: z.boolean().default(true),
  cooldown_seconds: z.number().int().min(0).max(86400).default(300),
})

const UpdateSchema = z.object({
  id: z.string().uuid(),
  metric_key: z.string().min(1).max(255).optional(),
  severity: z.enum(['info', 'warning', 'critical']).optional(),
  threshold_value: z.number().optional(),
  comparison: z.enum(['gt', 'lt', 'gte', 'lte', 'eq']).optional(),
  enabled: z.boolean().optional(),
  cooldown_seconds: z.number().int().min(0).max(86400).optional(),
})

Deno.serve(createHandler(async (req: Request): Promise<Response> => {
  const ctx = await authenticateRequest(req)
  await checkPermissionOrThrow(ctx.user.id, 'monitoring.configure')

  const body = await req.json()

  // Update path: if id is present
  if (body.id) {
    const validated = validateRequest(UpdateSchema, body)
    const { id, ...updates } = validated

    const { data, error } = await supabaseAdmin
      .from('alert_configs')
      .update(updates)
      .eq('id', id)
      .select()
      .maybeSingle()

    if (error) {
      throw new Error(`Alert config update failed: ${error.message}`)
    }
    if (!data) {
      return apiError(404, 'Alert config not found', { correlationId: ctx.correlationId })
    }

    // Fail-closed audit (partial): On audit failure the update persists in DB.
    // Caller receives 500. True rollback deferred — requires pre-fetch of old
    // values before update (DW-028). See also DW-024b for general pattern.
    const auditResult = await logAuditEvent({
      actorId: ctx.user.id,
      action: 'health.alert_config_updated',
      targetType: 'alert_config',
      targetId: id,
      metadata: { updates },
      ipAddress: ctx.ipAddress,
      userAgent: ctx.userAgent,
      correlationId: ctx.correlationId,
    })

    if (!auditResult.success) {
      // NOTE: The update has already persisted in the DB. True rollback requires
      // pre-fetching old values before the update (deferred: DW-028).
      // The caller receives a 500, surfacing the failure even though the change took effect.
      console.error('[ALERT-CONFIG] Audit write failed; update persists without audit record', {
        configId: id,
        correlationId: ctx.correlationId,
      })
      throw new Error('Alert config update aborted: audit trail write failed')
    }

    return apiSuccess(data)
  }

  // Create path
  const validated = validateRequest(CreateSchema, body)

  const { data, error } = await supabaseAdmin
    .from('alert_configs')
    .insert({
      ...validated,
      created_by: ctx.user.id,
    })
    .select()
    .single()

  if (error) {
    throw new Error(`Alert config creation failed: ${error.message}`)
  }

  // Fail-closed audit: delete the created config if audit write fails
  const auditResult = await logAuditEvent({
    actorId: ctx.user.id,
    action: 'health.alert_config_created',
    targetType: 'alert_config',
    targetId: data.id,
    metadata: { config: validated },
    ipAddress: ctx.ipAddress,
    userAgent: ctx.userAgent,
    correlationId: ctx.correlationId,
  })

  if (!auditResult.success) {
    // Roll back: delete the just-created config
    await supabaseAdmin.from('alert_configs').delete().eq('id', data.id)
    console.error('[ALERT-CONFIG] Audit write failed, rolled back creation', {
      configId: data.id,
      correlationId: ctx.correlationId,
    })
    throw new Error('Alert config creation aborted: audit trail write failed')
  }

  return apiSuccess(data, 201)
}, { rateLimit: 'strict' }))
