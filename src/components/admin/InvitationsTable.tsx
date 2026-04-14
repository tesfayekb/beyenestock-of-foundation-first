/**
 * InvitationsTable — Data table with status filter tabs and actions.
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
import { format } from 'date-fns';
import { RotateCw, Ban, Mail } from 'lucide-react';

const PAGE_SIZE = 50;
const STATUS_TABS = ['all', 'pending', 'accepted', 'expired', 'revoked'] as const;

export function InvitationsTable() {
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [page, setPage] = useState(1);
  const [confirmAction, setConfirmAction] = useState<{ type: 'revoke' | 'resend'; id: string } | null>(null);
  const { context } = useUserRoles();
  const canManage = checkPermission(context, 'users.invite.manage');

  const params = useMemo(() => ({
    status: statusFilter,
    limit: PAGE_SIZE,
    offset: (page - 1) * PAGE_SIZE,
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

  const handleConfirmAction = useCallback(async () => {
    if (!confirmAction) return;
    if (confirmAction.type === 'revoke') {
      await revokeInvitation(confirmAction.id);
    } else {
      await resendInvitation(confirmAction.id);
    }
    setConfirmAction(null);
  }, [confirmAction, revokeInvitation, resendInvitation]);

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
              {(isPending || isExpiredPending) && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={(e) => { e.stopPropagation(); setConfirmAction({ type: 'resend', id: row.id }); }}
                  title="Resend invitation"
                >
                  <RotateCw className="h-4 w-4" />
                </Button>
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
  }, [canManage]);

  if (isLoading) return <LoadingSkeleton rows={8} />;
  if (error) return <ErrorState message="Failed to load invitations" onRetry={refetch} />;

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
        title={confirmAction?.type === 'revoke' ? 'Revoke Invitation' : 'Resend Invitation'}
        description={
          confirmAction?.type === 'revoke'
            ? 'This will permanently revoke this invitation. The recipient will no longer be able to use it.'
            : 'This will send a new invitation email with a fresh token and reset the expiry timer.'
        }
        confirmLabel={confirmAction?.type === 'revoke' ? 'Revoke' : 'Resend'}
        onConfirm={handleConfirmAction}
        loading={isRevoking || isResending}
        destructive={confirmAction?.type === 'revoke'}
      />
    </div>
  );
}
