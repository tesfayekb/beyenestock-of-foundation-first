/**
 * Phase Activation Dashboard — /trading/activation
 *
 * Central control panel showing every feature's state:
 *   - What's active right now
 *   - What's built but waiting for trade-count threshold
 *   - What needs manual enabling (flag toggle)
 *   - What hasn't been built yet
 *   - A/B gate progress toward real capital deployment
 *   - Recent system alerts log
 */
import { useState } from 'react';
import { formatDistanceToNow } from 'date-fns';
import {
    CheckCircle2,
    Clock,
    Lock,
    Wrench,
    AlertTriangle,
    TrendingUp,
    Flag,
    Brain,
    Cpu,
    Activity,
} from 'lucide-react';
import { PageHeader } from '@/components/dashboard/PageHeader';
import { LoadingSkeleton } from '@/components/dashboard/LoadingSkeleton';
import { Badge } from '@/components/ui/badge';
import {
    Card,
    CardContent,
    CardHeader,
    CardTitle,
    CardDescription,
} from '@/components/ui/card';
import { Switch } from '@/components/ui/switch';
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import {
    useActivationStatus,
    ALL_FEATURES,
    type FeatureDefinition,
} from '@/hooks/trading/useActivationStatus';
import {
    useSetFeatureFlag,
    isFlagEnabled,
} from '@/hooks/trading/useFeatureFlags';

// Category icon map — every category in FeatureDefinition['category']
// must have an entry here.
const CAT_ICON: Record<FeatureDefinition['category'], React.ElementType> = {
    always_on: CheckCircle2,
    signal: Activity,
    strategy: TrendingUp,
    agent: Brain,
    model: Cpu,
    platform: Flag,
};

const CAT_LABEL: Record<FeatureDefinition['category'], string> = {
    always_on: 'Core Engine',
    signal: 'Signal Enhancements',
    strategy: 'Strategies',
    agent: 'AI Agents',
    model: 'Learning Models',
    platform: 'Platform',
};

const CAT_ORDER: FeatureDefinition['category'][] = [
    'always_on',
    'signal',
    'strategy',
    'agent',
    'model',
    'platform',
];

function buildStatusLabel(
    feature: FeatureDefinition,
    flags: Record<string, boolean>,
    tradeCount: number,
): { label: string; color: string; icon: React.ElementType } {
    if (feature.builtStatus === 'not_built') {
        return {
            label: 'Not built',
            color: 'text-muted-foreground',
            icon: Wrench,
        };
    }
    if (feature.builtStatus === 'dormant') {
        const flagOn = isFlagEnabled(flags, feature.key);
        if (flagOn) {
            return {
                label: 'Active',
                color: 'text-success',
                icon: CheckCircle2,
            };
        }
        if (
            feature.activationThreshold &&
            tradeCount >= feature.activationThreshold
        ) {
            return {
                label: 'READY — enable now',
                color: 'text-amber-600',
                icon: AlertTriangle,
            };
        }
        return {
            label: 'Dormant',
            color: 'text-muted-foreground',
            icon: Lock,
        };
    }
    // builtStatus === 'live' — check if it has a trade threshold
    if (feature.activationThreshold) {
        if (tradeCount >= feature.activationThreshold) {
            return {
                label: 'Active',
                color: 'text-success',
                icon: CheckCircle2,
            };
        }
        return {
            label: `Auto at ${feature.activationThreshold} trades`,
            color: 'text-muted-foreground',
            icon: Clock,
        };
    }
    return {
        label: 'Active',
        color: 'text-success',
        icon: CheckCircle2,
    };
}

function ProgressBar({ current, max }: { current: number; max: number }) {
    const pct = Math.min(100, (current / max) * 100);
    return (
        <div className="h-1 rounded-full bg-muted overflow-hidden mt-1">
            <div
                className="h-full rounded-full bg-primary transition-all duration-500"
                style={{ width: `${pct}%` }}
            />
        </div>
    );
}

function AlertLevel({ level }: { level: string }) {
    const cfg =
        {
            critical:
                'bg-destructive/10 text-destructive border-destructive/20',
            warning:
                'bg-amber-500/10 text-amber-600 border-amber-500/20',
            info: 'bg-blue-500/10 text-blue-600 border-blue-500/20',
        }[level] ?? 'bg-muted text-muted-foreground border-border';
    return (
        <Badge variant="outline" className={`text-xs capitalize ${cfg}`}>
            {level}
        </Badge>
    );
}

