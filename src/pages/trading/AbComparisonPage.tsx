/**
 * A/B Validation Gate — /trading/ab-comparison
 *
 * Phase 3B dashboard. Visualises Portfolio A (rule-based shadow)
 * vs Portfolio B (live paper system) over the 90-day validation
 * window. The gate opens when ≥90 days, ≥100 closed trades, and
 * Portfolio B leads Portfolio A by ≥+8% annualized.
 *
 * Label note: while `agents:ai_synthesis:enabled` is OFF, Portfolio B
 * uses the same rule-based prediction logic as Portfolio A — the A/B
 * difference is "synthetic-P&L shadow vs live-execution paper trading"
 * rather than "rule-based vs AI". When the synthesis flag flips on,
 * Portfolio B starts consuming AI synthesis output and these labels
 * may be revised to reflect the AI-vs-rules contrast the gate was
 * originally designed to validate.
 *
 * Layout follows the MilestonesPage pattern: PageHeader, summary
 * card with progress bars, then a list of comparison cards / table.
 */
import {
    GitCompare,
    CheckCircle2,
    Clock,
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
import { useAbComparison, type AbDailyRow } from '@/hooks/trading/useAbComparison';

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

export default function AbComparisonPage() {
    const { data, isLoading, isError } = useAbComparison();

    const gate = data?.gate;
    const daily = data?.daily ?? [];

    const daysElapsed = gate?.days_elapsed ?? 0;
    const daysRequired = gate?.days_required ?? 90;
    const tradesCount = gate?.trades_count ?? 0;
    const tradesRequired = gate?.trades_required ?? 100;
    const lead = gate?.portfolio_b_lead_pct ?? null;
    const gatePassed = gate?.gate_passed ?? false;

    const daysPct = Math.min(100, (daysElapsed / daysRequired) * 100);
    const tradesPct = Math.min(100, (tradesCount / tradesRequired) * 100);
    const leadPct = lead === null
        ? 0
        : Math.max(0, Math.min(100, (lead / 8) * 100));

    // Most recent 30 rows for the table — daily comes back ascending,
    // so slice from the tail and reverse to display newest-first.
    const recentRows: AbDailyRow[] = [...daily].slice(-30).reverse();

    return (
        <div className="space-y-6">
            <PageHeader
                title="A/B Validation Gate"
                subtitle="Portfolio A (rule-based shadow) vs Portfolio B (live paper system)"
            />

            {isError && (
                <Card className="border-destructive/30 bg-destructive/5">
                    <CardContent className="pt-6">
                        <p className="text-sm text-destructive">
                            Failed to fetch A/B status. The endpoint may
                            be unavailable or the migration has not been
                            applied yet.
                        </p>
                    </CardContent>
                </Card>
            )}

            {/* Gate status banner */}
            <Card
                className={
                    gatePassed
                        ? 'border-success/30 bg-success/5'
                        : 'border-primary/20'
                }
            >
                <CardHeader className="pb-3">
                    <CardTitle className="flex items-center gap-2 text-base">
                        {gatePassed ? (
                            <CheckCircle2 className="h-5 w-5 text-success" />
                        ) : (
                            <Clock className="h-5 w-5 text-primary" />
                        )}
                        {gatePassed
                            ? 'Gate passed — system validated for real capital deployment'
                            : 'Gate pending — collecting validation data'}
                        {gatePassed && (
                            <Badge
                                variant="outline"
                                className="ml-2 bg-success/10 text-success border-success/20"
                            >
                                PASSED
                            </Badge>
                        )}
                    </CardTitle>
                </CardHeader>
                <CardContent className="space-y-5">
                    {/* Days elapsed */}
                    <div>
                        <div className="flex items-center justify-between text-sm mb-1.5">
                            <span className="text-muted-foreground">
                                Days elapsed
                            </span>
                            <span className="font-mono font-medium">
                                {daysElapsed} / {daysRequired}
                            </span>
                        </div>
                        <div className="h-2 rounded-full bg-muted overflow-hidden">
                            <div
                                className={`h-full rounded-full transition-all duration-500 ${
                                    daysElapsed >= daysRequired
                                        ? 'bg-success'
                                        : 'bg-primary'
                                }`}
                                style={{ width: `${daysPct}%` }}
                            />
                        </div>
                    </div>

                    {/* Trades closed */}
                    <div>
                        <div className="flex items-center justify-between text-sm mb-1.5">
                            <span className="text-muted-foreground">
                                Closed trades (Portfolio B)
                            </span>
                            <span className="font-mono font-medium">
                                {tradesCount} / {tradesRequired}
                            </span>
                        </div>
                        <div className="h-2 rounded-full bg-muted overflow-hidden">
                            <div
                                className={`h-full rounded-full transition-all duration-500 ${
                                    tradesCount >= tradesRequired
                                        ? 'bg-success'
                                        : 'bg-primary'
                                }`}
                                style={{ width: `${tradesPct}%` }}
                            />
                        </div>
                    </div>

                    {/* Portfolio B lead vs A */}
                    <div>
                        <div className="flex items-center justify-between text-sm mb-1.5">
                            <span className="text-muted-foreground">
                                Portfolio B lead vs A (annualized, target +8%)
                            </span>
                            <span
                                className={`font-mono font-medium ${pnlColor(
                                    lead,
                                )}`}
                            >
                                {lead === null ? '—' : formatPct(lead)}
                            </span>
                        </div>
                        <div className="h-2 rounded-full bg-muted overflow-hidden">
                            <div
                                className={`h-full rounded-full transition-all duration-500 ${
                                    lead !== null && lead >= 8
                                        ? 'bg-success'
                                        : 'bg-primary'
                                }`}
                                style={{ width: `${leadPct}%` }}
                            />
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Comparison stats */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                <Card>
                    <CardContent className="pt-5">
                        <p className="text-xs uppercase tracking-wide text-muted-foreground">
                            Portfolio A total P&L
                        </p>
                        <p
                            className={`mt-1 text-2xl font-bold font-mono ${pnlColor(
                                gate?.a_total_pnl,
                            )}`}
                        >
                            {formatCurrency(gate?.a_total_pnl)}
                        </p>
                        <p className="text-xs text-muted-foreground mt-1">
                            Rule-based shadow
                        </p>
                    </CardContent>
                </Card>
                <Card>
                    <CardContent className="pt-5">
                        <p className="text-xs uppercase tracking-wide text-muted-foreground">
                            Portfolio B total P&L
                        </p>
                        <p
                            className={`mt-1 text-2xl font-bold font-mono ${pnlColor(
                                gate?.b_total_pnl,
                            )}`}
                        >
                            {formatCurrency(gate?.b_total_pnl)}
                        </p>
                        <p className="text-xs text-muted-foreground mt-1">
                            Live paper system
                        </p>
                    </CardContent>
                </Card>
                <Card>
                    <CardContent className="pt-5">
                        <p className="text-xs uppercase tracking-wide text-muted-foreground">
                            A annualized
                        </p>
                        <p
                            className={`mt-1 text-2xl font-bold font-mono ${pnlColor(
                                gate?.a_annualized_pct,
                            )}`}
                        >
                            {formatPct(gate?.a_annualized_pct)}
                        </p>
                        <p className="text-xs text-muted-foreground mt-1">
                            On $100k account
                        </p>
                    </CardContent>
                </Card>
                <Card>
                    <CardContent className="pt-5">
                        <p className="text-xs uppercase tracking-wide text-muted-foreground">
                            B annualized
                        </p>
                        <p
                            className={`mt-1 text-2xl font-bold font-mono ${pnlColor(
                                gate?.b_annualized_pct,
                            )}`}
                        >
                            {formatPct(gate?.b_annualized_pct)}
                        </p>
                        <p className="text-xs text-muted-foreground mt-1">
                            On $100k account
                        </p>
                    </CardContent>
                </Card>
            </div>

            {/* Daily comparison table */}
            <Card>
                <CardHeader className="pb-2">
                    <CardTitle className="text-base flex items-center gap-2">
                        <GitCompare className="h-4 w-4 text-primary" />
                        Daily comparison
                        <Badge variant="outline" className="text-xs ml-1">
                            last 30 days
                        </Badge>
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    {isLoading ? (
                        <p className="text-sm text-muted-foreground py-4">
                            Loading…
                        </p>
                    ) : recentRows.length === 0 ? (
                        <p className="text-sm text-muted-foreground py-4">
                            Shadow tracking started — first comparison
                            appears after today's market close.
                        </p>
                    ) : (
                        <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                                <thead>
                                    <tr className="border-b text-xs uppercase tracking-wide text-muted-foreground">
                                        <th className="text-left font-medium py-2 pr-4">
                                            Date
                                        </th>
                                        <th className="text-right font-medium py-2 px-3">
                                            A P&L
                                        </th>
                                        <th className="text-right font-medium py-2 px-3">
                                            B P&L
                                        </th>
                                        <th className="text-right font-medium py-2 px-3">
                                            SPX move
                                        </th>
                                        <th className="text-left font-medium py-2 pl-3">
                                            A regime
                                        </th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {recentRows.map((row) => (
                                        <tr
                                            key={row.session_date}
                                            className="border-b last:border-0 hover:bg-muted/30"
                                        >
                                            <td className="py-2 pr-4 font-mono text-xs">
                                                {row.session_date}
                                            </td>
                                            <td
                                                className={`py-2 px-3 text-right font-mono ${pnlColor(
                                                    row.a_synthetic_pnl,
                                                )}`}
                                            >
                                                <span className="inline-flex items-center gap-1.5 justify-end">
                                                    <PnlIcon
                                                        value={row.a_synthetic_pnl}
                                                    />
                                                    {row.a_no_trade
                                                        ? 'no trade'
                                                        : formatCurrency(
                                                              row.a_synthetic_pnl,
                                                          )}
                                                </span>
                                            </td>
                                            <td
                                                className={`py-2 px-3 text-right font-mono ${pnlColor(
                                                    row.b_session_pnl,
                                                )}`}
                                            >
                                                <span className="inline-flex items-center gap-1.5 justify-end">
                                                    <PnlIcon
                                                        value={row.b_session_pnl}
                                                    />
                                                    {row.b_no_trade
                                                        ? 'no trade'
                                                        : formatCurrency(
                                                              row.b_session_pnl,
                                                          )}
                                                </span>
                                            </td>
                                            <td className="py-2 px-3 text-right font-mono text-muted-foreground">
                                                {row.move_pct === null ||
                                                row.move_pct === undefined
                                                    ? '—'
                                                    : `${(
                                                          row.move_pct * 100
                                                      ).toFixed(2)}%`}
                                            </td>
                                            <td className="py-2 pl-3">
                                                <Badge
                                                    variant="outline"
                                                    className="text-xs"
                                                >
                                                    {row.a_regime ?? 'unknown'}
                                                </Badge>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}
