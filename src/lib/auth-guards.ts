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

/** Default threshold: 5 minutes */
const RECENT_AUTH_THRESHOLD_MS = 5 * 60 * 1000;

/**
 * Checks if user authenticated recently enough for sensitive actions.
 * Fail-secure: returns false if unable to determine.
 * 
 * Used by: admin-panel, user-panel (password change, email change, MFA disable, account deletion).
 */
export function isRecentlyAuthenticated(
  user: User | null,
  thresholdMs: number = RECENT_AUTH_THRESHOLD_MS
): boolean {
  if (!user?.last_sign_in_at) return false;

  const lastSignIn = new Date(user.last_sign_in_at).getTime();
  const now = Date.now();

  return (now - lastSignIn) < thresholdMs;
}

/**
 * Prompts re-authentication via Supabase reauthentication flow.
 * Returns true if user should be prompted to re-authenticate.
 */
export function requiresReauthentication(
  user: User | null,
  thresholdMs: number = RECENT_AUTH_THRESHOLD_MS
): boolean {
  return !isRecentlyAuthenticated(user, thresholdMs);
}
