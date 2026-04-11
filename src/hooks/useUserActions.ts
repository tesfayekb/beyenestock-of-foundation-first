import { useMutation, useQueryClient } from '@tanstack/react-query';
import { getAuthHeaders, getProjectUrl } from '@/lib/api-headers';
import { toast } from 'sonner';

interface UserActionParams {
  user_id: string;
  reason?: string;
}

async function invokeUserAction(functionName: string, params: UserActionParams) {
  const headers = await getAuthHeaders();

  const res = await fetch(`${getProjectUrl()}/functions/v1/${functionName}`, {
    method: 'POST',
    headers: { ...headers, 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error ?? `Action failed (${res.status})`);
  }

  return res.json();
}

export function useDeactivateUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (params: UserActionParams) => invokeUserAction('deactivate-user', params),
    onSuccess: (_data, variables) => {
      toast.success('User deactivated successfully');
      queryClient.invalidateQueries({ queryKey: ['admin', 'users'] });
      queryClient.invalidateQueries({ queryKey: ['admin', 'user', variables.user_id] });
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to deactivate user');
    },
  });
}

export function useReactivateUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (params: UserActionParams) => invokeUserAction('reactivate-user', params),
    onSuccess: (_data, variables) => {
      toast.success('User reactivated successfully');
      queryClient.invalidateQueries({ queryKey: ['admin', 'users'] });
      queryClient.invalidateQueries({ queryKey: ['admin', 'user', variables.user_id] });
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to reactivate user');
    },
  });
}
