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
import {
  Activity,
  AlertCircle,
  Brain,
  CheckCircle,
  Minus,
  Radio,
  Target,
  TrendingDown,
  TrendingUp as TrendUp,
} from 'lucide-react';
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
import {
  useTradeIntelligence,
  isBriefStale,
} from '@/hooks/trading/useTradeIntelligence';
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

  const { data: intel } = useTradeIntelligence();

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

      {/* AI Intelligence + Milestones row (Phase 4C) */}
      <div className="grid gap-4 md:grid-cols-3">
        {/* AI Intelligence — spans 2 cols */}
        <Card className="md:col-span-2">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-medium flex items-center gap-2">
                <Brain className="h-4 w-4" />
                AI Intelligence
              </CardTitle>
              {intel?.calendar?.day_classification &&
                intel.calendar.day_classification !== 'normal' && (
                  <Badge
                    variant="outline"
                    className={
                      intel.calendar.day_classification === 'catalyst_major'
                        ? 'bg-amber-500/10 text-amber-600 border-amber-500/20'
                        : 'bg-blue-500/10 text-blue-600 border-blue-500/20'
                    }
                  >
                    {intel.calendar.day_classification.replace(/_/g, ' ')}
                  </Badge>
                )}
            </div>
          </CardHeader>
          <CardContent>
            {!intel ||
            (!intel.synthesis?.direction && !intel.flow?.flow_direction) ? (
              <p className="text-sm text-muted-foreground italic">
                AI agents are off — enable in Config to activate.
              </p>
            ) : (
              <>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  {/* Synthesis */}
                  <div className="space-y-1">
                    <p className="text-xs text-muted-foreground">Synthesis</p>
                    {intel.synthesis?.direction ? (
                      <>
                        <p className="text-sm font-semibold capitalize flex items-center gap-1">
                          {intel.synthesis.direction === 'bull' ? (
                            <TrendUp className="h-3.5 w-3.5 text-success" />
                          ) : intel.synthesis.direction === 'bear' ? (
                            <TrendingDown className="h-3.5 w-3.5 text-destructive" />
                          ) : (
                            <Minus className="h-3.5 w-3.5 text-muted-foreground" />
                          )}
                          {intel.synthesis.direction}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {intel.synthesis.confidence != null
                            ? `${(intel.synthesis.confidence * 100).toFixed(0)}% · `
                            : ''}
                          {intel.synthesis.strategy?.replace(/_/g, ' ') ?? '—'}
                        </p>
                        {isBriefStale(intel.synthesis.generated_at) && (
                          <p className="text-xs text-amber-600 flex items-center gap-1">
                            <AlertCircle className="h-3 w-3" />
                            stale
                          </p>
                        )}
                      </>
                    ) : (
                      <p className="text-xs text-muted-foreground italic">off</p>
                    )}
                  </div>

                  {/* Flow */}
                  <div className="space-y-1">
                    <p className="text-xs text-muted-foreground">Options Flow</p>
                    {intel.flow?.flow_score != null ? (
                      <>
                        <p
                          className={`text-sm font-semibold font-mono ${
                            (intel.flow.flow_score ?? 0) > 30
                              ? 'text-success'
                              : (intel.flow.flow_score ?? 0) < -30
                              ? 'text-destructive'
                              : 'text-foreground'
                          }`}
                        >
                          {(intel.flow.flow_score ?? 0) > 0 ? '+' : ''}
                          {intel.flow.flow_score}
                        </p>
                        <p className="text-xs text-muted-foreground capitalize">
                          {intel.flow.flow_direction ?? '—'}
                          {intel.flow.put_call_ratio != null
                            ? ` · P/C ${intel.flow.put_call_ratio.toFixed(2)}`
                            : ''}
                        </p>
                      </>
                    ) : (
                      <p className="text-xs text-muted-foreground italic">off</p>
                    )}
                  </div>

                  {/* Sentiment */}
                  <div className="space-y-1">
                    <p className="text-xs text-muted-foreground">Sentiment</p>
                    {intel.sentiment?.sentiment_score != null ? (
                      <>
                        <p
                          className={`text-sm font-semibold font-mono ${
                            (intel.sentiment.sentiment_score ?? 0) > 20
                              ? 'text-success'
                              : (intel.sentiment.sentiment_score ?? 0) < -20
                              ? 'text-destructive'
                              : 'text-foreground'
                          }`}
                        >
                          {(intel.sentiment.sentiment_score ?? 0) > 0 ? '+' : ''}
                          {intel.sentiment.sentiment_score}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          F&G: {intel.sentiment.fear_greed_index ?? '—'}
                          {intel.sentiment.overnight_gap_pct != null
                            ? ` · gap ${
                                intel.sentiment.overnight_gap_pct > 0 ? '+' : ''
                              }${intel.sentiment.overnight_gap_pct.toFixed(2)}%`
                            : ''}
                        </p>
                      </>
                    ) : (
                      <p className="text-xs text-muted-foreground italic">off</p>
                    )}
                  </div>

                  {/* Confluence */}
                  <div className="space-y-1">
                    <p className="text-xs text-muted-foreground">Confluence</p>
                    {intel.synthesis?.confluence_score != null ? (
                      <>
                        <p
                          className={`text-2xl font-bold font-mono ${
                            intel.synthesis.confluence_score >= 0.66
                              ? 'text-success'
                              : intel.synthesis.confluence_score >= 0.33
                              ? 'text-amber-500'
                              : 'text-muted-foreground'
                          }`}
                        >
                          {(intel.synthesis.confluence_score * 100).toFixed(0)}%
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {intel.synthesis.confluence_score >= 0.66
                            ? 'all agree'
                            : intel.synthesis.confluence_score >= 0.33
                            ? 'partial'
                            : 'diverge'}
                        </p>
                      </>
                    ) : (
                      <p className="text-xs text-muted-foreground italic">—</p>
                    )}
                  </div>
                </div>

                {/* Rationale */}
                {intel.synthesis?.rationale && (
                  <p className="mt-3 text-xs text-muted-foreground border-t pt-3 italic line-clamp-2">
                    &ldquo;{intel.synthesis.rationale}&rdquo;
                  </p>
                )}

                {/* Events */}
                {(intel.calendar?.events?.length ?? 0) > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {intel.calendar!.events!.slice(0, 5).map((ev, i) => (
                      <Badge
                        key={i}
                        variant="outline"
                        className={`text-xs ${
                          ev.is_major
                            ? 'bg-amber-500/10 text-amber-600 border-amber-500/20'
                            : 'bg-muted text-muted-foreground border-border'
                        }`}
                      >
                        {ev.event}
                      </Badge>
                    ))}
                  </div>
                )}
              </>
            )}
          </CardContent>
        </Card>

        {/* Trade Milestone Tracker */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Target className="h-4 w-4" />
              Milestones
            </CardTitle>
          </CardHeader>
          <CardContent>
            {(() => {
              const count = session?.virtual_trades_count ?? 0;
              const MILESTONES = [
                { at: 1, label: 'Live', detail: 'System confirmed' },
                { at: 5, label: 'Butterfly', detail: 'Enable iron butterfly' },
                {
                  at: 20,
                  label: 'Full AI',
                  detail: 'Straddle · Flow · Sentiment',
                },
                { at: 40, label: 'Override', detail: 'AI hint override' },
                { at: 100, label: 'Model', detail: 'Meta-label model' },
              ];
              const next = MILESTONES.find((m) => m.at > count);
              return (
                <div className="space-y-3">
                  <div>
                    <span className="text-3xl font-bold font-mono">{count}</span>
                    <span className="text-sm text-muted-foreground ml-1">
                      trades
                    </span>
                  </div>
                  {next && (
                    <p className="text-xs text-muted-foreground">
                      {next.at - count} to{' '}
                      <span className="font-medium">{next.label}</span>
                      <br />
                      <span className="italic">{next.detail}</span>
                    </p>
                  )}
                  <div className="space-y-1">
                    {MILESTONES.map((m) => (
                      <div key={m.at} className="flex items-center gap-2">
                        <div
                          className={`h-1.5 w-1.5 rounded-full shrink-0 ${
                            count >= m.at ? 'bg-success' : 'bg-muted'
                          }`}
                        />
                        <div
                          className={`h-0.5 flex-1 rounded ${
                            count >= m.at ? 'bg-success' : 'bg-muted'
                          }`}
                        />
                        <span
                          className={`text-xs font-mono shrink-0 ${
                            count >= m.at
                              ? 'text-success font-semibold'
                              : 'text-muted-foreground'
                          }`}
                        >
                          {m.at}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })()}
          </CardContent>
        </Card>
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
