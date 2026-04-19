/**
 * Subscriptions — /trading/subscriptions
 * All external services the system depends on: cost, key status,
 * masked key preview, and dashboard links.
 *
 * Security: masked key previews show first 4 + last 6 chars only.
 * Full keys are never stored in this system — use Railway for that.
 * MFA is already required to access this page.
 */
import { useQuery } from '@tanstack/react-query';
import { ExternalLink, CheckCircle2, XCircle, Eye } from 'lucide-react';
import { PageHeader } from '@/components/dashboard/PageHeader';
import { LoadingSkeleton } from '@/components/dashboard/LoadingSkeleton';
import { Badge } from '@/components/ui/badge';
import {
    Card,
    CardContent,
    CardHeader,
    CardTitle,
} from '@/components/ui/card';

const BACKEND_URL =
    (import.meta.env.VITE_BACKEND_URL as string | undefined) ??
    'https://diplomatic-mercy-production-7e61.up.railway.app';

// ─── Service definitions ─────────────────────────────────────────────────────

interface ServiceDef {
    id: string;
    name: string;
    purpose: string;
    costMonthly: number;
    costNote?: string;
    dashboardUrl: string;
    keyId: string;
    healthServiceName?: string;
    category: 'infrastructure' | 'data' | 'ai' | 'execution';
}

const SERVICES: ServiceDef[] = [
    // Infrastructure
    {
        id: 'railway',
        name: 'Railway',
        purpose: 'Backend hosting (diplomatic-mercy)',
        costMonthly: 20,
        costNote: 'Variable by usage',
        dashboardUrl: 'https://railway.app',
        keyId: '',
        category: 'infrastructure',
    },
    {
        id: 'supabase',
        name: 'Supabase',
        purpose: 'Database (trading positions, sessions, predictions)',
        costMonthly: 25,
        dashboardUrl:
            'https://supabase.com/dashboard/project/hnfvuxcwjferoocvybnf',
        keyId: 'supabase_url',
        category: 'infrastructure',
    },
    {
        id: 'lovable',
        name: 'Lovable',
        purpose: 'Frontend hosting and deployment',
        costMonthly: 25,
        dashboardUrl: 'https://lovable.dev',
        keyId: '',
        category: 'infrastructure',
    },
    {
        id: 'redis',
        name: 'Redis (Railway)',
        purpose: 'Agent briefs, feature flags, GEX data, session state',
        costMonthly: 5,
        costNote: 'Included in Railway plan',
        dashboardUrl: 'https://railway.app',
        keyId: '',
        category: 'infrastructure',
    },
    // Data feeds
    {
        id: 'databento',
        name: 'Databento',
        purpose: 'OPRA real-time options trade feed (SPXW/SPX)',
        costMonthly: 150,
        dashboardUrl: 'https://app.databento.com',
        keyId: 'databento',
        healthServiceName: 'databento_feed',
        category: 'data',
    },
    {
        id: 'polygon',
        name: 'Polygon.io',
        purpose: 'VIX, VVIX, SPX price data, options put/call ratios',
        costMonthly: 79,
        dashboardUrl: 'https://polygon.io/dashboard',
        keyId: 'polygon',
        healthServiceName: 'polygon_feed',
        category: 'data',
    },
    {
        id: 'finnhub',
        name: 'Finnhub',
        purpose: 'Economic calendar (FOMC/CPI/NFP) with consensus data',
        costMonthly: 0,
        costNote: '$125/yr billed annually',
        dashboardUrl: 'https://finnhub.io/dashboard',
        keyId: 'finnhub',
        healthServiceName: 'economic_calendar',
        category: 'data',
    },
    {
        id: 'unusual_whales',
        name: 'Unusual Whales',
        purpose: 'Options flow alerts (large unusual trades)',
        costMonthly: 126,
        dashboardUrl: 'https://unusualwhales.com',
        keyId: 'unusual_whales',
        healthServiceName: 'flow_agent',
        category: 'data',
    },
    {
        id: 'newsapi',
        name: 'NewsAPI',
        purpose: 'Financial headlines for sentiment scoring',
        costMonthly: 0,
        costNote: 'Free tier (100 req/day)',
        dashboardUrl: 'https://newsapi.org/account',
        keyId: 'newsapi',
        healthServiceName: 'sentiment_agent',
        category: 'data',
    },
    // AI
    {
        id: 'anthropic',
        name: 'Anthropic (Claude)',
        purpose: 'Morning synthesis — trade recommendations',
        costMonthly: 0,
        costNote: 'Usage-based (~$0.003/call)',
        dashboardUrl: 'https://console.anthropic.com',
        keyId: 'anthropic',
        healthServiceName: 'synthesis_agent',
        category: 'ai',
    },
    {
        id: 'openai',
        name: 'OpenAI (optional)',
        purpose: 'Alternative synthesis provider — set AI_PROVIDER=openai',
        costMonthly: 0,
        costNote: 'Usage-based if enabled',
        dashboardUrl: 'https://platform.openai.com',
        keyId: 'openai',
        category: 'ai',
    },
    // Execution
    {
        id: 'tradier',
        name: 'Tradier',
        purpose: 'Options execution (paper + live trading)',
        costMonthly: 0,
        costNote: 'Commission per trade (~$0.35/contract)',
        dashboardUrl: 'https://dash.tradier.com',
        keyId: 'tradier',
        healthServiceName: 'tradier_websocket',
        category: 'execution',
    },
];

