/**
 * Learning Dashboard — /trading/learning
 * Section 13 UI Observability Sprint — Item UI-1.
 *
 * Read-only operator observability for Section 12's adaptive
 * systems. Every panel has an explicit warmup state so an operator
 * never sees null / undefined / NaN while Redis is populating.
 *
 * Data source: Supabase Edge Function `get-learning-stats`, which
 * proxies to Railway's GET /admin/trading/learning-stats. See
 * src/hooks/trading/useLearningStats.ts for the shape.
 */
import { useMemo } from 'react';
import {
    Activity,
    AlertTriangle,
    BarChart2,
    CheckCircle,
    Gauge,
    Layers,
    ShieldAlert,
    Sliders,
} from 'lucide-react';
import { PageHeader } from '@/components/dashboard/PageHeader';
import { LoadingSkeleton } from '@/components/dashboard/LoadingSkeleton';
import { ErrorState } from '@/components/dashboard/ErrorState';
import { Badge } from '@/components/ui/badge';
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from '@/components/ui/card';
import { formatPnl } from '@/lib/format-pnl';
import {
    useLearningStats,
    type LearningStats,
    type StrategyMatrixCell,
} from '@/hooks/trading/useLearningStats';

// Default butterfly threshold values — must match backend defaults
// in backend/butterfly_threshold_calibrator.py and the fail-open
// skeleton in supabase/functions/get-learning-stats/index.ts.
const BUTTERFLY_DEFAULTS = {
    gex_conf: 0.40,
    wall_distance: 0.003,
    concentration: 0.25,
} as const;

const DEFAULT_HALT_THRESHOLD_PCT = -0.03;

// Mirror the fixed 6-reason list surfaced by the backend. Backend
// writes the same keys — keeping this list here as a presentation
// contract so the UI stays stable if backend reorders them.
const BUTTERFLY_REASONS = [
    'regime_mismatch',
    'time_gate',
    'failed_today',
    'low_concentration',
    'wall_unstable',
    'drawdown_block',
] as const;

const REASON_LABELS: Record<(typeof BUTTERFLY_REASONS)[number], string> = {
    regime_mismatch: 'Regime mismatch',
    time_gate: 'Time gate',
    failed_today: 'Failed today',
    low_concentration: 'Low concentration',
    wall_unstable: 'Wall unstable',
    drawdown_block: 'Drawdown block',
};

function formatPct(value: number | null | undefined, digits = 2): string {
    if (value === null || value === undefined || Number.isNaN(value)) {
        return '—';
    }
    return `${(value * 100).toFixed(digits)}%`;
}

function formatNumber(
    value: number | null | undefined,
    digits = 2,
): string {
    if (value === null || value === undefined || Number.isNaN(value)) {
        return '—';
    }
    return value.toFixed(digits);
}

function formatIsoTimestamp(value: string | null | undefined): string {
    if (!value) return '—';
    // The backend stores either a plain ISO timestamp or a
    // "phase|timestamp" audit string — strip the phase prefix if
    // present so the UI always shows just a human timestamp.
    const raw = value.includes('|') ? value.split('|')[1] : value;
    const parsed = new Date(raw);
    if (Number.isNaN(parsed.getTime())) return raw;
    return parsed.toLocaleString();
}

// ── Panel 1 — IV/RV Ratio ──────────────────────────────────────────
function IvRvPanel({ data }: { data: LearningStats }) {
    const rv = data.realized_vol_20d;
    const vix = data.vix_current;
    const ratio = data.iv_rv_ratio;

    const ratioColor =
        ratio === null
            ? 'text-muted-foreground'
            : ratio > 1.1
            ? 'text-success'
            : 'text-destructive';

    const isWarmup = rv === null;

    return (
        <Card>
            <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                    <Gauge className="h-4 w-4" />
                    IV / RV Ratio
                </CardTitle>
                <CardDescription className="text-xs">
                    Credit strategies favored when IV &gt; RV × 1.10.
                </CardDescription>
            </CardHeader>
            <CardContent>
                {isWarmup ? (
                    <p className="text-sm text-muted-foreground italic">
                        Collecting daily returns — realized volatility
                        needs 20 daily samples before it stabilises.
                    </p>
                ) : (
                    <div className="grid grid-cols-3 gap-3">
                        <div>
                            <p className="text-xs text-muted-foreground">
                                Realized Vol (20d)
                            </p>
                            <p className="text-xl font-mono font-semibold">
                                {formatNumber(rv, 2)}
                            </p>
                        </div>
                        <div>
                            <p className="text-xs text-muted-foreground">
                                VIX (live)
                            </p>
                            <p className="text-xl font-mono font-semibold">
                                {formatNumber(vix, 2)}
                            </p>
                        </div>
                        <div>
                            <p className="text-xs text-muted-foreground">
                                IV / RV
                            </p>
                            <p
                                className={`text-2xl font-bold font-mono ${ratioColor}`}
                            >
                                {formatNumber(ratio, 2)}×
                            </p>
                        </div>
                    </div>
                )}
            </CardContent>
        </Card>
    );
}

