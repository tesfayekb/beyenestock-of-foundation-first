/**
 * assign-permission-to-role — Assign a permission to a role.
 *
 * Requires: permissions.assign permission.
 * Guards:
 *   - Blocked on permission-locked roles (e.g. user role).
 *   - Blocked on superadmin (inherits all permissions automatically).
 *   - Admin role modifications require superadmin + 5min reauth.
 * Audit: HIGH-RISK (fail-closed with rollback).
 *
 * Dependency enforcement: when assigning a permission that has
 * dependencies (defined in PERMISSION_DEPS), any missing deps
 * are auto-inserted in the same operation.
 *
 * POST /assign-permission-to-role
 * Body: { role_id: string (UUID), permission_id: string (UUID) }
 */
import { createHandler, apiSuccess } from '../_shared/handler.ts'
import { authenticateRequest } from '../_shared/authenticate-request.ts'
import { checkPermissionOrThrow, requireRecentAuth } from '../_shared/authorization.ts'
import { logAuditEvent } from '../_shared/audit.ts'
import { supabaseAdmin } from '../_shared/supabase-admin.ts'
import { PERMISSION_DEPS } from '../_shared/permission-deps.ts'
import { z } from 'https://deno.land/x/zod@v3.22.4/mod.ts'
import { validateRequest } from '../_shared/validate-request.ts'

const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

/**
 * Permissions that are permanently restricted to superadmin only.
 * These can never be assigned to any other role — they govern role/permission
 * management itself and must remain under superadmin-exclusive control.
 */
const SUPERADMIN_ONLY_PERMISSIONS = new Set([
  'permissions.assign',
  'permissions.revoke',
  'roles.create',
  'roles.edit',
  'roles.delete',
  'jobs.emergency',
])

const BodySchema = z.object({
  role_id: z.string().trim().regex(uuidRegex, 'Invalid UUID'),
  permission_id: z.string().trim().regex(uuidRegex, 'Invalid UUID'),
})

function resolveAllDeps(key: string): string[] {
  const visited = new Set<string>()
  const queue = [...(PERMISSION_DEPS[key] ?? [])]
  for (let i = 0; i < queue.length; i++) {
    const dep = queue[i]
    if (visited.has(dep)) continue
    visited.add(dep)
    for (const t of (PERMISSION_DEPS[dep] ?? [])) {
      if (!visited.has(t)) queue.push(t)
    }
  }
  return Array.from(visited)
}

