/**
 * revoke-invitation — Revoke a pending invitation.
 *
 * Owner: user-onboarding module
 * Classification: security-critical
 * Lifecycle: active
 *
 * POST /revoke-invitation
 * Body: { invitation_id: string (UUID) }
 *
 * Authorization: users.invite.manage + recent auth (30min)
 * Only pending invitations can be revoked.
 * Emits user.invitation_revoked audit event.
 */
import { createHandler, apiSuccess } from '../_shared/handler.ts'
import { authenticateRequest } from '../_shared/authenticate-request.ts'
import { checkPermissionOrThrow, requireRecentAuth } from '../_shared/authorization.ts'
import { logAuditEvent } from '../_shared/audit.ts'
import { supabaseAdmin } from '../_shared/supabase-admin.ts'
import { z } from 'https://deno.land/x/zod@v3.22.4/mod.ts'
import { validateRequest } from '../_shared/validate-request.ts'

const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

const BodySchema = z.object({
  invitation_id: z.string().trim().regex(uuidRegex, 'Invalid UUID'),
})

Deno.serve(createHandler(async (req: Request) => {
  if (req.method !== 'POST') {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(405, 'Method not allowed', { correlationId: crypto.randomUUID() })
  }

  const ctx = await authenticateRequest(req)
  await checkPermissionOrThrow(ctx.user.id, 'users.invite.manage')
  requireRecentAuth(ctx.user.lastSignInAt, 30 * 60 * 1000, ctx.user.id)

  const body = await req.json()
  const { invitation_id } = validateRequest(BodySchema, body)

  // Fetch invitation
  const { data: invitation, error: fetchError } = await supabaseAdmin
    .from('invitations')
    .select('id, email, status, expires_at')
    .eq('id', invitation_id)
    .single()

  if (fetchError || !invitation) {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(404, 'Invitation not found', { correlationId: ctx.correlationId })
  }

  if (invitation.status !== 'pending') {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(409, `Cannot revoke invitation with status: ${invitation.status}`, {
      code: 'INVALID_STATUS',
      correlationId: ctx.correlationId,
    })
  }

  // Mark as revoked
  const { error: updateError } = await supabaseAdmin
    .from('invitations')
    .update({ status: 'revoked' })
    .eq('id', invitation_id)

  if (updateError) {
    console.error('[REVOKE-INVITATION] Update failed:', updateError)
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(500, 'Failed to revoke invitation', { correlationId: ctx.correlationId })
  }

  // Try to delete the pending auth user created by inviteUserByEmail
  // This is best-effort — if the user already set their password, this will fail silently
  try {
    const { data: listData } = await supabaseAdmin.auth.admin.listUsers({ page: 1, perPage: 50 })
    const pendingUser = listData?.users?.find(
      u => u.email?.toLowerCase() === invitation.email.toLowerCase() && !u.email_confirmed_at
    )
    if (pendingUser) {
      await supabaseAdmin.auth.admin.deleteUser(pendingUser.id)
    }
  } catch {
    // Best-effort cleanup — don't fail the revocation
    console.warn('[REVOKE-INVITATION] Failed to cleanup pending auth user for:', invitation.email)
  }

  // Audit
  await logAuditEvent({
    actorId: ctx.user.id,
    action: 'user.invitation_revoked',
    targetType: 'invitations',
    targetId: invitation_id,
    metadata: {
      email: invitation.email,
      was_expired: new Date(invitation.expires_at) < new Date(),
    },
    ipAddress: ctx.ipAddress,
    userAgent: ctx.userAgent,
    correlationId: ctx.correlationId,
  })

  return apiSuccess({
    success: true,
    invitation_id,
    correlation_id: ctx.correlationId,
  })
}, { rateLimit: 'strict' }))
