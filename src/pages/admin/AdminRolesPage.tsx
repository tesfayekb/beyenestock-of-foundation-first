import { PageHeader } from '@/components/dashboard/PageHeader';
import { EmptyState } from '@/components/dashboard/EmptyState';
import { Shield } from 'lucide-react';

export default function AdminRolesPage() {
  return (
    <>
      <PageHeader title="Roles" subtitle="Role management will be implemented in Stage 4C." />
      <EmptyState icon={Shield} title="Coming Soon" description="Role listing, detail views, and assignment flows will be available here." />
    </>
  );
}
