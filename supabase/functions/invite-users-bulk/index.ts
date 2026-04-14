/**
 * invite-users-bulk — Send up to 50 invitations in a single call.
 *
 * Owner: user-onboarding module
 * Classification: security-critical
 * Lifecycle: active
 *
 * POST /invite-users-bulk
 * Body: { emails: string[], role_id?: string (UUID) }
 *
 * Authorization: users.invite + recent auth (30min)
 * Pre-check: invite_enabled must be true
 * Processing: Sequential to respect Supabase rate limits
 * Returns: { succeeded: [...], failed: [...], skipped_existing: [...] }
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
  emails: z.array(z.string().trim().email().max(320)).min(1).max(50),
  role_id: z.string().trim().regex(uuidRegex, 'Invalid UUID').optional(),
})

async function generateTokenPair(): Promise<{ rawToken: string; tokenHash: string }> {
  const bytes = new Uint8Array(32)
  crypto.getRandomValues(bytes)
  const rawToken = btoa(String.fromCharCode(...bytes))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '')
  const encoder = new TextEncoder()
  const hashBuffer = await crypto.subtle.digest('SHA-256', encoder.encode(rawToken))
  const hashArray = new Uint8Array(hashBuffer)
  const tokenHash = Array.from(hashArray).map(b => b.toString(16).padStart(2, '0')).join('')
  return { rawToken, tokenHash }
}

interface BulkResult {
  succeeded: string[]
  failed: { email: string; reason: string }[]
  skipped_existing: string[]
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
  const role_id = input.role_id

  // Deduplicate and normalize emails
  const emails = [...new Set(input.emails.map((e: string) => e.trim().toLowerCase()))]

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
    if (role.key === 'superadmin') {
      const { apiError } = await import('../_shared/api-error.ts')
      return apiError(403, 'Cannot invite users with superadmin role', {
        correlationId: ctx.correlationId,
      })
    }
  }

  const result: BulkResult = { succeeded: [], failed: [], skipped_existing: [] }

  // Process sequentially to respect Supabase rate limits
  for (const email of emails) {
    try {
      // Check existing auth user (direct email lookup — no pagination issues)
      const { data: userData } = await supabaseAdmin.auth.admin.getUserByEmail(email)
      if (userData?.user) {
        result.skipped_existing.push(email)
        continue
      }

      // Check existing pending invitation
      const { data: pendingInvite } = await supabaseAdmin
        .from('invitations')
        .select('id, expires_at')
        .eq('email', email)
        .eq('status', 'pending')
        .single()

      if (pendingInvite) {
        const isExpired = new Date(pendingInvite.expires_at) < new Date()
        if (!isExpired) {
          result.failed.push({ email, reason: 'pending_invitation_exists' })
          continue
        }
        // Mark expired
        await supabaseAdmin
          .from('invitations')
          .update({ status: 'expired' })
          .eq('id', pendingInvite.id)
      }

      // Generate token + insert
      const { tokenHash } = await generateTokenPair()
      const invitationId = crypto.randomUUID()

      const { error: insertError } = await supabaseAdmin
        .from('invitations')
        .insert({
          id: invitationId,
          email,
          token_hash: tokenHash,
          role_id: role_id ?? null,
          invited_by: ctx.user.id,
          status: 'pending',
        })

      if (insertError) {
        result.failed.push({ email, reason: insertError.message })
        continue
      }

      // Send invite email
      const { error: inviteError } = await supabaseAdmin.auth.admin.inviteUserByEmail(email, {
        data: { invitation_id: invitationId },
      })

      if (inviteError) {
        // Rollback
        await supabaseAdmin.from('invitations').delete().eq('id', invitationId)
        result.failed.push({ email, reason: 'email_send_failed' })
        continue
      }

      result.succeeded.push(email)
    } catch (err) {
      result.failed.push({ email, reason: err instanceof Error ? err.message : 'unknown_error' })
    }
  }

  // Audit
  await logAuditEvent({
    actorId: ctx.user.id,
    action: 'user.bulk_invited',
    targetType: 'invitations',
    metadata: {
      total_requested: emails.length,
      succeeded_count: result.succeeded.length,
      failed_count: result.failed.length,
      skipped_existing_count: result.skipped_existing.length,
      role_id: role_id ?? null,
    },
    ipAddress: ctx.ipAddress,
    userAgent: ctx.userAgent,
    correlationId: ctx.correlationId,
  })

  return apiSuccess({
    ...result,
    correlation_id: ctx.correlationId,
  })
}, { rateLimit: 'strict' }))
