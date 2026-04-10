import { LayoutDashboard, Users, Shield, Key, FileText } from 'lucide-react';
import type { NavSection } from './navigation.types';

export const adminNavigation: NavSection[] = [
  {
    label: 'Overview',
    items: [
      {
        title: 'Dashboard',
        url: '/admin',
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
        url: '/admin/users',
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
        url: '/admin/roles',
        icon: Shield,
        permission: 'roles.view',
      },
      {
        title: 'Permissions',
        url: '/admin/permissions',
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
        url: '/admin/audit',
        icon: FileText,
        permission: 'audit.view',
      },
    ],
  },
];
