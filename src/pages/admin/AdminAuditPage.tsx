import { PageHeader } from '@/components/dashboard/PageHeader';
import { EmptyState } from '@/components/dashboard/EmptyState';
import { FileText } from 'lucide-react';

export default function AdminAuditPage() {
  return (
    <>
      <PageHeader title="Audit Logs" subtitle="Audit log viewer will be implemented in Stage 4D." />
      <EmptyState icon={FileText} title="Coming Soon" description="Searchable audit logs with metadata viewer and CSV export will be available here." />
    </>
  );
}