const CATEGORY_LABELS: Record<ServiceDef['category'], string> = {
    infrastructure: 'Infrastructure',
    data: 'Data Feeds',
    ai: 'AI Providers',
    execution: 'Execution',
};

const CATEGORY_ORDER: ServiceDef['category'][] = [
    'infrastructure',
    'data',
    'ai',
    'execution',
];

// ─── Hooks ────────────────────────────────────────────────────────────────────

interface KeyStatus {
    configured?: boolean;
    masked?: string;
    env_var?: string;
    sandbox?: boolean;
    today_tokens_in?: number;
    today_tokens_out?: number;
    provider?: string;
    model?: string;
}

async function fetchKeyStatus(): Promise<Record<string, KeyStatus>> {
    const res = await fetch(`${BACKEND_URL}/admin/subscriptions/key-status`);
    if (!res.ok) throw new Error('Failed to fetch key status');
    const data = await res.json();
    return data.keys ?? {};
}

// ─── Sub-components ──────────────────────────────────────────────────────────

function KeyBadge({
    keyId,
    keys,
}: {
    keyId: string;
    keys: Record<string, KeyStatus>;
}) {
    if (!keyId) {
        return (
            <Badge
                variant="outline"
                className="text-xs bg-muted text-muted-foreground border-border"
            >
                Login only
            </Badge>
        );
    }
    const info = keys[keyId];
    if (!info) {
        return (
            <Badge
                variant="outline"
                className="text-xs bg-muted text-muted-foreground border-border"
            >
                Unknown
            </Badge>
        );
    }
    if (!info.configured) {
        return (
            <Badge
                variant="outline"
                className="text-xs bg-destructive/10 text-destructive border-destructive/20 flex items-center gap-1"
            >
                <XCircle className="h-3 w-3" />
                Not configured
            </Badge>
        );
    }
    return (
        <Badge
            variant="outline"
            className="text-xs bg-success/10 text-success border-success/20 flex items-center gap-1"
        >
            <CheckCircle2 className="h-3 w-3" />
            Configured
        </Badge>
    );
}

function MaskedKey({
    keyId,
    keys,
}: {
    keyId: string;
    keys: Record<string, KeyStatus>;
}) {
    if (!keyId) return null;
    const info = keys[keyId];
    if (!info?.configured) return null;
    return (
        <span className="text-xs font-mono text-muted-foreground flex items-center gap-1">
            <Eye className="h-3 w-3" />
            {info.masked}
        </span>
    );
}

function CostDisplay({ service }: { service: ServiceDef }) {
    if (service.costMonthly === 0 && service.costNote) {
        return (
            <span className="text-sm font-medium text-muted-foreground">
                {service.costNote}
            </span>
        );
    }
    return (
        <div>
            <span className="text-sm font-bold font-mono">
                ${service.costMonthly}
                <span className="text-xs font-normal text-muted-foreground">
                    /mo
                </span>
            </span>
            {service.costNote && (
                <p className="text-xs text-muted-foreground">
                    {service.costNote}
                </p>
            )}
        </div>
    );
}

// ─── Main page ───────────────────────────────────────────────────────────────

