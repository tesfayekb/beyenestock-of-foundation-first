/**
 * update-profile — Update a user profile.
 *
 * Self-access: requires users.edit_self + requireSelfScope() enforcement.
 * Admin access: requires users.edit_any (any user).
 *
 * PATCH /update-profile
 * Body: { user_id?: string, display_name?: string, avatar_url?: string }
 * If user_id omitted, updates the authenticated user's own profile.
 */
import { createHandler, apiSuccess } from '../_shared/handler.ts'
import { authenticateRequest } from '../_shared/authenticate-request.ts'
import { checkPermissionOrThrow, requireSelfScope } from '../_shared/authorization.ts'
import { logAuditEvent } from '../_shared/audit.ts'
import { supabaseAdmin } from '../_shared/supabase-admin.ts'
import { z } from 'https://deno.land/x/zod@v3.22.4/mod.ts'
import { validateRequest } from '../_shared/validate-request.ts'

const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

const BodySchema = z.object({
  user_id: z.string().trim().regex(uuidRegex, 'Invalid UUID').optional(),
  display_name: z.string().trim().min(1).max(255).optional(),
  avatar_url: z.string().url().max(2048).nullable().optional(),
}).refine(
  (d) => d.display_name !== undefined || d.avatar_url !== undefined,
  { message: 'At least one field to update is required' }
)

Deno.serve(createHandler(async (req: Request) => {
  if (req.method !== 'PATCH') {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(405, 'Method not allowed', { correlationId: crypto.randomUUID() })
  }

  const ctx = await authenticateRequest(req)
  const body = await req.json()
  const { user_id, display_name, avatar_url } = validateRequest(BodySchema, body)

  const targetUserId = user_id ?? ctx.user.id
  const isSelf = targetUserId === ctx.user.id

  if (isSelf) {
    // Layered enforcement: permission + self-scope
    await checkPermissionOrThrow(ctx.user.id, 'users.edit_self')
    requireSelfScope(ctx, targetUserId)
  } else {
    await checkPermissionOrThrow(ctx.user.id, 'users.edit_any')
  }

  // Build update payload — only include provided fields
  const updatePayload: Record<string, unknown> = {}
  if (display_name !== undefined) updatePayload.display_name = display_name
  if (avatar_url !== undefined) updatePayload.avatar_url = avatar_url

  const { data, error } = await supabaseAdmin
    .from('profiles')
    .update(updatePayload)
    .eq('id', targetUserId)
    .select('id, display_name, avatar_url, email_verified, status, created_at, updated_at')
    .single()

  if (error || !data) {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(404, 'Profile not found', { correlationId: ctx.correlationId })
  }

  // Audit — standard risk (log and continue)
  await logAuditEvent({
    actorId: ctx.user.id,
    action: 'user.profile_updated',
    targetType: 'user',
    targetId: targetUserId,
    metadata: {
      is_self: isSelf,
      fields_changed: Object.keys(updatePayload),
    },
    ipAddress: ctx.ipAddress,
    userAgent: ctx.userAgent,
    correlationId: ctx.correlationId,
  })

  return apiSuccess({ profile: data })
}))
