/**
 * InvitationStatusBadge — Reusable badge for invitation statuses.
 * Computes virtual 'expired' for pending invitations past TTL.
 *
 * Owner: user-onboarding module
 */
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

type InvitationStatus = 'pending' | 'accepted' | 'expired' | 'revoked';

interface InvitationStatusBadgeProps {
  status: string;
  expiresAt: string;
}

function computeStatus(status: string, expiresAt: string): InvitationStatus {
  if (status === 'pending' && new Date(expiresAt) < new Date()) {
    return 'expired';
  }
  return status as InvitationStatus;
}

const statusStyles: Record<InvitationStatus, string> = {
  pending: 'bg-warning/10 text-warning border-warning/20',
  accepted: 'bg-success/10 text-success border-success/20',
  expired: 'bg-muted text-muted-foreground border-border',
  revoked: 'bg-destructive/10 text-destructive border-destructive/20',
};

const statusLabels: Record<InvitationStatus, string> = {
  pending: 'Pending',
  accepted: 'Accepted',
  expired: 'Expired',
  revoked: 'Revoked',
};

export function InvitationStatusBadge({ status, expiresAt }: InvitationStatusBadgeProps) {
  const computed = computeStatus(status, expiresAt);
  return (
    <Badge variant="outline" className={cn('font-medium', statusStyles[computed])}>
      {statusLabels[computed]}
    </Badge>
  );
}

export { computeStatus };
