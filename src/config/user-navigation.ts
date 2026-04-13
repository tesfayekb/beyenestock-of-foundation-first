import { LayoutDashboard, UserCircle, ShieldCheck } from 'lucide-react';
import type { NavSection } from './navigation.types';
import { ROUTES } from './routes';

export const userNavigation: NavSection[] = [
  {
    label: 'Account',
    items: [
      {
        title: 'Dashboard',
        url: ROUTES.DASHBOARD,
        icon: LayoutDashboard,
      },
      {
        title: 'Profile',
        url: ROUTES.SETTINGS,
        icon: UserCircle,
        permission: 'profile.self_manage',
      },
      {
        title: 'Security',
        url: ROUTES.SETTINGS_SECURITY,
        icon: ShieldCheck,
        permission: 'mfa.self_manage',
      },
    ],
  },
];
