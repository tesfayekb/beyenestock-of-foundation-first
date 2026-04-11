/**
 * useMfaFactors — list and unenroll MFA TOTP factors via Supabase Auth.
 * FINDING-2/4 FIX: Migrated to React Query for consistent caching across navigation.
 */
import { useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { supabase } from '@/integrations/supabase/client';
import { useAuth } from '@/contexts/AuthContext';
import { toast } from 'sonner';

export interface MfaFactor {
  id: string;
  friendly_name?: string;
  factor_type: string;
  status: 'verified' | 'unverified';
  created_at: string;
  updated_at: string;
}

const MFA_FACTORS_KEY = ['mfa', 'factors'] as const;

export function useMfaFactors() {
  const queryClient = useQueryClient();
  const { user } = useAuth();

  const query = useQuery({
    queryKey: MFA_FACTORS_KEY,
    queryFn: async () => {
      const { data, error } = await supabase.auth.mfa.listFactors();
      if (error) throw error;
      return (data?.totp ?? []) as MfaFactor[];
    },
    staleTime: 30_000,
    enabled: !!user,
  });

  const unenrollMutation = useMutation({
    mutationFn: async (factorId: string) => {
      const { error } = await supabase.auth.mfa.unenroll({ factorId });
      if (error) throw error;
      return factorId;
    },
    onSuccess: (factorId) => {
      queryClient.setQueryData(MFA_FACTORS_KEY, (prev: MfaFactor[] | undefined) =>
        prev ? prev.filter((f) => f.id !== factorId) : []
      );
      toast.success('MFA factor removed');
    },
    onError: (err: Error) => {
      toast.error(err.message || 'Failed to remove MFA factor');
    },
  });

  // Backward-compatible listFactors — triggers refetch if stale
  const listFactors = useCallback(() => {
    query.refetch();
  }, [query]);

  const unenrollFactor = useCallback(async (factorId: string) => {
    try {
      await unenrollMutation.mutateAsync(factorId);
      return true;
    } catch {
      return false;
    }
  }, [unenrollMutation]);

  return {
    factors: query.data ?? [],
    loading: query.isLoading,
    unenrolling: unenrollMutation.isPending,
    listFactors,
    unenrollFactor,
  };
}