// ── Panel 2 — Butterfly Gate Counters ──────────────────────────────
function ButterflyGatesPanel({ data }: { data: LearningStats }) {
    const gates = data.butterfly_gates ?? {};
    const allowed = data.butterfly_allowed_today ?? 0;

    const values = BUTTERFLY_REASONS.map((r) => gates[r] ?? 0);
    const allZero = allowed === 0 && values.every((v) => v === 0);

    const maxVal = Math.max(allowed, ...values, 1);

    return (
        <Card>
            <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                    <ShieldAlert className="h-4 w-4" />
                    Butterfly Gate Counters (today)
                </CardTitle>
                <CardDescription className="text-xs">
                    Why the iron butterfly was blocked — and how often
                    it was allowed through.
                </CardDescription>
            </CardHeader>
            <CardContent>
                {allZero ? (
                    <p className="text-sm text-muted-foreground italic">
                        No butterfly attempts today — counters reset
                        each session.
                    </p>
                ) : (
                    <div className="space-y-1.5">
                        {/* Allowed bar (green, on top) */}
                        <GateBar
                            label="Allowed"
                            count={allowed}
                            max={maxVal}
                            variant="allowed"
                        />
                        {BUTTERFLY_REASONS.map((reason) => (
                            <GateBar
                                key={reason}
                                label={REASON_LABELS[reason]}
                                count={gates[reason] ?? 0}
                                max={maxVal}
                                variant={
                                    reason === 'drawdown_block'
                                        ? 'pending'
                                        : 'blocked'
                                }
                                note={
                                    reason === 'drawdown_block'
                                        ? 'wiring pending'
                                        : undefined
                                }
                            />
                        ))}
                    </div>
                )}
            </CardContent>
        </Card>
    );
}

function GateBar({
    label,
    count,
    max,
    variant,
    note,
}: {
    label: string;
    count: number;
    max: number;
    variant: 'allowed' | 'blocked' | 'pending';
    note?: string;
}) {
    const pct = max > 0 ? Math.round((count / max) * 100) : 0;
    const barClass =
        variant === 'allowed'
            ? 'bg-success/70'
            : variant === 'pending'
            ? 'bg-muted'
            : 'bg-destructive/60';
    const textClass =
        variant === 'pending' ? 'text-muted-foreground' : '';

    return (
        <div className={`flex items-center gap-3 text-xs ${textClass}`}>
            <div className="w-32 shrink-0 flex items-center gap-1">
                <span>{label}</span>
                {note ? (
                    <span className="text-[10px] italic text-muted-foreground">
                        ({note})
                    </span>
                ) : null}
            </div>
            <div className="flex-1 h-2 rounded bg-muted/30 overflow-hidden">
                <div
                    className={`h-full ${barClass}`}
                    style={{ width: `${pct}%` }}
                />
            </div>
            <div className="w-8 text-right font-mono">{count}</div>
        </div>
    );
}

