/**
 * deactivate-user — Deactivate a user account.
 *
 * Requires: users.deactivate permission + recent authentication.
 * High-risk: fail-closed audit (abort if audit write fails).
 * Session revocation: fail-closed with compensating rollback.
 *
 * POST /deactivate-user
 * Body: { user_id: string, reason?: string }
 *
 * Effects:
 * - Sets profile status to 'deactivated'
 * - Revokes all active sessions via Supabase Admin API
 * - Logs audit event (fail-closed)
 *
 * Transaction semantics:
 * - Audit write → fail-closed (abort before any mutation)
 * - Status update → fail-closed
 * - Session revocation → fail-closed with compensating rollback
 *   (if session revocation fails, status is rolled back to 'active')
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

Deno.serve(createHandler(async (req: Request) => { {
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

  // Revoke all sessions via Admin API — FAIL-CLOSED with compensating rollback
  const { error: signOutErr } = await supabaseAdmin.auth.admin.signOut(user_id)
  if (signOutErr) {
    // Compensating rollback: restore status to 'active' since sessions are still live
    console.error('[DEACTIVATE] Session revocation failed — rolling back status', {
      userId: user_id,
      correlationId: ctx.correlationId,
      error: signOutErr.message,
    })

    const { error: rollbackErr } = await supabaseAdmin
      .from('profiles')
      .update({ status: 'active' })
      .eq('id', user_id)

    if (rollbackErr) {
      // Critical: status is 'deactivated' but sessions are live — log for manual intervention
      console.error('[DEACTIVATE] CRITICAL: Rollback also failed — manual intervention required', {
        userId: user_id,
        correlationId: ctx.correlationId,
        rollbackError: rollbackErr.message,
      })
    }

    // Log compensating action for audit trail
    await logAuditEvent({
      actorId: ctx.user.id,
      action: 'user.deactivation_rolled_back',
      targetType: 'user',
      targetId: user_id,
      metadata: {
        reason: 'Session revocation failed',
        rollback_success: !rollbackErr,
        original_reason: reason ?? null,
      },
      ipAddress: ctx.ipAddress,
      userAgent: ctx.userAgent,
      correlationId: ctx.correlationId,
    })

    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(500, 'Deactivation failed: could not revoke sessions. Status restored.', {
      code: 'SESSION_REVOCATION_FAILED',
      correlationId: ctx.correlationId,
    })
  }

  return apiSuccess({
    message: 'User deactivated successfully',
    user_id,
    correlationId: ctx.correlationId,
  })
}))
