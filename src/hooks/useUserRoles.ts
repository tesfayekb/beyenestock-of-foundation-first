import { useQuery } from '@tanstack/react-query';
import { supabase } from '@/integrations/supabase/client';
import { useAuth } from '@/contexts/AuthContext';
import type { AuthorizationContext } from '@/lib/rbac';

interface UseUserRolesResult {
  roles: string[];
  permissions: string[];
  isSuperadmin: boolean;
  loading: boolean;
  context: AuthorizationContext | null;
  refetch: () => Promise<void>;
}

const USER_ROLES_KEY = ['authorization-context'] as const;

/**
 * Fetches the current user's effective authorization context via
 * get_my_authorization_context() RPC. Uses React Query for shared
 * cross-component cache — all call sites share a single RPC call.
 *
 * UX-only — does NOT enforce access. Server-side enforcement is authoritative.
 */
export function useUserRoles(): UseUserRolesResult {
  const { user } = useAuth();

  const query = useQuery({
    queryKey: USER_ROLES_KEY,
    queryFn: async (): Promise<AuthorizationContext> => {
      const { data, error } = await supabase.rpc('get_my_authorization_context');

      if (error || !data) {
        console.error('Failed to fetch authorization context:', error?.message);
        // Fail-secure: return empty context
        return { roles: [], permissions: [], is_superadmin: false };
      }

      const ctx = data as unknown as AuthorizationContext;
      return {
        roles: ctx.roles ?? [],
        permissions: ctx.permissions ?? [],
        is_superadmin: ctx.is_superadmin ?? false,
      };
    },
    enabled: !!user,
    staleTime: 5 * 60 * 1000, // 5 minutes — roles rarely change mid-session
    retry: 2,
  });

  const context = query.data ?? null;

  return {
    roles: context?.roles ?? [],
    permissions: context?.permissions ?? [],
    isSuperadmin: context?.is_superadmin ?? false,
    loading: query.isLoading,
    context,
    refetch: async () => { await query.refetch(); },
  };
}

export { USER_ROLES_KEY };
