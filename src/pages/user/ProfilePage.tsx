import { PageHeader } from '@/components/dashboard/PageHeader';

export default function ProfilePage() {
  return (
    <div className="space-y-6">
      <PageHeader title="Profile" subtitle="Manage your account settings" />
      <p className="text-sm text-muted-foreground">
        Profile management will be implemented in Stage 4E.
      </p>
    </div>
  );
}
