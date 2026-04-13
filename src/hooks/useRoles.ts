import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';

export interface RoleListItem {
  id: string;
  key: string;
  name: string;
  description: string | null;
  is_base: boolean;
  is_immutable: boolean;
  is_permission_locked: boolean;
  created_at: string;
  updated_at: string;
  permission_count: number;
  user_count: number;
}

export interface PermissionListItem {
  id: string;
  key: string;
  description: string | null;
  created_at: string;
  role_names: string[];
}

export interface RoleDetail extends RoleListItem {
  permissions: { id: string; key: string; description: string | null }[];
  users: { id: string; display_name: string | null; assigned_at: string }[];
}

/** Shared query key for role list — used by hooks and prefetch. */
export const ROLES_QUERY_KEY = ['admin', 'roles'] as const;

/** Shared query fn for role list — used by hooks and prefetch. */
export const rolesQueryFn = () => apiClient.get<RoleListItem[]>('list-roles');

export function useRoles(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: ROLES_QUERY_KEY,
    queryFn: rolesQueryFn,
    staleTime: 5 * 60 * 1000,
    enabled: options?.enabled ?? true,
  });
}

export function useRoleDetail(roleId: string | undefined) {
  return useQuery({
    queryKey: ['admin', 'role', roleId],
    queryFn: () => apiClient.get<RoleDetail>('get-role-detail', { role_id: roleId }),
    enabled: !!roleId,
    staleTime: 5 * 60 * 1000,
  });
}

/** Shared query key for permissions list — used by hooks and prefetch. */
export const PERMISSIONS_QUERY_KEY = ['admin', 'permissions'] as const;

/** Shared query fn for permissions list — used by hooks and prefetch. */
export const permissionsQueryFn = () => apiClient.get<PermissionListItem[]>('list-permissions');

export function usePermissions() {
  return useQuery({
    queryKey: PERMISSIONS_QUERY_KEY,
    queryFn: permissionsQueryFn,
    staleTime: 5 * 60 * 1000,
  });
}
