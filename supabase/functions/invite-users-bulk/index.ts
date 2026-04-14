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

const EntrySchema = z.object({
  email: z.string().trim().email().max(320),
  display_name: z.string().trim().max(255).optional(),
  last_name: z.string().trim().max(255).optional(),
})

const BodySchema = z.object({
  entries: z.array(EntrySchema).min(1).max(50),
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

  // Deduplicate by email, keep first occurrence
  const seen = new Set<string>()
  const entries = input.entries.filter((entry: { email: string }) => {
    const e = entry.email.trim().toLowerCase()
    if (seen.has(e)) return false
    seen.add(e)
    return true
  }).map((entry: { email: string; display_name?: string; last_name?: string }) => ({
    ...entry,
    email: entry.email.trim().toLowerCase(),
  }))
  const { data: configRow } = await supabaseAdmin
    .from('system_config')
    .select('value')
    .eq('key', 'onboarding_mode')
    .single()

  const config = configRow?.value as {
    invite_enabled?: boolean
    followup_days?: number
    max_followups?: number
  } | null
  if (config && config.invite_enabled === false) {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(400, 'Invitations are currently disabled', {
      code: 'INVITES_DISABLED',
      correlationId: ctx.correlationId,
    })
  }

  // Calculate dynamic expiry from followup settings
  const followupDays = config?.followup_days ?? 3
  const maxFollowups = config?.max_followups ?? 2
  const totalDays = followupDays * (maxFollowups + 1)
  const expiresAt = new Date(Date.now() + totalDays * 24 * 60 * 60 * 1000).toISOString()

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
  for (const entry of entries) {
    const email = entry.email
    try {
      // Check existing user in profiles
      const { data: profileData } = await supabaseAdmin
        .from('profiles')
        .select('id')
        .eq('email', email)
        .maybeSingle()

      if (profileData) {
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
          expires_at: expiresAt,
        })

      if (insertError) {
        result.failed.push({ email, reason: insertError.message })
        continue
      }

      // Build metadata for the invite email
      const inviteMetadata: Record<string, string> = { invitation_id: invitationId }
      if (entry.display_name) inviteMetadata.display_name = entry.display_name
      if (entry.last_name) inviteMetadata.last_name = entry.last_name

      // Send invite email
      const { error: inviteError } = await supabaseAdmin.auth.admin.inviteUserByEmail(email, {
        data: inviteMetadata,
      })

      if (inviteError) {
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
      total_requested: entries.length,
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
