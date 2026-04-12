/**
 * revoke-permission-from-role — Revoke a permission from a role.
 *
 * Requires: permissions.revoke permission.
 * Audit: HIGH-RISK (fail-closed with rollback).
 *
 * Dependency enforcement: refuses revocation if another permission
 * currently assigned to the same role depends on the one being removed.
 *
 * POST /revoke-permission-from-role
 * Body: { role_id: string (UUID), permission_id: string (UUID) }
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
  permission_id: z.string().trim().regex(uuidRegex, 'Invalid UUID'),
})

/**
 * Permission dependency map — server-side copy.
 * Mirrors src/config/permission-deps.ts. Kept inline to avoid
 * import-path issues in the Deno edge function runtime.
 */
const PERMISSION_DEPS: Record<string, string[]> = {
  'roles.assign':        ['roles.view', 'users.view_all', 'admin.access'],
  'roles.revoke':        ['roles.view', 'users.view_all', 'admin.access'],
  'roles.create':        ['roles.view', 'admin.access'],
  'roles.delete':        ['roles.view', 'admin.access'],
  'roles.edit':          ['roles.view', 'admin.access'],
  'permissions.assign':  ['roles.view', 'permissions.view', 'admin.access'],
  'permissions.revoke':  ['roles.view', 'permissions.view', 'admin.access'],
  'permissions.view':    ['admin.access'],
  'users.edit_any':      ['users.view_all', 'admin.access'],
  'users.deactivate':    ['users.view_all', 'admin.access'],
  'users.reactivate':    ['users.view_all', 'admin.access'],
  'audit.export':        ['audit.view', 'admin.access'],
  'audit.view':          ['admin.access'],
  'monitoring.configure': ['monitoring.view', 'admin.access'],
  'monitoring.view':      ['admin.access'],
  'jobs.trigger':            ['jobs.view', 'admin.access'],
  'jobs.pause':              ['jobs.view', 'admin.access'],
  'jobs.resume':             ['jobs.view', 'admin.access'],
  'jobs.retry':              ['jobs.view', 'admin.access'],
  'jobs.deadletter.manage':  ['jobs.view', 'admin.access'],
  'jobs.emergency':          ['admin.access'],
  'jobs.view':               ['admin.access'],
  'admin.config':            ['admin.access'],
}

/**
 * Find all permission keys that directly depend on the given key.
 * Returns keys where `key` appears in their dependency list.
 */
function findDependents(targetKey: string): string[] {
  const dependents: string[] = []
  for (const [permKey, deps] of Object.entries(PERMISSION_DEPS)) {
    if (deps.includes(targetKey)) {
      dependents.push(permKey)
    }
  }
  return dependents
}

Deno.serve(createHandler(async (req: Request) => {
  if (req.method !== 'POST') {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(405, 'Method not allowed', { correlationId: crypto.randomUUID() })
  }

  const ctx = await authenticateRequest(req)
  await checkPermissionOrThrow(ctx.user.id, 'permissions.revoke')
  requireRecentAuth(ctx.user.lastSignInAt, 30 * 60 * 1000, ctx.user.id)

  const body = await req.json()
  const { role_id, permission_id } = validateRequest(BodySchema, body)

  // Validate role exists
  const { data: role } = await supabaseAdmin
    .from('roles').select('id, key, is_immutable').eq('id', role_id).single()
  if (!role) {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(404, 'Role not found', { correlationId: ctx.correlationId })
  }

  if (role.is_immutable) {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(409, `Cannot modify permissions of immutable role: ${role.key}`, {
      correlationId: ctx.correlationId,
    })
  }

  // Validate permission exists
  const { data: permission } = await supabaseAdmin
    .from('permissions').select('id, key').eq('id', permission_id).single()
  if (!permission) {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(404, 'Permission not found', { correlationId: ctx.correlationId })
  }

  // Validate mapping exists
  const { data: mapping } = await supabaseAdmin
    .from('role_permissions')
    .select('id')
    .eq('role_id', role_id)
    .eq('permission_id', permission_id)
    .single()

  if (!mapping) {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(404, 'Permission not assigned to this role', {
      correlationId: ctx.correlationId,
    })
  }

  // --- Dependency enforcement ---
  // Check if any other permission currently assigned to this role
  // lists the target permission as a dependency. If so, block revocation.
  const dependentKeys = findDependents(permission.key)

  if (dependentKeys.length > 0) {
    // Fetch which of these dependent permissions are currently assigned to this role
    const { data: depPerms } = await supabaseAdmin
      .from('permissions')
      .select('id, key')
      .in('key', dependentKeys)

    if (depPerms && depPerms.length > 0) {
      const { data: assignedDeps } = await supabaseAdmin
        .from('role_permissions')
        .select('permission_id')
        .eq('role_id', role_id)
        .in('permission_id', depPerms.map(p => p.id))

      if (assignedDeps && assignedDeps.length > 0) {
        const assignedDepIds = new Set(assignedDeps.map(a => a.permission_id))
        const blockers = depPerms
          .filter(p => assignedDepIds.has(p.id))
          .map(p => p.key)

        if (blockers.length > 0) {
          const { apiError } = await import('../_shared/api-error.ts')
          return apiError(409, `Cannot revoke ${permission.key}: required by ${blockers.join(', ')}`, {
            correlationId: ctx.correlationId,
            code: 'DEPENDENCY_VIOLATION',
            blocked_by: blockers,
          })
        }
      }
    }
  }

  // Delete mapping
  const { error: deleteError } = await supabaseAdmin
    .from('role_permissions')
    .delete()
    .eq('role_id', role_id)
    .eq('permission_id', permission_id)

  if (deleteError) throw deleteError

  // Audit — HIGH-RISK (fail-closed with rollback)
  const auditResult = await logAuditEvent({
    actorId: ctx.user.id,
    action: 'rbac.permission_revoked',
    targetType: 'role_permissions',
    targetId: role_id,
    metadata: {
      role_id,
      role_key: role.key,
      permission_id,
      permission_key: permission.key,
    },
    ipAddress: ctx.ipAddress,
    userAgent: ctx.userAgent,
    correlationId: ctx.correlationId,
  })

  if (!auditResult.success) {
    // Rollback: re-assign the permission
    await supabaseAdmin
      .from('role_permissions')
      .insert({ role_id, permission_id })

    const { apiError } = await import('../_shared/api-error.ts')
    console.error('[REVOKE-PERM] Audit write failed — rolling back', auditResult)
    return apiError(500, 'Audit logging failed — operation rolled back', {
      code: 'AUDIT_WRITE_FAILED',
      correlationId: ctx.correlationId,
    })
  }

  return apiSuccess({
    success: true,
    correlation_id: ctx.correlationId,
    message: `Permission ${permission.key} revoked from role ${role.key}`,
  })
}))
