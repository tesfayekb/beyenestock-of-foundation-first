import { PageHeader } from '@/components/dashboard/PageHeader';
import { StatCard } from '@/components/dashboard/StatCard';
import { LoadingSkeleton } from '@/components/dashboard/LoadingSkeleton';
import { ErrorState } from '@/components/dashboard/ErrorState';
import { useUserStats } from '@/hooks/useUserStats';
import { useRoles } from '@/hooks/useRoles';
import { Users, UserCheck, UserX, Shield, ShieldCheck } from 'lucide-react';

export default function AdminDashboard() {
  const { data: stats, isLoading: loadingStats, error: errorStats } = useUserStats();
  const { data: roles, isLoading: loadingRoles } = useRoles();

  // Derive roles breakdown from useRoles() data — warms the ['admin', 'roles'] cache
  const rolesBreakdown = (roles ?? [])
    .filter((r) => r.user_count > 0)
    .sort((a, b) => b.user_count - a.user_count);

  return (
    <div className="space-y-6">
      <PageHeader title="Admin Dashboard" subtitle="System overview and management" />

      {errorStats ? (
        <ErrorState message={errorStats.message || 'Failed to load dashboard stats.'} />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {loadingStats ? (
            <div className="col-span-full">
              <LoadingSkeleton variant="card" rows={4} />
            </div>
          ) : (
            <>
              <StatCard title="Total Users" value={stats?.total ?? 0} icon={Users} />
              <StatCard title="Active Users" value={stats?.active ?? 0} icon={UserCheck} />
              <StatCard title="Deactivated" value={stats?.deactivated ?? 0} icon={UserX} />
              <StatCard
                title="Active Rate"
                value={
                  (stats?.total ?? 0) > 0
                    ? `${Math.round(((stats?.active ?? 0) / (stats?.total ?? 1)) * 100)}%`
                    : '—'
                }
                icon={Shield}
              />
            </>
          )}
        </div>
      )}

      {/* Roles Breakdown */}
      {loadingRoles ? (
        <div>
          <h3 className="mb-3 text-sm font-medium text-muted-foreground">Roles Breakdown</h3>
          <LoadingSkeleton variant="card" rows={3} />
        </div>
      ) : rolesBreakdown.length > 0 ? (
        <div>
          <h3 className="mb-3 text-sm font-medium text-muted-foreground">Roles Breakdown</h3>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {rolesBreakdown.map((r) => (
              <StatCard key={r.key} title={r.name} value={r.user_count} icon={ShieldCheck} />
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}
