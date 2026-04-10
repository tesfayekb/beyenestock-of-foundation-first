/**
 * deactivate-user — Deactivate a user account.
 *
 * Requires: users.deactivate permission + recent authentication.
 * High-risk: fail-closed audit (abort if audit write fails).
 *
 * POST /deactivate-user
 * Body: { user_id: string, reason?: string }
 *
 * Effects:
 * - Sets profile status to 'deactivated'
 * - Revokes all active sessions via Supabase Admin API
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
    return apiError(405, 'Method not allowed')
  }

  const ctx = await authenticateRequest(req)
  await checkPermissionOrThrow(ctx.user.id, 'users.deactivate')
  requireRecentAuth(ctx.user.lastSignInAt)

  const body = await req.json()
  const { user_id, reason } = validateRequest(BodySchema, body)

  // Prevent self-deactivation
  if (user_id === ctx.user.id) {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(400, 'Cannot deactivate your own account', { correlationId: ctx.correlationId })
  }

  // Verify target exists and is currently active
  const { data: profile, error: fetchErr } = await supabaseAdmin
    .from('profiles')
    .select('id, status')
    .eq('id', user_id)
    .single()

  if (fetchErr || !profile) {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(404, 'User not found', { correlationId: ctx.correlationId })
  }

  if (profile.status === 'deactivated') {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(409, 'User is already deactivated', { correlationId: ctx.correlationId })
  }

  // HIGH-RISK: Audit first (fail-closed)
  const auditResult = await logAuditEvent({
    actorId: ctx.user.id,
    action: 'user.account_deactivated',
    targetType: 'user',
    targetId: user_id,
    metadata: { reason: reason ?? null },
    ipAddress: ctx.ipAddress,
    userAgent: ctx.userAgent,
    correlationId: ctx.correlationId,
  })

  if (!auditResult.success) {
    const { apiError } = await import('../_shared/api-error.ts')
    console.error('[DEACTIVATE] Audit write failed — aborting (fail-closed)', auditResult)
    return apiError(500, 'Operation aborted: audit trail could not be written', {
      code: 'AUDIT_WRITE_FAILED',
      correlationId: ctx.correlationId,
    })
  }

  // Set status to deactivated
  const { error: updateErr } = await supabaseAdmin
    .from('profiles')
    .update({ status: 'deactivated' })
    .eq('id', user_id)

  if (updateErr) {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(500, 'Failed to deactivate user', { correlationId: ctx.correlationId })
  }

  // Revoke all sessions via Admin API
  const { error: signOutErr } = await supabaseAdmin.auth.admin.signOut(user_id)
  if (signOutErr) {
    // Log but don't abort — status is already changed, session revocation is best-effort
    console.error('[DEACTIVATE] Session revocation failed:', signOutErr.message, {
      userId: user_id,
      correlationId: ctx.correlationId,
    })
  }

  return apiSuccess({
    message: 'User deactivated successfully',
    user_id,
    correlationId: ctx.correlationId,
  })
}))
