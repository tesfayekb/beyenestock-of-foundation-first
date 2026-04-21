/**
 * Performance — /admin/trading/performance
 * Phase 3B deliverable TPLAN-CONSOLE-003F
 *
 * Session history, rolling model accuracy, and drift status.
 */
import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { AlertTriangle, BarChart2 } from 'lucide-react';
import { PageHeader } from '@/components/dashboard/PageHeader';
import { StatCard } from '@/components/dashboard/StatCard';
import { LoadingSkeleton } from '@/components/dashboard/LoadingSkeleton';
import { ErrorState } from '@/components/dashboard/ErrorState';
import { EmptyState } from '@/components/dashboard/EmptyState';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { supabase } from '@/integrations/supabase/client';
import { formatPnl } from '@/lib/format-pnl';
import { useLearningStatsBanner } from '@/hooks/trading/useLearningStats';
import { ROUTES } from '@/config/routes';

interface TradingSessionSummaryRow {
  session_date: string;
  virtual_pnl: number | null;
  virtual_wins: number | null;
  virtual_losses: number | null;
  virtual_trades_count: number | null;
  regime: string | null;
  session_status: string;
}

interface ModelPerformanceRow {
  accuracy_5d: number | null;
  accuracy_20d: number | null;
  accuracy_60d: number | null;
  drift_status: string | null;
  drift_z_score: number | null;
  profit_factor_20d: number | null;
  preservation_triggers_this_week: number | null;
  challenger_active: boolean | null;
}

function driftBadgeClass(status: string | null): string {
  if (!status) return 'bg-muted text-muted-foreground border-border';
  const s = status.toLowerCase();
  if (s === 'ok') return 'bg-success/10 text-success border-success/20';
  if (s === 'warning') return 'bg-amber-500/10 text-amber-600 border-amber-500/20';
  if (s === 'critical') return 'bg-destructive/10 text-destructive border-destructive/20';
  return 'bg-muted text-muted-foreground border-border';
}

function sessionStatusBadgeClass(status: string): string {
  const s = status.toLowerCase();
  if (s === 'active') return 'bg-success/10 text-success border-success/20';
  if (s === 'halted') return 'bg-destructive/10 text-destructive border-destructive/20';
  return 'bg-muted text-muted-foreground border-border';
}

function MetricRow({
  label,
  value,
}: {
  label: string;
  value: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-0.5">
      <p className="text-xs text-muted-foreground">{label}</p>
      <div className="text-sm font-semibold">{value}</div>
    </div>
  );
}

/**
 * StrategyBreakdownCard (Phase 4C)
 * Per-strategy win rate and avg P&L across all closed virtual positions.
 * Strategies with fewer than 5 trades show "<5 trades" instead of metrics —
 * win rate is too noisy to trust under that sample size.
 *
 * MUST be defined above TradingPerformancePage default export so React's
 * function-name resolution sees it without hoisting surprises.
 */
