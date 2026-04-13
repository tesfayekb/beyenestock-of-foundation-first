import { useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { DashboardLayout } from './DashboardLayout';
import { userNavigation } from '@/config/user-navigation';
import { RequireAuth } from '@/components/auth/RequireAuth';
import { Outlet, Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { useUserRoles } from '@/hooks/useUserRoles';
import { PROFILE_KEY, profileQueryFn } from '@/hooks/useProfile';
import { MFA_FACTORS_KEY, mfaFactorsQueryFn } from '@/hooks/useMfaFactors';
import { ROUTES } from '@/config/routes';

/**
 * UserLayout renders the shell with RequireAuth.
 * Prefetches profile and MFA factors so child pages render instantly.
 *
 * GAP 6: If the user holds admin.access permission, MFA is enforced
 * here too — prevents admins from bypassing MFA via the user dashboard.
 */
export function UserLayout() {
  const { user, mfaStatus } = useAuth();
  const queryClient = useQueryClient();
  const location = useLocation();
  const { permissions } = useUserRoles();

  useEffect(() => {
    if (!user) return;
    queryClient.prefetchQuery({ queryKey: [...PROFILE_KEY], queryFn: profileQueryFn, staleTime: 30_000 });
    queryClient.prefetchQuery({ queryKey: [...MFA_FACTORS_KEY], queryFn: mfaFactorsQueryFn, staleTime: 30_000 });
  }, [user, queryClient]);

  // GAP 6: Enforce MFA for users who hold admin.access permission
  const hasAdminAccess = permissions.includes('admin.access');
  if (hasAdminAccess && mfaStatus === 'none') {
    const returnTo = `${location.pathname}${location.search}${location.hash}`;
    return (
      <RequireAuth>
        <Navigate to={ROUTES.MFA_ENROLL} replace state={{ returnTo }} />
      </RequireAuth>
    );
  }

  return (
    <RequireAuth>
      <DashboardLayout sections={userNavigation}>
        <Outlet />
      </DashboardLayout>
    </RequireAuth>
  );
}