// ── Panel 3 — Regime × Strategy Matrix ────────────────────────────
function StrategyMatrixPanel({ data }: { data: LearningStats }) {
    const rows = data.strategy_matrix ?? [];

    if (rows.length === 0) {
        return (
            <Card>
                <CardHeader className="pb-3">
                    <CardTitle className="text-sm font-medium flex items-center gap-2">
                        <Layers className="h-4 w-4" />
                        Regime × Strategy Matrix
                    </CardTitle>
                    <CardDescription className="text-xs">
                        Win-rate and P&amp;L by regime/strategy cell.
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <p className="text-sm text-muted-foreground italic">
                        Collecting trades — each cell needs 10 closed
                        paper trades before it starts influencing
                        sizing. Rows appear as cells fill.
                    </p>
                </CardContent>
            </Card>
        );
    }

    return (
        <Card>
            <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                    <Layers className="h-4 w-4" />
                    Regime × Strategy Matrix
                </CardTitle>
                <CardDescription className="text-xs">
                    Red rows are actively reducing sizing; yellow rows
                    are still building data.
                </CardDescription>
            </CardHeader>
            <CardContent className="p-0">
                <div className="overflow-x-auto">
                    <table className="w-full text-xs">
                        <thead>
                            <tr className="border-b bg-muted/50">
                                <th className="px-3 py-2 text-left font-medium text-muted-foreground">
                                    Regime
                                </th>
                                <th className="px-3 py-2 text-left font-medium text-muted-foreground">
                                    Strategy
                                </th>
                                <th className="px-3 py-2 text-right font-medium text-muted-foreground">
                                    Win Rate
                                </th>
                                <th className="px-3 py-2 text-right font-medium text-muted-foreground">
                                    Avg P&amp;L
                                </th>
                                <th className="px-3 py-2 text-right font-medium text-muted-foreground">
                                    Profit Factor
                                </th>
                                <th className="px-3 py-2 text-right font-medium text-muted-foreground">
                                    Trades
                                </th>
                            </tr>
                        </thead>
                        <tbody className="divide-y">
                            {rows.map((row, i) => (
                                <MatrixRow key={`${row.regime}|${row.strategy}|${i}`} row={row} />
                            ))}
                        </tbody>
                    </table>
                </div>
            </CardContent>
        </Card>
    );
}

function MatrixRow({ row }: { row: StrategyMatrixCell }) {
    const count = row.trade_count ?? 0;
    const winRate = row.win_rate ?? null;
    const avg = formatPnl(row.avg_pnl ?? null);
    const pf = row.profit_factor ?? null;

    // Active reduction: >=10 trades AND win_rate < 40% → red
    // Building: 5-9 trades → yellow
    // Else: neutral
    const rowClass =
        count >= 10 && (winRate ?? 1) < 0.4
            ? 'bg-destructive/5'
            : count >= 5 && count < 10
            ? 'bg-amber-500/5'
            : '';

    return (
        <tr className={`${rowClass} hover:bg-muted/30 transition-colors`}>
            <td className="px-3 py-2 capitalize font-mono">{row.regime}</td>
            <td className="px-3 py-2 capitalize">
                {row.strategy.replace(/_/g, ' ')}
            </td>
            <td className="px-3 py-2 text-right font-mono">
                {winRate != null ? `${(winRate * 100).toFixed(0)}%` : '—'}
            </td>
            <td className={`px-3 py-2 text-right font-mono ${avg.className}`}>
                {avg.text}
            </td>
            <td className="px-3 py-2 text-right font-mono">
                {pf != null ? pf.toFixed(2) : '—'}
            </td>
            <td className="px-3 py-2 text-right font-mono">{count}</td>
        </tr>
    );
}

// ── Panel 4 — Model Drift Alert ────────────────────────────────────
function ModelDriftPanel({ data }: { data: LearningStats }) {
    const drifting = data.model_drift_alert === true;
    return (
        <Card>
            <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4" />
                    Model Drift (live)
                </CardTitle>
                <CardDescription className="text-xs">
                    Rolling 10-day prediction accuracy vs the 60-day
                    baseline.
                </CardDescription>
            </CardHeader>
            <CardContent>
                {drifting ? (
                    <div className="rounded-lg border border-destructive/50 bg-destructive/10 px-3 py-2 text-sm text-destructive flex items-center gap-2">
                        <AlertTriangle className="h-4 w-4 shrink-0" />
                        <span>
                            <strong>Model drift detected.</strong> Review
                            predictions before the next cycle.
                        </span>
                    </div>
                ) : (
                    <Badge
                        variant="outline"
                        className="bg-success/10 text-success border-success/20"
                    >
                        <CheckCircle className="h-3 w-3 mr-1" />
                        No drift detected
                    </Badge>
                )}
            </CardContent>
        </Card>
    );
}

// ── Panel 5 — Sizing Phase ─────────────────────────────────────────
const SIZING_PHASE_LABELS: Record<number, { title: string; detail: string }> = {
    1: {
        title: 'Phase 1 — Paper trading',
        detail: 'Standard sizing (0.5% core, 0.25% satellite).',
    },
    2: {
        title: 'Phase 2 — E1 Active',
        detail:
            'Increased sizing (0.75% core, 0.375% satellite). Gate: 45-day Sharpe ≥ 1.2.',
    },
    3: {
        title: 'Phase 3 — E2 Active',
        detail:
            'Full sizing (1.0% core, 0.5% satellite). Gate: 90-day Sharpe ≥ 1.5.',
    },
    4: {
        title: 'Phase 4 — Manual override',
        detail:
            'Never reached by auto-advance. Requires operator action.',
    },
};

