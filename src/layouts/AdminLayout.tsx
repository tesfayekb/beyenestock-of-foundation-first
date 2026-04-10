import { DashboardLayout } from './DashboardLayout';
import { adminNavigation } from '@/config/admin-navigation';
import { RequireAuth } from '@/components/auth/RequireAuth';
import { RequirePermission } from '@/components/auth/RequirePermission';
import { AccessDenied } from '@/components/dashboard/AccessDenied';

export function AdminLayout() {
  return (
    <RequireAuth>
      <RequirePermission
        permission="admin.access"
        fallback={
          <div className="min-h-screen flex items-center justify-center bg-background">
            <AccessDenied message="You need admin access to view this page." />
          </div>
        }
      >
        <DashboardLayout sections={adminNavigation} />
      </RequirePermission>
    </RequireAuth>
  );
}
