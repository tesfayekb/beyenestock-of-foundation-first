/**
 * assign-role — Assign a role to a user.
 *
 * Requires: roles.assign permission.
 * Guards:
 *   - Superadmin role can only be assigned by another superadmin (5min reauth).
 *   - User role cannot be manually assigned (auto-assigned on signup).
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

  // Validate target user and role in parallel
  const [userResult, roleResult] = await Promise.all([
    supabaseAdmin.auth.admin.getUserById(target_user_id),
    supabaseAdmin.from('roles').select('id, key').eq('id', role_id).single(),
  ])

  if (!userResult.data?.user) {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(404, 'Target user not found', { correlationId: ctx.correlationId })
  }

  const role = roleResult.data
  if (roleResult.error || !role) {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(404, 'Role not found', { correlationId: ctx.correlationId })
  }

  // Block manual assignment of the base user role — it is auto-assigned on signup
  if (role.key === 'user') {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(409, 'User role is automatically assigned on signup and cannot be manually assigned', {
      correlationId: ctx.correlationId,
      code: 'USER_ROLE_AUTO_ASSIGNED',
    })
  }

  // Privilege hierarchy enforcement (mirrors revoke-role)
  // Weight: superadmin=3, admin=2, everything else=1
  const ROLE_WEIGHTS: Record<string, number> = { superadmin: 3, admin: 2 }
  const targetWeight = ROLE_WEIGHTS[role.key] ?? 1

  if (targetWeight >= 2) {
    // Only superadmin can assign admin or superadmin roles
    const { data: actorIsSuperadmin } = await supabaseAdmin.rpc('is_superadmin', {
      _user_id: ctx.user.id,
    })
    if (!actorIsSuperadmin) {
      const { apiError } = await import('../_shared/api-error.ts')
      return apiError(403, `Only superadmin can assign the ${role.key} role`, {
        correlationId: ctx.correlationId,
      })
    }
  }

  // Tighter reauth window for superadmin assignment: 5 minutes
  if (role.key === 'superadmin') {
    requireRecentAuth(ctx.user.lastSignInAt, 5 * 60 * 1000, ctx.user.id)
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
      assigned_by_is_superadmin: role.key === 'superadmin' ? true : undefined,
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
}, { rateLimit: 'strict' }))
