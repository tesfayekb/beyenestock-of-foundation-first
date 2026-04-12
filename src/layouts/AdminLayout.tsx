import { useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { DashboardLayout } from './DashboardLayout';
import { adminNavigation } from '@/config/admin-navigation';
import { RequireAuth } from '@/components/auth/RequireAuth';
import { RequirePermission } from '@/components/auth/RequirePermission';
import { AccessDenied } from '@/components/dashboard/AccessDenied';
import { Outlet, Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { ROUTES } from '@/config/routes';
import { ROLES_QUERY_KEY, rolesQueryFn, PERMISSIONS_QUERY_KEY, permissionsQueryFn } from '@/hooks/useRoles';
import { apiClient } from '@/lib/api-client';

/**
 * AdminLayout renders the shell unconditionally (sidebar + header),
 * then permission-gates the content area.
 * AccessDenied renders INSIDE the shell so navigation remains usable.
 *
 * MFA enforcement: admins without MFA enrolled are redirected to /mfa-enroll.
 * This is independent of RequireAuth's challenge_required check — it catches
 * the case where MFA has never been set up at all.
 */
export function AdminLayout() {
  const { mfaStatus, user } = useAuth();
  const location = useLocation();
  const queryClient = useQueryClient();
  const returnTo = `${location.pathname}${location.search}${location.hash}`;

  // Prefetch core admin data sets on layout mount so child pages render instantly
  useEffect(() => {
    if (!user) return;
    queryClient.prefetchQuery({ queryKey: [...ROLES_QUERY_KEY], queryFn: rolesQueryFn, staleTime: 5 * 60 * 1000 });
    queryClient.prefetchQuery({ queryKey: [...PERMISSIONS_QUERY_KEY], queryFn: permissionsQueryFn, staleTime: 5 * 60 * 1000 });
    queryClient.prefetchQuery({
      queryKey: ['admin', 'users', { limit: 25, offset: 0 }],
      queryFn: () => apiClient.get('list-users', { limit: 25, offset: 0 }),
      staleTime: 30_000,
    });
  }, [user, queryClient]);

  return (
    <RequireAuth>
      <RequireMfaForAdmin mfaStatus={mfaStatus} returnTo={returnTo}>
        <DashboardLayout sections={adminNavigation} title="Admin Console">
          <RequirePermission
            permission="admin.access"
            fallback={<AccessDenied message="You need admin access to view this page." />}
          >
            <Outlet />
          </RequirePermission>
        </DashboardLayout>
      </RequireMfaForAdmin>
    </RequireAuth>
  );
}

/**
 * Redirects to MFA enrollment if admin user has no MFA factors enrolled.
 * mfaStatus === 'none' means the user has never set up MFA.
 * RequireAuth already handles 'challenge_required' (enrolled but not verified).
 */
function RequireMfaForAdmin({
  mfaStatus,
  returnTo,
  children,
}: {
  mfaStatus: string;
  returnTo: string;
  children: React.ReactNode;
}) {
  if (mfaStatus === 'none') {
    return <Navigate to={ROUTES.MFA_ENROLL} replace state={{ returnTo }} />;
  }
  return <>{children}</>;
}
