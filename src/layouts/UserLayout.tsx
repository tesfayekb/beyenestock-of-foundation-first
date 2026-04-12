import { useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { DashboardLayout } from './DashboardLayout';
import { userNavigation } from '@/config/user-navigation';
import { RequireAuth } from '@/components/auth/RequireAuth';
import { Outlet } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { PROFILE_KEY, profileQueryFn } from '@/hooks/useProfile';
import { MFA_FACTORS_KEY, mfaFactorsQueryFn } from '@/hooks/useMfaFactors';

/**
 * UserLayout renders the shell with RequireAuth.
 * Prefetches profile and MFA factors so child pages render instantly.
 */
export function UserLayout() {
  const { user } = useAuth();
  const queryClient = useQueryClient();

  useEffect(() => {
    if (!user) return;
    queryClient.prefetchQuery({ queryKey: [...PROFILE_KEY], queryFn: profileQueryFn, staleTime: 30_000 });
    queryClient.prefetchQuery({ queryKey: [...MFA_FACTORS_KEY], queryFn: mfaFactorsQueryFn, staleTime: 30_000 });
  }, [user, queryClient]);

  return (
    <RequireAuth>
      <DashboardLayout sections={userNavigation}>
        <Outlet />
      </DashboardLayout>
    </RequireAuth>
  );
}
