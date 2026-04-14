/**
 * Auth Shared Functions
 * 
 * Implements shared functions defined in docs/07-reference/function-index.md:
 * - getSessionContext()
 * - requireVerifiedEmail() — component guard
 * - requireRecentAuth() — utility for sensitive actions
 * 
 * getCurrentUser() and requireAuth() are implemented in AuthContext/RequireAuth.
 */

import type { Session, User } from '@supabase/supabase-js';
import { supabase } from '@/integrations/supabase/client';

interface FactorLike {
  status?: string;
  last_challenged_at?: string | null;
}

function getMostRecentAuthAt(user: User | null): number | null {
  if (!user) return null;

  const timestamps: number[] = [];

  if (user.last_sign_in_at) {
    const signInAt = new Date(user.last_sign_in_at).getTime();
    if (Number.isFinite(signInAt)) timestamps.push(signInAt);
  }

  const factors = ((user.factors ?? []) as FactorLike[])
    .filter((factor) => factor.status === 'verified' && factor.last_challenged_at);

  for (const factor of factors) {
    const challengedAt = new Date(factor.last_challenged_at as string).getTime();
    if (Number.isFinite(challengedAt)) timestamps.push(challengedAt);
  }

  return timestamps.length > 0 ? Math.max(...timestamps) : null;
}

// ─── getSessionContext ───────────────────────────────────────────────

export interface SessionContext {
  user: User;
  session: Session;
  accessToken: string;
  expiresAt: number | undefined;
  isEmailVerified: boolean;
  lastSignInAt: string | undefined;
}

/**
 * Returns current session metadata.
 * Fail-secure: returns null if no valid session.
 * 
 * Used by: All modules needing session info.
 */
export async function getSessionContext(): Promise<SessionContext | null> {
  const { data: { session }, error } = await supabase.auth.getSession();
  if (error || !session?.user) return null;

  return {
    user: session.user,
    session,
    accessToken: session.access_token,
    expiresAt: session.expires_at,
    isEmailVerified: !!session.user.email_confirmed_at,
    lastSignInAt: session.user.last_sign_in_at ?? undefined,
  };
}

// ─── requireVerifiedEmail ────────────────────────────────────────────

/**
 * Checks if user's email is verified.
 * Fail-secure: returns false if unable to determine.
 * 
 * Used by: RequireVerifiedEmail component guard.
 */
export function isEmailVerified(user: User | null): boolean {
  if (!user) return false;
  return !!user.email_confirmed_at;
}

// ─── requireRecentAuth ──────────────────────────────────────────────

/** Default threshold: 30 minutes */
const RECENT_AUTH_THRESHOLD_MS = 30 * 60 * 1000;

/**
 * Checks if user authenticated recently enough for sensitive actions.
 * Accepts either a fresh sign-in or a recent verified MFA challenge.
 * Fail-secure: returns false if unable to determine.
 * 
 * Used by: admin-panel, user-panel (password change, email change, MFA disable, account deletion).
 */
export function isRecentlyAuthenticated(
  user: User | null,
  thresholdMs: number = RECENT_AUTH_THRESHOLD_MS
): boolean {
  const mostRecentAuthAt = getMostRecentAuthAt(user);
  if (!mostRecentAuthAt) return false;

  return (Date.now() - mostRecentAuthAt) < thresholdMs;
}

/**
 * Prompts re-authentication when the user has not recently signed in or
 * completed a recent verified MFA challenge.
 */
export function requiresReauthentication(
  user: User | null,
  thresholdMs: number = RECENT_AUTH_THRESHOLD_MS
): boolean {
  return !isRecentlyAuthenticated(user, thresholdMs);
}
