/**
 * AI Intelligence — /trading/intelligence
 *
 * Full-page view of all AI agent outputs: economic calendar, macro brief,
 * options flow, market sentiment, and the consolidated synthesis
 * recommendation. Mirrors the embedded War Room panel but with full
 * detail, dedicated cards per agent, and freshness badges.
 */
import { formatDistanceToNow } from 'date-fns';
import {
    Brain,
    TrendingUp,
    TrendingDown,
    AlertCircle,
    Activity,
    Newspaper,
    BarChart2,
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
import {
    useTradeIntelligence,
    isBriefStale,
    briefAgeMinutes,
} from '@/hooks/trading/useTradeIntelligence';

function AgeBadge({ generatedAt }: { generatedAt?: string }) {
    if (!generatedAt) {
        return <span className="text-xs text-muted-foreground">no data</span>;
    }
    const stale = isBriefStale(generatedAt);
    const age = briefAgeMinutes(generatedAt);
    const label =
        age < 1
            ? 'just now'
            : formatDistanceToNow(new Date(generatedAt), { addSuffix: true });
    return (
        <span
            className={`text-xs flex items-center gap-1 ${
                stale ? 'text-amber-600' : 'text-muted-foreground'
            }`}
        >
            {stale && <AlertCircle className="h-3 w-3" />}
            {label}
        </span>
    );
}

function DirectionBadge({ direction }: { direction?: string }) {
    if (!direction || direction === 'neutral') {
        return (
            <Badge
                variant="outline"
                className="bg-muted text-muted-foreground border-border"
            >
                Neutral
            </Badge>
        );
    }
    if (direction === 'bull') {
        return (
            <Badge
                variant="outline"
                className="bg-success/10 text-success border-success/20 flex items-center gap-1"
            >
                <TrendingUp className="h-3 w-3" /> Bull
            </Badge>
        );
    }
    return (
        <Badge
            variant="outline"
            className="bg-destructive/10 text-destructive border-destructive/20 flex items-center gap-1"
        >
            <TrendingDown className="h-3 w-3" /> Bear
        </Badge>
    );
}

export default function IntelligencePage() {
    const { data: intel, isLoading } = useTradeIntelligence();

    if (isLoading) {
        return (
            <div className="space-y-6">
                <PageHeader
                    title="AI Intelligence"
                    subtitle="Agent outputs and market signals"
                />
                <LoadingSkeleton variant="card" rows={4} />
            </div>
        );
    }

    const agentsEnabled =
        intel?.flags?.['agents:ai_synthesis:enabled'] ?? false;

    return (
        <div className="space-y-6">
            <PageHeader
                title="AI Intelligence"
                subtitle="Real-time output from all AI agents — updated each morning"
            />

            {!agentsEnabled && (
                <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-4 text-sm text-amber-700">
                    AI Synthesis is currently <strong>OFF</strong>. Go to
                    Feature Flags and enable &ldquo;AI Synthesis (Claude)&rdquo;
                    to activate the intelligence layer.
                </div>
            )}

            {/* Synthesis */}
            <Card>
                <CardHeader className="pb-3">
                    <div className="flex items-center justify-between flex-wrap gap-2">
                        <CardTitle className="text-base flex items-center gap-2">
                            <Brain className="h-4 w-4" />
                            AI Synthesis — Claude Recommendation
                        </CardTitle>
                        <AgeBadge
                            generatedAt={intel?.synthesis?.generated_at}
                        />
                    </div>
                    <CardDescription>
                        Claude synthesizes all signals into a single structured
                        trade recommendation.
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    {!intel?.synthesis?.direction ? (
                        <p className="text-sm text-muted-foreground italic">
                            No synthesis available. Enable AI Synthesis in
                            Feature Flags.
                        </p>
                    ) : (
                        <div className="space-y-4">
                            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                                <div>
                                    <p className="text-xs text-muted-foreground mb-1">
                                        Direction
                                    </p>
                                    <DirectionBadge
                                        direction={intel.synthesis.direction}
                                    />
                                </div>
                                <div>
                                    <p className="text-xs text-muted-foreground mb-1">
                                        Confidence
                                    </p>
                                    <p className="text-xl font-bold font-mono">
                                        {intel.synthesis.confidence != null
                                            ? `${(intel.synthesis.confidence * 100).toFixed(0)}%`
                                            : '—'}
                                    </p>
                                </div>
                                <div>
                                    <p className="text-xs text-muted-foreground mb-1">
                                        Strategy
                                    </p>
                                    <p className="text-sm font-medium capitalize">
                                        {intel.synthesis.strategy?.replace(
                                            /_/g,
                                            ' ',
                                        ) ?? '—'}
                                    </p>
                                </div>
                                <div>
                                    <p className="text-xs text-muted-foreground mb-1">
                                        Risk Level
                                    </p>
                                    <p className="text-xl font-bold font-mono">
                                        {intel.synthesis.risk_level ?? '—'}
                                        <span className="text-sm font-normal text-muted-foreground">
                                            /10
                                        </span>
                                    </p>
                                </div>
                            </div>
                            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                                <div>
                                    <p className="text-xs text-muted-foreground mb-1">
                                        Sizing Modifier
                                    </p>
                                    <p className="text-sm font-medium">
                                        {intel.synthesis.sizing_modifier != null
                                            ? `${intel.synthesis.sizing_modifier}×`
                                            : '—'}
                                    </p>
                                </div>
                                <div>
                                    <p className="text-xs text-muted-foreground mb-1">
                                        Signal Confluence
                                    </p>
                                    <p
                                        className={`text-sm font-medium ${
                                            (intel.synthesis.confluence_score ??
                                                0) >= 0.66
                                                ? 'text-success'
                                                : (intel.synthesis
                                                      .confluence_score ?? 0) >=
                                                  0.33
                                                ? 'text-amber-500'
                                                : 'text-muted-foreground'
                                        }`}
                                    >
                                        {intel.synthesis.confluence_score !=
                                        null
                                            ? `${(intel.synthesis.confluence_score * 100).toFixed(0)}% — ${
                                                  intel.synthesis
                                                      .confluence_score >= 0.66
                                                      ? 'all signals agree'
                                                      : intel.synthesis
                                                            .confluence_score >=
                                                        0.33
                                                      ? 'partial agreement'
                                                      : 'signals diverge'
                                              }`
                                            : '—'}
                                    </p>
                                </div>
                                <div>
                                    <p className="text-xs text-muted-foreground mb-1">
                                        Flow Direction
                                    </p>
                                    <DirectionBadge
                                        direction={
                                            intel.synthesis.flow_direction
                                        }
                                    />
                                </div>
                            </div>
                            {intel.synthesis.rationale && (
                                <div className="rounded-lg bg-muted/40 p-3">
                                    <p className="text-xs text-muted-foreground mb-1">
                                        Claude&apos;s Rationale
                                    </p>
                                    <p className="text-sm italic">
                                        &ldquo;{intel.synthesis.rationale}
                                        &rdquo;
                                    </p>
                                </div>
                            )}
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* Calendar + Flow + Sentiment row */}
            <div className="grid gap-4 md:grid-cols-3">
                {/* Calendar */}
                <Card>
                    <CardHeader className="pb-3">
                        <CardTitle className="text-sm font-medium flex items-center gap-2">
                            <Activity className="h-4 w-4" />
                            Economic Calendar
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-3">
                        {intel?.calendar?.day_classification && (
                            <div>
                                <p className="text-xs text-muted-foreground mb-1">
                                    Today
                                </p>
                                <Badge
                                    variant="outline"
                                    className={
                                        intel.calendar.day_classification ===
                                        'catalyst_major'
                                            ? 'bg-amber-500/10 text-amber-600 border-amber-500/20'
                                            : intel.calendar
                                                    .day_classification ===
                                                'earnings_major'
                                              ? 'bg-blue-500/10 text-blue-600 border-blue-500/20'
                                              : 'bg-muted text-muted-foreground border-border'
                                    }
                                >
                                    {intel.calendar.day_classification.replace(
                                        /_/g,
                                        ' ',
                                    )}
                                </Badge>
                            </div>
                        )}
                        {(intel?.calendar?.events?.length ?? 0) > 0 ? (
                            <div className="space-y-2">
                                <p className="text-xs text-muted-foreground">
                                    Events
                                </p>
                                {intel!.calendar!.events!.map((ev, i) => (
                                    <div
                                        key={i}
                                        className="flex items-start gap-2"
                                    >
                                        <div
                                            className={`mt-1 h-2 w-2 rounded-full shrink-0 ${
                                                ev.is_major
                                                    ? 'bg-amber-500'
                                                    : 'bg-muted-foreground'
                                            }`}
                                        />
                                        <div>
                                            <p className="text-xs font-medium">
                                                {ev.event}
                                            </p>
                                            {ev.time && (
                                                <p className="text-xs text-muted-foreground">
                                                    {ev.time} ET
                                                </p>
                                            )}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <p className="text-xs text-muted-foreground italic">
                                No events today
                            </p>
                        )}
                        {(intel?.calendar?.earnings?.length ?? 0) > 0 && (
                            <div>
                                <p className="text-xs text-muted-foreground mb-1">
                                    Major Earnings
                                </p>
                                <div className="flex flex-wrap gap-1">
                                    {intel!.calendar!.earnings!.map((e, i) => (
                                        <Badge
                                            key={i}
                                            variant="outline"
                                            className="text-xs"
                                        >
                                            {e.ticker}
                                        </Badge>
                                    ))}
                                </div>
                            </div>
                        )}
                    </CardContent>
                </Card>

                {/* Options Flow */}
                <Card>
                    <CardHeader className="pb-3">
                        <div className="flex items-center justify-between">
                            <CardTitle className="text-sm font-medium flex items-center gap-2">
                                <BarChart2 className="h-4 w-4" />
                                Options Flow
                            </CardTitle>
                            <AgeBadge
                                generatedAt={intel?.flow?.generated_at}
                            />
                        </div>
                    </CardHeader>
                    <CardContent className="space-y-3">
                        {intel?.flow?.flow_score == null ? (
                            <p className="text-xs text-muted-foreground italic">
                                Flow agent is off. Enable in Feature Flags.
                            </p>
                        ) : (
                            <>
                                <div>
                                    <p className="text-xs text-muted-foreground mb-1">
                                        Flow Score
                                    </p>
                                    <p
                                        className={`text-3xl font-bold font-mono ${
                                            (intel.flow.flow_score ?? 0) > 30
                                                ? 'text-success'
                                                : (intel.flow.flow_score ?? 0) <
                                                  -30
                                                ? 'text-destructive'
                                                : 'text-foreground'
                                        }`}
                                    >
                                        {(intel.flow.flow_score ?? 0) > 0
                                            ? '+'
                                            : ''}
                                        {intel.flow.flow_score}
                                    </p>
                                    <p className="text-xs text-muted-foreground">
                                        −100 (extreme puts) to +100 (extreme
                                        calls)
                                    </p>
                                </div>
                                <div className="grid grid-cols-2 gap-3">
                                    <div>
                                        <p className="text-xs text-muted-foreground mb-1">
                                            Direction
                                        </p>
                                        <DirectionBadge
                                            direction={
                                                intel.flow.flow_direction
                                            }
                                        />
                                    </div>
                                    <div>
                                        <p className="text-xs text-muted-foreground mb-1">
                                            P/C Ratio
                                        </p>
                                        <p className="text-sm font-medium font-mono">
                                            {intel.flow.put_call_ratio?.toFixed(
                                                2,
                                            ) ?? '—'}
                                        </p>
                                        <p className="text-xs text-muted-foreground">
                                            {(intel.flow.put_call_ratio ?? 1) <
                                            0.7
                                                ? 'bullish'
                                                : (intel.flow.put_call_ratio ??
                                                      1) > 1.3
                                                ? 'bearish'
                                                : 'neutral'}
                                        </p>
                                    </div>
                                </div>
                                {intel.flow.unusual_activity_count != null && (
                                    <p className="text-xs text-muted-foreground">
                                        {intel.flow.unusual_activity_count}{' '}
                                        unusual alerts detected
                                    </p>
                                )}
                            </>
                        )}
                    </CardContent>
                </Card>

                {/* Sentiment */}
                <Card>
                    <CardHeader className="pb-3">
                        <div className="flex items-center justify-between">
                            <CardTitle className="text-sm font-medium flex items-center gap-2">
                                <Newspaper className="h-4 w-4" />
                                Market Sentiment
                            </CardTitle>
                            <AgeBadge
                                generatedAt={intel?.sentiment?.generated_at}
                            />
                        </div>
                    </CardHeader>
                    <CardContent className="space-y-3">
                        {intel?.sentiment?.sentiment_score == null ? (
                            <p className="text-xs text-muted-foreground italic">
                                Sentiment agent is off. Enable in Feature Flags.
                            </p>
                        ) : (
                            <>
                                <div>
                                    <p className="text-xs text-muted-foreground mb-1">
                                        Sentiment Score
                                    </p>
                                    <p
                                        className={`text-3xl font-bold font-mono ${
                                            (intel.sentiment.sentiment_score ??
                                                0) > 20
                                                ? 'text-success'
                                                : (intel.sentiment
                                                      .sentiment_score ?? 0) <
                                                  -20
                                                ? 'text-destructive'
                                                : 'text-foreground'
                                        }`}
                                    >
                                        {(intel.sentiment.sentiment_score ??
                                            0) > 0
                                            ? '+'
                                            : ''}
                                        {intel.sentiment.sentiment_score}
                                    </p>
                                </div>
                                <div className="grid grid-cols-2 gap-3">
                                    <div>
                                        <p className="text-xs text-muted-foreground mb-1">
                                            Fear &amp; Greed
                                        </p>
                                        <p className="text-sm font-medium font-mono">
                                            {intel.sentiment.fear_greed_index ??
                                                '—'}
                                            <span className="text-xs font-normal text-muted-foreground">
                                                /100
                                            </span>
                                        </p>
                                        <p className="text-xs text-muted-foreground capitalize">
                                            {intel.sentiment.fear_greed_label ??
                                                ''}
                                        </p>
                                    </div>
                                    <div>
                                        <p className="text-xs text-muted-foreground mb-1">
                                            Overnight Gap
                                        </p>
                                        <p
                                            className={`text-sm font-medium font-mono ${
                                                (intel.sentiment
                                                    .overnight_gap_pct ?? 0) > 0
                                                    ? 'text-success'
                                                    : (intel.sentiment
                                                          .overnight_gap_pct ??
                                                          0) < 0
                                                    ? 'text-destructive'
                                                    : 'text-foreground'
                                            }`}
                                        >
                                            {intel.sentiment.overnight_gap_pct !=
                                            null
                                                ? `${
                                                      intel.sentiment
                                                          .overnight_gap_pct > 0
                                                          ? '+'
                                                          : ''
                                                  }${intel.sentiment.overnight_gap_pct.toFixed(2)}%`
                                                : '—'}
                                        </p>
                                    </div>
                                </div>
                                {(intel.sentiment.top_headlines?.length ?? 0) >
                                    0 && (
                                    <div>
                                        <p className="text-xs text-muted-foreground mb-1">
                                            Top Headlines
                                        </p>
                                        <div className="space-y-1">
                                            {intel.sentiment.top_headlines!
                                                .slice(0, 2)
                                                .map((h, i) => (
                                                    <p
                                                        key={i}
                                                        className="text-xs text-muted-foreground line-clamp-1"
                                                    >
                                                        • {h}
                                                    </p>
                                                ))}
                                        </div>
                                    </div>
                                )}
                            </>
                        )}
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
