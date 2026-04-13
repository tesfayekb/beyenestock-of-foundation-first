import { createContext, useContext, useEffect, useState, useCallback, type ReactNode } from 'react';
import type { User, Session, AuthError } from '@supabase/supabase-js';
import { useQueryClient } from '@tanstack/react-query';
import { supabase } from '@/integrations/supabase/client';
import {
  emitSignedUp,
  emitSignedIn,
  emitSignedOut,
  emitFailedAttempt,
  emitPasswordReset,
} from '@/lib/auth-events';

type MfaStatus = 'none' | 'enrolled' | 'challenge_required';

interface AuthState {
  user: User | null;
  session: Session | null;
  loading: boolean;
  mfaStatus: MfaStatus;
}

interface AuthContextType extends AuthState {
  signUp: (email: string, password: string, displayName?: string, captchaToken?: string) => Promise<{ error: AuthError | null }>;
  signIn: (email: string, password: string, captchaToken?: string) => Promise<{ error: AuthError | null; mfaChallengeRequired?: boolean }>;
  signOut: () => Promise<void>;
  resetPassword: (email: string) => Promise<{ error: AuthError | null }>;
  updatePassword: (password: string) => Promise<{ error: AuthError | null }>;
  checkMfaStatus: () => Promise<MfaStatus>;
  completeMfaChallenge: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

/**
 * Derive MFA status from the session's AAL claim — zero network calls.
 * Falls back to the SDK call only when needed for challenge detection.
 */
function deriveMfaStatusFromSession(session: Session | null): MfaStatus {
  if (!session) return 'none';

  const factors = session.user?.factors;
  const hasVerifiedTotpFactor = factors?.some(
    f => f.factor_type === 'totp' && f.status === 'verified'
  );

  if (!hasVerifiedTotpFactor) return 'none';

  // Parse the JWT to read the aal claim — it's not exposed on the Session object
  try {
    const payload = JSON.parse(atob(session.access_token.split('.')[1]));
    if (payload.aal === 'aal2') return 'enrolled';
  } catch {
    // If JWT parsing fails, fall back to amr array check
    const amr = (session as unknown as { amr?: Array<{ method: string }> }).amr;
    if (amr?.some(a => a.method === 'totp')) return 'enrolled';
  }

  // Has factor but session is aal1 → needs challenge
  return 'challenge_required';
}

/**
 * Full SDK MFA check — used only for sign-in verification where
 * we need the authoritative server state.
 */
async function getMfaStatusFromSdk(): Promise<MfaStatus> {
  const { data, error } = await supabase.auth.mfa.getAuthenticatorAssuranceLevel();
  if (error || !data) return 'none';

  if (data.currentLevel === 'aal1' && data.nextLevel === 'aal2') {
    return 'challenge_required';
  }
  if (data.currentLevel === 'aal2') {
    return 'enrolled';
  }
  return 'none';
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [state, setState] = useState<AuthState>({
    user: null,
    session: null,
    loading: true,
    mfaStatus: 'none',
  });

  const updateMfaStatus = useCallback(async () => {
    const status = await getMfaStatusFromSdk();
    setState(prev => ({ ...prev, mfaStatus: status }));
    return status;
  }, []);

  useEffect(() => {
    let isMounted = true;

    const syncAuthState = (session: Session | null) => {
      const mfaStatus = deriveMfaStatusFromSession(session);

      if (isMounted) {
        setState({
          user: session?.user ?? null,
          session,
          loading: false,
          mfaStatus,
        });
      }
    };

    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      window.setTimeout(() => {
        // GAP 12: Purge stale cached data when session is lost (token expiry, forced revocation)
        if (event === 'SIGNED_OUT' || (event === 'TOKEN_REFRESHED' && !session)) {
          queryClient.clear();
        }
        syncAuthState(session);
      }, 0);
    });

    void supabase.auth.getSession()
      .then(({ data: { session } }) => syncAuthState(session))
      .catch(() => {
        if (isMounted) {
          setState({ user: null, session: null, loading: false, mfaStatus: 'none' });
        }
      });

    return () => {
      isMounted = false;
      subscription.unsubscribe();
    };
  }, []);

  const signUp = useCallback(async (email: string, password: string, displayName?: string, captchaToken?: string) => {
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        data: { display_name: displayName },
        emailRedirectTo: window.location.origin,
        captchaToken,
      },
    });

    if (!error && data.user) {
      emitSignedUp(data.user.id, 'email');
    }

    return { error };
  }, []);

  const signIn = useCallback(async (email: string, password: string, captchaToken?: string) => {
    const { data, error } = await supabase.auth.signInWithPassword({ email, password, options: { captchaToken } });

    if (error) {
      const reason = error.message?.toLowerCase().includes('invalid')
        ? 'invalid_password'
        : 'unknown_user';
      emitFailedAttempt(reason as 'invalid_password' | 'unknown_user');
      return { error, mfaChallengeRequired: false };
    }

    if (data.user) {
      emitSignedIn(data.user.id, 'password');
    }

    // After sign-in, use SDK for authoritative MFA state
    const status = await getMfaStatusFromSdk();
    setState(prev => ({ ...prev, mfaStatus: status }));
    return { error: null, mfaChallengeRequired: status === 'challenge_required' };
  }, []);

  const signOut = useCallback(async () => {
    const userId = state.user?.id;
    queryClient.clear();
    // GAP 5: Global session termination — revokes all refresh tokens across all devices
    await supabase.auth.signOut({ scope: 'global' });
    if (userId) {
      emitSignedOut(userId);
    }
  }, [state.user?.id, queryClient]);

  const resetPassword = useCallback(async (email: string) => {
    const { error } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}/reset-password`,
    });
    if (!error) {
      emitPasswordReset('unknown', 'requested');
    }
    return { error };
  }, []);

  const updatePassword = useCallback(async (password: string) => {
    const { error } = await supabase.auth.updateUser({ password });
    if (!error && state.user) {
      emitPasswordReset(state.user.id, 'completed');
      // GAP 8: Revoke all other sessions after password change to prevent
      // compromised sessions from remaining active
      await supabase.auth.signOut({ scope: 'others' });
    }
    return { error };
  }, [state.user]);

  const completeMfaChallenge = useCallback(() => {
    setState(prev => ({ ...prev, mfaStatus: 'enrolled' }));
  }, []);

  return (
    <AuthContext.Provider value={{
      ...state,
      signUp,
      signIn,
      signOut,
      resetPassword,
      updatePassword,
      checkMfaStatus: updateMfaStatus,
      completeMfaChallenge,
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
