/**
 * send-signup-nudge — Send a signup reminder email for a pending invitation
 * when the invite system is disabled but open signup is enabled.
 *
 * Owner: user-onboarding module
 * Classification: security-critical
 * Lifecycle: active
 *
 * POST /send-signup-nudge
 * Body: { invitation_id: string (UUID) }
 *
 * Authorization: users.invite.manage + recent auth (30min)
 * Pre-check: signup_enabled must be true (so user can actually sign up)
 * Uses Supabase's inviteUserByEmail as the email delivery mechanism
 * (the invitation_id in metadata ensures the handle_new_user_role trigger
 * still processes role assignment when the user signs up).
 *
 * Rate limit: 3 nudges per email per 24h
 * Emits user.signup_nudge_sent audit event.
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

const NUDGE_LIMIT = 3
const NUDGE_WINDOW_HOURS = 24

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

  // Check system config — signup must be enabled for nudge to make sense
  const { data: configRow } = await supabaseAdmin
    .from('system_config')
    .select('value')
    .eq('key', 'onboarding_mode')
    .single()

  const sysConfig = configRow?.value as {
    signup_enabled?: boolean
    invite_enabled?: boolean
  } | null

  if (sysConfig && sysConfig.signup_enabled === false) {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(400, 'Open signup is disabled. Cannot send signup reminder when users cannot register.', {
      code: 'SIGNUP_DISABLED',
      correlationId: ctx.correlationId,
    })
  }

  // Fetch the invitation
  const { data: invitation, error: fetchError } = await supabaseAdmin
    .from('invitations')
    .select('id, email, role_id, status, expires_at')
    .eq('id', invitation_id)
    .single()

  if (fetchError || !invitation) {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(404, 'Invitation not found', { correlationId: ctx.correlationId })
  }

  // Only pending (active or expired) invitations can receive a nudge
  if (invitation.status !== 'pending' && invitation.status !== 'expired') {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(409, `Cannot send reminder for invitation with status: ${invitation.status}`, {
      code: 'INVALID_STATUS',
      correlationId: ctx.correlationId,
    })
  }

  // Check if user already signed up
  const { data: userList } = await supabaseAdmin.auth.admin.listUsers({ page: 1, perPage: 1000 })
  const existingUser = userList?.users?.find(u => u.email === invitation.email)
  if (existingUser?.email_confirmed_at) {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(409, 'User has already signed up.', {
      code: 'USER_ALREADY_EXISTS',
      correlationId: ctx.correlationId,
    })
  }

  // Rate limit: max N nudges per email in 24h (shared with invitations table activity)
  const windowStart = new Date(Date.now() - NUDGE_WINDOW_HOURS * 60 * 60 * 1000).toISOString()
  const { count: recentActivity } = await supabaseAdmin
    .from('audit_logs')
    .select('id', { count: 'exact', head: true })
    .eq('action', 'user.signup_nudge_sent')
    .eq('metadata->>email', invitation.email)
    .gte('created_at', windowStart)

  if ((recentActivity ?? 0) >= NUDGE_LIMIT) {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(429, `Maximum ${NUDGE_LIMIT} signup reminders per email per ${NUDGE_WINDOW_HOURS} hours`, {
      code: 'NUDGE_RATE_LIMITED',
      correlationId: ctx.correlationId,
    })
  }

  // Delete any existing pending auth user (best-effort cleanup before re-invite)
  if (existingUser?.user && !existingUser.user.email_confirmed_at) {
    try {
      await supabaseAdmin.auth.admin.deleteUser(existingUser.user.id)
    } catch {
      console.warn('[SEND-SIGNUP-NUDGE] Failed to cleanup old pending auth user')
    }
  }

  // Use inviteUserByEmail to send an email with a link
  // The invitation_id in metadata ensures role assignment still works via trigger
  const { error: inviteError } = await supabaseAdmin.auth.admin.inviteUserByEmail(invitation.email, {
    data: {
      invitation_id: invitation.id,
      signup_nudge: true,
    },
  })

  if (inviteError) {
    console.error('[SEND-SIGNUP-NUDGE] inviteUserByEmail failed:', inviteError)
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(500, 'Failed to send signup reminder email', { correlationId: ctx.correlationId })
  }

  // Audit
  await logAuditEvent({
    actorId: ctx.user.id,
    action: 'user.signup_nudge_sent',
    targetType: 'invitations',
    targetId: invitation_id,
    metadata: {
      email: invitation.email,
      role_id: invitation.role_id,
      invite_system_disabled: sysConfig?.invite_enabled === false,
    },
    ipAddress: ctx.ipAddress,
    userAgent: ctx.userAgent,
    correlationId: ctx.correlationId,
  })

  return apiSuccess({
    success: true,
    invitation_id: invitation.id,
    email: invitation.email,
    correlation_id: ctx.correlationId,
  })
}, { rateLimit: 'strict' }))
