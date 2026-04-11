/**
 * list-roles — Return all roles with permission and user counts.
 *
 * Requires: roles.view permission.
 *
 * GET /list-roles
 * Response: { data: RoleListItem[] }
 */
import { createHandler, apiSuccess } from '../_shared/handler.ts'
import { authenticateRequest } from '../_shared/authenticate-request.ts'
import { checkPermissionOrThrow } from '../_shared/authorization.ts'
import { supabaseAdmin } from '../_shared/supabase-admin.ts'

interface RoleListItem {
  id: string
  key: string
  name: string
  description: string | null
  is_base: boolean
  is_immutable: boolean
  created_at: string
  updated_at: string
  permission_count: number
  user_count: number
}

Deno.serve(createHandler(async (req: Request) => {
  if (req.method !== 'GET') {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(405, 'Method not allowed', { correlationId: crypto.randomUUID() })
  }

  const ctx = await authenticateRequest(req)
  await checkPermissionOrThrow(ctx.user.id, 'roles.view')

  // Fetch roles
  const { data: roles, error } = await supabaseAdmin
    .from('roles')
    .select('id, key, name, description, is_base, is_immutable, created_at, updated_at')
    .order('created_at', { ascending: true })

  if (error) throw error

  // Get permission counts per role
  const { data: rpData } = await supabaseAdmin
    .from('role_permissions')
    .select('role_id')

  const permCounts = new Map<string, number>()
  for (const rp of rpData ?? []) {
    permCounts.set(rp.role_id, (permCounts.get(rp.role_id) ?? 0) + 1)
  }

  // Get user counts per role
  const { data: urData } = await supabaseAdmin
    .from('user_roles')
    .select('role_id')

  const userCounts = new Map<string, number>()
  for (const ur of urData ?? []) {
    userCounts.set(ur.role_id, (userCounts.get(ur.role_id) ?? 0) + 1)
  }

  const result: RoleListItem[] = (roles ?? []).map((r) => ({
    ...r,
    permission_count: permCounts.get(r.id) ?? 0,
    user_count: userCounts.get(r.id) ?? 0,
  }))

  return apiSuccess({ data: result })
}))
