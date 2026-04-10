/**
 * Server-side authorization helpers.
 *
 * checkPermissionOrThrow — Default authorization primitive (permission-first)
 * requireSelfScope — Self-scope enforcement (actor derived internally)
 * requireRole — Rare infrastructure gating only
 * requireRecentAuth — Sensitive action guard
 *
 * All are fail-secure: deny on error.
 *
 * Enforcement rule: All authorization denials MUST throw PermissionDeniedError.
 * Manual apiError(403, ...) returns from authorization logic are prohibited.
 */
import { supabaseAdmin } from './supabase-admin.ts'
import { PermissionDeniedError } from './errors.ts'

// ─── checkPermissionOrThrow ─────────────────────────────────────────

/**
 * Default server-side authorization primitive.
 * Checks has_permission() SQL security definer function.
 * Throws PermissionDeniedError (403) on denial — includes userId for audit.
 */
export async function checkPermissionOrThrow(
  userId: string,
  permissionKey: string
): Promise<void> {
  const { data, error } = await supabaseAdmin.rpc('has_permission', {
    _user_id: userId,
    _permission_key: permissionKey,
  })

  if (error || data !== true) {
    throw new PermissionDeniedError(
      `Permission denied: ${permissionKey}`,
      permissionKey,
      { userId, reason: 'missing_permission' }
    )
  }
}

// ─── requireSelfScope ───────────────────────────────────────────────

/**
 * Enforces that the authenticated actor matches the target resource owner.
 * Actor is derived internally from the authenticated context — callers
 * only supply the target user ID to prevent misuse.
 */
export function requireSelfScope(
  ctx: { user: { id: string } },
  targetUserId: string
): void {
  if (ctx.user.id !== targetUserId) {
    throw new PermissionDeniedError(
      'Self-scope violation: cannot access another user\'s resource',
      'self_scope',
      { userId: ctx.user.id, reason: 'self_scope_violation' }
    )
  }
}

// ─── requireRole ────────────────────────────────────────────────────

/**
 * Rare infrastructure utility — NOT the default authorization primitive.
 * Use checkPermissionOrThrow() for business endpoints.
 */
export async function requireRole(
  userId: string,
  roleKey: string
): Promise<void> {
  const { data, error } = await supabaseAdmin.rpc('has_role', {
    _user_id: userId,
    _role_key: roleKey,
  })

  if (error || data !== true) {
    throw new PermissionDeniedError(
      `Role required: ${roleKey}`,
      roleKey,
      { userId, reason: 'missing_permission' }
    )
  }
}

// ─── requireRecentAuth ──────────────────────────────────────────────

const DEFAULT_RECENT_AUTH_THRESHOLD_MS = 5 * 60 * 1000

/**
 * Verifies user authenticated recently enough for sensitive actions.
 * Fail-secure: throws if unable to determine.
 */
export function requireRecentAuth(
  lastSignInAt: string | undefined,
  thresholdMs: number = DEFAULT_RECENT_AUTH_THRESHOLD_MS,
  userId?: string
): void {
  if (!lastSignInAt) {
    throw new PermissionDeniedError(
      'Recent authentication required',
      'recent_auth',
      { userId, reason: 'recent_auth_required' }
    )
  }

  const lastSignIn = new Date(lastSignInAt).getTime()
  const elapsed = Date.now() - lastSignIn

  if (elapsed > thresholdMs) {
    throw new PermissionDeniedError(
      'Session too old for this action — please re-authenticate',
      'recent_auth',
      { userId, reason: 'recent_auth_required' }
    )
  }
}

// Re-export for convenience
export { PermissionDeniedError } from './errors.ts'
