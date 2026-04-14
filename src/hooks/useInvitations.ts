/**
 * useInvitations — List, revoke, and resend invitations.
 *
 * Owner: user-onboarding module
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { useToast } from '@/hooks/use-toast';

export interface Invitation {
  id: string;
  email: string;
  status: string;
  role_id: string | null;
  role_name: string | null;
  invited_by: string;
  invited_by_name: string | null;
  created_at: string;
  expires_at: string;
  accepted_at: string | null;
}

interface InvitationsResponse {
  data: {
    invitations: Invitation[];
    total: number;
    limit: number;
    offset: number;
  };
}

export const INVITATIONS_KEY = ['admin', 'invitations'] as const;

export function useInvitations(params?: {
  status?: string;
  limit?: number;
  offset?: number;
}) {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const query = useQuery({
    queryKey: [...INVITATIONS_KEY, params],
    queryFn: async () => {
      const queryParams: Record<string, string | number | undefined> = {};
      if (params?.status && params.status !== 'all') queryParams.status = params.status;
      if (params?.limit) queryParams.limit = params.limit;
      if (params?.offset) queryParams.offset = params.offset;
      const res = await apiClient.get<InvitationsResponse>('list-invitations', queryParams);
      return res.data;
    },
    staleTime: 30_000,
  });

  const revokeMutation = useMutation({
    mutationFn: async (invitationId: string) => {
      return apiClient.post('revoke-invitation', { invitation_id: invitationId });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [...INVITATIONS_KEY] });
      toast({ title: 'Invitation revoked' });
    },
    onError: (error: Error) => {
      toast({ variant: 'destructive', title: 'Revoke failed', description: error.message });
    },
  });

  const resendMutation = useMutation({
    mutationFn: async (invitationId: string) => {
      return apiClient.post('resend-invitation', { invitation_id: invitationId });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [...INVITATIONS_KEY] });
      toast({ title: 'Invitation resent', description: 'A new invitation email has been sent.' });
    },
    onError: (error: Error) => {
      toast({ variant: 'destructive', title: 'Resend failed', description: error.message });
    },
  });

  return {
    invitations: query.data?.invitations ?? [],
    total: query.data?.total ?? 0,
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
    revokeInvitation: revokeMutation.mutateAsync,
    isRevoking: revokeMutation.isPending,
    resendInvitation: resendMutation.mutateAsync,
    isResending: resendMutation.isPending,
  };
}
