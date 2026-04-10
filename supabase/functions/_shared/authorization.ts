/**
 * Server-side authorization helpers.
 *
 * checkPermissionOrThrow — Default authorization primitive (permission-first)
 * requireSelfScope — Self-scope enforcement (actor derived internally)
 * requireRole — Rare infrastructure gating only
 * requireRecentAuth — Sensitive action guard
 *
 * All are fail-secure: deny on error.
 * All are server-side only — client-side checks are UX-only.
 */
import { supabaseAdmin } from './supabase-admin.ts'

// ─── checkPermissionOrThrow ─────────────────────────────────────────

/**
 * Default server-side authorization primitive.
 * Checks has_permission() SQL security definer function.
 * Throws PermissionDeniedError (403) on denial.
 *
 * Used by: ALL Phase 3+ business edge functions.
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
      permissionKey
    )
  }
}

// ─── requireSelfScope ───────────────────────────────────────────────

/**
 * Enforces that the authenticated actor matches the target resource owner.
 * Actor is derived from the actorUserId passed by the caller
 * (which comes from authenticateRequest — not from client input).
 *
 * Single-param variant: actorUserId is passed from authenticated context,
 * compared against targetUserId.
 */
export function requireSelfScope(
  actorUserId: string,
  targetUserId: string
): void {
  if (actorUserId !== targetUserId) {
    throw new PermissionDeniedError(
      'Self-scope violation: cannot access another user\'s resource',
      'self_scope'
    )
  }
}

// ─── requireRole ────────────────────────────────────────────────────

/**
 * Rare infrastructure utility — NOT the default authorization primitive.
 * Reserved for coarse administrative gating (e.g., admin panel route access).
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
      roleKey
    )
  }
}

// ─── requireRecentAuth ──────────────────────────────────────────────

/** Default threshold: 5 minutes */
const DEFAULT_RECENT_AUTH_THRESHOLD_MS = 5 * 60 * 1000

/**
 * Verifies user authenticated recently enough for sensitive actions.
 * Fail-secure: throws if unable to determine.
 */
export function requireRecentAuth(
  lastSignInAt: string | undefined,
  thresholdMs: number = DEFAULT_RECENT_AUTH_THRESHOLD_MS
): void {
  if (!lastSignInAt) {
    throw new PermissionDeniedError(
      'Recent authentication required',
      'recent_auth'
    )
  }

  const lastSignIn = new Date(lastSignInAt).getTime()
  const elapsed = Date.now() - lastSignIn

  if (elapsed > thresholdMs) {
    throw new PermissionDeniedError(
      'Session too old for this action — please re-authenticate',
      'recent_auth'
    )
  }
}

// ─── Error class ────────────────────────────────────────────────────

export class PermissionDeniedError extends Error {
  permissionKey: string

  constructor(message: string, permissionKey: string) {
    super(message)
    this.name = 'PermissionDeniedError'
    this.permissionKey = permissionKey
  }
}
