import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

type StatusType = 'active' | 'deactivated' | 'pending' | 'info';

interface StatusBadgeProps {
  status: StatusType;
  label?: string;
}

const statusConfig: Record<StatusType, { className: string; defaultLabel: string }> = {
  active: {
    className: 'bg-success/10 text-success border-success/20 hover:bg-success/10',
    defaultLabel: 'Active',
  },
  deactivated: {
    className: 'bg-destructive/10 text-destructive border-destructive/20 hover:bg-destructive/10',
    defaultLabel: 'Deactivated',
  },
  pending: {
    className: 'bg-warning/10 text-warning border-warning/20 hover:bg-warning/10',
    defaultLabel: 'Pending',
  },
  info: {
    className: 'bg-muted text-muted-foreground border-border hover:bg-muted',
    defaultLabel: 'Info',
  },
};

export function StatusBadge({ status, label }: StatusBadgeProps) {
  const config = statusConfig[status] ?? statusConfig.info;

  return (
    <Badge variant="outline" className={cn('font-medium', config.className)}>
      <span className="sr-only">Status: </span>
      {label ?? config.defaultLabel}
    </Badge>
  );
}
