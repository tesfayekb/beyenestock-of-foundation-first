import { PageHeader } from '@/components/dashboard/PageHeader';
import { EmptyState } from '@/components/dashboard/EmptyState';
import { Users } from 'lucide-react';

export default function AdminUsersPage() {
  return (
    <>
      <PageHeader title="Users" subtitle="User management will be implemented in Stage 4B." />
      <EmptyState icon={Users} title="Coming Soon" description="User list, detail views, and deactivation flows will be available here." />
    </>
  );
}