Deno.serve(createHandler(async (req: Request) => {
  if (req.method !== 'POST') {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(405, 'Method not allowed', { correlationId: crypto.randomUUID() })
  }

  const ctx = await authenticateRequest(req)
  await checkPermissionOrThrow(ctx.user.id, 'permissions.assign')
  requireRecentAuth(ctx.user.lastSignInAt, 30 * 60 * 1000, ctx.user.id)

  const body = await req.json()
  const { role_id, permission_id } = validateRequest(BodySchema, body)

  // Validate role and permission in parallel (independent lookups)
  const [roleResult, permResult] = await Promise.all([
    supabaseAdmin.from('roles').select('id, key, is_immutable, is_permission_locked').eq('id', role_id).single(),
    supabaseAdmin.from('permissions').select('id, key').eq('id', permission_id).single(),
  ])

  const role = roleResult.data
  const permission = permResult.data

  if (!role) {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(404, 'Role not found', { correlationId: ctx.correlationId })
  }

  // Block permission-locked roles (e.g. user role)
  if (role.is_permission_locked) {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(409, `Cannot modify permissions of permission-locked role: ${role.key}`, {
      correlationId: ctx.correlationId,
    })
  }

  // Block superadmin — inherits all permissions automatically
  if (role.key === 'superadmin') {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(409, 'Superadmin inherits all permissions automatically — individual assignments are not allowed', {
      correlationId: ctx.correlationId,
    })
  }

  // Admin role: only superadmin can modify its permissions, with tighter reauth
  if (role.key === 'admin') {
    const { data: actorIsSuperadmin } = await supabaseAdmin.rpc('is_superadmin', {
      _user_id: ctx.user.id,
    })
    if (!actorIsSuperadmin) {
      const { apiError } = await import('../_shared/api-error.ts')
      return apiError(403, 'Only a superadmin can modify admin role permissions', {
        correlationId: ctx.correlationId,
      })
    }
    requireRecentAuth(ctx.user.lastSignInAt, 5 * 60 * 1000, ctx.user.id)
  }

  if (!permission) {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(404, 'Permission not found', { correlationId: ctx.correlationId })
  }

  // Block superadmin-only permissions from being assigned to any non-superadmin role
  if (role.key !== 'superadmin' && SUPERADMIN_ONLY_PERMISSIONS.has(permission.key)) {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(403, `Permission "${permission.key}" is restricted to superadmin only and cannot be assigned to other roles`, {
      correlationId: ctx.correlationId,
      code: 'SUPERADMIN_ONLY_PERMISSION',
    })
  }

  // --- Dependency resolution ---
  const depKeys = resolveAllDeps(permission.key)
  let autoAddedKeys: string[] = []

  if (depKeys.length > 0) {
    // Fetch dependency permissions AND all existing role mappings in parallel
    const [depPermsResult, existingResult] = await Promise.all([
      supabaseAdmin.from('permissions').select('id, key').in('key', depKeys),
      supabaseAdmin.from('role_permissions').select('permission_id').eq('role_id', role_id),
    ])

    const depPerms = depPermsResult.data
    const existingIds = new Set((existingResult.data ?? []).map(m => m.permission_id))

    if (depPerms && depPerms.length > 0) {
      const missing = depPerms.filter(p => !existingIds.has(p.id))

      if (missing.length > 0) {
        // Batch insert all missing dependencies at once
        const rows = missing.map(p => ({ role_id, permission_id: p.id }))
        const { error: depInsertErr } = await supabaseAdmin
          .from('role_permissions')
          .insert(rows)

        if (depInsertErr) {
          if (depInsertErr.code !== '23505') throw depInsertErr
        }
        autoAddedKeys = missing.map(p => p.key)
      }
    }
  }

  // Assign the requested permission
  const { error: insertError } = await supabaseAdmin
    .from('role_permissions')
    .insert({ role_id, permission_id })

  if (insertError) {
    if (insertError.code === '23505') {
      const { apiError } = await import('../_shared/api-error.ts')
      return apiError(409, 'Permission already assigned to role', {
        correlationId: ctx.correlationId,
      })
    }
    throw insertError
  }

  // Audit — HIGH-RISK (fail-closed with rollback)
  const auditResult = await logAuditEvent({
    actorId: ctx.user.id,
    action: 'rbac.permission_assigned',
    targetType: 'role_permissions',
    targetId: role_id,
    metadata: {
      role_id,
      role_key: role.key,
      permission_id,
      permission_key: permission.key,
      auto_added_dependencies: autoAddedKeys,
    },
    ipAddress: ctx.ipAddress,
    userAgent: ctx.userAgent,
    correlationId: ctx.correlationId,
  })

  if (!auditResult.success) {
    // Rollback: remove the permission assignment + auto-added deps
    const rollbackIds = [permission_id]
    if (autoAddedKeys.length > 0) {
      const { data: depPermsToRemove } = await supabaseAdmin
        .from('permissions')
        .select('id')
        .in('key', autoAddedKeys)
      if (depPermsToRemove) {
        rollbackIds.push(...depPermsToRemove.map(dp => dp.id))
      }
    }

    await supabaseAdmin
      .from('role_permissions')
      .delete()
      .eq('role_id', role_id)
      .in('permission_id', rollbackIds)

    const { apiError } = await import('../_shared/api-error.ts')
    console.error('[ASSIGN-PERM] Audit write failed — rolling back', auditResult)
    return apiError(500, 'Audit logging failed — operation rolled back', {
      code: 'AUDIT_WRITE_FAILED',
      correlationId: ctx.correlationId,
    })
  }

  return apiSuccess({
    success: true,
    correlation_id: ctx.correlationId,
    message: `Permission ${permission.key} assigned to role ${role.key}`,
    auto_added_dependencies: autoAddedKeys,
  })
}, { rateLimit: 'strict' }))
