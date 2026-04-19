/**
 * Feature Flags — /trading/flags
 *
 * Dedicated page for enabling and disabling all strategy and agent
 * feature flags. Toggling a switch opens a confirmation dialog so the
 * operator cannot accidentally activate a strategy that has not yet
 * met its required-trade threshold.
 */
import { useState } from 'react';
import { CheckCircle2, Circle } from 'lucide-react';
import { PageHeader } from '@/components/dashboard/PageHeader';
import { LoadingSkeleton } from '@/components/dashboard/LoadingSkeleton';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import {
    Card,
    CardContent,
    CardHeader,
    CardTitle,
    CardDescription,
} from '@/components/ui/card';
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
    useFeatureFlags,
    useSetFeatureFlag,
    FLAG_DEFINITIONS,
} from '@/hooks/trading/useFeatureFlags';

interface PendingToggle {
    key: string;
    label: string;
    enabled: boolean;
    requiredTrades: number;
}

export default function FeatureFlagsPage() {
    const { data: flags, isLoading } = useFeatureFlags();
    const setFlag = useSetFeatureFlag();
    const [pendingToggle, setPendingToggle] = useState<PendingToggle | null>(
        null,
    );

    if (isLoading) {
        return (
            <div className="space-y-6">
                <PageHeader
                    title="Feature Flags"
                    subtitle="Enable strategies and AI agents"
                />
                <LoadingSkeleton variant="card" rows={3} />
            </div>
        );
    }

    const enabledCount = FLAG_DEFINITIONS.filter(
        (f) => flags?.[f.key],
    ).length;

    return (
        <div className="space-y-6">
            <PageHeader
                title="Feature Flags"
                subtitle="Enable features in order — validate each over the required trades before proceeding"
            />

            {/* Summary */}
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <span className="font-medium text-foreground">
                    {enabledCount}
                </span>
                of {FLAG_DEFINITIONS.length} flags enabled
            </div>

            {/* Activation order notice */}
            <div className="rounded-lg border bg-muted/30 p-4 text-sm space-y-1">
                <p className="font-medium">Recommended activation order:</p>
                <ol className="list-decimal list-inside space-y-1 text-muted-foreground">
                    <li>
                        AI Synthesis — enable after Monday confirms trading is
                        live
                    </li>
                    <li>Iron Butterfly — enable after 5+ closed trades</li>
                    <li>
                        Long Straddle + Flow Agent + Sentiment Agent — enable
                        after 20+ trades
                    </li>
                    <li>
                        Calendar Spread — enable after 20+ trades and straddle
                        validated
                    </li>
                    <li>
                        AI Strategy Override — enable after 40+ trades with
                        synthesis validated
                    </li>
                </ol>
            </div>

            {/* Agent flags */}
            <Card>
                <CardHeader>
                    <CardTitle className="text-base">AI Agents</CardTitle>
                    <CardDescription>
                        Intelligence agents that enrich Claude&apos;s morning
                        brief.
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                    {FLAG_DEFINITIONS.filter((f) => f.category === 'agent').map(
                        (flag) => {
                            const isOn = flags?.[flag.key] ?? false;
                            return (
                                <div
                                    key={flag.key}
                                    className="flex items-start justify-between gap-4 rounded-lg border p-4"
                                >
                                    <div className="space-y-1 min-w-0">
                                        <div className="flex items-center gap-2 flex-wrap">
                                            {isOn ? (
                                                <CheckCircle2 className="h-4 w-4 text-success shrink-0" />
                                            ) : (
                                                <Circle className="h-4 w-4 text-muted-foreground shrink-0" />
                                            )}
                                            <p className="font-medium text-sm">
                                                {flag.label}
                                            </p>
                                            {flag.requiredTrades > 0 && (
                                                <Badge
                                                    variant="outline"
                                                    className="text-xs"
                                                >
                                                    {flag.requiredTrades}+
                                                    trades required
                                                </Badge>
                                            )}
                                            {isOn && (
                                                <Badge
                                                    variant="outline"
                                                    className="text-xs bg-success/10 text-success border-success/20"
                                                >
                                                    ACTIVE
                                                </Badge>
                                            )}
                                        </div>
                                        <p className="text-xs text-muted-foreground pl-6">
                                            {flag.description}
                                        </p>
                                    </div>
                                    <Switch
                                        checked={isOn}
                                        disabled={setFlag.isPending}
                                        onCheckedChange={(checked) =>
                                            setPendingToggle({
                                                key: flag.key,
                                                label: flag.label,
                                                enabled: checked,
                                                requiredTrades:
                                                    flag.requiredTrades,
                                            })
                                        }
                                    />
                                </div>
                            );
                        },
                    )}
                </CardContent>
            </Card>

            {/* Strategy flags */}
            <Card>
                <CardHeader>
                    <CardTitle className="text-base">Strategies</CardTitle>
                    <CardDescription>
                        Trading strategies beyond the default iron condor.
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                    {FLAG_DEFINITIONS.filter(
                        (f) => f.category === 'strategy',
                    ).map((flag) => {
                        const isOn = flags?.[flag.key] ?? false;
                        return (
                            <div
                                key={flag.key}
                                className="flex items-start justify-between gap-4 rounded-lg border p-4"
                            >
                                <div className="space-y-1 min-w-0">
                                    <div className="flex items-center gap-2 flex-wrap">
                                        {isOn ? (
                                            <CheckCircle2 className="h-4 w-4 text-success shrink-0" />
                                        ) : (
                                            <Circle className="h-4 w-4 text-muted-foreground shrink-0" />
                                        )}
                                        <p className="font-medium text-sm">
                                            {flag.label}
                                        </p>
                                        <Badge
                                            variant="outline"
                                            className="text-xs"
                                        >
                                            {flag.requiredTrades}+ trades
                                            required
                                        </Badge>
                                        {isOn && (
                                            <Badge
                                                variant="outline"
                                                className="text-xs bg-success/10 text-success border-success/20"
                                            >
                                                ACTIVE
                                            </Badge>
                                        )}
                                    </div>
                                    <p className="text-xs text-muted-foreground pl-6">
                                        {flag.description}
                                    </p>
                                </div>
                                <Switch
                                    checked={isOn}
                                    disabled={setFlag.isPending}
                                    onCheckedChange={(checked) =>
                                        setPendingToggle({
                                            key: flag.key,
                                            label: flag.label,
                                            enabled: checked,
                                            requiredTrades: flag.requiredTrades,
                                        })
                                    }
                                />
                            </div>
                        );
                    })}
                </CardContent>
            </Card>

            {/* Confirmation dialog — single instance, parent-controlled */}
            <AlertDialog
                open={pendingToggle !== null}
                onOpenChange={(open) => {
                    if (!open) setPendingToggle(null);
                }}
            >
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>
                            {pendingToggle?.enabled ? 'Enable' : 'Disable'}{' '}
                            {pendingToggle?.label}?
                        </AlertDialogTitle>
                        <AlertDialogDescription>
                            {pendingToggle?.enabled
                                ? `This activates ${pendingToggle.label} immediately. ${
                                      pendingToggle.requiredTrades > 0
                                          ? `Recommended: ${pendingToggle.requiredTrades}+ closed paper trades before enabling.`
                                          : 'No trade minimum required.'
                                  }`
                                : `This deactivates ${pendingToggle?.label} immediately. The system falls back to the next available strategy.`}
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
