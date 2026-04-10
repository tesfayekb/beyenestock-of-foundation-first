/**
 * revoke-role — Revoke a role from a user.
 *
 * Requires: roles.revoke permission.
 * Audit: HIGH-RISK (fail-closed with rollback).
 *
 * POST /revoke-role
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
  await checkPermissionOrThrow(ctx.user.id, 'roles.revoke')
  requireRecentAuth(ctx.user.lastSignInAt, undefined, ctx.user.id)

  const body = await req.json()
  const { target_user_id, role_id } = validateRequest(BodySchema, body)

  // Get role info
  const { data: role, error: roleError } = await supabaseAdmin
    .from('roles').select('id, key').eq('id', role_id).single()
  if (roleError || !role) {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(404, 'Role not found', { correlationId: ctx.correlationId })
  }

  // Self-superadmin-revocation guard
  if (role.key === 'superadmin' && target_user_id === ctx.user.id) {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(409, 'Cannot revoke your own superadmin role', {
      correlationId: ctx.correlationId,
    })
  }

  // Last-superadmin guard (DB trigger also enforces this)
  if (role.key === 'superadmin') {
    const { count } = await supabaseAdmin
      .from('user_roles')
      .select('id', { count: 'exact', head: true })
      .eq('role_id', role_id)
    if ((count ?? 0) <= 1) {
      const { apiError } = await import('../_shared/api-error.ts')
      return apiError(409, 'Cannot revoke the last superadmin assignment', {
        correlationId: ctx.correlationId,
      })
    }
  }

  // Check assignment exists
  const { data: assignment } = await supabaseAdmin
    .from('user_roles')
    .select('id')
    .eq('user_id', target_user_id)
    .eq('role_id', role_id)
    .single()

  if (!assignment) {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(404, 'Role assignment not found', { correlationId: ctx.correlationId })
  }

  // Delete assignment
  const { error: deleteError } = await supabaseAdmin
    .from('user_roles')
    .delete()
    .eq('user_id', target_user_id)
    .eq('role_id', role_id)

  if (deleteError) throw deleteError

  // Audit — HIGH-RISK (fail-closed with rollback)
  const auditResult = await logAuditEvent({
    actorId: ctx.user.id,
    action: 'rbac.role_revoked',
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
    // Rollback: re-assign the role
    await supabaseAdmin
      .from('user_roles')
      .insert({ user_id: target_user_id, role_id, assigned_by: ctx.user.id })

    const { apiError } = await import('../_shared/api-error.ts')
    console.error('[REVOKE-ROLE] Audit write failed — rolling back', auditResult)
    return apiError(500, 'Audit logging failed — operation rolled back', {
      code: 'AUDIT_WRITE_FAILED',
      correlationId: ctx.correlationId,
    })
  }

  return apiSuccess({
    success: true,
    correlation_id: ctx.correlationId,
    message: `Role ${role.key} revoked from user`,
  })
}))
