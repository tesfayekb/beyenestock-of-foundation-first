/**
 * assign-role — Assign a role to a user.
 *
 * Requires: roles.assign permission.
 * Audit: HIGH-RISK (fail-closed with rollback).
 *
 * POST /assign-role
 * Body: { target_user_id: string (UUID), role_id: string (UUID) }
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
  target_user_id: z.string().trim().regex(uuidRegex, 'Invalid UUID'),
  role_id: z.string().trim().regex(uuidRegex, 'Invalid UUID'),
})

Deno.serve(createHandler(async (req: Request) => {
  if (req.method !== 'POST') {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(405, 'Method not allowed', { correlationId: crypto.randomUUID() })
  }

  const ctx = await authenticateRequest(req)
  await checkPermissionOrThrow(ctx.user.id, 'roles.assign')
  requireRecentAuth(ctx.user.lastSignInAt, 30 * 60 * 1000, ctx.user.id)

  const body = await req.json()
  const { target_user_id, role_id } = validateRequest(BodySchema, body)

  // Validate target user exists
  const { data: targetUser } = await supabaseAdmin.auth.admin.getUserById(target_user_id)
  if (!targetUser?.user) {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(404, 'Target user not found', { correlationId: ctx.correlationId })
  }

  // Validate role exists
  const { data: role, error: roleError } = await supabaseAdmin
    .from('roles').select('id, key').eq('id', role_id).single()
  if (roleError || !role) {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(404, 'Role not found', { correlationId: ctx.correlationId })
  }

  // Assign role
  const { error: insertError } = await supabaseAdmin
    .from('user_roles')
    .insert({ user_id: target_user_id, role_id, assigned_by: ctx.user.id })

  if (insertError) {
    if (insertError.code === '23505') {
      const { apiError } = await import('../_shared/api-error.ts')
      return apiError(409, 'Role already assigned', { correlationId: ctx.correlationId })
    }
    throw insertError
  }

  // Audit — HIGH-RISK (fail-closed with rollback)
  const auditResult = await logAuditEvent({
    actorId: ctx.user.id,
    action: 'rbac.role_assigned',
    targetType: 'user_roles',
    targetId: target_user_id,
    metadata: {
      role_id,
      role_key: role.key,
      target_user_id,
    },
    ipAddress: ctx.ipAddress,
    userAgent: ctx.userAgent,
    correlationId: ctx.correlationId,
  })

  if (!auditResult.success) {
    // Rollback: remove the role assignment
    await supabaseAdmin
      .from('user_roles')
      .delete()
      .eq('user_id', target_user_id)
      .eq('role_id', role_id)

    const { apiError } = await import('../_shared/api-error.ts')
    console.error('[ASSIGN-ROLE] Audit write failed — rolling back', auditResult)
    return apiError(500, 'Audit logging failed — operation rolled back', {
      code: 'AUDIT_WRITE_FAILED',
      correlationId: ctx.correlationId,
    })
  }

  return apiSuccess({
    success: true,
    correlation_id: ctx.correlationId,
    message: `Role ${role.key} assigned to user`,
  })
}))
