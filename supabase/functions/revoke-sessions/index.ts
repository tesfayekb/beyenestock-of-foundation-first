/**
 * revoke-sessions — User self-service session revocation.
 *
 * POST /revoke-sessions
 * Body: { scope: 'others' | 'global' }
 *
 * Uses ctx.user.id as target — no user_id body param needed.
 * Requires: requireRecentAuth() (sensitive action)
 * Audit: user.sessions_revoked
 *
 * Owner: auth module (DW-019)
 */
import { createHandler, apiSuccess } from '../_shared/handler.ts'
import { authenticateRequest } from '../_shared/authenticate-request.ts'
import { requireRecentAuth } from '../_shared/authorization.ts'
import { validateRequest, z } from '../_shared/validate-request.ts'
import { supabaseAdmin } from '../_shared/supabase-admin.ts'
import { logAuditEvent } from '../_shared/audit.ts'

const BodySchema = z.object({
  scope: z.enum(['others', 'global']),
})

Deno.serve(createHandler(async (req: Request): Promise<Response> => {
  const ctx = await authenticateRequest(req)
  requireRecentAuth(ctx.user.lastSignInAt, 30 * 60 * 1000, ctx.user.id)

  const body = validateRequest(BodySchema, await req.json())

  // Use Supabase admin SDK to sign out sessions
  const { error } = await supabaseAdmin.auth.admin.signOut(
    ctx.user.id,
    body.scope,
  )

  if (error) {
    throw new Error(`Session revocation failed: ${error.message}`)
  }

  await logAuditEvent({
    actorId: ctx.user.id,
    action: 'user.sessions_revoked',
    targetType: 'user',
    targetId: ctx.user.id,
    metadata: { scope: body.scope },
    ipAddress: ctx.ipAddress,
    userAgent: ctx.userAgent,
    correlationId: ctx.correlationId,
  })

  return apiSuccess({
    success: true,
    scope: body.scope,
    message: body.scope === 'global'
      ? 'All sessions revoked, including current'
      : 'Other sessions revoked, current session preserved',
  })
}, { rateLimit: 'strict' }))
