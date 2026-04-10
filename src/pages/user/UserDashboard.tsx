import { PageHeader } from '@/components/dashboard/PageHeader';

export default function UserDashboard() {
  return (
    <div className="space-y-6">
      <PageHeader title="Dashboard" subtitle="Welcome back" />
      <p className="text-sm text-muted-foreground">
        Your dashboard content will appear here.
      </p>
    </div>
  );
}
