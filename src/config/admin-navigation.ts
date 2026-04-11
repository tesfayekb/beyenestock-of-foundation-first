import { LayoutDashboard, Users, Shield, Key, FileText } from 'lucide-react';
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
        permission: 'roles.view',
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
