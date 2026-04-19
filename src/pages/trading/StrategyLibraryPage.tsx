/**
 * Strategy Library — /trading/strategies
 *
 * Reference page for all 7 trading strategies. Shows what each
 * strategy is, when it fires, current flag status, sizing, and
 * exit rules. Informative even before any trades have happened —
 * the operator can study the playbook here without needing live data.
 */
import {
    CheckCircle2,
    Circle,
    TrendingUp,
    TrendingDown,
    Minus,
    AlertTriangle,
} from 'lucide-react';
import { PageHeader } from '@/components/dashboard/PageHeader';
import { Badge } from '@/components/ui/badge';
import {
    Card,
    CardContent,
    CardHeader,
    CardTitle,
} from '@/components/ui/card';
import { useFeatureFlags } from '@/hooks/trading/useFeatureFlags';

interface StrategyDef {
    name: string;
    type: string;
    flagKey: string | null;
    direction: 'bull' | 'bear' | 'neutral' | 'any';
    regime: string;
    riskPct: string;
    maxLoss: string;
    fires: string;
    exitRule: string;
    phase: string;
}

const STRATEGIES: StrategyDef[] = [
    {
        name: 'Iron Condor',
        type: 'Credit',
        flagKey: null,
        direction: 'neutral',
        regime: 'Range / Pin',
        riskPct: '0.5%',
        maxLoss: 'Spread width',
        fires: 'Default on range and pin_range regime days',
        exitRule: '40% of max profit OR 3:45 PM time stop',
        phase: 'Live (default)',
    },
    {
        name: 'Iron Butterfly',
        type: 'Credit',
        flagKey: 'strategy:iron_butterfly:enabled',
        direction: 'neutral',
        regime: 'Gamma Pin',
        riskPct: '0.4%',
        maxLoss: 'Spread width',
        fires: 'SPX within 0.3% of GEX wall (gamma pin detected)',
        exitRule: '40% of max profit OR 3:45 PM time stop',
        phase: 'Phase 2B',
    },
    {
        name: 'Long Straddle',
        type: 'Debit',
        flagKey: 'strategy:long_straddle:enabled',
        direction: 'any',
        regime: 'Catalyst day (pre-announcement)',
        riskPct: '0.25%',
        maxLoss: '100% of premium paid',
        fires: 'day_type = event (FOMC/CPI/NFP) BEFORE announcement',
        exitRule: '30 min before announcement OR 100% profit',
        phase: 'Phase 2B',
    },
    {
        name: 'Calendar Spread',
        type: 'Debit',
        flagKey: 'strategy:calendar_spread:enabled',
        direction: 'neutral',
        regime: 'Post-catalyst IV crush',
        riskPct: '0.3%',
        maxLoss: '$150/contract typical',
        fires: 'After catalyst announces (≥14:30 ET on event days)',
        exitRule: '3:45 PM time stop (captures IV crush)',
        phase: 'Phase 3C',
    },
    {
        name: 'Bull Call Spread',
        type: 'Debit',
        flagKey: 'strategy:ai_hint_override:enabled',
        direction: 'bull',
        regime: 'AI confidence ≥ 65% bull',
        riskPct: '0.3%',
        maxLoss: '100% of debit paid',
        fires: 'AI Synthesis recommends bull + override flag ON',
        exitRule: '100% profit OR 100% loss OR 3:45 PM',
        phase: 'Phase 2B',
    },
    {
        name: 'Bear Put Spread',
        type: 'Debit',
        flagKey: 'strategy:ai_hint_override:enabled',
        direction: 'bear',
        regime: 'AI confidence ≥ 65% bear',
        riskPct: '0.3%',
        maxLoss: '100% of debit paid',
        fires: 'AI Synthesis recommends bear + override flag ON',
        exitRule: '100% profit OR 100% loss OR 3:45 PM',
        phase: 'Phase 2B',
    },
    {
        name: 'Put Credit Spread',
        type: 'Credit',
        flagKey: null,
        direction: 'bull',
        regime: 'Quiet bullish / crisis fallback',
        riskPct: '0.5%',
        maxLoss: 'Spread width',
        fires: 'Quiet bullish regime OR crisis fallback',
        exitRule: '40% of max profit OR 3:45 PM time stop',
        phase: 'Live (fallback)',
    },
];

