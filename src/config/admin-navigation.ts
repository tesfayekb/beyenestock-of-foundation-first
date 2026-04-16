import { LayoutDashboard, Users, Shield, Key, FileText, Activity, Cog, UserPlus, HeartPulse, Radio, TrendingUp, Zap, BarChart2, Settings2 } from 'lucide-react';
import type { NavSection } from './navigation.types';
import { ROUTES } from './routes';

export const adminNavigation: NavSection[] = [
  {
    label: 'Overview',
    items: [
      {
        title: 'Dashboard',
        url: ROUTES.ADMIN,
        icon: LayoutDashboard,
        permission: 'admin.access',
      },
    ],
  },
  {
    label: 'User Management',
    items: [
      {
        title: 'Users',
        url: ROUTES.ADMIN_USERS,
        icon: Users,
        permission: 'users.view_all',
      },
      {
        title: 'Invitations',
        url: ROUTES.ADMIN_ONBOARDING,
        icon: UserPlus,
        permission: 'users.invite',
      },
    ],
  },
  {
    label: 'Access Control',
    items: [
      {
        title: 'Roles',
        url: ROUTES.ADMIN_ROLES,
        icon: Shield,
        permission: 'roles.view',
      },
      {
        title: 'Permissions',
        url: ROUTES.ADMIN_PERMISSIONS,
        icon: Key,
        permission: 'permissions.view',
      },
    ],
  },
  {
    label: 'Operations',
    items: [
      {
        title: 'System Health',
        url: ROUTES.ADMIN_HEALTH,
        icon: Activity,
        permission: 'monitoring.view',
      },
      {
        title: 'Jobs',
        url: ROUTES.ADMIN_JOBS,
        icon: Cog,
        permission: 'jobs.view',
      },
    ],
  },
  {
    label: 'Trading System',
    items: [
      {
        title: 'War Room',
        url: ROUTES.ADMIN_TRADING_WARROOM,
        icon: Radio,
        permission: 'trading.view',
      },
      {
        title: 'Positions',
        url: ROUTES.ADMIN_TRADING_POSITIONS,
        icon: TrendingUp,
        permission: 'trading.view',
      },
      {
        title: 'Signals',
        url: ROUTES.ADMIN_TRADING_SIGNALS,
        icon: Zap,
        permission: 'trading.view',
      },
      {
        title: 'Performance',
        url: ROUTES.ADMIN_TRADING_PERFORMANCE,
        icon: BarChart2,
        permission: 'trading.view',
      },
      {
        title: 'Engine Health',
        url: ROUTES.ADMIN_TRADING_HEALTH,
        icon: HeartPulse,
        permission: 'trading.view',
      },
      {
        title: 'Config',
        url: ROUTES.ADMIN_TRADING_CONFIG,
        icon: Settings2,
        permission: 'trading.configure',
      },
    ],
  },
  {
    label: 'Compliance',
    items: [
      {
        title: 'Audit Logs',
        url: ROUTES.ADMIN_AUDIT,
        icon: FileText,
        permission: 'audit.view',
      },
    ],
  },
];
