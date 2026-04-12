/**
 * assign-permission-to-role — Assign a permission to a role.
 *
 * Requires: permissions.assign permission.
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
import { z } from 'https://deno.land/x/zod@v3.22.4/mod.ts'
import { validateRequest } from '../_shared/validate-request.ts'

const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

const BodySchema = z.object({
  role_id: z.string().trim().regex(uuidRegex, 'Invalid UUID'),
  permission_id: z.string().trim().regex(uuidRegex, 'Invalid UUID'),
})

/**
 * Permission dependency map — server-side copy.
 * Mirrors src/config/permission-deps.ts (canonical source).
 * ⚠️  SYNC: Must match src/config/permission-deps.ts and
 *    supabase/functions/revoke-permission-from-role/index.ts.
 *    See RW-008 in regression-watchlist.md for drift detection protocol.
 *    Last synced: 2026-04-12 — 23 entries.
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
    supabaseAdmin.from('roles').select('id, key, is_immutable').eq('id', role_id).single(),
    supabaseAdmin.from('permissions').select('id, key').eq('id', permission_id).single(),
  ])

  const role = roleResult.data
  const permission = permResult.data

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

  if (!permission) {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(404, 'Permission not found', { correlationId: ctx.correlationId })
  }

  // --- Dependency resolution ---
  const depKeys = resolveAllDeps(permission.key)
  let autoAddedKeys: string[] = []

  if (depKeys.length > 0) {
    // Fetch dependency permissions and existing mappings in parallel
    const { data: depPerms } = await supabaseAdmin
      .from('permissions')
      .select('id, key')
      .in('key', depKeys)

    if (depPerms && depPerms.length > 0) {
      const { data: existingMappings } = await supabaseAdmin
        .from('role_permissions')
        .select('permission_id')
        .eq('role_id', role_id)
        .in('permission_id', depPerms.map(p => p.id))

      const existingIds = new Set((existingMappings ?? []).map(m => m.permission_id))
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
