/**
 * get-profile — Fetch a user profile.
 *
 * Self-access: requires users.view_self + requireSelfScope() enforcement.
 * Admin access: requires users.view_all (any user).
 *
 * GET /get-profile?user_id=<uuid>
 * If user_id omitted, returns the authenticated user's own profile.
 *
 * Performance: Email is now materialized on profiles (MIG-034).
 * No auth.admin.getUserById() call needed.
 */
import { createHandler, apiSuccess } from '../_shared/handler.ts'
import { authenticateRequest } from '../_shared/authenticate-request.ts'
import { checkPermissionOrThrow, requireSelfScope } from '../_shared/authorization.ts'
import { supabaseAdmin } from '../_shared/supabase-admin.ts'
import { z } from 'https://deno.land/x/zod@v3.22.4/mod.ts'
import { validateRequest } from '../_shared/validate-request.ts'

const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

const QuerySchema = z.object({
  user_id: z.string().trim().regex(uuidRegex, 'Invalid UUID').optional(),
})

Deno.serve(createHandler(async (req: Request) => {
  if (req.method !== 'GET') {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(405, 'Method not allowed', { correlationId: crypto.randomUUID() })
  }

  const ctx = await authenticateRequest(req)
  const params = new URL(req.url).searchParams
  const { user_id } = validateRequest(QuerySchema, {
    user_id: params.get('user_id') ?? undefined,
  })

  const targetUserId = user_id ?? ctx.user.id
  const isSelf = targetUserId === ctx.user.id

  if (isSelf) {
    await checkPermissionOrThrow(ctx.user.id, 'users.view_self')
    requireSelfScope(ctx, targetUserId)
  } else {
    await checkPermissionOrThrow(ctx.user.id, 'users.view_all')
  }

  const { data, error } = await supabaseAdmin
    .from('profiles')
    .select('id, display_name, last_name, avatar_url, email, email_verified, status, created_at, updated_at')
    .eq('id', targetUserId)
    .single()

  if (error || !data) {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(404, 'Profile not found', { correlationId: ctx.correlationId })
  }

  return apiSuccess({ profile: data })
}))
