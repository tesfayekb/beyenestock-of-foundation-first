/**
 * Signals — /admin/trading/signals
 * Phase 3B deliverable TPLAN-CONSOLE-003E
 *
 * Prediction engine output log — 100 most recent prediction cycles.
 */
import { useMemo } from 'react';
import { formatDistanceToNow } from 'date-fns';
import { Zap } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { PageHeader } from '@/components/dashboard/PageHeader';
import { StatCard } from '@/components/dashboard/StatCard';
import { LoadingSkeleton } from '@/components/dashboard/LoadingSkeleton';
import { ErrorState } from '@/components/dashboard/ErrorState';
import { EmptyState } from '@/components/dashboard/EmptyState';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { supabase } from '@/integrations/supabase/client';

interface PredictionOutputRow {
  id: string;
  predicted_at: string;
  direction: string | null;
  confidence: number | null;
  regime: string | null;
  rcs: number | null;
  cv_stress_score: number | null;
  no_trade_signal: boolean | null;
  no_trade_reason: string | null;
  capital_preservation_mode: boolean | null;
  p_bull: number | null;
  p_bear: number | null;
  p_neutral: number | null;
}

function directionBadgeClass(direction: string | null): string {
  if (!direction) return 'bg-muted text-muted-foreground border-border';
  const d = direction.toLowerCase();
  if (d === 'bull' || d === 'bullish')
    return 'bg-success/10 text-success border-success/20';
  if (d === 'bear' || d === 'bearish')
    return 'bg-destructive/10 text-destructive border-destructive/20';
  return 'bg-muted text-muted-foreground border-border';
}

function rcsClass(rcs: number | null): string {
  if (rcs == null) return 'text-muted-foreground';
  if (rcs >= 60) return 'text-success';
  if (rcs >= 40) return 'text-amber-500';
  return 'text-destructive';
}

function cvClass(cv: number | null): string {
  if (cv == null) return 'text-muted-foreground';
  if (cv <= 30) return 'text-success';
  if (cv <= 60) return 'text-amber-500';
  return 'text-destructive';
}

export default function TradingSignalsPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['trading', 'signals', 'log'],
    queryFn: async () => {
      const { data: rows, error: err } = await supabase
        .from('trading_prediction_outputs')
        .select(
          'id, predicted_at, direction, confidence, regime, rcs, cv_stress_score, no_trade_signal, no_trade_reason, capital_preservation_mode, p_bull, p_bear, p_neutral'
        )
        .order('predicted_at', { ascending: false })
        .limit(100);
      if (err) throw err;
      return (rows as PredictionOutputRow[]) ?? [];
    },
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });

  const noTradeCount = useMemo(
    () => data?.filter((r) => r.no_trade_signal).length ?? 0,
    [data]
  );

  const capitalPreservationCount = useMemo(
    () => data?.filter((r) => r.capital_preservation_mode).length ?? 0,
    [data]
  );

  const totalCount = data?.length ?? 0;

  if (isLoading) {
    return (
      <div className="space-y-6">
        <PageHeader title="Signals" subtitle="Prediction engine output log" />
        <LoadingSkeleton variant="card" rows={4} />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <PageHeader title="Signals" subtitle="Prediction engine output log" />
        <ErrorState message="Failed to load signals data." />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Signals" subtitle="Prediction engine output log" />

      {/* Stat cards */}
      <div className="grid gap-3 grid-cols-1 sm:grid-cols-3">
        <StatCard title="Total Signals" value={totalCount} icon={Zap} />
        <StatCard title="No-Trade Signals" value={noTradeCount} icon={Zap} />
        <StatCard
          title="Capital Preservation Active"
          value={capitalPreservationCount}
          icon={Zap}
        />
      </div>

      {/* Table */}
      {!data || data.length === 0 ? (
        <EmptyState
          icon={Zap}
          title="No prediction signals yet"
          description="Signals appear every 5 minutes during market hours."
        />
      ) : (
        <Card>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-muted/50">
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">
                      Time
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">
                      Direction
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-muted-foreground">
                      Confidence
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">
                      Regime
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-muted-foreground">
                      RCS
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-muted-foreground">
                      CV_Stress
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">
                      No-Trade
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">
                      Reason
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {data.map((row) => (
                    <tr
                      key={row.id}
                      className="hover:bg-muted/30 transition-colors"
                    >
                      <td className="px-4 py-3 text-xs text-muted-foreground whitespace-nowrap">
                        {formatDistanceToNow(new Date(row.predicted_at), {
                          addSuffix: true,
                        })}
                      </td>
                      <td className="px-4 py-3">
                        <Badge
                          variant="outline"
                          className={`text-xs capitalize ${directionBadgeClass(
                            row.direction
                          )}`}
                        >
                          {row.direction ?? 'none'}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-xs">
                        {row.confidence != null
                          ? `${(row.confidence * 100).toFixed(1)}%`
                          : '—'}
                      </td>
                      <td className="px-4 py-3">
                        {row.regime ? (
                          <Badge
                            variant="outline"
                            className="text-xs capitalize bg-muted text-muted-foreground border-border"
                          >
                            {row.regime}
                          </Badge>
                        ) : (
                          <span className="text-muted-foreground text-xs">—</span>
                        )}
                      </td>
                      <td
                        className={`px-4 py-3 text-right font-mono text-xs font-semibold ${rcsClass(
                          row.rcs
                        )}`}
                      >
                        {row.rcs != null ? row.rcs.toFixed(1) : '—'}
                      </td>
                      <td
                        className={`px-4 py-3 text-right font-mono text-xs font-semibold ${cvClass(
                          row.cv_stress_score
                        )}`}
                      >
                        {row.cv_stress_score != null
                          ? row.cv_stress_score.toFixed(1)
                          : '—'}
                      </td>
                      <td className="px-4 py-3">
                        {row.no_trade_signal ? (
                          <Badge
                            variant="outline"
                            className="text-xs bg-amber-500/10 text-amber-600 border-amber-500/20"
                          >
                            NO TRADE
                          </Badge>
                        ) : null}
                      </td>
                      <td className="px-4 py-3 text-xs text-muted-foreground max-w-[160px] truncate">
                        {row.no_trade_reason
                          ? row.no_trade_reason.slice(0, 30)
                          : null}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
