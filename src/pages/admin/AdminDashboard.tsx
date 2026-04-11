import { PageHeader } from '@/components/dashboard/PageHeader';
import { StatCard } from '@/components/dashboard/StatCard';
import { LoadingSkeleton } from '@/components/dashboard/LoadingSkeleton';
import { ErrorState } from '@/components/dashboard/ErrorState';
import { useUsers } from '@/hooks/useUsers';
import { Users, UserCheck, UserX, Shield } from 'lucide-react';

export default function AdminDashboard() {
  const { data: activeData, isLoading: loadingActive, error: errorActive } = useUsers({ status: 'active', limit: 1 });
  const { data: deactivatedData, isLoading: loadingDeactivated } = useUsers({ status: 'deactivated', limit: 1 });
  const { data: allData, isLoading: loadingAll } = useUsers({ limit: 1 });

  const isLoading = loadingActive || loadingDeactivated || loadingAll;

  if (isLoading) {
    return (
      <div className="space-y-6">
        <PageHeader title="Admin Dashboard" subtitle="System overview and management" />
        <LoadingSkeleton variant="card" rows={4} />
      </div>
    );
  }

  if (errorActive) {
    return (
      <div className="space-y-6">
        <PageHeader title="Admin Dashboard" subtitle="System overview and management" />
        <ErrorState message="Failed to load dashboard stats." />
      </div>
    );
  }

  const totalUsers = allData?.total ?? 0;
  const activeUsers = activeData?.total ?? 0;
  const deactivatedUsers = deactivatedData?.total ?? 0;

  return (
    <div className="space-y-6">
      <PageHeader title="Admin Dashboard" subtitle="System overview and management" />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Users"
          value={totalUsers}
          icon={Users}
        />
        <StatCard
          title="Active Users"
          value={activeUsers}
          icon={UserCheck}
        />
        <StatCard
          title="Deactivated"
          value={deactivatedUsers}
          icon={UserX}
        />
        <StatCard
          title="Active Rate"
          value={totalUsers > 0 ? `${Math.round((activeUsers / totalUsers) * 100)}%` : '—'}
          icon={Shield}
        />
      </div>
    </div>
  );
}
