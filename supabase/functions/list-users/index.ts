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
    return apiError(405, 'Method not allowed')
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
    query = query.ilike('display_name', `%${search}%`)
  }

  const { data, error, count } = await query

  if (error) {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(500, 'Failed to list users', { correlationId: ctx.correlationId })
  }

  return apiSuccess({
    users: data ?? [],
    total: count ?? 0,
    limit,
    offset,
  })
}))
