/**
 * list-users — List/filter user profiles (admin).
 *
 * Requires: users.view_all permission.
 *
 * GET /list-users?limit=50&offset=0&status=active&search=...
 *
 * Search matches both display_name and email (server-side).
 * Returns roles summary per user.
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

const EMAIL_SEARCH_CAP = 500

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

  // Only call auth.admin.listUsers when search is active (email search) or
  // when we need email enrichment. For list-without-search, skip the expensive
  // auth call entirely — emails are fetched lazily on user detail page.
  let authUsersCache: { id: string; email?: string }[] | null = null
  const needsEmailSearch = !!search

  async function getAuthUsers() {
    if (authUsersCache) return authUsersCache
    const { data: authData } = await supabaseAdmin.auth.admin.listUsers({
      page: 1,
      perPage: 1000,
    })
    authUsersCache = authData?.users ?? []
    return authUsersCache
  }

  // Step 1: Build email search ID set if search is active
  let emailSearchIds: string[] | null = null

  if (search) {
    const authUsers = await getAuthUsers()
    const lowerSearch = search.toLowerCase()
    emailSearchIds = authUsers
      .filter((u) => u.email?.toLowerCase().includes(lowerSearch))
      .map((u) => u.id)
      .slice(0, EMAIL_SEARCH_CAP)
  }

  // Step 2: Query profiles
  let query = supabaseAdmin
    .from('profiles')
    .select('id, display_name, avatar_url, email_verified, status, created_at, updated_at', { count: 'exact' })
    .order('created_at', { ascending: false })

  if (status) {
    query = query.eq('status', status)
  }

  if (search) {
    if (emailSearchIds && emailSearchIds.length > 0) {
      query = query.or(`display_name.ilike.%${search}%,id.in.(${emailSearchIds.join(',')})`)
    } else {
      query = query.or(`display_name.ilike.%${search}%`)
    }
  }

  query = query.range(offset, offset + limit - 1)

  const { data, error, count } = await query

  if (error) {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(500, 'Failed to list users', { correlationId: ctx.correlationId })
  }

  const profiles = data ?? []

  // Step 3: Enrich with email + roles — reuse cached auth users
  let enrichedUsers = profiles.map((p) => ({
    ...p,
    email: null as string | null,
    roles: [] as { role_key: string; role_name: string }[],
  }))

  if (profiles.length > 0) {
    const userIds = profiles.map((p) => p.id)

    // Email enrichment — only when search was active (auth users already cached)
    // For non-search requests, skip the expensive auth call; emails are
    // fetched lazily on the user detail page instead.
    const emailMap = new Map<string, string>()
    if (needsEmailSearch) {
      const authUsers = await getAuthUsers()
      for (const u of authUsers) {
        if (userIds.includes(u.id) && u.email) {
          emailMap.set(u.id, u.email)
        }
      }
    }

    // Roles enrichment — single batch query for this page
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
      email: emailMap.get(p.id) ?? null,
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
