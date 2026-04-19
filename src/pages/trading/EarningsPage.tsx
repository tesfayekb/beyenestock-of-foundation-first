/**
 * Earnings Volatility System — /trading/earnings
 *
 * Phase 5A dashboard. Surfaces the standalone earnings straddle
 * system that runs alongside the SPX engine in backend_earnings/.
 *
 * Layout follows the AbComparisonPage pattern: PageHeader →
 * (mandatory) tax warning banner → upcoming events → active
 * position → historical performance table → hardcoded edge
 * summary table.
 *
 * The edge summary table data is HARDCODED from the spec — it
 * does not reflect live calculator state, just the static
 * historical baseline used for the entry filter.
 */
import {
    AlertTriangle,
    CalendarClock,
    Briefcase,
    Activity,
    TrendingUp,
    TrendingDown,
    Minus,
} from 'lucide-react';
import { PageHeader } from '@/components/dashboard/PageHeader';
import {
    Card,
    CardContent,
    CardHeader,
    CardTitle,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
    useEarningsStatus,
    type EarningsRecentPosition,
} from '@/hooks/trading/useEarningsStatus';

// Hardcoded edge baseline — mirrors EARNINGS_HISTORY in
// backend_earnings/edge_calculator.py. Keep these two lists in
// sync when the calculator history is refreshed each quarter.
interface EdgeRow {
    ticker: string;
    beat_rate: number;
    avg_actual_move_pct: number;
    avg_implied_move_pct: number;
}

const EDGE_BASELINE: EdgeRow[] = [
    { ticker: 'NVDA', beat_rate: 0.75, avg_actual_move_pct: 8.6, avg_implied_move_pct: 6.2 },
    { ticker: 'META', beat_rate: 0.67, avg_actual_move_pct: 7.8, avg_implied_move_pct: 6.1 },
    { ticker: 'AAPL', beat_rate: 0.58, avg_actual_move_pct: 4.2, avg_implied_move_pct: 3.5 },
    { ticker: 'TSLA', beat_rate: 0.67, avg_actual_move_pct: 10.8, avg_implied_move_pct: 9.1 },
    { ticker: 'AMZN', beat_rate: 0.67, avg_actual_move_pct: 7.1, avg_implied_move_pct: 5.8 },
    { ticker: 'GOOGL', beat_rate: 0.58, avg_actual_move_pct: 6.2, avg_implied_move_pct: 5.1 },
];

function formatCurrency(n: number | null | undefined): string {
    if (n === null || n === undefined) return '—';
    const sign = n >= 0 ? '+' : '−';
    return `${sign}$${Math.abs(n).toFixed(2)}`;
}

function formatPct(n: number | null | undefined, digits = 2): string {
    if (n === null || n === undefined) return '—';
    const sign = n >= 0 ? '+' : '−';
    return `${sign}${Math.abs(n).toFixed(digits)}%`;
}

function formatMovePct(fraction: number | null | undefined): string {
    if (fraction === null || fraction === undefined) return '—';
    return formatPct(fraction * 100);
}

function pnlColor(n: number | null | undefined): string {
    if (n === null || n === undefined) return 'text-muted-foreground';
    if (n > 0) return 'text-success';
    if (n < 0) return 'text-destructive';
    return 'text-muted-foreground';
}

function PnlIcon({ value }: { value: number | null | undefined }) {
    if (value === null || value === undefined) {
        return <Minus className="h-3.5 w-3.5 text-muted-foreground" />;
    }
    if (value > 0) {
        return <TrendingUp className="h-3.5 w-3.5 text-success" />;
    }
    if (value < 0) {
        return <TrendingDown className="h-3.5 w-3.5 text-destructive" />;
    }
    return <Minus className="h-3.5 w-3.5 text-muted-foreground" />;
}

function formatScanTimestamp(iso: string | null): string {
    if (!iso) return 'never';
    try {
        return new Date(iso).toLocaleString();
    } catch {
        return iso;
    }
}

