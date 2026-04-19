/**
 * War Room — /admin/trading/warroom
 * Phase 3A deliverable TPLAN-CONSOLE-003A
 *
 * Primary operator cockpit. Real-time regime, CV_Stress, prediction,
 * open positions, capital preservation, and session control.
 */
import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { formatDistanceToNow } from 'date-fns';
import { Activity, CheckCircle, Radio } from 'lucide-react';
import { PageHeader } from '@/components/dashboard/PageHeader';
import { StatCard } from '@/components/dashboard/StatCard';
import { LoadingSkeleton } from '@/components/dashboard/LoadingSkeleton';
import { ErrorState } from '@/components/dashboard/ErrorState';
import { EmptyState } from '@/components/dashboard/EmptyState';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { RegimePanel } from '@/components/trading/RegimePanel';
import { CVStressPanel } from '@/components/trading/CVStressPanel';
import { PredictionConfidence } from '@/components/trading/PredictionConfidence';
import { KillSwitchButton } from '@/components/trading/KillSwitchButton';
import { CapitalPreservationStatus } from '@/components/trading/CapitalPreservationStatus';
import { useTradingSession } from '@/hooks/trading/useTradingSession';
import { useTradingPrediction } from '@/hooks/trading/useTradingPrediction';
import { useTradingPositions } from '@/hooks/trading/useTradingPositions';
import { useTradingSystemHealth } from '@/hooks/trading/useTradingSystemHealth';
import { ROUTES } from '@/config/routes';

const EXPECTED_SERVICES = [
  'prediction_engine',
  'gex_engine',
  'strategy_selector',
  'risk_engine',
  'execution_engine',
  'learning_engine',
  'data_ingestor',
  'sentinel',
  'tradier_websocket',
  'databento_feed',
  'cboe_feed',
] as const;

const REGIME_MAX_TRADES: Record<string, number> = {
  trend: 2,
  range: 3,
  bullish: 2,
  bearish: 2,
  crisis: 1,
  volatile: 1,
  pin: 3,
};

function sessionStatusBadgeClass(status: string | null): string {
  if (!status) return 'bg-muted text-muted-foreground border-border';
  const s = status.toLowerCase();
  if (s === 'active') return 'bg-success/10 text-success border-success/20';
  if (s === 'halted') return 'bg-destructive/10 text-destructive border-destructive/20';
  if (s === 'closed') return 'bg-muted text-muted-foreground border-border';
  return 'bg-muted text-muted-foreground border-border';
}

function pnlTextClass(pnl: number | null): string {
  if (pnl == null) return 'text-foreground';
  return pnl >= 0 ? 'text-success' : 'text-destructive';
}

