import { DashboardLayout } from './DashboardLayout';
import { userNavigation } from '@/config/user-navigation';
import { RequireAuth } from '@/components/auth/RequireAuth';

export function UserLayout() {
  return (
    <RequireAuth>
      <DashboardLayout sections={userNavigation} />
    </RequireAuth>
  );
}
