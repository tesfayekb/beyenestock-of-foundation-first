import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';

export interface RoleListItem {
  id: string;
  key: string;
  name: string;
  description: string | null;
  is_base: boolean;
  is_immutable: boolean;
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

export function useRoles(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: ['admin', 'roles'],
    queryFn: () => apiClient.get<RoleListItem[]>('list-roles'),
    staleTime: 30_000,
    enabled: options?.enabled ?? true,
  });
}

export function useRoleDetail(roleId: string | undefined) {
  return useQuery({
    queryKey: ['admin', 'role', roleId],
    queryFn: () => apiClient.get<RoleDetail>('get-role-detail', { role_id: roleId }),
    enabled: !!roleId,
    staleTime: 30_000,
  });
}

export function usePermissions() {
  return useQuery({
    queryKey: ['admin', 'permissions'],
    queryFn: () => apiClient.get<PermissionListItem[]>('list-permissions'),
    staleTime: 30_000,
  });
}
