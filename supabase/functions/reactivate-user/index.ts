/**
 * reactivate-user — Reactivate a deactivated user account.
 *
 * Requires: users.reactivate permission + recent authentication.
 * High-risk: fail-closed audit (abort if audit write fails).
 *
 * POST /reactivate-user
 * Body: { user_id: string, reason?: string }
 *
 * Effects:
 * - Sets profile status back to 'active'
 * - Does NOT restore previously revoked sessions
 * - Logs audit event (fail-closed)
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
  user_id: z.string().trim().regex(uuidRegex, 'Invalid UUID'),
  reason: z.string().trim().max(500).optional(),
})

Deno.serve(createHandler(async (req: Request) => {
  if (req.method !== 'POST') {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(405, 'Method not allowed', { correlationId: crypto.randomUUID() })
  }

  const ctx = await authenticateRequest(req)
  await checkPermissionOrThrow(ctx.user.id, 'users.reactivate')
  requireRecentAuth(ctx.user.lastSignInAt)

  const body = await req.json()
  const { user_id, reason } = validateRequest(BodySchema, body)

  // Verify target exists and is currently deactivated
  const { data: profile, error: fetchErr } = await supabaseAdmin
    .from('profiles')
    .select('id, status')
    .eq('id', user_id)
    .single()

  if (fetchErr || !profile) {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(404, 'User not found', { correlationId: ctx.correlationId })
  }

  if (profile.status === 'active') {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(409, 'User is already active', { correlationId: ctx.correlationId })
  }

  // HIGH-RISK: Audit first (fail-closed)
  const auditResult = await logAuditEvent({
    actorId: ctx.user.id,
    action: 'user.account_reactivated',
    targetType: 'user',
    targetId: user_id,
    metadata: { reason: reason ?? null },
    ipAddress: ctx.ipAddress,
    userAgent: ctx.userAgent,
    correlationId: ctx.correlationId,
  })

  if (!auditResult.success) {
    const { apiError } = await import('../_shared/api-error.ts')
    console.error('[REACTIVATE] Audit write failed — aborting (fail-closed)', auditResult)
    return apiError(500, 'Operation aborted: audit trail could not be written', {
      code: 'AUDIT_WRITE_FAILED',
      correlationId: ctx.correlationId,
    })
  }

  // Clear the auth ban first (fail-closed: if we can't unban, don't flip status)
  try {
    const { error: unbanErr } = await supabaseAdmin.auth.admin.updateUserById(user_id, {
      ban_duration: 'none',
    })
    if (unbanErr) throw unbanErr
  } catch (e) {
    const { apiError } = await import('../_shared/api-error.ts')
    const errMsg = e instanceof Error ? e.message : String(e)
    console.error('[REACTIVATE] Failed to clear auth ban — aborting', {
      userId: user_id,
      correlationId: ctx.correlationId,
      error: errMsg,
    })
    return apiError(500, 'Failed to clear authentication ban', {
      code: 'AUTH_UNBAN_FAILED',
      correlationId: ctx.correlationId,
    })
  }

  // Set status back to active
  const { error: updateErr } = await supabaseAdmin
    .from('profiles')
    .update({ status: 'active' })
    .eq('id', user_id)

  if (updateErr) {
    // Compensating rollback: re-ban since status didn't update
    console.error('[REACTIVATE] Profile update failed after unban — re-banning', {
      userId: user_id,
      correlationId: ctx.correlationId,
    })
    await supabaseAdmin.auth.admin.updateUserById(user_id, {
      ban_duration: '876000h',
    })
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(500, 'Failed to reactivate user', { correlationId: ctx.correlationId })
  }

  return apiSuccess({
    message: 'User reactivated successfully',
    user_id,
    correlationId: ctx.correlationId,
  })
}, { rateLimit: 'strict' }))
