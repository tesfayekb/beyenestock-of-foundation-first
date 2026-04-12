/**
 * POST /health-alert-config — Create or update an alert configuration.
 *
 * Requires Bearer JWT + monitoring.configure permission.
 * Creates a new alert config or updates an existing one (by id).
 * Fail-closed audit: config change is rolled back if audit write fails.
 *
 * Update path: Pre-fetches old values before update. On audit failure,
 * restores original values (true rollback — DW-028 resolved).
 *
 * Owner: health-monitoring module
 * Classification: privileged
 * Rate limit: strict (mutation)
 */
import { createHandler, apiSuccess } from '../_shared/handler.ts'
import { apiError } from '../_shared/api-error.ts'
import { authenticateRequest } from '../_shared/authenticate-request.ts'
import { checkPermissionOrThrow, requireRecentAuth } from '../_shared/authorization.ts'
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
  requireRecentAuth(ctx.user.lastSignInAt, 30 * 60 * 1000, ctx.user.id)

  const body = await req.json()

  // ── Update path ──
  if (body.id) {
    const validated = validateRequest(UpdateSchema, body)
    const { id, ...updates } = validated

    // Pre-fetch old values for rollback (DW-028: true fail-closed)
    const { data: oldConfig, error: fetchError } = await supabaseAdmin
      .from('alert_configs')
      .select('*')
      .eq('id', id)
      .single()

    if (fetchError || !oldConfig) {
      return apiError(404, 'Alert config not found', { correlationId: ctx.correlationId })
    }

    // Apply update
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

    // Fail-closed audit with true rollback
    const auditResult = await logAuditEvent({
      actorId: ctx.user.id,
      action: 'health.alert_config_updated',
      targetType: 'alert_config',
      targetId: id,
      metadata: {
        updates,
        previous_values: Object.fromEntries(
          Object.keys(updates).map((k) => [k, (oldConfig as Record<string, unknown>)[k]])
        ),
      },
      ipAddress: ctx.ipAddress,
      userAgent: ctx.userAgent,
      correlationId: ctx.correlationId,
    })

    if (!auditResult.success) {
      // Rollback: restore original values
      const rollbackFields: Record<string, unknown> = {}
      for (const key of Object.keys(updates)) {
        rollbackFields[key] = (oldConfig as Record<string, unknown>)[key]
      }

      const { error: rollbackError } = await supabaseAdmin
        .from('alert_configs')
        .update(rollbackFields)
        .eq('id', id)

      if (rollbackError) {
        console.error('[ALERT-CONFIG] Rollback also failed — data may be inconsistent', {
          configId: id,
          correlationId: ctx.correlationId,
          rollbackError: rollbackError.message,
        })
      }

      console.error('[ALERT-CONFIG] Audit write failed; update rolled back', {
        configId: id,
        correlationId: ctx.correlationId,
      })
      return apiError(500, 'Alert config update aborted: audit trail write failed', {
        code: 'AUDIT_WRITE_FAILED',
        correlationId: ctx.correlationId,
      })
    }

    return apiSuccess(data)
  }

  // ── Create path ──
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
    await supabaseAdmin.from('alert_configs').delete().eq('id', data.id)
    console.error('[ALERT-CONFIG] Audit write failed, rolled back creation', {
      configId: data.id,
      correlationId: ctx.correlationId,
    })
    return apiError(500, 'Alert config creation aborted: audit trail write failed', {
      code: 'AUDIT_WRITE_FAILED',
      correlationId: ctx.correlationId,
    })
  }

  return apiSuccess(data, 201)
}, { rateLimit: 'strict' }))
