/**
 * InvitationsTable — Data table with status filter tabs and actions.
 * When invite system is disabled, resend becomes "Send Signup Reminder".
 *
 * Owner: user-onboarding module
 */
import { useState, useMemo, useCallback } from 'react';
import { DataTable, type DataTableColumn } from '@/components/dashboard/DataTable';
import { InvitationStatusBadge } from '@/components/admin/InvitationStatusBadge';
import { LoadingSkeleton } from '@/components/dashboard/LoadingSkeleton';
import { ErrorState } from '@/components/dashboard/ErrorState';
import { EmptyState } from '@/components/dashboard/EmptyState';
import { Button } from '@/components/ui/button';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ConfirmActionDialog } from '@/components/dashboard/ConfirmActionDialog';
import { useInvitations, type Invitation } from '@/hooks/useInvitations';
import { useUserRoles } from '@/hooks/useUserRoles';
import { checkPermission } from '@/lib/rbac';
import { apiClient } from '@/lib/api-client';
import { useToast } from '@/hooks/use-toast';
import { format } from 'date-fns';
import { RotateCw, Ban, Mail, Send } from 'lucide-react';

const PAGE_SIZE = 50;
const STATUS_TABS = ['all', 'pending', 'accepted', 'expired', 'revoked'] as const;

interface InvitationsTableProps {
  inviteEnabled: boolean;
}

