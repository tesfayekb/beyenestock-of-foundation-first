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

  // Step 1: Build an email lookup map from auth.users (targeted by page batch)
  // For scalability, we fetch only needed users after profile query,
  // but for email search we need to pre-build a map.
  let emailSearchIds: Set<string> | null = null

  if (search) {
    // Fetch auth users to find email matches
    const { data: authData } = await supabaseAdmin.auth.admin.listUsers({
      page: 1,
      perPage: 1000,
    })
    if (authData?.users) {
      const lowerSearch = search.toLowerCase()
      emailSearchIds = new Set(
        authData.users
          .filter((u) => u.email?.toLowerCase().includes(lowerSearch))
          .map((u) => u.id)
      )
    }
  }

  // Step 2: Query profiles with display_name filter
  let query = supabaseAdmin
    .from('profiles')
    .select('id, display_name, avatar_url, email_verified, status, created_at, updated_at', { count: 'exact' })
    .order('created_at', { ascending: false })

  if (status) {
    query = query.eq('status', status)
  }

  if (search) {
    if (emailSearchIds && emailSearchIds.size > 0) {
      // Match display_name OR any of the email-matched IDs
      const emailIdArray = Array.from(emailSearchIds)
      query = query.or(`display_name.ilike.%${search}%,id.in.(${emailIdArray.join(',')})`)
    } else {
      query = query.or(`display_name.ilike.%${search}%`)
    }
  }

  // Apply pagination after filter
  query = query.range(offset, offset + limit - 1)

  const { data, error, count } = await query

  if (error) {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(500, 'Failed to list users', { correlationId: ctx.correlationId })
  }

  const profiles = data ?? []

  // Step 3: Enrich with email + roles for the current page only
  let enrichedUsers = profiles.map((p) => ({ ...p, email: null as string | null, roles: [] as { role_key: string; role_name: string }[] }))

  if (profiles.length > 0) {
    const userIds = profiles.map((p) => p.id)

    // Fetch emails — targeted by IDs on this page
    const { data: authData } = await supabaseAdmin.auth.admin.listUsers({
      page: 1,
      perPage: 1000,
    })
    const emailMap = new Map<string, string>()
    if (authData?.users) {
      for (const u of authData.users) {
        if (userIds.includes(u.id) && u.email) {
          emailMap.set(u.id, u.email)
        }
      }
    }

    // Fetch roles for these users
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
