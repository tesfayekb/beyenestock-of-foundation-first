import { PageHeader } from '@/components/dashboard/PageHeader';

export default function AdminDashboard() {
  return (
    <div className="space-y-6">
      <PageHeader title="Admin Dashboard" subtitle="System overview and management" />
      <p className="text-sm text-muted-foreground">
        Admin dashboard content will be implemented in Stage 4B.
      </p>
    </div>
  );
}
