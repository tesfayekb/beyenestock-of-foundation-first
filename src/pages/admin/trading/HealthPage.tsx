/**
 * Engine Health — /admin/trading/health
 * Phase 1 deliverable TPLAN-INFRA-001-I
 *
 * SEPARATE from foundation /admin/health.
 * Reads from `trading_system_health` table (NOT `system_health_snapshots`).
 * Refetch interval: 10s ALWAYS (per route-index.md).
 */
import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { formatDistanceToNow } from 'date-fns';
import { Activity, AlertTriangle, CheckCircle, XCircle, CircleSlash, Clock, HeartPulse, Bell } from 'lucide-react';
import { PageHeader } from '@/components/dashboard/PageHeader';
import { StatCard } from '@/components/dashboard/StatCard';
import { LoadingSkeleton } from '@/components/dashboard/LoadingSkeleton';
import { ErrorState } from '@/components/dashboard/ErrorState';
import { EmptyState } from '@/components/dashboard/EmptyState';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { supabase } from '@/integrations/supabase/client';
import { isMarketOpen, isMarketDay, getMarketStatusLabel } from '@/lib/market-calendar';

type ServiceStatus = 'healthy' | 'degraded' | 'error' | 'offline' | 'idle';

interface TradingHealthRow {
  id: string;
  service_name: string;
  status: string;
  last_heartbeat_at: string;
  latency_ms: number | null;
  error_count_1h: number | null;
  last_error_message: string | null;
}

interface TradingAlertRow {
  id: string;
  metric_key: string;
  metric_value: number;
  threshold_value: number;
  severity: string;
  created_at: string;
  resolved_at: string | null;
}

const EXPECTED_SERVICES = [
  'prediction_engine',
  'gex_engine',
  'strategy_selector',
  'risk_engine',
  'execution_engine',
  'data_ingestor',
  'tradier_websocket',
  'databento_feed',
  'polygon_feed',
] as const;
// NOTE: learning_engine, sentinel, cboe_feed removed — these services
// have not been built yet and never write health status. They were
// permanently showing as "offline" giving a false picture.
// Add them back when actually implemented.

const STATUS_CONFIG: Record<ServiceStatus, { Icon: typeof CheckCircle; badgeClass: string; iconClass: string }> = {
  healthy: {
    Icon: CheckCircle,
    badgeClass: 'bg-success/10 text-success border-success/20',
    iconClass: 'text-success',
  },
  degraded: {
    Icon: AlertTriangle,
    badgeClass: 'bg-warning/10 text-warning border-warning/20',
    iconClass: 'text-warning',
  },
  error: {
    Icon: XCircle,
    badgeClass: 'bg-destructive/10 text-destructive border-destructive/20',
    iconClass: 'text-destructive',
  },
  offline: {
    Icon: CircleSlash,
    badgeClass: 'bg-muted text-muted-foreground border-border',
    iconClass: 'text-muted-foreground',
  },
  // 'idle' = not running because market is closed (weekend, holiday,
  // outside hours). Neutral grey + Clock icon — not an alarm color.
  idle: {
    Icon: Clock,
    badgeClass: 'bg-muted text-muted-foreground border-border',
    iconClass: 'text-muted-foreground',
  },
};

function normalizeStatus(status: string): ServiceStatus {
  const s = status.toLowerCase();
  if (s === 'healthy' || s === 'degraded' || s === 'error' || s === 'offline' || s === 'idle') return s;
  if (s === 'unhealthy') return 'error';
  return 'offline';
}

interface TradingServiceCardProps {
  serviceName: string;
  row: TradingHealthRow | undefined;
}

function TradingServiceCard({ serviceName, row }: TradingServiceCardProps) {
  const status: ServiceStatus = row ? normalizeStatus(row.status) : 'offline';
  const cfg = STATUS_CONFIG[status];
  const { Icon } = cfg;

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between gap-2">
          <CardTitle className="text-sm font-medium capitalize">
            {serviceName.replace(/_/g, ' ')}
          </CardTitle>
          <Badge variant="outline" className={cfg.badgeClass}>
            <Icon className={`mr-1 h-3 w-3 ${cfg.iconClass}`} />
            {status}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-1.5 text-xs text-muted-foreground">
        {row ? (
          <>
            <p>
              Last heartbeat:{' '}
              <span className="font-mono text-foreground">
                {formatDistanceToNow(new Date(row.last_heartbeat_at), { addSuffix: true })}
              </span>
            </p>
            <p>
              Latency:{' '}
              <span className="font-mono text-foreground">
                {row.latency_ms != null ? `${row.latency_ms}ms` : '—'}
              </span>
            </p>
            <p>
              Errors (1h):{' '}
              <span className={`font-mono ${(row.error_count_1h ?? 0) > 0 ? 'text-destructive' : 'text-foreground'}`}>
                {row.error_count_1h ?? 0}
              </span>
            </p>
            {row.last_error_message && row.status !== 'healthy' && (
              <p className="mt-2 truncate text-destructive" title={row.last_error_message}>
                {row.last_error_message}
              </p>
            )}
          </>
        ) : (
          <p className="italic">No heartbeat received</p>
        )}
      </CardContent>
    </Card>
  );
}

