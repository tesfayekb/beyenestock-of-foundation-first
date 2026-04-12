/**
 * POST /mfa-recovery-verify — Verify a recovery code for MFA bypass.
 *
 * Accepts a recovery code, verifies against stored hashes, marks used.
 * Does NOT require MFA (that's the point — user is locked out of MFA).
 * Requires: Bearer JWT (AAL1 only — user has password but not MFA factor).
 *
 * Security: Per-user lockout after 5 failed attempts (15-min cooldown).
 * Audit: auth.mfa_recovery_used / auth.mfa_recovery_failed
 *
 * Owner: auth module (DW-008)
 */
import { createHandler, apiSuccess } from '../_shared/handler.ts'
import { authenticateRequest } from '../_shared/authenticate-request.ts'
import { validateRequest, z } from '../_shared/validate-request.ts'
import { supabaseAdmin } from '../_shared/supabase-admin.ts'
import { logAuditEvent } from '../_shared/audit.ts'
import { compare } from 'https://deno.land/x/bcrypt@v0.4.1/mod.ts'

const BodySchema = z.object({
  code: z.string().length(8),
})

const MAX_FAILED_ATTEMPTS = 5
const LOCKOUT_DURATION_MS = 15 * 60 * 1000 // 15 minutes

Deno.serve(createHandler(async (req: Request): Promise<Response> => {
  const ctx = await authenticateRequest(req)
  const userId = ctx.user.id
  const body = validateRequest(BodySchema, await req.json())

  // ── Check lockout status ──
  const { data: attemptRecord } = await supabaseAdmin
    .from('mfa_recovery_attempts')
    .select('failed_count, locked_until')
    .eq('user_id', userId)
    .maybeSingle()

  if (attemptRecord?.locked_until && new Date(attemptRecord.locked_until) > new Date()) {
    await logAuditEvent({
      actorId: userId,
      action: 'auth.mfa_recovery_failed',
      targetType: 'user',
      targetId: userId,
      metadata: { reason: 'account_locked', locked_until: attemptRecord.locked_until },
      ipAddress: ctx.ipAddress,
      userAgent: ctx.userAgent,
      correlationId: ctx.correlationId,
    })

    return new Response(
      JSON.stringify({ error: 'Account temporarily locked due to too many failed attempts. Try again later.' }),
      { status: 429, headers: { 'Content-Type': 'application/json' } }
    )
  }

  // ── Fetch unused codes ──
  const { data: codes, error: fetchError } = await supabaseAdmin
    .from('mfa_recovery_codes')
    .select('id, code_hash')
    .eq('user_id', userId)
    .is('used_at', null)

  if (fetchError) {
    throw new Error(`Failed to fetch recovery codes: ${fetchError.message}`)
  }

  if (!codes || codes.length === 0) {
    return new Response(
      JSON.stringify({ error: 'No recovery codes available. Generate new codes from security settings.' }),
      { status: 400, headers: { 'Content-Type': 'application/json' } }
    )
  }

  // ── Check each code (bcrypt compare is slow by design — 10 codes max) ──
  let matchedCodeId: string | null = null
  for (const entry of codes) {
    const isMatch = await compare(body.code.toUpperCase(), entry.code_hash)
    if (isMatch) {
      matchedCodeId = entry.id
      break
    }
  }

  if (!matchedCodeId) {
    // ── Increment failed attempt counter ──
    const newCount = (attemptRecord?.failed_count ?? 0) + 1
    const lockedUntil = newCount >= MAX_FAILED_ATTEMPTS
      ? new Date(Date.now() + LOCKOUT_DURATION_MS).toISOString()
      : null

    await supabaseAdmin
      .from('mfa_recovery_attempts')
      .upsert({
        user_id: userId,
        failed_count: newCount,
        locked_until: lockedUntil,
        last_attempt_at: new Date().toISOString(),
      }, { onConflict: 'user_id' })

    await logAuditEvent({
      actorId: userId,
      action: 'auth.mfa_recovery_failed',
      targetType: 'user',
      targetId: userId,
      metadata: {
        reason: 'invalid_code',
        failed_count: newCount,
        locked: newCount >= MAX_FAILED_ATTEMPTS,
      },
      ipAddress: ctx.ipAddress,
      userAgent: ctx.userAgent,
      correlationId: ctx.correlationId,
    })

    return new Response(
      JSON.stringify({ error: 'Invalid recovery code.' }),
      { status: 401, headers: { 'Content-Type': 'application/json' } }
    )
  }

  // ── Success: mark code used + clear attempt counter ──
  await Promise.all([
    supabaseAdmin
      .from('mfa_recovery_codes')
      .update({ used_at: new Date().toISOString() })
      .eq('id', matchedCodeId),
    supabaseAdmin
      .from('mfa_recovery_attempts')
      .delete()
      .eq('user_id', userId),
  ])

  const remaining = codes.length - 1

  await logAuditEvent({
    actorId: userId,
    action: 'auth.mfa_recovery_used',
    targetType: 'user',
    targetId: userId,
    metadata: { remaining_codes: remaining },
    ipAddress: ctx.ipAddress,
    userAgent: ctx.userAgent,
    correlationId: ctx.correlationId,
  })

  return apiSuccess({
    success: true,
    remaining_codes: remaining,
    message: remaining === 0
      ? 'Recovery code accepted. No codes remaining — generate new ones immediately.'
      : `Recovery code accepted. ${remaining} codes remaining.`,
  })
}, { rateLimit: 'strict' }))