export default function TradingWarRoomPage() {
  const {
    data: session,
    isLoading: sessionLoading,
    error: sessionError,
  } = useTradingSession();

  const {
    data: prediction,
    isLoading: predictionLoading,
    error: predictionError,
  } = useTradingPrediction();

  const {
    data: openPositions,
    isLoading: positionsLoading,
  } = useTradingPositions({ status: 'open' });

  const { serviceMap, isLoading: healthLoading } = useTradingSystemHealth();

  const isLoading = sessionLoading || predictionLoading || positionsLoading || healthLoading;
  const hasError = sessionError ?? predictionError;
  const noSession = !sessionLoading && !sessionError && !session;

  const regimeMaxTrades = useMemo(() => {
    if (!session?.regime) return 3;
    return REGIME_MAX_TRADES[session.regime.toLowerCase()] ?? 3;
  }, [session?.regime]);

  const winRate = useMemo(() => {
    const wins = session?.virtual_wins ?? 0;
    const total = session?.virtual_trades_count ?? 0;
    if (total === 0) return null;
    return (wins / total) * 100;
  }, [session]);

  const healthyCount = useMemo(() => {
    let n = 0;
    for (const name of EXPECTED_SERVICES) {
      const row = serviceMap.get(name);
      if (row && row.status === 'healthy') n += 1;
    }
    return n;
  }, [serviceMap]);

  const predictionAge = useMemo(() => {
    if (!prediction?.predicted_at) return null;
    return formatDistanceToNow(new Date(prediction.predicted_at), {
      addSuffix: true,
    });
  }, [prediction?.predicted_at]);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="War Room"
          subtitle="Trading operator cockpit — refreshing"
        />
        <LoadingSkeleton variant="card" rows={4} />
      </div>
    );
  }

  if (hasError) {
    return (
      <div className="space-y-6">
        <PageHeader title="War Room" subtitle="Trading operator cockpit" />
        <ErrorState message="Failed to load War Room data. Check backend connectivity." />
      </div>
    );
  }

  if (noSession) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="War Room"
          subtitle={new Date().toLocaleDateString('en-US', {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric',
          })}
        />
        <EmptyState
          icon={Radio}
          title="No session for today"
          description="The trading backend has not created a session for today yet. Start the backend service to begin."
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <PageHeader
          title="War Room"
          subtitle={new Date().toLocaleDateString('en-US', {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric',
          })}
        />
        <div className="flex flex-wrap items-center gap-3">
          <Badge
            variant="outline"
            className={`capitalize ${sessionStatusBadgeClass(session?.session_status ?? null)}`}
          >
            {session?.session_status ?? 'unknown'}
          </Badge>
          <KillSwitchButton
            sessionId={session?.id ?? null}
            sessionStatus={session?.session_status ?? null}
          />
        </div>
      </div>

      {/* Top row: stat cards */}
      <div className="grid gap-3 grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Virtual P&L"
          value={
            session?.virtual_pnl != null
              ? `${session.virtual_pnl >= 0 ? '+' : ''}$${session.virtual_pnl.toFixed(2)}`
              : '—'
          }
          icon={Activity}
        />
        <StatCard
          title="Win Rate"
          value={winRate != null ? `${winRate.toFixed(1)}%` : '—'}
          icon={CheckCircle}
        />
        <StatCard
          title="Trades Today"
          value={`${session?.virtual_trades_count ?? 0} / ${regimeMaxTrades}`}
          icon={Radio}
        />
        <StatCard
          title="Session Status"
          value={session?.session_status ?? '—'}
          icon={Activity}
        />
      </div>

      {/* Middle row: regime, CV_Stress, prediction */}
      <div className="grid gap-4 md:grid-cols-3">
        <RegimePanel
          regime={prediction?.regime ?? session?.regime ?? null}
          rcs={prediction?.rcs ?? null}
          regimeAgreement={prediction?.regime_agreement ?? null}
          allocationTier={prediction?.allocation_tier ?? null}
        />
        <CVStressPanel
          cvStress={prediction?.cv_stress_score ?? null}
          charmVelocity={prediction?.charm_velocity ?? null}
          vannaVelocity={prediction?.vanna_velocity ?? null}
        />
        <PredictionConfidence
          pBull={prediction?.p_bull ?? null}
          pBear={prediction?.p_bear ?? null}
          pNeutral={prediction?.p_neutral ?? null}
          direction={prediction?.direction ?? null}
          confidence={prediction?.confidence ?? null}
          noTradeSignal={prediction?.no_trade_signal ?? null}
          noTradeReason={prediction?.no_trade_reason ?? null}
        />
      </div>

      {/* Bottom row: capital preservation + open positions */}
      <div className="grid gap-4 md:grid-cols-2">
        <div className="space-y-4">
          <CapitalPreservationStatus
            consecutiveLossesToday={session?.consecutive_losses_today ?? null}
            capitalPreservationActive={session?.capital_preservation_active ?? null}
            virtualTradesCount={session?.virtual_trades_count ?? null}
          />
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium">Engine Health</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold font-mono">
                {healthyCount}
                <span className="text-base font-normal text-muted-foreground ml-1">
                  / {EXPECTED_SERVICES.length} healthy
                </span>
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Open positions */}
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-medium">
                Open Positions
              </CardTitle>
              <Link
                to={ROUTES.TRADING_POSITIONS}
                className="text-xs text-primary hover:underline"
              >
                View all
              </Link>
            </div>
          </CardHeader>
          <CardContent>
            {!openPositions || openPositions.length === 0 ? (
              <p className="text-sm text-muted-foreground italic">
                No open positions
              </p>
            ) : (
              <div className="space-y-2">
                {openPositions.slice(0, 5).map((pos) => (
                  <div
                    key={pos.id}
                    className="flex items-center justify-between gap-2 rounded-md border p-2 text-xs"
                  >
                    <div className="space-y-0.5 min-w-0">
                      <p className="font-medium capitalize truncate">
                        {pos.strategy_type ?? '—'} · {pos.instrument ?? '—'}
                      </p>
                      <p className="text-muted-foreground">
                        {pos.contracts ?? 0} contracts · credit{' '}
                        {pos.entry_credit != null
                          ? `$${pos.entry_credit.toFixed(2)}`
                          : '—'}
                      </p>
                    </div>
                    <span
                      className={`font-mono font-semibold shrink-0 ${pnlTextClass(
                        pos.current_pnl ?? null
                      )}`}
                    >
                      {pos.current_pnl != null
                        ? `${pos.current_pnl >= 0 ? '+' : ''}$${pos.current_pnl.toFixed(2)}`
                        : '—'}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Footer */}
      <div className="flex flex-wrap items-center gap-4 text-xs text-muted-foreground border-t pt-4">
        <span>
          Last prediction:{' '}
          <span className="font-mono">{predictionAge ?? '—'}</span>
        </span>
        <span>Next cycle: ~5 min</span>
        <span className="ml-auto">
          {healthyCount} / {EXPECTED_SERVICES.length} services healthy
        </span>
      </div>
    </div>
  );
}
