import { PageHeader } from '@/components/dashboard/PageHeader';

export default function SecurityPage() {
  return (
    <div className="space-y-6">
      <PageHeader title="Security" subtitle="MFA, sessions, and account security" />
      <p className="text-sm text-muted-foreground">
        Security settings will be implemented in Stage 4E.
      </p>
    </div>
  );
}
