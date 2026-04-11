import { DashboardLayout } from './DashboardLayout';
import { adminNavigation } from '@/config/admin-navigation';
import { RequireAuth } from '@/components/auth/RequireAuth';
import { RequirePermission } from '@/components/auth/RequirePermission';
import { AccessDenied } from '@/components/dashboard/AccessDenied';
import { Outlet } from 'react-router-dom';

/**
 * AdminLayout renders the shell unconditionally (sidebar + header),
 * then permission-gates the content area.
 * AccessDenied renders INSIDE the shell so navigation remains usable.
 */
export function AdminLayout() {
  return (
    <RequireAuth>
      <DashboardLayout sections={adminNavigation} title="Admin Console">
        <RequirePermission
          permission="admin.access"
          fallback={<AccessDenied message="You need admin access to view this page." />}
        >
          <Outlet />
        </RequirePermission>
      </DashboardLayout>
    </RequireAuth>
  );
}
