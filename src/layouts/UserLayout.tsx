import { DashboardLayout } from './DashboardLayout';
import { userNavigation } from '@/config/user-navigation';
import { RequireAuth } from '@/components/auth/RequireAuth';
import { Outlet } from 'react-router-dom';

/**
 * UserLayout renders the shell with RequireAuth.
 * Individual route-level permissions are enforced in App.tsx via PermissionGate.
 */
export function UserLayout() {
  return (
    <RequireAuth>
      <DashboardLayout sections={userNavigation}>
        <Outlet />
      </DashboardLayout>
    </RequireAuth>
  );
}
