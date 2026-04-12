/**
 * list-users — List/filter user profiles (admin).
 *
 * Requires: users.view_all permission.
 *
 * GET /list-users?limit=50&offset=0&status=active&search=...
 *
 * Search matches display_name and email (both on profiles table).
 * Returns roles summary per user.
 *
 * Performance: No auth.admin.listUsers() call. Email is materialized
 * on profiles via sync trigger (MIG-034). Single DB round-trip for
 * search + pagination + roles enrichment.
 */
import { createHandler, apiSuccess } from '../_shared/handler.ts'
import { authenticateRequest } from '../_shared/authenticate-request.ts'
import { checkPermissionOrThrow } from '../_shared/authorization.ts'
import { supabaseAdmin } from '../_shared/supabase-admin.ts'
import { z } from 'https://deno.land/x/zod@v3.22.4/mod.ts'
import { validateRequest } from '../_shared/validate-request.ts'

const QuerySchema = z.object({
  limit: z.coerce.number().int().min(1).max(100).default(50),
  offset: z.coerce.number().int().min(0).default(0),
  status: z.enum(['active', 'deactivated']).optional(),
  search: z.string().trim().max(255).optional(),
})

Deno.serve(createHandler(async (req: Request) => {
  if (req.method !== 'GET') {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(405, 'Method not allowed', { correlationId: crypto.randomUUID() })
  }

  const ctx = await authenticateRequest(req)
  await checkPermissionOrThrow(ctx.user.id, 'users.view_all')

  const params = new URL(req.url).searchParams
  const { limit, offset, status, search } = validateRequest(QuerySchema, {
    limit: params.get('limit') ?? undefined,
    offset: params.get('offset') ?? undefined,
    status: params.get('status') ?? undefined,
    search: params.get('search') ?? undefined,
  })

  // Query profiles — email is now a materialized column (MIG-034)
  let query = supabaseAdmin
    .from('profiles')
    .select('id, display_name, avatar_url, email, email_verified, status, created_at, updated_at', { count: 'exact' })
    .order('created_at', { ascending: false })

  if (status) {
    query = query.eq('status', status)
  }

  if (search) {
    query = query.or(`display_name.ilike.%${search}%,email.ilike.%${search}%`)
  }

  query = query.range(offset, offset + limit - 1)

  const { data, error, count } = await query

  if (error) {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(500, 'Failed to list users', { correlationId: ctx.correlationId })
  }

  const profiles = data ?? []

  // Roles enrichment — single batch query for this page
  let enrichedUsers = profiles.map((p) => ({
    ...p,
    roles: [] as { role_key: string; role_name: string }[],
  }))

  if (profiles.length > 0) {
    const userIds = profiles.map((p) => p.id)

    const { data: userRoles } = await supabaseAdmin
      .from('user_roles')
      .select('user_id, roles(key, name)')
      .in('user_id', userIds)

    const rolesMap = new Map<string, { role_key: string; role_name: string }[]>()
    if (userRoles) {
      for (const ur of userRoles as any[]) {
        const existing = rolesMap.get(ur.user_id) ?? []
        existing.push({
          role_key: ur.roles?.key ?? '',
          role_name: ur.roles?.name ?? '',
        })
        rolesMap.set(ur.user_id, existing)
      }
    }

    enrichedUsers = profiles.map((p) => ({
      ...p,
      roles: rolesMap.get(p.id) ?? [],
    }))
  }

  return apiSuccess({
    users: enrichedUsers,
    total: count ?? 0,
    limit,
    offset,
  })
}))
