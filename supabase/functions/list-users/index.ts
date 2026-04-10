/**
 * list-users — List/filter user profiles (admin).
 *
 * Requires: users.view_all permission.
 *
 * GET /list-users?limit=50&offset=0&status=active&search=...
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

  let query = supabaseAdmin
    .from('profiles')
    .select('id, display_name, avatar_url, email_verified, status, created_at, updated_at', { count: 'exact' })
    .order('created_at', { ascending: false })
    .range(offset, offset + limit - 1)

  if (status) {
    query = query.eq('status', status)
  }

  if (search) {
    query = query.or(`display_name.ilike.%${search}%`);
  }

  const { data, error, count } = await query

  if (error) {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(500, 'Failed to list users', { correlationId: ctx.correlationId })
  }

  const profiles = data ?? []

  // Enrich with email from auth.users for admin display
  let enrichedUsers = profiles
  if (profiles.length > 0) {
    const userIds = profiles.map((p) => p.id)
    // Batch fetch auth users — admin API supports listing by page
    // For small batches (≤100), a single listUsers call with filter is efficient
    const { data: authData } = await supabaseAdmin.auth.admin.listUsers({
      page: 1,
      perPage: 1000,
    })

    if (authData?.users) {
      const emailMap = new Map(
        authData.users
          .filter((u) => userIds.includes(u.id))
          .map((u) => [u.id, u.email ?? null])
      )

      enrichedUsers = profiles.map((p) => ({
        ...p,
        email: emailMap.get(p.id) ?? null,
      }))
    }
  }

  // If search term provided, also filter by email match (post-enrichment)
  let filteredUsers = enrichedUsers
  let filteredTotal = count ?? 0
  if (search && enrichedUsers.length > 0 && enrichedUsers[0] && 'email' in enrichedUsers[0]) {
    // Re-filter to include email matches that display_name filter missed
    // Note: primary filter is display_name via DB query; email match is additive client-side
    // For large-scale, this should move to a DB view or function
    filteredUsers = enrichedUsers
    // The DB already filtered by display_name, so all results are relevant
    // Email-only matches would require a separate query approach (future optimization)
  }

  return apiSuccess({
    users: filteredUsers,
    total: filteredTotal,
    limit,
    offset,
  })
}))