function SizingPhasePanel({ data }: { data: LearningStats }) {
    const phase = data.sizing_phase ?? 1;
    const info =
        SIZING_PHASE_LABELS[phase] ?? {
            title: `Phase ${phase}`,
            detail: 'Unknown phase.',
        };
    const advancedAt = data.sizing_phase_advanced_at ?? null;

    return (
        <Card>
            <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                    <Activity className="h-4 w-4" />
                    Sizing Phase
                </CardTitle>
                <CardDescription className="text-xs">
                    Auto-advances on rolling Sharpe gates (E1, E2).
                </CardDescription>
            </CardHeader>
            <CardContent>
                <p className="text-2xl font-bold">{info.title}</p>
                <p className="text-xs text-muted-foreground mt-1">
                    {info.detail}
                </p>
                {phase > 1 && advancedAt ? (
                    <p className="text-xs text-muted-foreground mt-2 font-mono">
                        Advanced: {formatIsoTimestamp(advancedAt)}
                    </p>
                ) : null}
            </CardContent>
        </Card>
    );
}

// ── Panel 6 — Adaptive Halt Threshold ──────────────────────────────
function HaltThresholdPanel({ data }: { data: LearningStats }) {
    const pct = data.halt_threshold_pct;
    const source = data.halt_threshold_source ?? 'default';
    const isAdaptive = source === 'adaptive';

    return (
        <Card>
            <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                    <ShieldAlert className="h-4 w-4" />
                    Adaptive Halt Threshold
                </CardTitle>
                <CardDescription className="text-xs">
                    Daily drawdown that halts the session — calibrates
                    from historical losses.
                </CardDescription>
            </CardHeader>
            <CardContent>
                {isAdaptive ? (
                    <div>
                        <p className="text-2xl font-bold font-mono text-success">
                            {formatPct(pct, 2)}
                        </p>
                        <p className="text-xs text-muted-foreground mt-1">
                            Calibrated from the last 100 closed trades.
                        </p>
                    </div>
                ) : (
                    <div>
                        <p className="text-2xl font-bold font-mono text-muted-foreground">
                            {formatPct(DEFAULT_HALT_THRESHOLD_PCT, 1)}{' '}
                            <span className="text-sm font-normal">
                                (default)
                            </span>
                        </p>
                        <p className="text-xs text-muted-foreground mt-1">
                            Using default — adaptive calibration
                            activates after 100 closed trades.
                        </p>
                    </div>
                )}
            </CardContent>
        </Card>
    );
}

