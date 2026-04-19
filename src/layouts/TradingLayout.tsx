import { useEffect, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Outlet } from 'react-router-dom';
import { DashboardLayout } from './DashboardLayout';
import { tradingNavigation } from '@/config/trading-navigation';
import { RequireAuth } from '@/components/auth/RequireAuth';
import { RequirePermission } from '@/components/auth/RequirePermission';
import { AccessDenied } from '@/components/dashboard/AccessDenied';
import { useAuth } from '@/contexts/AuthContext';
import { USER_ROLES_KEY } from '@/hooks/useUserRoles';
import { supabase } from '@/integrations/supabase/client';

/**
 * TradingLayout — dedicated shell for the Trading Console at /trading/*.
 *
 * Phase 4C: split from AdminLayout so traders without admin.access can
 * still see paper trading data. Gates on trading.view (not admin.access)
 * and does NOT enforce MFA — viewing paper trading data is not an admin
 * operation. Individual pages additionally gate on trading.configure for
 * write operations (the Config page).
 *
 * Prefetches the authorization context so the inner RequirePermission
 * gate renders instantly without a skeleton flash.
 */
export function TradingLayout() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const prefetchedRef = useRef(false);

  if (user && !prefetchedRef.current) {
    prefetchedRef.current = true;
    queryClient.prefetchQuery({
      queryKey: [...USER_ROLES_KEY],
      queryFn: async () => {
        const { data, error } = await supabase.rpc('get_my_authorization_context');
        if (error || !data) {
          return { roles: [], permissions: [], is_superadmin: false };
        }
        const ctx = data as unknown as {
          roles: string[];
          permissions: string[];
          is_superadmin: boolean;
        };
        return {
          roles: ctx.roles ?? [],
          permissions: ctx.permissions ?? [],
          is_superadmin: ctx.is_superadmin ?? false,
        };
      },
      staleTime: 5 * 60 * 1000,
    });
  }

  useEffect(() => {
    prefetchedRef.current = false;
  }, [user?.id]);

  return (
    <RequireAuth>
      <DashboardLayout sections={tradingNavigation} title="Trading Console">
        <RequirePermission
          permission="trading.view"
          fallback={
            <AccessDenied message="You need trading access to view this page." />
          }
        >
          <Outlet />
        </RequirePermission>
      </DashboardLayout>
    </RequireAuth>
  );
}
