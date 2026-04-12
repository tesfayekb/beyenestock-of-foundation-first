import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { toast } from 'sonner';

interface AssignRoleParams {
  target_user_id: string;
  role_id: string;
}

interface RevokeRoleParams {
  target_user_id: string;
  role_id: string;
}

interface AssignPermissionParams {
  role_id: string;
  permission_id: string;
}

interface RevokePermissionParams {
  role_id: string;
  permission_id: string;
}

interface DeleteRoleParams {
  role_id: string;
  reason: string;
}

interface UpdateRoleParams {
  role_id: string;
  name?: string;
  description?: string;
}

interface AssignPermissionResult {
  success: boolean;
  correlation_id: string;
  message: string;
  auto_added_dependencies?: string[];
}

export function useAssignRole() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (params: AssignRoleParams) => apiClient.post('assign-role', params),
    onSuccess: (_data, variables) => {
      toast.success('Role assigned successfully');
      queryClient.invalidateQueries({ queryKey: ['admin', 'user-roles', variables.target_user_id] });
      queryClient.invalidateQueries({ queryKey: ['admin', 'roles'] });
      queryClient.invalidateQueries({ queryKey: ['admin', 'role'] });
      queryClient.invalidateQueries({ queryKey: ['admin', 'users'] });
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to assign role');
    },
  });
}

export function useRevokeRole() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (params: RevokeRoleParams) => apiClient.post('revoke-role', params),
    onSuccess: (_data, variables) => {
      toast.success('Role revoked successfully');
      queryClient.invalidateQueries({ queryKey: ['admin', 'user-roles', variables.target_user_id] });
      queryClient.invalidateQueries({ queryKey: ['admin', 'roles'] });
      queryClient.invalidateQueries({ queryKey: ['admin', 'role'] });
      queryClient.invalidateQueries({ queryKey: ['admin', 'users'] });
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to revoke role');
    },
  });
}

export function useAssignPermission() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (params: AssignPermissionParams) =>
      apiClient.post<AssignPermissionResult>('assign-permission-to-role', params),
    onSuccess: (data, variables) => {
      const deps = data.auto_added_dependencies ?? [];
      if (deps.length > 0) {
        toast.success(`Permission assigned. Also enabled dependencies: ${deps.join(', ')}`);
      } else {
        toast.success('Permission assigned successfully');
      }
      queryClient.invalidateQueries({ queryKey: ['admin', 'role', variables.role_id] });
      queryClient.invalidateQueries({ queryKey: ['admin', 'roles'] });
      queryClient.invalidateQueries({ queryKey: ['admin', 'permissions'] });
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to assign permission');
    },
  });
}

export function useRevokePermission() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (params: RevokePermissionParams) => apiClient.post('revoke-permission-from-role', params),
    onSuccess: (_data, variables) => {
      toast.success('Permission revoked successfully');
      queryClient.invalidateQueries({ queryKey: ['admin', 'role', variables.role_id] });
      queryClient.invalidateQueries({ queryKey: ['admin', 'roles'] });
      queryClient.invalidateQueries({ queryKey: ['admin', 'permissions'] });
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to revoke permission');
    },
  });
}

export function useDeleteRole() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (params: DeleteRoleParams) => apiClient.post('delete-role', params),
    onSuccess: () => {
      toast.success('Role deleted successfully');
      queryClient.invalidateQueries({ queryKey: ['admin', 'roles'] });
      queryClient.invalidateQueries({ queryKey: ['admin', 'users'] });
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to delete role');
    },
  });
}

export function useUpdateRole() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (params: UpdateRoleParams) => apiClient.post('update-role', params),
    onSuccess: (_data, variables) => {
      toast.success('Role updated successfully');
      queryClient.invalidateQueries({ queryKey: ['admin', 'role', variables.role_id] });
      queryClient.invalidateQueries({ queryKey: ['admin', 'roles'] });
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to update role');
    },
  });
}
