/**
 * update-role — Update a custom role's name and/or description.
 *
 * Requires: roles.edit permission + recent auth.
 * Audit: rbac.role_updated (fail-closed).
 *
 * The role key is immutable (enforced by DB trigger) — only name and description can change.
 *
 * POST /update-role
 * Body: { role_id: string (UUID), name?: string, description?: string }
 */
import { createHandler, apiSuccess } from '../_shared/handler.ts'
import { authenticateRequest } from '../_shared/authenticate-request.ts'
import { checkPermissionOrThrow, requireRecentAuth } from '../_shared/authorization.ts'
import { logAuditEvent } from '../_shared/audit.ts'
import { supabaseAdmin } from '../_shared/supabase-admin.ts'
import { z } from 'https://deno.land/x/zod@v3.22.4/mod.ts'
import { validateRequest } from '../_shared/validate-request.ts'

const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

const BodySchema = z.object({
  role_id: z.string().trim().regex(uuidRegex, 'Invalid UUID'),
  name: z.string().trim().min(1).max(100).optional(),
  description: z.string().trim().max(500).optional(),
}).refine(
  (d) => d.name !== undefined || d.description !== undefined,
  { message: 'At least one of name or description must be provided' },
)

Deno.serve(createHandler(async (req: Request) => {
  if (req.method !== 'POST') {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(405, 'Method not allowed', { correlationId: crypto.randomUUID() })
  }

  const ctx = await authenticateRequest(req)
  await checkPermissionOrThrow(ctx.user.id, 'roles.edit')
  requireRecentAuth(ctx.user.lastSignInAt, 30 * 60 * 1000, ctx.user.id)

  const body = await req.json()
  const { role_id, name, description } = validateRequest(BodySchema, body)

  // Fetch role
  const { data: role, error: fetchErr } = await supabaseAdmin
    .from('roles')
    .select('id, key, name, description, is_immutable')
    .eq('id', role_id)
    .single()

  if (fetchErr || !role) {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(404, 'Role not found', { correlationId: ctx.correlationId })
  }

  if (role.is_immutable) {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(409, `Cannot modify immutable role: ${role.key}`, {
      correlationId: ctx.correlationId,
    })
  }

  const updates: Record<string, string> = {}
  if (name !== undefined) updates.name = name
  if (description !== undefined) updates.description = description

  const oldValues: Record<string, string | null> = {}
  if (name !== undefined) oldValues.name = role.name
  if (description !== undefined) oldValues.description = role.description

  const { error: updateErr } = await supabaseAdmin
    .from('roles')
    .update(updates)
    .eq('id', role_id)

  if (updateErr) throw updateErr

  // Audit
  const auditResult = await logAuditEvent({
    actorId: ctx.user.id,
    action: 'rbac.role_updated',
    targetType: 'roles',
    targetId: role_id,
    metadata: {
      role_key: role.key,
      changes: updates,
      previous: oldValues,
    },
    ipAddress: ctx.ipAddress,
    userAgent: ctx.userAgent,
    correlationId: ctx.correlationId,
  })

  if (!auditResult.success) {
    // Rollback
    await supabaseAdmin
      .from('roles')
      .update(oldValues)
      .eq('id', role_id)

    const { apiError } = await import('../_shared/api-error.ts')
    console.error('[UPDATE-ROLE] Audit write failed — rolling back', auditResult)
    return apiError(500, 'Audit logging failed — operation rolled back', {
      code: 'AUDIT_WRITE_FAILED',
      correlationId: ctx.correlationId,
    })
  }

  return apiSuccess({
    success: true,
    correlation_id: ctx.correlationId,
    message: `Role "${role.key}" updated successfully`,
  })
}))
