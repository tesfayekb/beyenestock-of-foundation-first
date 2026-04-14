/**
 * resend-invitation — Resend an invitation with a fresh token and TTL.
 *
 * Owner: user-onboarding module
 * Classification: security-critical
 * Lifecycle: active
 *
 * POST /resend-invitation
 * Body: { invitation_id: string (UUID) }
 *
 * Authorization: users.invite.manage + recent auth (30min)
 * Rate limit: 3 resends per email per 24h (enforced by DB query)
 * Flow: revoke old invitation → create new one → send new invite email
 * Emits user.invitation_resent audit event.
 */
import { createHandler, apiSuccess } from '../_shared/handler.ts'
import { authenticateRequest } from '../_shared/authenticate-request.ts'
import { checkPermissionOrThrow, requireRecentAuth } from '../_shared/authorization.ts'
import { logAuditEvent } from '../_shared/audit.ts'
import { supabaseAdmin } from '../_shared/supabase-admin.ts'
import { z } from 'https://deno.land/x/zod@v3.22.4/mod.ts'
import { validateRequest } from '../_shared/validate-request.ts'
import * as bcrypt from 'https://deno.land/x/bcrypt@v0.4.1/mod.ts'

const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

const BodySchema = z.object({
  invitation_id: z.string().trim().regex(uuidRegex, 'Invalid UUID'),
})

const RESEND_LIMIT = 3
const RESEND_WINDOW_HOURS = 24

async function generateTokenPair(): Promise<{ rawToken: string; tokenHash: string }> {
  const bytes = new Uint8Array(32)
  crypto.getRandomValues(bytes)
  const rawToken = btoa(String.fromCharCode(...bytes))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '')
  const tokenHash = await bcrypt.hash(rawToken, 10)
  return { rawToken, tokenHash }
}

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

  // Fetch the original invitation
  const { data: invitation, error: fetchError } = await supabaseAdmin
    .from('invitations')
    .select('id, email, role_id, status, expires_at')
    .eq('id', invitation_id)
    .single()

  if (fetchError || !invitation) {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(404, 'Invitation not found', { correlationId: ctx.correlationId })
  }

  // Only pending or expired invitations can be resent
  const isExpired = invitation.status === 'pending' && new Date(invitation.expires_at) < new Date()
  if (invitation.status !== 'pending' && invitation.status !== 'expired') {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(409, `Cannot resend invitation with status: ${invitation.status}`, {
      code: 'INVALID_STATUS',
      correlationId: ctx.correlationId,
    })
  }

  // Rate limit: max 3 resends per email in 24h
  const windowStart = new Date(Date.now() - RESEND_WINDOW_HOURS * 60 * 60 * 1000).toISOString()
  const { count: recentResends } = await supabaseAdmin
    .from('invitations')
    .select('id', { count: 'exact', head: true })
    .eq('email', invitation.email)
    .gte('created_at', windowStart)

  if ((recentResends ?? 0) >= RESEND_LIMIT) {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(429, `Maximum ${RESEND_LIMIT} invitations per email per ${RESEND_WINDOW_HOURS} hours`, {
      code: 'RESEND_RATE_LIMITED',
      correlationId: ctx.correlationId,
    })
  }

  // Revoke old invitation
  await supabaseAdmin
    .from('invitations')
    .update({ status: 'revoked' })
    .eq('id', invitation_id)

  // Delete pending auth user from old invite (best-effort)
  try {
    const { data: listData } = await supabaseAdmin.auth.admin.listUsers({ page: 1, perPage: 50 })
    const pendingUser = listData?.users?.find(
      u => u.email?.toLowerCase() === invitation.email.toLowerCase() && !u.email_confirmed_at
    )
    if (pendingUser) {
      await supabaseAdmin.auth.admin.deleteUser(pendingUser.id)
    }
  } catch {
    console.warn('[RESEND-INVITATION] Failed to cleanup old pending auth user')
  }

  // Create new invitation with fresh token and TTL
  const { tokenHash } = await generateTokenPair()
  const newInvitationId = crypto.randomUUID()

  const { error: insertError } = await supabaseAdmin
    .from('invitations')
    .insert({
      id: newInvitationId,
      email: invitation.email,
      token_hash: tokenHash,
      role_id: invitation.role_id,
      invited_by: ctx.user.id,
      status: 'pending',
    })

  if (insertError) {
    console.error('[RESEND-INVITATION] Insert failed:', insertError)
    // Attempt to restore old invitation
    await supabaseAdmin
      .from('invitations')
      .update({ status: 'pending' })
      .eq('id', invitation_id)
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(500, 'Failed to create new invitation', { correlationId: ctx.correlationId })
  }

  // Send new invite email
  const { error: inviteError } = await supabaseAdmin.auth.admin.inviteUserByEmail(invitation.email, {
    data: { invitation_id: newInvitationId },
  })

  if (inviteError) {
    // Rollback new invitation
    await supabaseAdmin.from('invitations').delete().eq('id', newInvitationId)
    // Restore old invitation
    await supabaseAdmin
      .from('invitations')
      .update({ status: invitation.status })
      .eq('id', invitation_id)
    console.error('[RESEND-INVITATION] inviteUserByEmail failed:', inviteError)
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(500, 'Failed to send invitation email', { correlationId: ctx.correlationId })
  }

  // Audit
  await logAuditEvent({
    actorId: ctx.user.id,
    action: 'user.invitation_resent',
    targetType: 'invitations',
    targetId: newInvitationId,
    metadata: {
      email: invitation.email,
      old_invitation_id: invitation_id,
      new_invitation_id: newInvitationId,
      role_id: invitation.role_id,
      was_expired: isExpired || invitation.status === 'expired',
    },
    ipAddress: ctx.ipAddress,
    userAgent: ctx.userAgent,
    correlationId: ctx.correlationId,
  })

  return apiSuccess({
    success: true,
    old_invitation_id: invitation_id,
    new_invitation_id: newInvitationId,
    correlation_id: ctx.correlationId,
  })
}, { rateLimit: 'strict' }))
