import { useQuery } from '@tanstack/react-query';
import { supabase } from '@/integrations/supabase/client';

export interface UserRoleAssignment {
  id: string;
  role_id: string;
  role_key: string;
  role_name: string;
  assigned_at: string;
}

/**
 * Fetch roles assigned to a specific user.
 * Uses Supabase client with RLS (requires roles.view permission).
 */
async function fetchUserRolesAdmin(userId: string): Promise<UserRoleAssignment[]> {
  const { data, error } = await supabase
    .from('user_roles')
    .select(`
      id,
      role_id,
      assigned_at,
      roles (
        key,
        name
      )
    `)
    .eq('user_id', userId);

  if (error) throw new Error(error.message);

  return (data ?? []).map((ur: any) => ({
    id: ur.id,
    role_id: ur.role_id,
    role_key: ur.roles?.key ?? '',
    role_name: ur.roles?.name ?? '',
    assigned_at: ur.assigned_at,
  }));
}

export function useUserRolesAdmin(userId: string | undefined) {
  return useQuery({
    queryKey: ['admin', 'user-roles', userId],
    queryFn: () => fetchUserRolesAdmin(userId!),
    enabled: !!userId,
    staleTime: 30_000,
  });
}