function StrategyBreakdownCard() {
  const { data, isLoading } = useQuery({
    queryKey: ['strategy-breakdown'],
    queryFn: async () => {
      const { data: rows, error } = await supabase
        .from('trading_positions')
        .select('strategy_type, net_pnl, status')
        .eq('status', 'closed')
        .eq('position_mode', 'virtual');
      if (error) throw error;
      return rows ?? [];
    },
    staleTime: 5 * 60_000,
  });

  const breakdown = useMemo(() => {
    if (!data) return [];
    const map: Record<
      string,
      { wins: number; losses: number; totalPnl: number; count: number }
    > = {};
    for (const pos of data) {
      const key = (pos.strategy_type as string | null) ?? 'unknown';
      if (!map[key]) map[key] = { wins: 0, losses: 0, totalPnl: 0, count: 0 };
      map[key].count += 1;
      const pnl = (pos.net_pnl as number | null) ?? 0;
      map[key].totalPnl += pnl;
      if (pnl > 0) map[key].wins += 1;
      else map[key].losses += 1;
    }
    return Object.entries(map)
      .map(([strategy, s]) => ({
        strategy,
        count: s.count,
        winRate: s.count > 0 ? (s.wins / s.count) * 100 : 0,
        avgPnl: s.count > 0 ? s.totalPnl / s.count : 0,
        totalPnl: s.totalPnl,
        insufficient: s.count < 5,
      }))
      .sort((a, b) => b.count - a.count);
  }, [data]);

  if (isLoading) return <LoadingSkeleton variant="card" rows={2} />;

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium">Strategy Breakdown</CardTitle>
        <CardDescription>
          Per-strategy P&amp;L across all closed paper trades.
          Strategies with fewer than 5 trades show insufficient data.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {!breakdown.length ? (
          <EmptyState
            icon={BarChart2}
            title="No closed trades yet"
            description="Breakdown appears after the first paper trade closes."
          />
        ) : (
          <div className="space-y-2">
            {breakdown.map((s) => (
              <div
                key={s.strategy}
                className="flex items-center gap-3 rounded-lg border p-3"
              >
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium capitalize">
                    {s.strategy.replace(/_/g, ' ')}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {s.count} trade{s.count !== 1 ? 's' : ''}
                  </p>
                </div>
                {s.insufficient ? (
                  <Badge
                    variant="outline"
                    className="text-xs bg-muted text-muted-foreground border-border"
                  >
                    &lt;5 trades
                  </Badge>
                ) : (
                  <>
                    <div className="text-right">
                      <p
                        className={`text-sm font-semibold font-mono ${
                          s.winRate >= 60
                            ? 'text-success'
                            : s.winRate >= 40
                            ? 'text-amber-500'
                            : 'text-destructive'
                        }`}
                      >
                        {s.winRate.toFixed(0)}%
                      </p>
                      <p className="text-xs text-muted-foreground">win</p>
                    </div>
                    {(() => {
                      const pnl = formatPnl(s.avgPnl);
                      return (
                        <div className="text-right">
                          <p className={`text-sm font-mono ${pnl.className}`}>
                            {pnl.text}
                          </p>
                          <p className="text-xs text-muted-foreground">avg</p>
                        </div>
                      );
                    })()}
                  </>
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default function TradingPerformancePage() {
  const {
    data: sessions,
    isLoading: sessionsLoading,
    error: sessionsError,
  } = useQuery({
    queryKey: ['trading', 'performance', 'sessions'],
    queryFn: async () => {
      const { data: rows, error: err } = await supabase
        .from('trading_sessions')
        .select(
          'session_date, virtual_pnl, virtual_wins, virtual_losses, virtual_trades_count, regime, session_status'
        )
        .gt('virtual_trades_count', 0)
        .order('session_date', { ascending: false })
        .limit(30);
      if (err) throw err;
      return (rows as TradingSessionSummaryRow[]) ?? [];
    },
    refetchInterval: 60_000,
    refetchIntervalInBackground: false,
  });

  const {
    data: modelPerf,
    isLoading: modelLoading,
    error: modelError,
  } = useQuery({
    queryKey: ['trading', 'performance', 'model'],
    queryFn: async () => {
      const { data: rows, error: err } = await supabase
        .from('trading_model_performance')
        .select(
          'accuracy_5d, accuracy_20d, accuracy_60d, drift_status, drift_z_score, profit_factor_20d, preservation_triggers_this_week, challenger_active'
        )
        .order('recorded_at', { ascending: false })
        .limit(1);
      if (err) throw err;
      return (rows?.[0] as ModelPerformanceRow | undefined) ?? null;
    },
    refetchInterval: 60_000,
    refetchIntervalInBackground: false,
  });

  // Section 13 UI-3: live model-drift banner. Uses the Edge-function
  // proxy to Railway (same hook as War Room). Separate from the
  // `modelPerf.drift_status` read above — that one is the historical
  // session-level drift stored in trading_model_performance, while
  // this one is the live 10-day rolling alert computed in Redis.
  const { data: learningStats } = useLearningStatsBanner();

  // Section 13 UI-4: missed-opportunity summary. Aggregates
  // counterfactual P&L on no-trade cycles over the last 7 days.
  // `counterfactual_pnl` is not yet in the generated Supabase types
  // (column added in migration 20260421_add_counterfactual_pnl.sql),
  // so the row shape is widened manually below. Same pattern as
  // useFeatureFlags' cast-to-`never` on trading_feature_flags.
  const { data: counterfactualData } = useQuery<
    Array<{ no_trade_reason: string | null; counterfactual_pnl: number | null }>
  >({
    queryKey: ['counterfactual-summary'],
    queryFn: async () => {
      const sevenDaysAgoIso = new Date(
        Date.now() - 7 * 24 * 60 * 60 * 1000
      ).toISOString();
      const { data: rows, error: err } = await supabase
        .from('trading_prediction_outputs')
        .select('no_trade_reason, counterfactual_pnl')
        .eq('no_trade_signal', true)
        .not('counterfactual_pnl', 'is', null)
        .gte('predicted_at', sevenDaysAgoIso);
      if (err) throw err;
      return ((rows ?? []) as unknown) as Array<{
        no_trade_reason: string | null;
        counterfactual_pnl: number | null;
      }>;
    },
    refetchInterval: 300_000,
    refetchIntervalInBackground: false,
  });

  const missedOpportunities = useMemo(() => {
    if (!counterfactualData?.length) return [] as Array<{
      reason: string;
      count: number;
      avg: number;
      total: number;
    }>;
    const byReason: Record<string, { count: number; total: number }> = {};
    for (const row of counterfactualData) {
      const r = row.no_trade_reason ?? 'unknown';
      if (!byReason[r]) byReason[r] = { count: 0, total: 0 };
      byReason[r].count += 1;
      byReason[r].total += row.counterfactual_pnl ?? 0;
    }
    return Object.entries(byReason)
      .map(([reason, { count, total }]) => ({
        reason,
        count,
        avg: count > 0 ? total / count : 0,
        total,
      }))
      .sort((a, b) => Math.abs(b.total) - Math.abs(a.total))
      .slice(0, 3);
  }, [counterfactualData]);

  const isLoading = sessionsLoading || modelLoading;
  const hasError = sessionsError ?? modelError;

  const totalPnl = useMemo(
    () =>
      sessions?.reduce((sum, s) => sum + (s.virtual_pnl ?? 0), 0) ?? null,
    [sessions]
  );

  const totalWins = useMemo(
    () => sessions?.reduce((sum, s) => sum + (s.virtual_wins ?? 0), 0) ?? 0,
    [sessions]
  );

  const totalTrades = useMemo(
    () =>
      sessions?.reduce((sum, s) => sum + (s.virtual_trades_count ?? 0), 0) ??
      0,
    [sessions]
  );

  const overallWinRate = useMemo(() => {
    if (totalTrades === 0) return null;
    return (totalWins / totalTrades) * 100;
  }, [totalWins, totalTrades]);

  const profitableSessions = useMemo(
    () => sessions?.filter((s) => (s.virtual_pnl ?? 0) > 0).length ?? 0,
    [sessions]
  );

  if (isLoading) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Performance"
          subtitle="Rolling metrics and model accuracy"
        />
        <LoadingSkeleton variant="card" rows={4} />
      </div>
    );
  }

  if (hasError) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Performance"
          subtitle="Rolling metrics and model accuracy"
        />
        <ErrorState message="Failed to load performance data." />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Performance"
        subtitle="Rolling metrics and model accuracy"
      />

      {/* Section 13 UI-3: live model-drift banner. Labeled "Live
          model drift" so it is clearly distinct from the
          session-level "Historical session drift" shown in the Model
          Performance card's Drift Status badge below. */}
      {learningStats?.model_drift_alert ? (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 px-4 py-3 text-sm text-destructive flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          <span>
            <strong>Live model drift detected.</strong> 10-day
            rolling prediction accuracy has dropped relative to the
            60-day baseline. Review the{' '}
            <Link to={ROUTES.TRADING_LEARNING} className="underline">
              Learning Dashboard
            </Link>{' '}
            for details. (Separate from Historical session drift
            below.)
          </span>
        </div>
      ) : null}

      {/* Section 1 — Session summary stat cards */}
      <div className="grid gap-3 grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Sessions"
          value={sessions?.length ?? 0}
          icon={BarChart2}
        />
        {(() => {
          const pnl = formatPnl(totalPnl);
          return (
            <StatCard
              title="Total Virtual P&L"
              value={<span className={pnl.className}>{pnl.text}</span>}
              icon={BarChart2}
            />
          );
        })()}
        <StatCard
          title="Overall Win Rate"
          value={
            overallWinRate != null ? `${overallWinRate.toFixed(1)}%` : '—'
          }
          icon={BarChart2}
        />
        <StatCard
          title="Profitable Sessions"
          value={profitableSessions}
          icon={BarChart2}
        />
      </div>

      {/* Section 2 — Model performance */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Model Performance</CardTitle>
          <CardDescription>
            Accuracy, drift status, and calibration metrics
          </CardDescription>
        </CardHeader>
        <CardContent>
          {!modelPerf ? (
            <EmptyState
              icon={BarChart2}
              title="No model performance data"
              description="Model performance data appears after the system has traded for multiple sessions."
            />
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-6">
              <MetricRow
                label="5-Day Accuracy"
                value={
                  modelPerf.accuracy_5d != null
                    ? `${(modelPerf.accuracy_5d * 100).toFixed(1)}%`
                    : '—'
                }
              />
              <MetricRow
                label="20-Day Accuracy"
                value={
                  modelPerf.accuracy_20d != null
                    ? `${(modelPerf.accuracy_20d * 100).toFixed(1)}%`
                    : '—'
                }
              />
              <MetricRow
                label="60-Day Accuracy"
                value={
                  modelPerf.accuracy_60d != null
                    ? `${(modelPerf.accuracy_60d * 100).toFixed(1)}%`
                    : '—'
                }
              />
              <MetricRow
                label="Profit Factor (20d)"
                value={
                  modelPerf.profit_factor_20d != null
                    ? modelPerf.profit_factor_20d.toFixed(2)
                    : '—'
                }
              />
              <MetricRow
                label="Drift Status"
                value={
                  <Badge
                    variant="outline"
                    className={`text-xs capitalize ${driftBadgeClass(
                      modelPerf.drift_status
                    )}`}
                  >
                    {modelPerf.drift_status ?? 'No data'}
                  </Badge>
                }
              />
              <MetricRow
                label="Drift Z-Score"
                value={
                  modelPerf.drift_z_score != null
                    ? modelPerf.drift_z_score.toFixed(2)
                    : '—'
                }
              />
              <MetricRow
                label="Preservation Triggers (week)"
                value={modelPerf.preservation_triggers_this_week ?? '—'}
              />
              <MetricRow
                label="Challenger Active"
                value={
                  <Badge
                    variant="outline"
                    className={
                      modelPerf.challenger_active
                        ? 'bg-success/10 text-success border-success/20'
                        : 'bg-muted text-muted-foreground border-border'
                    }
                  >
                    {modelPerf.challenger_active ? 'Yes' : 'No'}
                  </Badge>
                }
              />
            </div>
          )}
        </CardContent>
      </Card>

      {/* Section 3 — Recent sessions table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Recent Sessions</CardTitle>
          <CardDescription>Last 30 trading sessions</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {!sessions || sessions.length === 0 ? (
            <div className="p-6">
              <EmptyState
                icon={BarChart2}
                title="No sessions yet"
                description="Session data appears once the trading backend creates daily sessions."
              />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-muted/50">
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">
                      Date
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-muted-foreground">
                      P&L
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-muted-foreground">
                      Trades
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-muted-foreground">
                      Wins
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-muted-foreground">
                      Losses
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-muted-foreground">
                      Win Rate
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">
                      Regime
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">
                      Status
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {sessions.map((s) => {
                    const trades = s.virtual_trades_count ?? 0;
                    const wins = s.virtual_wins ?? 0;
                    const wr =
                      trades > 0
                        ? `${((wins / trades) * 100).toFixed(1)}%`
                        : '—';
                    const pnl = formatPnl(s.virtual_pnl);
                    return (
                      <tr
                        key={s.session_date}
                        className="hover:bg-muted/30 transition-colors"
                      >
                        <td className="px-4 py-3 font-mono text-xs">
                          {s.session_date}
                        </td>
                        <td
                          className={`px-4 py-3 text-right font-mono text-xs ${pnl.className}`}
                        >
                          {pnl.text}
                        </td>
                        <td className="px-4 py-3 text-right font-mono text-xs">
                          {trades}
                        </td>
                        <td className="px-4 py-3 text-right font-mono text-xs text-success">
                          {s.virtual_wins ?? 0}
                        </td>
                        <td className="px-4 py-3 text-right font-mono text-xs text-destructive">
                          {s.virtual_losses ?? 0}
                        </td>
                        <td className="px-4 py-3 text-right font-mono text-xs">
                          {wr}
                        </td>
                        <td className="px-4 py-3">
                          {s.regime ? (
                            <Badge
                              variant="outline"
                              className="text-xs capitalize bg-muted text-muted-foreground border-border"
                            >
                              {s.regime}
                            </Badge>
                          ) : (
                            <span className="text-xs text-muted-foreground">
                              —
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          <Badge
                            variant="outline"
                            className={`text-xs capitalize ${sessionStatusBadgeClass(
                              s.session_status
                            )}`}
                          >
                            {s.session_status}
                          </Badge>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Section 4 — Strategy Breakdown (Phase 4C) */}
      <StrategyBreakdownCard />

      {/* Section 5 — Missed Opportunities (Section 13 UI-4). Reads
          counterfactual P&L on no-trade cycles from the last 7 days
          and groups by no_trade_reason. Empty state during warmup. */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium">
            Missed Opportunities (This Week)
          </CardTitle>
          <CardDescription className="text-xs">
            Simulated P&amp;L on no-trade cycles, grouped by reason.
            Activates once the counterfactual engine has labeled
            ~30 sessions of no-trade data.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {missedOpportunities.length === 0 ? (
            <p className="text-sm text-muted-foreground italic">
              No counterfactual data yet — collecting from no-trade
              cycles.
            </p>
          ) : (
            <div className="space-y-2">
              {missedOpportunities.map(({ reason, count, avg, total }) => {
                const totalPnl = formatPnl(total);
                const avgPnl = formatPnl(avg);
                return (
                  <div
                    key={reason}
                    className="flex items-center justify-between gap-3 rounded-md border p-3 text-sm"
                  >
                    <span className="capitalize text-muted-foreground">
                      {reason.replace(/_/g, ' ')}
                    </span>
                    <div className="flex items-center gap-6 text-right">
                      <div>
                        <p className="text-xs text-muted-foreground">
                          cycles
                        </p>
                        <p className="font-mono text-sm">{count}</p>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">
                          avg
                        </p>
                        <p
                          className={`font-mono text-sm ${avgPnl.className}`}
                        >
                          {avgPnl.text}
                        </p>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">
                          total
                        </p>
                        <p
                          className={`font-mono text-sm font-semibold ${totalPnl.className}`}
                        >
                          {totalPnl.text}
                        </p>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
