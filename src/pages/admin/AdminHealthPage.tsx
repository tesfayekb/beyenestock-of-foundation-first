import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { PageHeader } from '@/components/dashboard/PageHeader';
import { StatCard } from '@/components/dashboard/StatCard';
import { LoadingSkeleton } from '@/components/dashboard/LoadingSkeleton';
import { ErrorState } from '@/components/dashboard/ErrorState';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { apiClient } from '@/lib/api-client';
import { supabase } from '@/integrations/supabase/client';
import { Activity, AlertTriangle, CheckCircle, XCircle, Clock, Bell } from 'lucide-react';
import { format } from 'date-fns';

type HealthStatus = 'healthy' | 'degraded' | 'unhealthy';

function statusColor(status: HealthStatus) {
  switch (status) {
    case 'healthy': return 'bg-success/10 text-success border-success/20';
    case 'degraded': return 'bg-warning/10 text-warning border-warning/20';
    case 'unhealthy': return 'bg-destructive/10 text-destructive border-destructive/20';
    default: return 'bg-muted text-muted-foreground';
  }
}

function StatusIcon({ status }: { status: HealthStatus }) {
  switch (status) {
    case 'healthy': return <CheckCircle className="h-4 w-4 text-success" />;
    case 'degraded': return <AlertTriangle className="h-4 w-4 text-warning" />;
    case 'unhealthy': return <XCircle className="h-4 w-4 text-destructive" />;
  }
}

