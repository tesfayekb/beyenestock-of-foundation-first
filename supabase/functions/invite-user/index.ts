/**
 * invite-user — Send a single invitation to a new user.
 *
 * Owner: user-onboarding module
 * Classification: security-critical
 * Lifecycle: active
 *
 * POST /invite-user
 * Body: { email: string, role_id?: string (UUID), display_name?: string }
 *
 * Authorization: users.invite + recent auth (30min)
 * Pre-check: invite_enabled must be true in system_config
 * Existing-user detection: returns 409 with user_id so admin can assign role directly
 *
 * Token flow:
 *   1. Generate 32-byte random token
 *   2. Bcrypt hash (cost 10) → stored as token_hash
 *   3. Insert invitation row
 *   4. Call supabase.auth.admin.inviteUserByEmail() with invitation_id in metadata
 *   5. Emit user.invited audit event
 */
import { createHandler, apiSuccess } from '../_shared/handler.ts'
import { authenticateRequest } from '../_shared/authenticate-request.ts'
import { checkPermissionOrThrow, requireRecentAuth } from '../_shared/authorization.ts'
import { logAuditEvent } from '../_shared/audit.ts'
import { supabaseAdmin } from '../_shared/supabase-admin.ts'
import { z } from 'https://deno.land/x/zod@v3.22.4/mod.ts'
import { validateRequest } from '../_shared/validate-request.ts'
import { normalizeRequest } from '../_shared/normalize-request.ts'
import * as bcrypt from 'https://deno.land/x/bcrypt@v0.4.1/mod.ts'

const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

const BodySchema = z.object({
  email: z.string().trim().email().max(320),
  role_id: z.string().trim().regex(uuidRegex, 'Invalid UUID').optional(),
  display_name: z.string().trim().min(1).max(255).optional(),
})

/**
 * Generate a cryptographically secure token and its bcrypt hash.
 */
async function generateTokenPair(): Promise<{ rawToken: string; tokenHash: string }> {
  const bytes = new Uint8Array(32)
  crypto.getRandomValues(bytes)
  // Base64url encode
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
  await checkPermissionOrThrow(ctx.user.id, 'users.invite')
  requireRecentAuth(ctx.user.lastSignInAt, 30 * 60 * 1000, ctx.user.id)

  const body = await req.json()
  const input = validateRequest(BodySchema, body)
  const { email, role_id, display_name } = normalizeRequest(input)

  // Check invite_enabled
  const { data: configRow } = await supabaseAdmin
    .from('system_config')
    .select('value')
    .eq('key', 'onboarding_mode')
    .single()

  const config = configRow?.value as { invite_enabled?: boolean } | null
  if (config && config.invite_enabled === false) {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(400, 'Invitations are currently disabled', {
      code: 'INVITES_DISABLED',
      correlationId: ctx.correlationId,
    })
  }

  // Validate role_id if provided
  if (role_id) {
    const { data: role, error: roleError } = await supabaseAdmin
      .from('roles')
      .select('id, key')
      .eq('id', role_id)
      .single()

    if (roleError || !role) {
      const { apiError } = await import('../_shared/api-error.ts')
      return apiError(404, 'Role not found', { correlationId: ctx.correlationId })
    }

    // Cannot invite with superadmin role
    if (role.key === 'superadmin') {
      const { apiError } = await import('../_shared/api-error.ts')
      return apiError(403, 'Cannot invite users with superadmin role', {
        correlationId: ctx.correlationId,
      })
    }
  }

  // Check for existing auth user (direct email lookup — no pagination issues)
  const { data: existingUserData } = await supabaseAdmin.auth.admin.getUserByEmail(email.toLowerCase())
  if (existingUserData?.user) {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(409, 'A user with this email already exists. Use role assignment instead.', {
      code: 'USER_ALREADY_EXISTS',
      correlationId: ctx.correlationId,
    })
  }

  // Check for existing pending invitation
  const { data: existingInvite } = await supabaseAdmin
    .from('invitations')
    .select('id, status, expires_at')
    .eq('email', email.toLowerCase())
    .eq('status', 'pending')
    .single()

  if (existingInvite) {
    const isExpired = new Date(existingInvite.expires_at) < new Date()
    if (!isExpired) {
      const { apiError } = await import('../_shared/api-error.ts')
      return apiError(409, 'A pending invitation already exists for this email. Revoke it first or use resend.', {
        code: 'INVITATION_PENDING',
        correlationId: ctx.correlationId,
      })
    }
    // Expired pending — mark as expired so partial unique index allows new insert
    await supabaseAdmin
      .from('invitations')
      .update({ status: 'expired' })
      .eq('id', existingInvite.id)
  }

  // Generate token
  const { rawToken, tokenHash } = await generateTokenPair()

  // Create invitation row
  const invitationId = crypto.randomUUID()
  const { error: insertError } = await supabaseAdmin
    .from('invitations')
    .insert({
      id: invitationId,
      email: email.toLowerCase(),
      token_hash: tokenHash,
      role_id: role_id ?? null,
      invited_by: ctx.user.id,
      status: 'pending',
    })

  if (insertError) {
    console.error('[INVITE-USER] Insert failed:', insertError)
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(500, 'Failed to create invitation', { correlationId: ctx.correlationId })
  }

  // Send invite email via Supabase Auth
  const inviteMetadata: Record<string, string> = { invitation_id: invitationId }
  if (display_name) inviteMetadata.display_name = display_name

  const { error: inviteError } = await supabaseAdmin.auth.admin.inviteUserByEmail(email, {
    data: inviteMetadata,
  })

  if (inviteError) {
    // Rollback: delete invitation row
    await supabaseAdmin.from('invitations').delete().eq('id', invitationId)
    console.error('[INVITE-USER] inviteUserByEmail failed:', inviteError)
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(500, 'Failed to send invitation email', { correlationId: ctx.correlationId })
  }

  // Audit
  await logAuditEvent({
    actorId: ctx.user.id,
    action: 'user.invited',
    targetType: 'invitations',
    targetId: invitationId,
    metadata: {
      email: email.toLowerCase(),
      role_id: role_id ?? null,
      display_name: display_name ?? null,
    },
    ipAddress: ctx.ipAddress,
    userAgent: ctx.userAgent,
    correlationId: ctx.correlationId,
  })

  return apiSuccess({
    invitation_id: invitationId,
    email: email.toLowerCase(),
    status: 'pending',
    correlation_id: ctx.correlationId,
  }, 201)
}, { rateLimit: 'strict' }))