export default function ActivationPage() {
    const { data, isLoading } = useActivationStatus();
    const setFlag = useSetFeatureFlag();
    const [pendingToggle, setPendingToggle] = useState<{
        key: string;
        label: string;
        enabled: boolean;
    } | null>(null);

    if (isLoading) {
        return (
            <div className="space-y-6">
                <PageHeader
                    title="Phase Activation"
                    subtitle="Feature state and threshold progress"
                />
                <LoadingSkeleton variant="card" rows={4} />
            </div>
        );
    }

    const tradeCount = data?.closed_trade_count ?? 0;
    const flags = data?.flags ?? {};
    const abGate = data?.ab_gate;
    const alerts = data?.recent_alerts ?? [];

    // Count features by state. Signal flags default ON when absent in
    // the trading_feature_flags table — use isFlagEnabled (not the raw
    // map) so disabled signal toggles are reflected as 'enabled' here
    // until the user explicitly disables them.
    const activeCount = ALL_FEATURES.filter((f) => {
        if (f.builtStatus === 'not_built') return false;
        if (f.builtStatus === 'live') {
            return (
                !f.activationThreshold ||
                tradeCount >= f.activationThreshold
            );
        }
        return isFlagEnabled(flags, f.key);
    }).length;

    const readyCount = ALL_FEATURES.filter(
        (f) =>
            f.builtStatus === 'dormant' &&
            !isFlagEnabled(flags, f.key) &&
            f.activationThreshold != null &&
            tradeCount >= f.activationThreshold,
    ).length;

    return (
        <div className="space-y-6">
            <PageHeader
                title="Phase Activation"
                subtitle="Every feature — its current state, threshold progress, and activation controls"
            />

            {/* Summary row */}
            <div className="grid gap-3 grid-cols-2 sm:grid-cols-4">
                <Card>
                    <CardContent className="pt-4 pb-3">
                        <p className="text-xs text-muted-foreground mb-1">
                            Paper trades
                        </p>
                        <p className="text-3xl font-bold font-mono">
                            {tradeCount}
                        </p>
                    </CardContent>
                </Card>
                <Card>
                    <CardContent className="pt-4 pb-3">
                        <p className="text-xs text-muted-foreground mb-1">
                            Active features
                        </p>
                        <p className="text-3xl font-bold font-mono text-success">
                            {activeCount}
                        </p>
                    </CardContent>
                </Card>
                <Card
                    className={
                        readyCount > 0 ? 'border-amber-500/30' : ''
                    }
                >
                    <CardContent className="pt-4 pb-3">
                        <p className="text-xs text-muted-foreground mb-1">
                            Ready to enable
                        </p>
                        <p
                            className={`text-3xl font-bold font-mono ${
                                readyCount > 0 ? 'text-amber-600' : ''
                            }`}
                        >
                            {readyCount}
                        </p>
                    </CardContent>
                </Card>
                <Card>
                    <CardContent className="pt-4 pb-3">
                        <p className="text-xs text-muted-foreground mb-1">
                            A/B gate
                        </p>
                        <p className="text-sm font-medium">
                            {abGate?.built
                                ? abGate.gate_passed
                                    ? 'Passed'
                                    : `${abGate.days_elapsed ?? 0}/${abGate.days_required}d`
                                : 'Not started'}
                        </p>
                    </CardContent>
                </Card>
            </div>

            {/* A/B Gate card */}
            <Card
                className={
                    abGate?.gate_passed
                        ? 'border-success/30 bg-success/5'
                        : ''
                }
            >
                <CardHeader className="pb-3">
                    <CardTitle className="text-sm font-medium flex items-center gap-2">
                        <TrendingUp className="h-4 w-4" />
                        A/B Validation Gate — Real Capital Deployment
                    </CardTitle>
                    <CardDescription>
                        Comparing live paper system (Portfolio B) vs
                        rule-based shadow baseline (Portfolio A). Gate
                        requires ≥+8% annualized uplift over 90 days
                        and 100+ closed trades.
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    {!abGate?.built ? (
                        <div className="flex items-center gap-2 text-sm text-amber-600">
                            <Wrench className="h-4 w-4 shrink-0" />
                            Phase 3B (A/B shadow infrastructure) not
                            yet built. Until it runs, every trading
                            day is an uncaptured data point.
                        </div>
                    ) : abGate.gate_passed ? (
                        <p className="text-success font-semibold">
                            Gate passed. System validated for real
                            capital deployment.
                        </p>
                    ) : (
                        <div className="space-y-3">
                            <div className="grid grid-cols-2 gap-4 text-sm">
                                <div>
                                    <p className="text-xs text-muted-foreground mb-1">
                                        Days elapsed
                                    </p>
                                    <p className="font-bold font-mono">
                                        {abGate.days_elapsed ?? 0} /{' '}
                                        {abGate.days_required}
                                    </p>
                                    <ProgressBar
                                        current={
                                            abGate.days_elapsed ?? 0
                                        }
                                        max={abGate.days_required}
                                    />
                                </div>
                                <div>
                                    <p className="text-xs text-muted-foreground mb-1">
                                        Trades
                                    </p>
                                    <p className="font-bold font-mono">
                                        {abGate.trades_count} /{' '}
                                        {abGate.trades_required}
                                    </p>
                                    <ProgressBar
                                        current={abGate.trades_count}
                                        max={abGate.trades_required}
                                    />
                                </div>
                            </div>
                            {abGate.portfolio_b_lead_pct != null && (
                                <p
                                    className={`text-sm font-medium ${
                                        abGate.portfolio_b_lead_pct >=
                                        8
                                            ? 'text-success'
                                            : 'text-muted-foreground'
                                    }`}
                                >
                                    Portfolio B lead:{' '}
                                    {abGate.portfolio_b_lead_pct >= 0
                                        ? '+'
                                        : ''}
                                    {abGate.portfolio_b_lead_pct.toFixed(
                                        1,
                                    )}
                                    % annualized
                                    {abGate.portfolio_b_lead_pct >= 8
                                        ? ' — meets threshold'
                                        : ' (needs +8%)'}
                                </p>
                            )}
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* Feature sections by category */}
            {CAT_ORDER.map((cat) => {
                const features = ALL_FEATURES.filter(
                    (f) => f.category === cat,
                );
                if (features.length === 0) return null;
                const CatIcon = CAT_ICON[cat];
                return (
                    <Card key={cat}>
                        <CardHeader className="pb-3">
                            <CardTitle className="text-sm font-medium flex items-center gap-2">
                                <CatIcon className="h-4 w-4" />
                                {CAT_LABEL[cat]}
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="p-0">
                            <div className="divide-y">
                                {features.map((feature) => {
                                    const status = buildStatusLabel(
                                        feature,
                                        flags,
                                        tradeCount,
                                    );
                                    const StatusIcon = status.icon;
                                    // Signal flags default ON when absent — use
                                    // isFlagEnabled so the Switch reflects the
                                    // backend's effective state, not the raw map.
                                    const flagOn = isFlagEnabled(
                                        flags,
                                        feature.key,
                                    );
                                    const isToggleable =
                                        feature.builtStatus ===
                                            'dormant' &&
                                        feature.thresholdType !==
                                            'command';
                                    const isSignalToggle =
                                        feature.builtStatus ===
                                            'live' &&
                                        feature.key.startsWith(
                                            'signal:',
                                        );
                                    const isReady =
                                        feature.builtStatus ===
                                            'dormant' &&
                                        !flagOn &&
                                        feature.activationThreshold !=
                                            null &&
                                        tradeCount >=
                                            feature.activationThreshold;

                                    return (
                                        <div
                                            key={feature.key}
                                            className={`flex items-start gap-3 px-6 py-3 ${
                                                isReady
                                                    ? 'bg-amber-500/5'
                                                    : ''
                                            }`}
                                        >
                                            <StatusIcon
                                                className={`h-4 w-4 mt-0.5 shrink-0 ${status.color}`}
                                            />
                                            <div className="flex-1 min-w-0 space-y-0.5">
                                                <div className="flex items-center gap-2 flex-wrap">
                                                    <span className="text-sm font-medium">
                                                        {feature.label}
                                                    </span>
                                                    {isReady && (
                                                        <Badge
                                                            variant="outline"
                                                            className="text-xs bg-amber-500/10 text-amber-600 border-amber-500/20 animate-pulse"
                                                        >
                                                            READY —
                                                            enable now
                                                        </Badge>
                                                    )}
                                                    {feature.builtStatus ===
                                                        'not_built' && (
                                                        <Badge
                                                            variant="outline"
                                                            className="text-xs bg-muted text-muted-foreground border-border"
                                                        >
                                                            Not built
                                                        </Badge>
                                                    )}
                                                    {feature.thresholdType ===
                                                        'command' && (
                                                        <Badge
                                                            variant="outline"
                                                            className="text-xs bg-blue-500/10 text-blue-600 border-blue-500/20"
                                                        >
                                                            Run training
                                                            command
                                                        </Badge>
                                                    )}
                                                </div>
                                                <p className="text-xs text-muted-foreground">
                                                    {feature.description}
                                                </p>
                                                {feature.activationThreshold &&
                                                    !flagOn &&
                                                    feature.builtStatus !==
                                                        'not_built' && (
                                                        <div className="mt-1">
                                                            <p className="text-xs text-muted-foreground mb-0.5">
                                                                {tradeCount}{' '}
                                                                /{' '}
                                                                {
                                                                    feature.activationThreshold
                                                                }{' '}
                                                                trades
                                                                {feature.autoEnable
                                                                    ? ' (auto-enables)'
                                                                    : ' (manual enable)'}
                                                            </p>
                                                            <ProgressBar
                                                                current={
                                                                    tradeCount
                                                                }
                                                                max={
                                                                    feature.activationThreshold
                                                                }
                                                            />
                                                        </div>
                                                    )}
                                            </div>
                                            {(isToggleable ||
                                                isSignalToggle) && (
                                                <Switch
                                                    checked={flagOn}
                                                    disabled={
                                                        setFlag.isPending ||
                                                        feature.builtStatus ===
                                                            'not_built'
                                                    }
                                                    onCheckedChange={(
                                                        checked,
                                                    ) =>
                                                        setPendingToggle(
                                                            {
                                                                key: feature.key,
                                                                label: feature.label,
                                                                enabled:
                                                                    checked,
                                                            },
                                                        )
                                                    }
                                                />
                                            )}
                                        </div>
                                    );
                                })}
                            </div>
                        </CardContent>
                    </Card>
                );
            })}

            {/* Event log */}
            <Card>
                <CardHeader className="pb-3">
                    <CardTitle className="text-sm font-medium flex items-center gap-2">
                        <Activity className="h-4 w-4" />
                        System Event Log
                    </CardTitle>
                    <CardDescription>
                        Recent alerts and activation events. Critical
                        events are also sent by email.
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    {alerts.length === 0 ? (
                        <p className="text-sm text-muted-foreground italic">
                            No events yet. Alerts appear here when the
                            system fires them (daily halt, backstop
                            trigger, milestone reached, etc.).
                        </p>
                    ) : (
                        <div className="space-y-2">
                            {alerts.map((alert, i) => (
                                <div
                                    key={i}
                                    className="flex items-start gap-3 rounded-lg border p-3 text-sm"
                                >
                                    <AlertLevel level={alert.level} />
                                    <div className="flex-1 min-w-0">
                                        <p className="font-medium">
                                            {alert.event.replace(
                                                /_/g,
                                                ' ',
                                            )}
                                        </p>
                                        {alert.detail && (
                                            <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">
                                                {alert.detail}
                                            </p>
                                        )}
                                    </div>
                                    <span className="text-xs text-muted-foreground shrink-0">
                                        {formatDistanceToNow(
                                            new Date(alert.fired_at),
                                            { addSuffix: true },
                                        )}
                                    </span>
                                </div>
                            ))}
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* Confirmation dialog for flag toggles */}
            <AlertDialog
                open={pendingToggle !== null}
                onOpenChange={(open) => {
                    if (!open) setPendingToggle(null);
                }}
            >
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>
                            {pendingToggle?.enabled
                                ? 'Enable'
                                : 'Disable'}{' '}
                            {pendingToggle?.label}?
                        </AlertDialogTitle>
                        <AlertDialogDescription>
                            {pendingToggle?.enabled
                                ? `This activates ${pendingToggle.label} immediately for the next trading cycle.`
                                : `This deactivates ${pendingToggle?.label} immediately.`}
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel
                            onClick={() => setPendingToggle(null)}
                        >
                            Cancel
                        </AlertDialogCancel>
                        <AlertDialogAction
                            onClick={() => {
                                if (!pendingToggle) return;
                                setFlag.mutate({
                                    flagKey: pendingToggle.key,
                                    enabled: pendingToggle.enabled,
                                });
                                setPendingToggle(null);
                            }}
                        >
                            Confirm
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </div>
    );
}