function DirectionIcon({ direction }: { direction: StrategyDef['direction'] }) {
    if (direction === 'bull') {
        return <TrendingUp className="h-3.5 w-3.5 text-success" />;
    }
    if (direction === 'bear') {
        return <TrendingDown className="h-3.5 w-3.5 text-destructive" />;
    }
    if (direction === 'any') {
        return <AlertTriangle className="h-3.5 w-3.5 text-amber-500" />;
    }
    return <Minus className="h-3.5 w-3.5 text-muted-foreground" />;
}

export default function StrategyLibraryPage() {
    const { data: flags } = useFeatureFlags();

    return (
        <div className="space-y-6">
            <PageHeader
                title="Strategy Library"
                subtitle="All 7 strategies — conditions, sizing, and current status"
            />

            <div className="grid gap-4 md:grid-cols-2">
                {STRATEGIES.map((s) => {
                    const isActive =
                        s.flagKey === null || (flags?.[s.flagKey] ?? false);
                    const isDefault = s.flagKey === null;
                    return (
                        <Card
                            key={s.name}
                            className={isActive ? 'border-success/30' : ''}
                        >
                            <CardHeader className="pb-3">
                                <div className="flex items-start justify-between gap-2">
                                    <div className="space-y-1">
                                        <CardTitle className="text-base flex items-center gap-2">
                                            {isActive ? (
                                                <CheckCircle2 className="h-4 w-4 text-success shrink-0" />
                                            ) : (
                                                <Circle className="h-4 w-4 text-muted-foreground shrink-0" />
                                            )}
                                            {s.name}
                                        </CardTitle>
                                        <div className="flex items-center gap-1 flex-wrap pl-6">
                                            <Badge
                                                variant="outline"
                                                className="text-xs"
                                            >
                                                {s.type}
                                            </Badge>
                                            <Badge
                                                variant="outline"
                                                className="text-xs flex items-center gap-1"
                                            >
                                                <DirectionIcon
                                                    direction={s.direction}
                                                />
                                                {s.direction === 'any'
                                                    ? 'any direction'
                                                    : s.direction}
                                            </Badge>
                                            <Badge
                                                variant="outline"
                                                className={`text-xs ${
                                                    isActive
                                                        ? 'bg-success/10 text-success border-success/20'
                                                        : 'bg-muted text-muted-foreground border-border'
                                                }`}
                                            >
                                                {isDefault
                                                    ? 'Default ON'
                                                    : isActive
                                                    ? 'Flag ON'
                                                    : 'Flag OFF'}
                                            </Badge>
                                        </div>
                                    </div>
                                    <Badge
                                        variant="outline"
                                        className="text-xs shrink-0"
                                    >
                                        {s.phase}
                                    </Badge>
                                </div>
                            </CardHeader>
                            <CardContent className="space-y-3 text-sm pl-6">
                                <div className="grid grid-cols-2 gap-2 text-xs">
                                    <div>
                                        <span className="text-muted-foreground">
                                            Regime:{' '}
                                        </span>
                                        <span>{s.regime}</span>
                                    </div>
                                    <div>
                                        <span className="text-muted-foreground">
                                            Risk:{' '}
                                        </span>
                                        <span className="font-medium">
                                            {s.riskPct} of account
                                        </span>
                                    </div>
                                    <div>
                                        <span className="text-muted-foreground">
                                            Max loss:{' '}
                                        </span>
                                        <span>{s.maxLoss}</span>
                                    </div>
                                </div>
                                <div>
                                    <p className="text-xs text-muted-foreground mb-0.5">
                                        Fires when
                                    </p>
                                    <p className="text-xs">{s.fires}</p>
                                </div>
                                <div>
                                    <p className="text-xs text-muted-foreground mb-0.5">
                                        Exit rule
                                    </p>
                                    <p className="text-xs">{s.exitRule}</p>
                                </div>
                            </CardContent>
                        </Card>
                    );
                })}
            </div>
        </div>
    );
}
