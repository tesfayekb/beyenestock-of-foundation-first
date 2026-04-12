/**
 * POST /mfa-recovery-generate — Generate MFA recovery codes.
 *
 * Generates 10 recovery codes, hashes them with bcrypt, stores hashes,
 * returns plaintext codes ONCE. Deletes any existing codes for the user.
 *
 * Requires: Bearer JWT + requireRecentAuth(30min)
 * Audit: auth.mfa_recovery_generated
 *
 * Owner: auth module (DW-008)
 */
import { createHandler, apiSuccess } from '../_shared/handler.ts'
import { authenticateRequest } from '../_shared/authenticate-request.ts'
import { requireRecentAuth } from '../_shared/authorization.ts'
import { supabaseAdmin } from '../_shared/supabase-admin.ts'
import { logAuditEvent } from '../_shared/audit.ts'
import { hash } from 'https://deno.land/x/bcrypt@v0.4.1/mod.ts'

function generateCode(): string {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789' // No I/O/0/1 for readability
  let code = ''
  const bytes = new Uint8Array(8)
  crypto.getRandomValues(bytes)
  for (let i = 0; i < 8; i++) {
    code += chars[bytes[i] % chars.length]
  }
  return code
}

Deno.serve(createHandler(async (req: Request): Promise<Response> => {
  const ctx = await authenticateRequest(req)
  requireRecentAuth(ctx.user.lastSignInAt, 30 * 60 * 1000, ctx.user.id)

  const userId = ctx.user.id

  // Generate 10 codes
  const codes: string[] = []
  for (let i = 0; i < 10; i++) {
    codes.push(generateCode())
  }

  // Hash all codes
  const hashes = await Promise.all(
    codes.map(async (code) => {
      const codeHash = await hash(code)
      return { user_id: userId, code_hash: codeHash }
    })
  )

  // Delete existing codes, then insert new ones (atomic-ish via service role)
  await supabaseAdmin
    .from('mfa_recovery_codes')
    .delete()
    .eq('user_id', userId)

  const { error: insertError } = await supabaseAdmin
    .from('mfa_recovery_codes')
    .insert(hashes)

  if (insertError) {
    throw new Error(`Failed to store recovery codes: ${insertError.message}`)
  }

  await logAuditEvent({
    actorId: userId,
    action: 'auth.mfa_recovery_generated',
    targetType: 'user',
    targetId: userId,
    metadata: { code_count: codes.length },
    ipAddress: ctx.ipAddress,
    userAgent: ctx.userAgent,
    correlationId: ctx.correlationId,
  })

  // Return plaintext codes — this is the ONLY time they are shown
  return apiSuccess({
    codes,
    message: 'Save these codes in a safe place. They will not be shown again.',
  })
}, { rateLimit: 'strict' }))
