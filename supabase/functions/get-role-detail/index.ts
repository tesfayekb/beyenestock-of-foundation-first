/**
 * get-role-detail — Return a single role with its permissions and assigned users.
 *
 * Requires: roles.view permission.
 *
 * GET /get-role-detail?role_id=<uuid>
 * Response: { data: RoleDetail }
 *
 * Superadmin auto-inherits all permissions via is_superadmin() — when role.key
 * is 'superadmin', ALL permissions are returned instead of role_permissions rows.
 */
import { createHandler, apiSuccess } from '../_shared/handler.ts'
import { authenticateRequest } from '../_shared/authenticate-request.ts'
import { checkPermissionOrThrow } from '../_shared/authorization.ts'
import { supabaseAdmin } from '../_shared/supabase-admin.ts'
import { z } from 'https://deno.land/x/zod@v3.22.4/mod.ts'
import { validateRequest } from '../_shared/validate-request.ts'

const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

const QuerySchema = z.object({
  role_id: z.string().trim().regex(uuidRegex, 'Invalid UUID'),
})

Deno.serve(createHandler(async (req: Request) => {
  if (req.method !== 'GET') {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(405, 'Method not allowed', { correlationId: crypto.randomUUID() })
  }

  const ctx = await authenticateRequest(req)
  await checkPermissionOrThrow(ctx.user.id, 'roles.view')

  const url = new URL(req.url)
  const params = Object.fromEntries(url.searchParams.entries())
  const { role_id } = validateRequest(QuerySchema, params)

  // Fetch role
  const { data: role, error } = await supabaseAdmin
    .from('roles')
    .select('id, key, name, description, is_base, is_immutable, created_at, updated_at')
    .eq('id', role_id)
    .single()

  if (error || !role) {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(404, 'Role not found', { correlationId: ctx.correlationId })
  }

  // Get permissions — superadmin inherits ALL, others use role_permissions join
  let permissions: { id: string; key: string; description: string | null }[] = []

  if (role.key === 'superadmin') {
    const { data: allPerms } = await supabaseAdmin
      .from('permissions')
      .select('id, key, description')
      .order('key', { ascending: true })

    permissions = allPerms ?? []
  } else {
    const { data: rpData } = await supabaseAdmin
      .from('role_permissions')
      .select('permission_id')
      .eq('role_id', role_id)

    const permissionIds = (rpData ?? []).map((rp) => rp.permission_id)

    if (permissionIds.length > 0) {
      const { data: permData } = await supabaseAdmin
        .from('permissions')
        .select('id, key, description')
        .in('id', permissionIds)

      permissions = permData ?? []
    }
  }

  // Get users with this role
  const { data: urData } = await supabaseAdmin
    .from('user_roles')
    .select('user_id, assigned_at')
    .eq('role_id', role_id)

  let users: { id: string; display_name: string | null; assigned_at: string }[] = []
  if (urData && urData.length > 0) {
    const userIds = urData.map((ur) => ur.user_id)
    const { data: profiles } = await supabaseAdmin
      .from('profiles')
      .select('id, display_name')
      .in('id', userIds)

    const profileMap = new Map((profiles ?? []).map((p) => [p.id, p.display_name]))
    users = urData.map((ur) => ({
      id: ur.user_id,
      display_name: profileMap.get(ur.user_id) ?? null,
      assigned_at: ur.assigned_at,
    }))
  }

  return apiSuccess({
    ...role,
    permission_count: permissions.length,
    user_count: users.length,
    permissions,
    users,
  })
}))