export function InvitationsTable({ inviteEnabled }: InvitationsTableProps) {
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [page, setPage] = useState(1);
  const [confirmAction, setConfirmAction] = useState<{ type: 'revoke' | 'resend' | 'nudge'; id: string; email?: string } | null>(null);
  const [isNudging, setIsNudging] = useState(false);
  const { context } = useUserRoles();
  const { toast } = useToast();
  const canManage = checkPermission(context, 'users.invite.manage');

  const params = useMemo(() => ({
    status: statusFilter,
    page,
    perPage: PAGE_SIZE,
  }), [statusFilter, page]);

  const {
    invitations,
    total,
    isLoading,
    error,
    refetch,
    revokeInvitation,
    isRevoking,
    resendInvitation,
    isResending,
  } = useInvitations(params);

  const handleSendNudge = useCallback(async (invitationId: string) => {
    setIsNudging(true);
    try {
      await apiClient.post('send-signup-nudge', { invitation_id: invitationId });
      toast({ title: 'Signup reminder sent', description: 'The user will receive an email encouraging them to sign up.' });
      refetch();
    } catch (err) {
      toast({ variant: 'destructive', title: 'Failed to send reminder', description: err instanceof Error ? err.message : 'Unknown error' });
    } finally {
      setIsNudging(false);
    }
  }, [toast, refetch]);

  const handleConfirmAction = useCallback(async () => {
    if (!confirmAction) return;
    if (confirmAction.type === 'revoke') {
      await revokeInvitation(confirmAction.id);
    } else if (confirmAction.type === 'resend') {
      await resendInvitation(confirmAction.id);
    } else if (confirmAction.type === 'nudge') {
      await handleSendNudge(confirmAction.id);
    }
    setConfirmAction(null);
  }, [confirmAction, revokeInvitation, resendInvitation, handleSendNudge]);

  const columns: DataTableColumn<Invitation>[] = useMemo(() => {
    const cols: DataTableColumn<Invitation>[] = [
      {
        key: 'email',
        header: 'Email',
        cell: (row) => (
          <span className="font-medium text-sm">{row.email}</span>
        ),
      },
      {
        key: 'status',
        header: 'Status',
        cell: (row) => (
          <InvitationStatusBadge status={row.status} expiresAt={row.expires_at} />
        ),
      },
      {
        key: 'role',
        header: 'Role',
        cell: (row) => (
          <span className="text-sm text-muted-foreground">{row.role_name ?? 'Default'}</span>
        ),
      },
      {
        key: 'invited_by',
        header: 'Invited By',
        cell: (row) => (
          <span className="text-sm text-muted-foreground">{row.invited_by_name ?? 'Unknown'}</span>
        ),
      },
      {
        key: 'created_at',
        header: 'Sent',
        cell: (row) => (
          <span className="text-sm text-muted-foreground">
            {format(new Date(row.created_at), 'MMM d, yyyy')}
          </span>
        ),
      },
      {
        key: 'expires_at',
        header: 'Expires',
        cell: (row) => (
          <span className="text-sm text-muted-foreground">
            {format(new Date(row.expires_at), 'MMM d, yyyy HH:mm')}
          </span>
        ),
      },
    ];

    if (canManage) {
      cols.push({
        key: 'actions',
        header: '',
        cell: (row) => {
          const isPending = row.status === 'pending' && new Date(row.expires_at) >= new Date();
          const isExpiredPending = row.status === 'pending' && new Date(row.expires_at) < new Date();

          if (!isPending && !isExpiredPending) return null;

          return (
            <div className="flex items-center gap-1 justify-end">
              {inviteEnabled ? (
                // Invite enabled: normal resend
                (isPending || isExpiredPending) && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={(e) => { e.stopPropagation(); setConfirmAction({ type: 'resend', id: row.id }); }}
                    title="Resend invitation"
                  >
                    <RotateCw className="h-4 w-4" />
                  </Button>
                )
              ) : (
                // Invite disabled: send signup reminder instead
                (isPending || isExpiredPending) && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={(e) => { e.stopPropagation(); setConfirmAction({ type: 'nudge', id: row.id, email: row.email }); }}
                    title="Send signup reminder"
                  >
                    <Send className="h-4 w-4" />
                  </Button>
                )
              )}
              {isPending && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={(e) => { e.stopPropagation(); setConfirmAction({ type: 'revoke', id: row.id }); }}
                  title="Revoke invitation"
                >
                  <Ban className="h-4 w-4" />
                </Button>
              )}
            </div>
          );
        },
      });
    }

    return cols;
  }, [canManage, inviteEnabled]);

  if (isLoading) return <LoadingSkeleton rows={8} />;
  if (error) return <ErrorState message="Failed to load invitations" onRetry={refetch} />;

  const confirmTitle = confirmAction?.type === 'revoke'
    ? 'Revoke Invitation'
    : confirmAction?.type === 'nudge'
      ? 'Send Signup Reminder'
      : 'Resend Invitation';

  const confirmDescription = confirmAction?.type === 'revoke'
    ? 'This will permanently revoke this invitation. The recipient will no longer be able to use it.'
    : confirmAction?.type === 'nudge'
      ? 'Since the invite system is disabled, this will send a signup reminder email encouraging the user to create an account directly via open signup.'
      : 'This will send a new invitation email with a fresh token and reset the expiry timer.';

  return (
    <div className="space-y-4">
      <Tabs value={statusFilter} onValueChange={(v) => { setStatusFilter(v); setPage(1); }}>
        <TabsList>
          {STATUS_TABS.map((tab) => (
            <TabsTrigger key={tab} value={tab} className="capitalize">
              {tab}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>

      {invitations.length === 0 ? (
        <EmptyState
          icon={Mail}
          title="No invitations"
          description={statusFilter === 'all' ? 'No invitations have been sent yet.' : `No ${statusFilter} invitations.`}
        />
      ) : (
        <DataTable
          columns={columns}
          data={invitations}
          total={total}
          page={page}
          pageSize={PAGE_SIZE}
          onPageChange={setPage}
        />
      )}

      <ConfirmActionDialog
        open={!!confirmAction}
        onOpenChange={(open) => !open && setConfirmAction(null)}
        title={confirmTitle}
        description={confirmDescription}
        confirmLabel={confirmAction?.type === 'revoke' ? 'Revoke' : confirmAction?.type === 'nudge' ? 'Send Reminder' : 'Resend'}
        onConfirm={handleConfirmAction}
        loading={isRevoking || isResending || isNudging}
        destructive={confirmAction?.type === 'revoke'}
      />
    </div>
  );
}
