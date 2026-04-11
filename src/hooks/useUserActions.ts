import { useMutation, useQueryClient } from '@tanstack/react-query';
import { supabase } from '@/integrations/supabase/client';
import { toast } from 'sonner';

interface UserActionParams {
  user_id: string;
  reason?: string;
}

async function invokeUserAction(functionName: string, params: UserActionParams) {
  const session = (await supabase.auth.getSession()).data.session;
  if (!session) throw new Error('Not authenticated');

  const projectUrl = import.meta.env.VITE_SUPABASE_URL;
  const url = `${projectUrl}/functions/v1/${functionName}`;

  const res = await fetch(url, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${session.access_token}`,
      'apikey': import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY,
      'Content-Type': 'application/json',
    },
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
