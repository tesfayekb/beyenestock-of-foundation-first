/**
 * list-permissions — Return all permissions with their assigned role names.
 *
 * Requires: permissions.view permission.
 *
 * GET /list-permissions
 * Response: { data: PermissionListItem[] }
 *
 * Performance: Parallelizes independent DB queries with Promise.all.
 */
import { createHandler, apiSuccess } from '../_shared/handler.ts'
import { authenticateRequest } from '../_shared/authenticate-request.ts'
import { checkPermissionOrThrow } from '../_shared/authorization.ts'
import { supabaseAdmin } from '../_shared/supabase-admin.ts'

Deno.serve(createHandler(async (req: Request) => {
  if (req.method !== 'GET') {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(405, 'Method not allowed', { correlationId: crypto.randomUUID() })
  }

  const ctx = await authenticateRequest(req)
  await checkPermissionOrThrow(ctx.user.id, 'permissions.view')

  // Parallel: fetch permissions and role_permissions at the same time
  const [permsResult, rpResult] = await Promise.all([
    supabaseAdmin
      .from('permissions')
      .select('id, key, description, created_at')
      .order('key', { ascending: true }),
    supabaseAdmin
      .from('role_permissions')
      .select('permission_id, role_id'),
  ])

  if (permsResult.error) throw permsResult.error

  const rpData = rpResult.data ?? []

  // Build role ID → permission mapping
  const roleIdsByPerm = new Map<string, string[]>()
  for (const rp of rpData) {
    const existing = roleIdsByPerm.get(rp.permission_id) ?? []
    existing.push(rp.role_id)
    roleIdsByPerm.set(rp.permission_id, existing)
  }

  // Fetch role names only if needed
  const allRoleIds = [...new Set(rpData.map((rp) => rp.role_id))]
  let roleNameMap = new Map<string, string>()
  if (allRoleIds.length > 0) {
    const { data: rolesData } = await supabaseAdmin
      .from('roles')
      .select('id, name')
      .in('id', allRoleIds)

    roleNameMap = new Map((rolesData ?? []).map((r) => [r.id, r.name]))
  }

  const result = (permsResult.data ?? []).map((p) => {
    const roleIds = roleIdsByPerm.get(p.id) ?? []
    return {
      ...p,
      role_names: roleIds.map((rid) => roleNameMap.get(rid) ?? '').filter(Boolean),
    }
  })

  return apiSuccess(result)
}))
