/**
 * delete-role — Delete a custom (non-immutable) role.
 *
 * Requires: roles.delete permission + recent auth.
 * Audit: rbac.role_deleted (fail-closed with rollback).
 *
 * DB cascade: role_permissions and user_roles rows are deleted automatically
 * via ON DELETE CASCADE foreign keys.
 * DB trigger: prevent_immutable_role_delete blocks deletion of immutable roles.
 *
 * POST /delete-role
 * Body: { role_id: string (UUID), reason: string }
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
  reason: z.string().trim().min(1, 'Reason is required').max(500),
})

Deno.serve(createHandler(async (req: Request) => {
  if (req.method !== 'POST') {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(405, 'Method not allowed', { correlationId: crypto.randomUUID() })
  }

  const ctx = await authenticateRequest(req)
  await checkPermissionOrThrow(ctx.user.id, 'roles.delete')
  requireRecentAuth(ctx.user.lastSignInAt, 30 * 60 * 1000, ctx.user.id)

  const body = await req.json()
  const { role_id, reason } = validateRequest(BodySchema, body)

  // Fetch role to validate existence and guard immutable/base roles (defense-in-depth)
  const { data: role, error: fetchErr } = await supabaseAdmin
    .from('roles')
    .select('id, key, name, is_base, is_immutable, description')
    .eq('id', role_id)
    .single()

  if (fetchErr || !role) {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(404, 'Role not found', { correlationId: ctx.correlationId })
  }

  if (role.is_immutable) {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(409, `Cannot delete immutable role: ${role.key}`, {
      correlationId: ctx.correlationId,
    })
  }

  if (role.is_base) {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(409, `Cannot delete base role: ${role.key}`, {
      correlationId: ctx.correlationId,
    })
  }

  // Capture cascade metadata before deletion
  const { count: userCount } = await supabaseAdmin
    .from('user_roles')
    .select('id', { count: 'exact', head: true })
    .eq('role_id', role_id)

  const { count: permCount } = await supabaseAdmin
    .from('role_permissions')
    .select('id', { count: 'exact', head: true })
    .eq('role_id', role_id)

  // Delete the role (cascades user_roles + role_permissions)
  const { error: deleteErr } = await supabaseAdmin
    .from('roles')
    .delete()
    .eq('id', role_id)

  if (deleteErr) {
    // DB trigger may also block this
    if (deleteErr.message?.includes('immutable')) {
      const { apiError } = await import('../_shared/api-error.ts')
      return apiError(409, `Cannot delete immutable role: ${role.key}`, {
        correlationId: ctx.correlationId,
      })
    }
    throw deleteErr
  }

  // Audit — fail-closed with rollback
  const auditResult = await logAuditEvent({
    actorId: ctx.user.id,
    action: 'rbac.role_deleted',
    targetType: 'roles',
    targetId: role_id,
    metadata: {
      role_key: role.key,
      role_name: role.name,
      reason,
      cascaded_user_assignments: userCount ?? 0,
      cascaded_permission_mappings: permCount ?? 0,
    },
    ipAddress: ctx.ipAddress,
    userAgent: ctx.userAgent,
    correlationId: ctx.correlationId,
  })

  if (!auditResult.success) {
    // Rollback: re-insert the role (note: cascaded rows are lost — this is documented)
    await supabaseAdmin
      .from('roles')
      .insert({
        id: role.id,
        key: role.key,
        name: role.name,
        description: role.description || null,
        is_base: false,
        is_immutable: false,
      })

    const { apiError } = await import('../_shared/api-error.ts')
    console.error('[DELETE-ROLE] Audit write failed — rolling back', auditResult)
    return apiError(500, 'Audit logging failed — operation rolled back', {
      code: 'AUDIT_WRITE_FAILED',
      correlationId: ctx.correlationId,
    })
  }

  return apiSuccess({
    success: true,
    correlation_id: ctx.correlationId,
    message: `Role "${role.name}" deleted successfully`,
  })
}))
