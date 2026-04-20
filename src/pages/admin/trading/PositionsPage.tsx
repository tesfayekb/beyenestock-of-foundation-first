/**
 * Positions — /admin/trading/positions
 * Phase 3B deliverable TPLAN-CONSOLE-003D
 *
 * Filterable virtual positions table. No detail drawer — Phase 4.
 */
import { useMemo, useState } from 'react';
import { formatDistanceToNow } from 'date-fns';
import { TrendingUp } from 'lucide-react';
import { PageHeader } from '@/components/dashboard/PageHeader';
import { StatCard } from '@/components/dashboard/StatCard';
import { LoadingSkeleton } from '@/components/dashboard/LoadingSkeleton';
import { ErrorState } from '@/components/dashboard/ErrorState';
import { EmptyState } from '@/components/dashboard/EmptyState';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import {
  useTradingPositions,
  type PositionStatusFilter,
} from '@/hooks/trading/useTradingPositions';
import { formatPnl } from '@/lib/format-pnl';

const TABS: { label: string; value: PositionStatusFilter }[] = [
  { label: 'All', value: 'all' },
  { label: 'Open', value: 'open' },
  { label: 'Closed', value: 'closed' },
];

function statusBadgeClass(status: string): string {
  const s = status.toLowerCase();
  if (s === 'open') return 'bg-success/10 text-success border-success/20';
  if (s === 'closed') return 'bg-muted text-muted-foreground border-border';
  if (s === 'cancelled') return 'bg-destructive/10 text-destructive border-destructive/20';
  return 'bg-muted text-muted-foreground border-border';
}

function positionTypeBadgeClass(type: string | null): string {
  if (!type) return 'bg-muted text-muted-foreground border-border';
  return type.toLowerCase() === 'core'
    ? 'bg-blue-500/10 text-blue-600 border-blue-500/20'
    : 'bg-muted text-muted-foreground border-border';
}

function capitalizeWords(str: string | null): string {
  if (!str) return '—';
  return str
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function TradingPositionsPage() {
  const [activeTab, setActiveTab] = useState<PositionStatusFilter>('all');

  const { data, isLoading, error } = useTradingPositions({ status: activeTab });

  const totalPnl = useMemo(() => {
    if (!data) return null;
    return data.reduce((sum, p) => {
      const v = p.status === 'closed' ? (p.net_pnl ?? 0) : (p.current_pnl ?? 0);
      return sum + v;
    }, 0);
  }, [data]);

  const openCount = useMemo(
    () => data?.filter((p) => p.status === 'open').length ?? 0,
    [data]
  );

  const closedCount = useMemo(
    () => data?.filter((p) => p.status === 'closed').length ?? 0,
    [data]
  );

  const totalCount = data?.length ?? 0;

  if (isLoading) {
    return (
      <div className="space-y-6">
        <PageHeader title="Positions" subtitle="Virtual trading positions" />
        <LoadingSkeleton variant="card" rows={4} />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <PageHeader title="Positions" subtitle="Virtual trading positions" />
        <ErrorState message="Failed to load positions data." />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Positions" subtitle="Virtual trading positions" />

      {/* Stat cards */}
      <div className="grid gap-3 grid-cols-2 lg:grid-cols-4">
        <StatCard title="Total Positions" value={totalCount} icon={TrendingUp} />
        <StatCard title="Open" value={openCount} icon={TrendingUp} />
        <StatCard title="Closed" value={closedCount} icon={TrendingUp} />
        {(() => {
          const pnl = formatPnl(totalPnl);
          return (
            <StatCard
              title="Total Virtual P&L"
              value={<span className={pnl.className}>{pnl.text}</span>}
              icon={TrendingUp}
            />
          );
        })()}
      </div>

      {/* Tab filter */}
      <div className="flex gap-1 rounded-md border p-1 w-fit">
        {TABS.map((tab) => (
          <button
            key={tab.value}
            onClick={() => setActiveTab(tab.value)}
            className={`rounded px-3 py-1 text-sm font-medium transition-colors ${
              activeTab === tab.value
                ? 'bg-primary text-primary-foreground'
                : 'text-muted-foreground hover:text-foreground hover:bg-muted'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Table */}
      {!data || data.length === 0 ? (
        <EmptyState
          icon={TrendingUp}
          title="No positions found"
          description="Virtual positions appear here once the trading cycle generates a signal during market hours."
        />
      ) : (
        <Card>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-muted/50">
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">
                      #
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">
                      Instrument
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">
                      Strategy
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">
                      Type
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-muted-foreground">
                      Contracts
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-muted-foreground">
                      Entry Credit
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">
                      Entry Regime
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-muted-foreground">
                      Entry RCS
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-muted-foreground">
                      P&L
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">
                      Status
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">
                      Entry At
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {data.map((pos, idx) => {
                    const rawPnl =
                      pos.status === 'closed' ? pos.net_pnl : pos.current_pnl;
                    const pnl = formatPnl(rawPnl);
                    return (
                      <tr
                        key={pos.id}
                        className="hover:bg-muted/30 transition-colors"
                      >
                        <td className="px-4 py-3 text-muted-foreground font-mono text-xs">
                          {idx + 1}
                        </td>
                        <td className="px-4 py-3 font-medium">
                          {pos.instrument ?? '—'}
                        </td>
                        <td className="px-4 py-3">
                          {capitalizeWords(pos.strategy_type)}
                        </td>
                        <td className="px-4 py-3">
                          <Badge
                            variant="outline"
                            className={`text-xs capitalize ${positionTypeBadgeClass(
                              pos.position_type
                            )}`}
                          >
                            {pos.position_type ?? '—'}
                          </Badge>
                        </td>
                        <td className="px-4 py-3 text-right font-mono">
                          {pos.contracts ?? '—'}
                        </td>
                        <td className="px-4 py-3 text-right font-mono">
                          {pos.entry_credit != null
                            ? `$${pos.entry_credit.toFixed(2)}`
                            : '—'}
                        </td>
                        <td className="px-4 py-3">
                          {pos.entry_regime ? (
                            <Badge
                              variant="outline"
                              className="text-xs capitalize bg-muted text-muted-foreground border-border"
                            >
                              {pos.entry_regime}
                            </Badge>
                          ) : (
                            <span className="text-muted-foreground">—</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-right font-mono">
                          {pos.entry_rcs != null
                            ? pos.entry_rcs.toFixed(1)
                            : '—'}
                        </td>
                        <td
                          className={`px-4 py-3 text-right font-mono ${pnl.className}`}
                        >
                          {pnl.text}
                        </td>
                        <td className="px-4 py-3">
                          <Badge
                            variant="outline"
                            className={`text-xs capitalize ${statusBadgeClass(
                              pos.status
                            )}`}
                          >
                            {pos.status}
                          </Badge>
                        </td>
                        <td className="px-4 py-3 text-xs text-muted-foreground whitespace-nowrap">
                          {pos.entry_at
                            ? formatDistanceToNow(new Date(pos.entry_at), {
                                addSuffix: true,
                              })
                            : '—'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