export default function SubscriptionsPage() {
    const {
        data: keys = {},
        isLoading,
        error,
    } = useQuery({
        queryKey: ['subscription-key-status'],
        queryFn: fetchKeyStatus,
        refetchInterval: 60_000,
        staleTime: 30_000,
        retry: 2,
    });

    // Monthly fixed cost total
    const monthlyTotal = SERVICES.reduce(
        (sum, s) => sum + s.costMonthly,
        0,
    );

    // Today's AI token usage (Anthropic counter; both providers feed it)
    const anthropicInfo = keys['anthropic'];
    const tokensIn = anthropicInfo?.today_tokens_in ?? 0;
    const tokensOut = anthropicInfo?.today_tokens_out ?? 0;
    const aiProvider = keys['ai_provider'];

    return (
        <div className="space-y-6">
            <PageHeader
                title="Subscriptions"
                subtitle="All external services, API keys, and operating costs"
            />

            {/* Security note */}
            <div className="rounded-lg border bg-muted/30 p-3 text-xs text-muted-foreground">
                <span className="font-medium text-foreground">Security: </span>
                Key previews show first 4 + last 6 characters only. Full keys
                are stored in Railway environment variables — never in this
                system. This page requires MFA to access.
            </div>

            {/* Summary cards */}
            <div className="grid gap-3 grid-cols-2 sm:grid-cols-4">
                <Card>
                    <CardContent className="pt-4 pb-3">
                        <p className="text-xs text-muted-foreground mb-1">
                            Monthly (fixed)
                        </p>
                        <p className="text-2xl font-bold font-mono">
                            ${monthlyTotal}
                        </p>
                        <p className="text-xs text-muted-foreground">
                            ~${(monthlyTotal * 12).toLocaleString()}/yr
                        </p>
                    </CardContent>
                </Card>
                <Card>
                    <CardContent className="pt-4 pb-3">
                        <p className="text-xs text-muted-foreground mb-1">
                            Variable costs
                        </p>
                        <p className="text-sm font-medium">Tradier + AI</p>
                        <p className="text-xs text-muted-foreground">
                            Commission + token based
                        </p>
                    </CardContent>
                </Card>
                <Card>
                    <CardContent className="pt-4 pb-3">
                        <p className="text-xs text-muted-foreground mb-1">
                            AI provider
                        </p>
                        <p className="text-sm font-medium capitalize">
                            {aiProvider?.provider ?? 'anthropic'}
                        </p>
                        <p className="text-xs text-muted-foreground font-mono">
                            {aiProvider?.model ?? 'claude-sonnet-4-5'}
                        </p>
                    </CardContent>
                </Card>
                <Card>
                    <CardContent className="pt-4 pb-3">
                        <p className="text-xs text-muted-foreground mb-1">
                            AI tokens today
                        </p>
                        <p className="text-sm font-medium font-mono">
                            {(tokensIn + tokensOut).toLocaleString()}
                        </p>
                        <p className="text-xs text-muted-foreground">
                            {tokensIn.toLocaleString()} in /{' '}
                            {tokensOut.toLocaleString()} out
                        </p>
                    </CardContent>
                </Card>
            </div>

            {isLoading && <LoadingSkeleton variant="card" rows={3} />}

            {!isLoading && error && (
                <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-3 text-xs text-amber-700">
                    Could not reach backend for key status. Showing service
                    list without live status.
                </div>
            )}

            {/* Services by category */}
            {CATEGORY_ORDER.map((category) => {
                const services = SERVICES.filter(
                    (s) => s.category === category,
                );
                return (
                    <Card key={category}>
                        <CardHeader className="pb-3">
                            <CardTitle className="text-sm font-medium">
                                {CATEGORY_LABELS[category]}
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="p-0">
                            <div className="divide-y">
                                {services.map((service) => (
                                    <div
                                        key={service.id}
                                        className="flex items-start gap-3 px-6 py-3 hover:bg-muted/30 transition-colors"
                                    >
                                        {/* Service info */}
                                        <div className="flex-1 min-w-0 space-y-1">
                                            <div className="flex items-center gap-2 flex-wrap">
                                                <span className="text-sm font-medium">
                                                    {service.name}
                                                </span>
                                                <KeyBadge
                                                    keyId={service.keyId}
                                                    keys={keys}
                                                />
                                                {service.keyId === 'tradier' &&
                                                    keys['tradier']?.sandbox && (
                                                        <Badge
                                                            variant="outline"
                                                            className="text-xs bg-amber-500/10 text-amber-600 border-amber-500/20"
                                                        >
                                                            Sandbox
                                                        </Badge>
                                                    )}
                                            </div>
                                            <p className="text-xs text-muted-foreground">
                                                {service.purpose}
                                            </p>
                                            <MaskedKey
                                                keyId={service.keyId}
                                                keys={keys}
                                            />
                                        </div>

                                        {/* Cost */}
                                        <div className="text-right shrink-0 min-w-[80px]">
                                            <CostDisplay service={service} />
                                        </div>

                                        {/* Dashboard link */}
                                        <a
                                            href={service.dashboardUrl}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="shrink-0 text-muted-foreground hover:text-foreground transition-colors mt-0.5"
                                            title={`Open ${service.name} dashboard`}
                                        >
                                            <ExternalLink className="h-4 w-4" />
                                        </a>
                                    </div>
                                ))}
                            </div>
                        </CardContent>
                    </Card>
                );
            })}

            {/* Footer note */}
            <p className="text-xs text-muted-foreground">
                To update API keys: Railway → friendly-peace → diplomatic-mercy
                → Variables. Changes take effect on next Railway redeploy. For
                key rotation: update Railway first, then verify the new masked
                preview here.
            </p>
        </div>
    );
}
