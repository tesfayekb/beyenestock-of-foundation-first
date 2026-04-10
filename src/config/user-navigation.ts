import { LayoutDashboard, UserCircle, ShieldCheck } from 'lucide-react';
import type { NavSection } from './navigation.types';

export const userNavigation: NavSection[] = [
  {
    label: 'Account',
    items: [
      {
        title: 'Dashboard',
        url: '/dashboard',
        icon: LayoutDashboard,
      },
      {
        title: 'Profile',
        url: '/settings',
        icon: UserCircle,
        permission: 'profile.self_manage',
      },
      {
        title: 'Security',
        url: '/settings/security',
        icon: ShieldCheck,
        permission: 'mfa.self_manage',
      },
    ],
  },
];
