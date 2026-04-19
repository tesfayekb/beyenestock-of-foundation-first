/**
 * Milestones — /trading/milestones
 *
 * Visualizes the trade-count milestone ladder: each unlock and the
 * specific feature flags it makes safe to enable. Shows progress
 * even before any trades exist so the operator understands what
 * comes next.
 */
import { CheckCircle2, Lock, ChevronRight } from 'lucide-react';
import { PageHeader } from '@/components/dashboard/PageHeader';
import {
    Card,
    CardContent,
    CardHeader,
    CardTitle,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useTradingSession } from '@/hooks/trading/useTradingSession';
import { useFeatureFlags } from '@/hooks/trading/useFeatureFlags';

interface Milestone {
    at: number;
    label: string;
    description: string;
    unlocks: string[];
    flagsToEnable: string[];
}

const MILESTONES: Milestone[] = [
    {
        at: 1,
        label: 'System Live',
        description:
            'First paper trade confirmed. System is working end-to-end.',
        unlocks: [
            'Confirms Databento feed, prediction engine, and execution are working',
        ],
        flagsToEnable: [],
    },
    {
        at: 5,
        label: 'Iron Butterfly',
        description: 'Enough trades to validate basic strategy logic.',
        unlocks: [
            'Iron butterfly fires on gamma pin days (SPX within 0.3% of GEX wall)',
        ],
        flagsToEnable: ['strategy:iron_butterfly:enabled'],
    },
    {
        at: 20,
        label: 'Kelly + Full AI',
        description:
            'Kelly sizing activates automatically. Enable remaining strategies.',
        unlocks: [
            'Kelly position sizing (auto-activates)',
            'Long straddle on catalyst days',
            'Calendar spread post-catalyst',
            'Flow agent (Unusual Whales + Polygon P/C)',
            'Sentiment agent (NewsAPI + Fear/Greed)',
        ],
        flagsToEnable: [
            'strategy:long_straddle:enabled',
            'strategy:calendar_spread:enabled',
            'agents:flow_agent:enabled',
            'agents:sentiment_agent:enabled',
        ],
    },
    {
        at: 40,
        label: 'AI Strategy Override',
        description: 'Enough history to validate AI synthesis accuracy.',
        unlocks: [
            'AI hint overrides regime-based strategy selection when confidence ≥ 65%',
        ],
        flagsToEnable: ['strategy:ai_hint_override:enabled'],
    },
    {
        at: 100,
        label: 'Meta-Label Model',
        description: 'Sufficient training data for machine learning.',
        unlocks: [
            'Meta-label model predicts whether each specific trade will hit profit target',
            '90-day A/B test can begin',
            'Phase 3A: model trained on real paper trade outcomes',
        ],
        flagsToEnable: [],
    },
];

export default function MilestonesPage() {
    const { data: session } = useTradingSession();
    const { data: flags } = useFeatureFlags();
    const tradeCount = session?.virtual_trades_count ?? 0;

    const nextMilestone = MILESTONES.find((m) => m.at > tradeCount);
    const progressPct = nextMilestone
        ? Math.min(100, (tradeCount / nextMilestone.at) * 100)
        : 100;

    return (
        <div className="space-y-6">
            <PageHeader
                title="Trade Milestones"
                subtitle="Progress toward full system capability"
            />

            {/* Current progress */}
            <Card>
                <CardContent className="pt-6">
                    <div className="flex items-baseline gap-3 mb-4">
                        <span className="text-5xl font-bold font-mono">
                            {tradeCount}
                        </span>
                        <span className="text-lg text-muted-foreground">
                            closed paper trades
                        </span>
                    </div>
                    {nextMilestone ? (
                        <>
                            <div className="flex items-center justify-between text-sm mb-2">
                                <span className="text-muted-foreground">
                                    Next milestone
                                </span>
                                <span className="font-medium">
                                    {nextMilestone.at - tradeCount} trades to{' '}
                                    <span className="text-primary">
                                        {nextMilestone.label}
                                    </span>
                                </span>
                            </div>
                            <div className="h-2 rounded-full bg-muted overflow-hidden">
                                <div
                                    className="h-full rounded-full bg-primary transition-all duration-500"
                                    style={{ width: `${progressPct}%` }}
                                />
                            </div>
                        </>
                    ) : (
                        <p className="text-sm text-success font-medium">
                            All milestones reached.
                        </p>
                    )}
                </CardContent>
            </Card>

            {/* Milestone list */}
            <div className="space-y-3">
                {MILESTONES.map((m) => {
                    const reached = tradeCount >= m.at;
                    const isNext = nextMilestone?.at === m.at;
                    const flagsReady = m.flagsToEnable.every(
                        (k) => flags?.[k],
                    );

                    return (
                        <Card
                            key={m.at}
                            className={`${
                                reached
                                    ? 'border-success/30 bg-success/5'
                                    : isNext
                                    ? 'border-primary/30'
                                    : ''
                            }`}
                        >
                            <CardHeader className="pb-2">
                                <div className="flex items-start justify-between gap-3">
                                    <div className="flex items-start gap-3">
                                        <div
                                            className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${
                                                reached
                                                    ? 'bg-success text-success-foreground'
                                                    : isNext
                                                    ? 'bg-primary text-primary-foreground'
                                                    : 'bg-muted text-muted-foreground'
                                            }`}
                                        >
                                            {reached ? (
                                                <CheckCircle2 className="h-4 w-4" />
                                            ) : isNext ? (
                                                <ChevronRight className="h-4 w-4" />
                                            ) : (
                                                <Lock className="h-4 w-4" />
                                            )}
                                        </div>
                                        <div>
                                            <CardTitle className="text-base flex items-center gap-2">
                                                {m.label}
                                                <Badge
                                                    variant="outline"
                                                    className="text-xs font-mono"
                                                >
                                                    {m.at} trades
                                                </Badge>
                                                {reached && (
                                                    <Badge
                                                        variant="outline"
                                                        className="text-xs bg-success/10 text-success border-success/20"
                                                    >
                                                        Reached
                                                    </Badge>
                                                )}
                                                {isNext && !reached && (
                                                    <Badge
                                                        variant="outline"
                                                        className="text-xs bg-primary/10 text-primary border-primary/20"
                                                    >
                                                        Next
                                                    </Badge>
                                                )}
                                            </CardTitle>
                                            <p className="text-sm text-muted-foreground mt-0.5">
                                                {m.description}
                                            </p>
                                        </div>
                                    </div>
                                </div>
                            </CardHeader>
                            <CardContent className="pl-14">
                                <div className="space-y-1">
                                    {m.unlocks.map((u, i) => (
                                        <p
                                            key={i}
                                            className="text-xs text-muted-foreground flex items-start gap-1"
                                        >
                                            <span className="mt-0.5 shrink-0">
                                                →
                                            </span>{' '}
                                            {u}
                                        </p>
                                    ))}
                                </div>
                                {m.flagsToEnable.length > 0 &&
                                    reached &&
                                    !flagsReady && (
                                        <p className="text-xs text-amber-600 mt-2 font-medium">
                                            Milestone reached — go to Feature
                                            Flags to enable the unlocked
                                            features.
                                        </p>
                                    )}
                                {m.flagsToEnable.length > 0 &&
                                    reached &&
                                    flagsReady && (
                                        <p className="text-xs text-success mt-2 font-medium">
                                            All flags for this milestone are
                                            enabled.
                                        </p>
                                    )}
                            </CardContent>
                        </Card>
                    );
                })}
            </div>
        </div>
    );
}
