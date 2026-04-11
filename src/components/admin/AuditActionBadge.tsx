import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

type ActionCategory = 'auth' | 'user' | 'role' | 'permission' | 'audit' | 'system';

interface AuditActionBadgeProps {
  action: string;
}

function categorizeAction(action: string): ActionCategory {
  if (action.startsWith('auth.') || action.startsWith('login') || action.startsWith('logout')) return 'auth';
  if (action.startsWith('user.')) return 'user';
  if (action.startsWith('role.')) return 'role';
  if (action.startsWith('permission.')) return 'permission';
  if (action.startsWith('audit.')) return 'audit';
  return 'system';
}

const categoryStyles: Record<ActionCategory, string> = {
  auth: 'bg-info/10 text-info border-info/20 hover:bg-info/10',
  user: 'bg-primary/10 text-primary border-primary/20 hover:bg-primary/10',
  role: 'bg-warning/10 text-warning border-warning/20 hover:bg-warning/10',
  permission: 'bg-accent text-accent-foreground border-border hover:bg-accent',
  audit: 'bg-success/10 text-success border-success/20 hover:bg-success/10',
  system: 'bg-muted text-muted-foreground border-border hover:bg-muted',
};

/**
 * Renders an audit action string as a color-coded badge.
 * Categories: auth, user, role, permission, audit, system.
 * Denial events (*.denied) use destructive styling.
 */
export function AuditActionBadge({ action }: AuditActionBadgeProps) {
  const isDenied = action.endsWith('.denied') || action.endsWith('.failed');
  const category = categorizeAction(action);

  const style = isDenied
    ? 'bg-destructive/10 text-destructive border-destructive/20 hover:bg-destructive/10'
    : categoryStyles[category];

  return (
    <Badge variant="outline" className={cn('font-mono text-xs font-medium', style)}>
      {action}
    </Badge>
  );
}