export default function EarningsPage() {
    const { data, isLoading, isError } = useEarningsStatus();

    const upcoming = data?.upcoming ?? [];
    const active = data?.active ?? null;
    const recent: EarningsRecentPosition[] = data?.recent_positions ?? [];
    const lastScanAt = data?.last_scan_at ?? null;

    return (
        <div className="space-y-6">
            <PageHeader
                title="Earnings Volatility System"
                subtitle="Phase 5A — ATM straddles on NVDA / AAPL / META / TSLA / AMZN / GOOGL"
            />

            {/* TAX WARNING — must be the first content element on the page */}
            <Card className="border-warning/40 bg-warning/5">
                <CardContent className="pt-5">
                    <div className="flex items-start gap-3">
                        <AlertTriangle className="h-5 w-5 text-warning mt-0.5 flex-shrink-0" />
                        <div className="space-y-1">
                            <p className="text-sm font-semibold text-warning-foreground">
                                Tax treatment notice — NOT Section 1256
                            </p>
                            <p className="text-sm text-muted-foreground leading-relaxed">
                                Individual equity options (NVDA, AAPL, META,
                                TSLA, AMZN, GOOGL) are NOT Section 1256
                                contracts. Standard short-term / long-term
                                capital gains rules apply — different from
                                the core SPX system's 60/40 treatment.
                                Consult your tax advisor before deploying
                                real capital on this strategy.
                            </p>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {isError && (
                <Card className="border-destructive/30 bg-destructive/5">
                    <CardContent className="pt-6">
                        <p className="text-sm text-destructive">
                            Failed to fetch earnings status. The endpoint
                            may be unavailable or the migration has not
                            been applied yet.
                        </p>
                    </CardContent>
                </Card>
            )}

            {/* Upcoming events */}
            <Card>
                <CardHeader className="pb-2">
                    <CardTitle className="text-base flex items-center gap-2">
                        <CalendarClock className="h-4 w-4 text-primary" />
                        Upcoming earnings events
                        <Badge variant="outline" className="text-xs ml-1">
                            next 14 days
                        </Badge>
                        <span className="ml-auto text-xs font-normal text-muted-foreground">
                            Last scan: {formatScanTimestamp(lastScanAt)}
                        </span>
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    {isLoading ? (
                        <p className="text-sm text-muted-foreground py-4">
                            Loading…
                        </p>
                    ) : upcoming.length === 0 ? (
                        <p className="text-sm text-muted-foreground py-4">
                            Earnings scan runs at 8:45 AM ET. First event
                            appears after scan.
                        </p>
                    ) : (
                        <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                                <thead>
                                    <tr className="border-b text-xs uppercase tracking-wide text-muted-foreground">
                                        <th className="text-left font-medium py-2 pr-4">
                                            Ticker
                                        </th>
                                        <th className="text-left font-medium py-2 px-3">
                                            Earnings
                                        </th>
                                        <th className="text-left font-medium py-2 px-3">
                                            Announce
                                        </th>
                                        <th className="text-left font-medium py-2 px-3">
                                            Entry date
                                        </th>
                                        <th className="text-right font-medium py-2 px-3">
                                            Edge
                                        </th>
                                        <th className="text-left font-medium py-2 pl-3">
                                            Decision
                                        </th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {upcoming.map((ev) => (
                                        <tr
                                            key={`${ev.ticker}-${ev.earnings_date}`}
                                            className="border-b last:border-0 hover:bg-muted/30"
                                        >
                                            <td className="py-2 pr-4 font-mono font-medium">
                                                {ev.ticker}
                                            </td>
                                            <td className="py-2 px-3 font-mono text-xs">
                                                {ev.earnings_date}
                                            </td>
                                            <td className="py-2 px-3">
                                                <Badge
                                                    variant="outline"
                                                    className="text-xs"
                                                >
                                                    {ev.announce_time}
                                                </Badge>
                                            </td>
                                            <td className="py-2 px-3 font-mono text-xs">
                                                {ev.entry_date ?? '—'}
                                            </td>
                                            <td className="py-2 px-3 text-right font-mono">
                                                {ev.edge_score === null ||
                                                ev.edge_score === undefined
                                                    ? '—'
                                                    : ev.edge_score.toFixed(3)}
                                            </td>
                                            <td className="py-2 pl-3">
                                                {ev.should_enter ? (
                                                    <Badge className="bg-success/15 text-success border-success/30 text-xs">
                                                        ENTER
                                                    </Badge>
                                                ) : (
                                                    <Badge
                                                        variant="outline"
                                                        className="text-xs text-muted-foreground"
                                                    >
                                                        skip
                                                    </Badge>
                                                )}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* Active position */}
            <Card>
                <CardHeader className="pb-2">
                    <CardTitle className="text-base flex items-center gap-2">
                        <Briefcase className="h-4 w-4 text-primary" />
                        Active position
                        {active ? (
                            <Badge className="bg-primary/15 text-primary border-primary/30 text-xs ml-1">
                                {active.ticker}
                            </Badge>
                        ) : (
                            <Badge
                                variant="outline"
                                className="text-xs ml-1 text-muted-foreground"
                            >
                                none
                            </Badge>
                        )}
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    {!active ? (
                        <p className="text-sm text-muted-foreground py-2">
                            No open earnings straddle. Entry job runs at
                            9:50 AM ET on each candidate's preferred entry
                            day. Only one position open at a time.
                        </p>
                    ) : (
                        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
                            <Stat
                                label="Earnings date"
                                value={active.earnings_date}
                            />
                            <Stat
                                label="Entry date"
                                value={active.entry_date ?? '—'}
                            />
                            <Stat
                                label="Expiry"
                                value={active.expiry_date ?? '—'}
                            />
                            <Stat
                                label="Strike"
                                value={
                                    active.call_strike
                                        ? `$${active.call_strike.toFixed(2)}`
                                        : '—'
                                }
                            />
                            <Stat
                                label="Contracts"
                                value={
                                    active.contracts !== undefined &&
                                    active.contracts !== null
                                        ? String(active.contracts)
                                        : '—'
                                }
                            />
                            <Stat
                                label="Total debit"
                                value={
                                    active.total_debit !== undefined &&
                                    active.total_debit !== null
                                        ? `$${active.total_debit.toFixed(2)}`
                                        : '—'
                                }
                            />
                            <Stat
                                label="Implied move"
                                value={formatMovePct(active.implied_move_pct)}
                            />
                            <Stat
                                label="Historical edge"
                                value={
                                    active.historical_edge_score === undefined ||
                                    active.historical_edge_score === null
                                        ? '—'
                                        : active.historical_edge_score.toFixed(
                                              3,
                                          )
                                }
                            />
                            <Stat
                                label="Stock @ entry"
                                value={
                                    active.stock_price_at_entry
                                        ? `$${active.stock_price_at_entry.toFixed(2)}`
                                        : '—'
                                }
                            />
                            <Stat
                                label="Announce"
                                value={active.announce_time ?? '—'}
                            />
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* Recent positions / historical performance */}
            <Card>
                <CardHeader className="pb-2">
                    <CardTitle className="text-base flex items-center gap-2">
                        <Activity className="h-4 w-4 text-primary" />
                        Historical performance
                        <Badge variant="outline" className="text-xs ml-1">
                            last 30 positions
                        </Badge>
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    {isLoading ? (
                        <p className="text-sm text-muted-foreground py-4">
                            Loading…
                        </p>
                    ) : recent.length === 0 ? (
                        <p className="text-sm text-muted-foreground py-4">
                            No earnings positions yet. First entry can fire
                            on the next candidate's preferred entry day at
                            9:50 AM ET.
                        </p>
                    ) : (
                        <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                                <thead>
                                    <tr className="border-b text-xs uppercase tracking-wide text-muted-foreground">
                                        <th className="text-left font-medium py-2 pr-4">
                                            Ticker
                                        </th>
                                        <th className="text-left font-medium py-2 px-3">
                                            Entry → Exit
                                        </th>
                                        <th className="text-left font-medium py-2 px-3">
                                            Status
                                        </th>
                                        <th className="text-right font-medium py-2 px-3">
                                            Debit
                                        </th>
                                        <th className="text-right font-medium py-2 px-3">
                                            Exit value
                                        </th>
                                        <th className="text-right font-medium py-2 px-3">
                                            Net P&L
                                        </th>
                                        <th className="text-right font-medium py-2 px-3">
                                            Implied / Actual
                                        </th>
                                        <th className="text-left font-medium py-2 pl-3">
                                            Reason
                                        </th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {recent.map((row) => (
                                        <tr
                                            key={row.id}
                                            className="border-b last:border-0 hover:bg-muted/30"
                                        >
                                            <td className="py-2 pr-4 font-mono font-medium">
                                                {row.ticker}
                                            </td>
                                            <td className="py-2 px-3 font-mono text-xs text-muted-foreground">
                                                {row.entry_date}
                                                {' → '}
                                                {row.exit_date ?? '…'}
                                            </td>
                                            <td className="py-2 px-3">
                                                <Badge
                                                    variant="outline"
                                                    className={`text-xs ${
                                                        row.status === 'open'
                                                            ? 'text-primary border-primary/30'
                                                            : ''
                                                    }`}
                                                >
                                                    {row.status}
                                                </Badge>
                                            </td>
                                            <td className="py-2 px-3 text-right font-mono">
                                                {row.total_debit === null
                                                    ? '—'
                                                    : `$${row.total_debit.toFixed(2)}`}
                                            </td>
                                            <td className="py-2 px-3 text-right font-mono">
                                                {row.exit_value === null
                                                    ? '—'
                                                    : `$${row.exit_value.toFixed(2)}`}
                                            </td>
                                            <td
                                                className={`py-2 px-3 text-right font-mono ${pnlColor(
                                                    row.net_pnl,
                                                )}`}
                                            >
                                                <span className="inline-flex items-center gap-1.5 justify-end">
                                                    <PnlIcon value={row.net_pnl} />
                                                    {formatCurrency(row.net_pnl)}
                                                </span>
                                                {row.net_pnl_pct !== null &&
                                                    row.net_pnl_pct !==
                                                        undefined && (
                                                        <span className="block text-xs text-muted-foreground">
                                                            {formatPct(
                                                                row.net_pnl_pct *
                                                                    100,
                                                            )}
                                                        </span>
                                                    )}
                                            </td>
                                            <td className="py-2 px-3 text-right font-mono text-xs text-muted-foreground">
                                                {formatMovePct(
                                                    row.implied_move_pct,
                                                )}
                                                {' / '}
                                                {formatMovePct(
                                                    row.actual_move_pct,
                                                )}
                                            </td>
                                            <td className="py-2 pl-3 text-xs text-muted-foreground">
                                                {row.exit_reason ?? '—'}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* Static edge baseline — HARDCODED from spec */}
            <Card>
                <CardHeader className="pb-2">
                    <CardTitle className="text-base flex items-center gap-2">
                        <TrendingUp className="h-4 w-4 text-primary" />
                        Edge baseline
                        <Badge variant="outline" className="text-xs ml-1">
                            historical reference
                        </Badge>
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <p className="text-xs text-muted-foreground mb-3">
                        Static baseline used by the entry filter. Actual
                        moves consistently exceeding implied moves is the
                        edge being captured. Update each quarter after
                        earnings season.
                    </p>
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="border-b text-xs uppercase tracking-wide text-muted-foreground">
                                    <th className="text-left font-medium py-2 pr-4">
                                        Ticker
                                    </th>
                                    <th className="text-right font-medium py-2 px-3">
                                        Beat rate
                                    </th>
                                    <th className="text-right font-medium py-2 px-3">
                                        Avg actual move
                                    </th>
                                    <th className="text-right font-medium py-2 px-3">
                                        Avg implied move
                                    </th>
                                    <th className="text-right font-medium py-2 pl-3">
                                        Edge ratio
                                    </th>
                                </tr>
                            </thead>
                            <tbody>
                                {EDGE_BASELINE.map((row) => {
                                    const ratio =
                                        row.avg_implied_move_pct > 0
                                            ? row.avg_actual_move_pct /
                                              row.avg_implied_move_pct
                                            : 0;
                                    return (
                                        <tr
                                            key={row.ticker}
                                            className="border-b last:border-0 hover:bg-muted/30"
                                        >
                                            <td className="py-2 pr-4 font-mono font-medium">
                                                {row.ticker}
                                            </td>
                                            <td className="py-2 px-3 text-right font-mono">
                                                {(row.beat_rate * 100).toFixed(0)}
                                                %
                                            </td>
                                            <td className="py-2 px-3 text-right font-mono">
                                                {row.avg_actual_move_pct.toFixed(
                                                    1,
                                                )}
                                                %
                                            </td>
                                            <td className="py-2 px-3 text-right font-mono">
                                                {row.avg_implied_move_pct.toFixed(
                                                    1,
                                                )}
                                                %
                                            </td>
                                            <td
                                                className={`py-2 pl-3 text-right font-mono ${
                                                    ratio > 1
                                                        ? 'text-success'
                                                        : 'text-muted-foreground'
                                                }`}
                                            >
                                                {ratio.toFixed(2)}×
                                            </td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}

function Stat({ label, value }: { label: string; value: string }) {
    return (
        <div>
            <p className="text-xs uppercase tracking-wide text-muted-foreground">
                {label}
            </p>
            <p className="mt-1 text-sm font-mono font-medium">{value}</p>
        </div>
    );
}
