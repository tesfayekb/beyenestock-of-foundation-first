/**
 * update-system-config — Update onboarding mode configuration.
 *
 * Owner: user-onboarding module
 * Classification: security-critical
 * Lifecycle: active
 *
 * PATCH /update-system-config
 * Body: { signup_enabled?: boolean, invite_enabled?: boolean, followup_days?: number, max_followups?: number }
 *
 * Authorization: admin.config (SUPERADMIN_ONLY) + recent auth required.
 * Validation: At least one mode must remain true (cannot disable both).
 * Audit: system.config_changed with { before, after } payload.
 */
import { createHandler, apiSuccess } from '../_shared/handler.ts'
import { authenticateRequest } from '../_shared/authenticate-request.ts'
import { checkPermissionOrThrow, requireRecentAuth } from '../_shared/authorization.ts'
import { logAuditEvent } from '../_shared/audit.ts'
import { supabaseAdmin } from '../_shared/supabase-admin.ts'
import { z } from 'https://deno.land/x/zod@v3.22.4/mod.ts'
import { validateRequest } from '../_shared/validate-request.ts'

const BodySchema = z.object({
  signup_enabled: z.boolean().optional(),
  invite_enabled: z.boolean().optional(),
  followup_days: z.number().int().min(1).max(30).optional(),
  max_followups: z.number().int().min(0).max(10).optional(),
}).refine(
  (d) => d.signup_enabled !== undefined || d.invite_enabled !== undefined ||
         d.followup_days !== undefined || d.max_followups !== undefined,
  { message: 'At least one field to update is required' }
)

Deno.serve(createHandler(async (req: Request) => {
  if (req.method !== 'PATCH') {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(405, 'Method not allowed', { correlationId: crypto.randomUUID() })
  }

  // Auth + permission + reauth
  const ctx = await authenticateRequest(req)
  await checkPermissionOrThrow(ctx.user.id, 'admin.config')
  requireRecentAuth(ctx.user.lastSignInAt, 5 * 60 * 1000, ctx.user.id)

  // Validate input
  const body = await req.json()
  const input = validateRequest(BodySchema, body)

  // Read current config
  const { data: currentRow, error: readError } = await supabaseAdmin
    .from('system_config')
    .select('value')
    .eq('key', 'onboarding_mode')
    .single()

  if (readError || !currentRow) {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(500, 'Failed to read current config', { correlationId: ctx.correlationId })
  }

  const before = currentRow.value as {
    signup_enabled: boolean
    invite_enabled: boolean
    followup_days?: number
    max_followups?: number
  }

  // Merge: only override provided fields
  const after = {
    signup_enabled: input.signup_enabled ?? before.signup_enabled,
    invite_enabled: input.invite_enabled ?? before.invite_enabled,
    followup_days: input.followup_days ?? (before.followup_days ?? 3),
    max_followups: input.max_followups ?? (before.max_followups ?? 2),
  }

  // Safety: at least one mode must be true
  if (!after.signup_enabled && !after.invite_enabled) {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(400, 'At least one onboarding mode (signup or invite) must be enabled. Disabling both would lock out all new users.', {
      code: 'VALIDATION_ERROR',
      correlationId: ctx.correlationId,
    })
  }

  // No-op check
  if (
    after.signup_enabled === before.signup_enabled &&
    after.invite_enabled === before.invite_enabled &&
    after.followup_days === (before.followup_days ?? 3) &&
    after.max_followups === (before.max_followups ?? 2)
  ) {
    return apiSuccess({ config: after, changed: false })
  }

  // Write updated config
  const { error: writeError } = await supabaseAdmin
    .from('system_config')
    .update({
      value: after,
      updated_by: ctx.user.id,
      updated_at: new Date().toISOString(),
    })
    .eq('key', 'onboarding_mode')

  if (writeError) {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(500, 'Failed to update config', { correlationId: ctx.correlationId })
  }

  // Audit
  const auditResult = await logAuditEvent({
    actorId: ctx.user.id,
    action: 'system.config_changed',
    targetType: 'system_config',
    targetId: 'onboarding_mode',
    metadata: {
      before,
      after,
      fields_changed: [
        ...(input.signup_enabled !== undefined ? ['signup_enabled'] : []),
        ...(input.invite_enabled !== undefined ? ['invite_enabled'] : []),
        ...(input.followup_days !== undefined ? ['followup_days'] : []),
        ...(input.max_followups !== undefined ? ['max_followups'] : []),
      ],
    },
    ipAddress: ctx.ipAddress,
    userAgent: ctx.userAgent,
    correlationId: ctx.correlationId,
  })

  if (!auditResult.success) {
    console.error('[UPDATE-SYSTEM-CONFIG] Audit write failed — config was updated but audit trail incomplete', auditResult)
  }

  return apiSuccess({ config: after, changed: true })
}))