export default function AdminHealthPage() {
  const [tab, setTab] = useState('overview');

  // Fetch latest health snapshot
  const { data: snapshot, isLoading: loadingSnapshot, error: snapshotError } = useQuery({
    queryKey: ['admin', 'health-snapshot'],
    queryFn: async () => {
      const { data, error } = await supabase
        .from('system_health_snapshots')
        .select('*')
        .order('created_at', { ascending: false })
        .limit(1)
        .maybeSingle();
      if (error) throw error;
      return data;
    },
    refetchInterval: 60_000,
  });

  // Fetch recent metrics
  const { data: metrics } = useQuery({
    queryKey: ['admin', 'system-metrics'],
    queryFn: async () => {
      const { data, error } = await supabase
        .from('system_metrics')
        .select('*')
        .order('recorded_at', { ascending: false })
        .limit(50);
      if (error) throw error;
      return data ?? [];
    },
    refetchInterval: 60_000,
  });

  // Fetch alert history
  const { data: alerts } = useQuery({
    queryKey: ['admin', 'alert-history'],
    queryFn: async () => {
      const { data, error } = await supabase
        .from('alert_history')
        .select('*')
        .order('created_at', { ascending: false })
        .limit(20);
      if (error) throw error;
      return data ?? [];
    },
    refetchInterval: 60_000,
  });

  // Fetch alert configs
  const { data: alertConfigs } = useQuery({
    queryKey: ['admin', 'alert-configs'],
    queryFn: async () => {
      const { data, error } = await supabase
        .from('alert_configs')
        .select('*')
        .order('created_at', { ascending: false });
      if (error) throw error;
      return data ?? [];
    },
  });

  const checks = (snapshot?.checks ?? {}) as Record<string, { status: string; latency_ms?: number; error?: string }>;
  const overallStatus = (snapshot?.status ?? 'unknown') as HealthStatus;

  return (
    <div className="space-y-6">
      <PageHeader title="System Health" subtitle="Real-time infrastructure monitoring" />

      {snapshotError ? (
        <ErrorState message="Failed to load health data" />
      ) : loadingSnapshot ? (
        <LoadingSkeleton variant="card" rows={3} />
      ) : (
        <>
          {/* Overall Status */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              title="Overall Status"
              value={overallStatus.charAt(0).toUpperCase() + overallStatus.slice(1)}
              icon={Activity}
            />
            <StatCard
              title="Last Check"
              value={snapshot?.created_at ? format(new Date(snapshot.created_at), 'HH:mm:ss') : '—'}
              icon={Clock}
            />
            <StatCard
              title="Active Alerts"
              value={alerts?.filter(a => !a.resolved_at).length ?? 0}
              icon={AlertTriangle}
            />
            <StatCard
              title="Alert Configs"
              value={alertConfigs?.length ?? 0}
              icon={Bell}
            />
          </div>

          <Tabs value={tab} onValueChange={setTab}>
            <TabsList>
              <TabsTrigger value="overview">Subsystems</TabsTrigger>
              <TabsTrigger value="metrics">Recent Metrics</TabsTrigger>
              <TabsTrigger value="alerts">Alert History</TabsTrigger>
              <TabsTrigger value="config">Alert Config</TabsTrigger>
            </TabsList>

            <TabsContent value="overview" className="mt-4">
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {Object.entries(checks).map(([name, check]) => (
                  <Card key={name}>
                    <CardHeader className="pb-3">
                      <div className="flex items-center justify-between">
                        <CardTitle className="text-sm font-medium capitalize">
                          {name.replace(/_/g, ' ')}
                        </CardTitle>
                        <Badge variant="outline" className={statusColor(check.status as HealthStatus)}>
                          <StatusIcon status={check.status as HealthStatus} />
                          <span className="ml-1">{check.status}</span>
                        </Badge>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <div className="text-xs text-muted-foreground space-y-1">
                        {check.latency_ms != null && (
                          <p>Latency: {check.latency_ms}ms</p>
                        )}
                        {check.error && (
                          <p className="text-destructive">{check.error}</p>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </TabsContent>

            <TabsContent value="metrics" className="mt-4">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Recent Metrics</CardTitle>
                  <CardDescription>Latest 50 metric recordings</CardDescription>
                </CardHeader>
                <CardContent>
                  {metrics && metrics.length > 0 ? (
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b text-left text-xs text-muted-foreground">
                            <th className="pb-2 pr-4">Metric</th>
                            <th className="pb-2 pr-4">Value</th>
                            <th className="pb-2">Recorded</th>
                          </tr>
                        </thead>
                        <tbody>
                          {metrics.map((m) => (
                            <tr key={m.id} className="border-b last:border-0">
                              <td className="py-2 pr-4 font-mono text-xs">{m.metric_key}</td>
                              <td className="py-2 pr-4">{m.value}</td>
                              <td className="py-2 text-muted-foreground text-xs">
                                {format(new Date(m.recorded_at), 'MMM d, HH:mm')}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground">No metrics recorded yet.</p>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="alerts" className="mt-4">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Alert History</CardTitle>
                  <CardDescription>Recent triggered alerts</CardDescription>
                </CardHeader>
                <CardContent>
                  {alerts && alerts.length > 0 ? (
                    <div className="space-y-3">
                      {alerts.map((a) => (
                        <div key={a.id} className="flex items-center justify-between rounded-md border p-3">
                          <div className="space-y-1">
                            <p className="text-sm font-medium">{a.metric_key}</p>
                            <p className="text-xs text-muted-foreground">
                              Value: {a.metric_value} (threshold: {a.threshold_value})
                            </p>
                          </div>
                          <div className="flex items-center gap-2">
                            <Badge variant="outline" className={
                              a.severity === 'critical' ? 'bg-destructive/10 text-destructive border-destructive/20' :
                              a.severity === 'warning' ? 'bg-warning/10 text-warning border-warning/20' :
                              'bg-muted text-muted-foreground'
                            }>
                              {a.severity}
                            </Badge>
                            {a.resolved_at ? (
                              <Badge variant="outline" className="bg-success/10 text-success border-success/20">resolved</Badge>
                            ) : (
                              <Badge variant="outline" className="bg-warning/10 text-warning border-warning/20">active</Badge>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground">No alerts triggered yet.</p>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="config" className="mt-4">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Alert Configurations</CardTitle>
                  <CardDescription>Active monitoring thresholds</CardDescription>
                </CardHeader>
                <CardContent>
                  {alertConfigs && alertConfigs.length > 0 ? (
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b text-left text-xs text-muted-foreground">
                            <th className="pb-2 pr-4">Metric</th>
                            <th className="pb-2 pr-4">Comparison</th>
                            <th className="pb-2 pr-4">Threshold</th>
                            <th className="pb-2 pr-4">Severity</th>
                            <th className="pb-2 pr-4">Cooldown</th>
                            <th className="pb-2">Enabled</th>
                          </tr>
                        </thead>
                        <tbody>
                          {alertConfigs.map((c) => (
                            <tr key={c.id} className="border-b last:border-0">
                              <td className="py-2 pr-4 font-mono text-xs">{c.metric_key}</td>
                              <td className="py-2 pr-4">{c.comparison}</td>
                              <td className="py-2 pr-4">{c.threshold_value}</td>
                              <td className="py-2 pr-4">
                                <Badge variant="outline" className={
                                  c.severity === 'critical' ? 'bg-destructive/10 text-destructive border-destructive/20' :
                                  c.severity === 'warning' ? 'bg-warning/10 text-warning border-warning/20' :
                                  'bg-muted text-muted-foreground'
                                }>{c.severity}</Badge>
                              </td>
                              <td className="py-2 pr-4">{c.cooldown_seconds}s</td>
                              <td className="py-2">
                                <Badge variant="outline" className={c.enabled ? 'bg-success/10 text-success' : 'bg-muted text-muted-foreground'}>
                                  {c.enabled ? 'yes' : 'no'}
                                </Badge>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground">No alert configurations yet.</p>
                  )}
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </>
      )}
    </div>
  );
}