export default function TradingHealthPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['admin', 'trading', 'health'],
    queryFn: async () => {
      const [healthRes, alertsRes] = await Promise.all([
        supabase
          .from('trading_system_health')
          .select('id, service_name, status, last_heartbeat_at, latency_ms, error_count_1h, last_error_message')
          .order('last_heartbeat_at', { ascending: false }),
        supabase
          .from('alert_history')
          .select('id, metric_key, metric_value, threshold_value, severity, created_at, resolved_at')
          .like('metric_key', 'trading.%')
          .order('created_at', { ascending: false })
          .limit(10),
      ]);
      if (healthRes.error) throw healthRes.error;
      if (alertsRes.error) throw alertsRes.error;
      return {
        health: (healthRes.data ?? []) as TradingHealthRow[],
        alerts: (alertsRes.data ?? []) as TradingAlertRow[],
      };
    },
    refetchInterval: 10_000,
    refetchIntervalInBackground: false,
  });

  // Latest row per service (data is already ordered by heartbeat desc)
  const serviceMap = useMemo(() => {
    const map = new Map<string, TradingHealthRow>();
    for (const row of data?.health ?? []) {
      if (!map.has(row.service_name)) map.set(row.service_name, row);
    }
    return map;
  }, [data?.health]);

  const offlineCount = useMemo(() => {
    let n = 0;
    for (const name of EXPECTED_SERVICES) {
      const row = serviceMap.get(name);
      // Idle services are NOT offline — they're calmly off because the
      // market is closed. Only true 'offline' or missing rows count.
      if (!row) {
        n += 1;
        continue;
      }
      const status = normalizeStatus(row.status);
      if (status === 'offline') n += 1;
    }
    return n;
  }, [serviceMap]);

  const healthyCount = useMemo(() => {
    let n = 0;
    for (const name of EXPECTED_SERVICES) {
      const row = serviceMap.get(name);
      if (row && normalizeStatus(row.status) === 'healthy') n += 1;
    }
    return n;
  }, [serviceMap]);

  const marketOpen = isMarketOpen();
  const marketDay = isMarketDay();
  const marketStatusLabel = getMarketStatusLabel();
  // Critical banner fires ONLY when the market is currently open AND we
  // have offline services. Weekends, holidays, pre-market, and after
  // close all suppress it — those are expected idle states, not alarms.
  const showCriticalBanner = marketOpen && offlineCount > 0;
  const isEmpty = !isLoading && !error && (data?.health.length ?? 0) === 0;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Engine Health"
        subtitle="Trading system service heartbeats — refreshes every 10s"
      />

      {showCriticalBanner && (
        <Alert variant="destructive" className="border-destructive bg-destructive/10">
          <AlertTriangle className="h-5 w-5" />
          <AlertTitle className="font-semibold">CRITICAL — Service offline during market hours</AlertTitle>
          <AlertDescription>
            {offlineCount} of {EXPECTED_SERVICES.length} trading services are offline while the market is open
            (9:30 AM – 4:00 PM ET). Investigate immediately.
          </AlertDescription>
        </Alert>
      )}

      {error ? (
        <ErrorState message="Failed to load trading health data" />
      ) : isLoading ? (
        <LoadingSkeleton variant="card" rows={3} />
      ) : isEmpty ? (
        <EmptyState
          icon={HeartPulse}
          title="Services not yet reporting"
          description="Start the Python backend to see health status. Trading services upsert a heartbeat to trading_system_health every 10 seconds."
        />
      ) : (
        <>
          <div className="grid gap-3 grid-cols-2 lg:grid-cols-4">
            <StatCard title="Expected Services" value={EXPECTED_SERVICES.length} icon={Activity} />
            <StatCard title="Healthy" value={healthyCount} icon={CheckCircle} />
            <StatCard title="Offline" value={offlineCount} icon={CircleSlash} />
            <StatCard title="Market Status" value={marketStatusLabel} icon={HeartPulse} />
          </div>

          {!marketOpen && (
            <p className="text-xs text-muted-foreground">
              {marketDay
                ? 'Outside market hours (Mon–Fri 9:30–16:00 ET).'
                : 'Market closed (weekend or holiday).'}{' '}
              Data feeds report <span className="font-medium">idle</span>{' '}
              when markets are closed — this is expected behavior, not an
              error.
            </p>
          )}

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {EXPECTED_SERVICES.map((name) => (
              <TradingServiceCard key={name} serviceName={name} row={serviceMap.get(name)} />
            ))}
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Bell className="h-4 w-4" />
                Recent Trading Alerts
              </CardTitle>
              <CardDescription>Last 10 alerts where metric_key starts with trading.</CardDescription>
            </CardHeader>
            <CardContent>
              {data && data.alerts.length > 0 ? (
                <div className="space-y-3">
                  {data.alerts.map((a) => (
                    <div key={a.id} className="flex items-center justify-between gap-3 rounded-md border p-3">
                      <div className="space-y-1 min-w-0">
                        <p className="text-sm font-medium font-mono truncate">{a.metric_key}</p>
                        <p className="text-xs text-muted-foreground">
                          Value: {a.metric_value} (threshold: {a.threshold_value}) ·{' '}
                          {formatDistanceToNow(new Date(a.created_at), { addSuffix: true })}
                        </p>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <Badge
                          variant="outline"
                          className={
                            a.severity === 'critical'
                              ? 'bg-destructive/10 text-destructive border-destructive/20'
                              : a.severity === 'warning'
                              ? 'bg-warning/10 text-warning border-warning/20'
                              : 'bg-muted text-muted-foreground'
                          }
                        >
                          {a.severity}
                        </Badge>
                        {a.resolved_at ? (
                          <Badge variant="outline" className="bg-success/10 text-success border-success/20">
                            resolved
                          </Badge>
                        ) : (
                          <Badge variant="outline" className="bg-warning/10 text-warning border-warning/20">
                            active
                          </Badge>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">No trading alerts in history.</p>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
