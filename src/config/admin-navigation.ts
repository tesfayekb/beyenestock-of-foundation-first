import { LayoutDashboard, Users, Shield, Key, FileText, Home, Activity, Cog } from 'lucide-react';
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
  {
    label: 'Account',
    items: [
      {
        title: 'My Dashboard',
        url: ROUTES.DASHBOARD,
        icon: Home,
      },
    ],
  },
];