// ── Panel 7 — Calibrated Butterfly Thresholds ─────────────────────
function ButterflyThresholdsPanel({ data }: { data: LearningStats }) {
    const t = data.butterfly_thresholds;
    const isCalibrated = t?.source === 'calibrated';

    const rows: Array<{
        label: string;
        defaultValue: number;
        calibrated: number | null;
        formatter: (v: number | null | undefined) => string;
    }> = [
        {
            label: 'GEX Confidence',
            defaultValue: BUTTERFLY_DEFAULTS.gex_conf,
            calibrated: t?.gex_conf ?? null,
            formatter: (v) => formatNumber(v, 2),
        },
        {
            label: 'Wall Distance',
            defaultValue: BUTTERFLY_DEFAULTS.wall_distance,
            calibrated: t?.wall_distance ?? null,
            formatter: (v) => formatPct(v, 2),
        },
        {
            label: 'Concentration',
            defaultValue: BUTTERFLY_DEFAULTS.concentration,
            calibrated: t?.concentration ?? null,
            formatter: (v) => formatNumber(v, 2),
        },
    ];

    return (
        <Card>
            <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                    <Sliders className="h-4 w-4" />
                    Calibrated Butterfly Thresholds
                </CardTitle>
                <CardDescription className="text-xs">
                    Entry thresholds — tighten or loosen with trade
                    history.
                </CardDescription>
            </CardHeader>
            <CardContent className="p-0">
                {!isCalibrated ? (
                    <div className="px-6 pb-6">
                        <p className="text-sm text-muted-foreground italic">
                            Using defaults — calibration activates
                            after 20 butterfly trades.
                        </p>
                    </div>
                ) : null}
                <div className="overflow-x-auto">
                    <table className="w-full text-xs">
                        <thead>
                            <tr className="border-b bg-muted/50">
                                <th className="px-3 py-2 text-left font-medium text-muted-foreground">
                                    Threshold
                                </th>
                                <th className="px-3 py-2 text-right font-medium text-muted-foreground">
                                    Default
                                </th>
                                <th className="px-3 py-2 text-right font-medium text-muted-foreground">
                                    Calibrated
                                </th>
                                <th className="px-3 py-2 text-left font-medium text-muted-foreground">
                                    Source
                                </th>
                            </tr>
                        </thead>
                        <tbody className="divide-y">
                            {rows.map((row) => {
                                const changed =
                                    isCalibrated &&
                                    row.calibrated !== null &&
                                    Math.abs(
                                        (row.calibrated ?? 0) -
                                            row.defaultValue,
                                    ) > 1e-9;
                                return (
                                    <tr
                                        key={row.label}
                                        className={
                                            changed
                                                ? 'bg-success/5'
                                                : ''
                                        }
                                    >
                                        <td className="px-3 py-2">
                                            {row.label}
                                        </td>
                                        <td className="px-3 py-2 text-right font-mono text-muted-foreground">
                                            {row.formatter(
                                                row.defaultValue,
                                            )}
                                        </td>
                                        <td
                                            className={`px-3 py-2 text-right font-mono ${
                                                changed
                                                    ? 'text-success font-semibold'
                                                    : ''
                                            }`}
                                        >
                                            {isCalibrated
                                                ? row.formatter(
                                                      row.calibrated,
                                                  )
                                                : '—'}
                                        </td>
                                        <td className="px-3 py-2">
                                            <Badge
                                                variant="outline"
                                                className={
                                                    isCalibrated
                                                        ? 'bg-success/10 text-success border-success/20'
                                                        : 'bg-muted text-muted-foreground border-border'
                                                }
                                            >
                                                {isCalibrated
                                                    ? 'calibrated'
                                                    : 'default'}
                                            </Badge>
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            </CardContent>
        </Card>
    );
}

// ── Page ──────────────────────────────────────────────────────────
export default function TradingLearningPage() {
    const { data, isLoading, error } = useLearningStats();

    const hasProxyError = useMemo(
        () => Boolean(data?.error),
        [data?.error],
    );

    if (isLoading) {
        return (
            <div className="space-y-6">
                <PageHeader
                    title="Learning"
                    subtitle="Adaptive systems — observability snapshot"
                />
                <LoadingSkeleton variant="card" rows={4} />
            </div>
        );
    }

    if (error || !data) {
        return (
            <div className="space-y-6">
                <PageHeader
                    title="Learning"
                    subtitle="Adaptive systems — observability snapshot"
                />
                <ErrorState message="Failed to load learning stats. Check Supabase function deployment and RAILWAY_ADMIN_KEY / RAILWAY_API_URL secrets." />
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <PageHeader
                title="Learning"
                subtitle="Adaptive systems — observability snapshot"
            />

            {hasProxyError ? (
                <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm text-amber-700 flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4 shrink-0" />
                    <span>
                        Upstream trading API is unreachable — showing
                        default / warmup values. Check the Railway
                        service.
                    </span>
                </div>
            ) : null}

            {/* Row 1 — Health strip */}
            <div className="grid gap-4 md:grid-cols-3">
                <IvRvPanel data={data} />
                <ModelDriftPanel data={data} />
                <SizingPhasePanel data={data} />
            </div>

            {/* Row 2 — Gates + halt */}
            <div className="grid gap-4 md:grid-cols-2">
                <ButterflyGatesPanel data={data} />
                <HaltThresholdPanel data={data} />
            </div>

            {/* Row 3 — Matrix + thresholds */}
            <div className="grid gap-4 md:grid-cols-2">
                <StrategyMatrixPanel data={data} />
                <ButterflyThresholdsPanel data={data} />
            </div>

            {/* Footer — spacer */}
            <div className="flex items-center gap-2 text-xs text-muted-foreground border-t pt-4">
                <BarChart2 className="h-3 w-3" />
                <span>
                    Refreshes every 60s · Source: /admin/trading/learning-stats
                </span>
            </div>
        </div>
    );
}
