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
  signUp: (email: string, password: string, displayName?: string) => Promise<{ error: AuthError | null }>;
  signIn: (email: string, password: string) => Promise<{ error: AuthError | null; mfaChallengeRequired?: boolean }>;
  signOut: () => Promise<void>;
  resetPassword: (email: string) => Promise<{ error: AuthError | null }>;
  updatePassword: (password: string) => Promise<{ error: AuthError | null }>;
  checkMfaStatus: () => Promise<MfaStatus>;
  completeMfaChallenge: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

async function getMfaStatus(): Promise<MfaStatus> {
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
    const status = await getMfaStatus();
    setState(prev => ({ ...prev, mfaStatus: status }));
    return status;
  }, []);

  useEffect(() => {
    let isMounted = true;

    const syncAuthState = async (session: Session | null) => {
      const base = {
        user: session?.user ?? null,
        session,
        loading: false,
      };

      if (!session) {
        if (isMounted) {
          setState({ ...base, mfaStatus: 'none' });
        }
        return;
      }

      const status = await getMfaStatus();

      if (isMounted) {
        setState({ ...base, mfaStatus: status });
      }
    };

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      window.setTimeout(() => {
        void syncAuthState(session);
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

  const signUp = useCallback(async (email: string, password: string, displayName?: string) => {
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        data: { display_name: displayName },
        emailRedirectTo: window.location.origin,
      },
    });

    if (!error && data.user) {
      emitSignedUp(data.user.id, 'email');
    }

    return { error };
  }, []);

  const signIn = useCallback(async (email: string, password: string) => {
    const { data, error } = await supabase.auth.signInWithPassword({ email, password });

    if (error) {
      // Determine failure reason for event emission
      const reason = error.message?.toLowerCase().includes('invalid')
        ? 'invalid_password'
        : 'unknown_user';
      emitFailedAttempt(reason as 'invalid_password' | 'unknown_user');
      return { error, mfaChallengeRequired: false };
    }

    if (data.user) {
      emitSignedIn(data.user.id, 'password');
    }

    const status = await getMfaStatus();
    setState(prev => ({ ...prev, mfaStatus: status }));
    return { error: null, mfaChallengeRequired: status === 'challenge_required' };
  }, []);

  const signOut = useCallback(async () => {
    const userId = state.user?.id;
    queryClient.clear(); // Prevent cross-user data flash on shared devices
    await supabase.auth.signOut();
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
