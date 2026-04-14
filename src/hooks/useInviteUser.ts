/**
 * useInviteUser — Send single or bulk invitations.
 *
 * Owner: user-onboarding module
 */
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { useToast } from '@/hooks/use-toast';
import { INVITATIONS_KEY } from '@/hooks/useInvitations';

interface InviteUserInput {
  email: string;
  role_id?: string;
  display_name?: string;
}

interface BulkInviteInput {
  emails: string[];
  role_id?: string;
}

interface BulkInviteResult {
  data: {
    succeeded: string[];
    failed: { email: string; reason: string }[];
    skipped_existing: string[];
  };
}

export function useInviteUser() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const inviteMutation = useMutation({
    mutationFn: async (input: InviteUserInput) => {
      return apiClient.post('invite-user', input);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [...INVITATIONS_KEY] });
      toast({ title: 'Invitation sent', description: 'The user will receive an email invitation.' });
    },
    onError: (error: Error) => {
      toast({ variant: 'destructive', title: 'Invite failed', description: error.message });
    },
  });

  const bulkInviteMutation = useMutation({
    mutationFn: async (input: BulkInviteInput) => {
      return apiClient.post<BulkInviteResult>('invite-users-bulk', input);
    },
    onSuccess: (_data) => {
      queryClient.invalidateQueries({ queryKey: [...INVITATIONS_KEY] });
    },
    onError: (error: Error) => {
      toast({ variant: 'destructive', title: 'Bulk invite failed', description: error.message });
    },
  });

  return {
    inviteUser: inviteMutation.mutateAsync,
    isInviting: inviteMutation.isPending,
    bulkInvite: bulkInviteMutation.mutateAsync,
    isBulkInviting: bulkInviteMutation.isPending,
  };
}
