import { createContext, useContext, useEffect, useState, useCallback, type ReactNode } from 'react';
import type { User, Session, AuthError } from '@supabase/supabase-js';
import { supabase } from '@/integrations/supabase/client';

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
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (_event, session) => {
        const base = {
          user: session?.user ?? null,
          session,
          loading: false,
        };

        if (session) {
          const status = await getMfaStatus();
          setState({ ...base, mfaStatus: status });
        } else {
          setState({ ...base, mfaStatus: 'none' });
        }
      }
    );

    supabase.auth.getSession().then(async ({ data: { session } }) => {
      const base = {
        user: session?.user ?? null,
        session,
        loading: false,
      };

      if (session) {
        const status = await getMfaStatus();
        setState({ ...base, mfaStatus: status });
      } else {
        setState({ ...base, mfaStatus: 'none' });
      }
    });

    return () => subscription.unsubscribe();
  }, []);

  const signUp = useCallback(async (email: string, password: string, displayName?: string) => {
    const { error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        data: { display_name: displayName },
        emailRedirectTo: window.location.origin,
      },
    });
    return { error };
  }, []);

  const signIn = useCallback(async (email: string, password: string) => {
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) return { error, mfaChallengeRequired: false };

    const status = await getMfaStatus();
    setState(prev => ({ ...prev, mfaStatus: status }));
    return { error: null, mfaChallengeRequired: status === 'challenge_required' };
  }, []);

  const signOut = useCallback(async () => {
    await supabase.auth.signOut();
  }, []);

  const resetPassword = useCallback(async (email: string) => {
    const { error } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}/reset-password`,
    });
    return { error };
  }, []);

  const updatePassword = useCallback(async (password: string) => {
    const { error } = await supabase.auth.updateUser({ password });
    return { error };
  }, []);

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
