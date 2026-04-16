import { PageHeader } from '@/components/dashboard/PageHeader';

export default function TradingPerformancePage() {
  return (
    <div className="space-y-6">
      <PageHeader title="Performance" subtitle="Rolling metrics and model accuracy — Phase 3B" />
      <p className="text-muted-foreground">
        Full performance charts coming in Phase 3B.
      </p>
    </div>
  );
}
