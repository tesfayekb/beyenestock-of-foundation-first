import { PageHeader } from '@/components/dashboard/PageHeader';
import { EmptyState } from '@/components/dashboard/EmptyState';
import { Key } from 'lucide-react';

export default function AdminPermissionsPage() {
  return (
    <>
      <PageHeader title="Permissions" subtitle="Permission management will be implemented in Stage 4C." />
      <EmptyState icon={Key} title="Coming Soon" description="Permission listing and role-permission assignment will be available here." />
    </>
  );
}
