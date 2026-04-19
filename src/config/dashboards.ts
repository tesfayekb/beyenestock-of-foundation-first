import { Shield, Home, TrendingUp, type LucideIcon } from 'lucide-react';
import type { AuthorizationContext } from '@/lib/rbac';
import { checkPermission } from '@/lib/rbac';

export interface DashboardEntry {
  id: string;
  label: string;
  icon: LucideIcon;
  basePath: string;
  /** Permission required to see this dashboard. null = always visible. */
  permission: string | null;
}

export const dashboards: DashboardEntry[] = [
  { id: 'admin', label: 'Admin Console', icon: Shield, basePath: '/admin', permission: 'admin.access' },
  { id: 'trading', label: 'Trading Console', icon: TrendingUp, basePath: '/trading', permission: 'trading.view' },
  { id: 'user', label: 'My Dashboard', icon: Home, basePath: '/dashboard', permission: null },
];

/** Returns dashboards the current user is allowed to see. */
export function getAvailableDashboards(context: AuthorizationContext): DashboardEntry[] {
  return dashboards.filter(
    (d) => d.permission === null || checkPermission(context, d.permission),
  );
}
