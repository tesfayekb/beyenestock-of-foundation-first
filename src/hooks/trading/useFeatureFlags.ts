/**
 * useFeatureFlags — read and write Redis feature flags via the backend API.
 *
 * Phase 4C — backs the Feature Flag toggle panel on the Trading Console
 * Config page. Polls every 30 seconds so the UI reflects out-of-band
 * changes (e.g. flags toggled via railway-cli).
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL ?? 'https://diplomatic-mercy-production-7e61.up.railway.app';

export interface FlagDefinition {
    key: string;
    label: string;
    description: string;
    /** Minimum closed paper trades before this flag is safe to enable. */
    requiredTrades: number;
    category: 'agent' | 'strategy';
}

export const FLAG_DEFINITIONS: FlagDefinition[] = [
    {
        key: 'agents:ai_synthesis:enabled',
        label: 'AI Synthesis (Claude)',
        description:
            'Claude produces structured trade recommendations from all signal sources.',
        requiredTrades: 0,
        category: 'agent',
    },
    {
        key: 'agents:flow_agent:enabled',
        label: 'Flow Agent',
        description:
            'Unusual Whales + Polygon put/call ratio options flow intelligence.',
        requiredTrades: 20,
        category: 'agent',
    },
    {
        key: 'agents:sentiment_agent:enabled',
        label: 'Sentiment Agent',
        description:
            'NewsAPI headlines + CNN Fear/Greed + overnight gap sentiment scoring.',
        requiredTrades: 20,
        category: 'agent',
    },
    {
        key: 'strategy:iron_butterfly:enabled',
        label: 'Iron Butterfly',
        description:
            'Fires on gamma pin days when SPX is within 0.3% of the GEX wall.',
        requiredTrades: 5,
        category: 'strategy',
    },
    {
        key: 'strategy:long_straddle:enabled',
        label: 'Long Straddle',
        description:
            'Buys ATM straddle before catalyst events. Exits 30 min before announcement.',
        requiredTrades: 20,
        category: 'strategy',
    },
    {
        key: 'strategy:calendar_spread:enabled',
        label: 'Calendar Spread',
        description:
            'Post-catalyst IV crush. Sell 0DTE ATM / buy next-Friday ATM straddle.',
        requiredTrades: 20,
        category: 'strategy',
    },
    {
        key: 'strategy:ai_hint_override:enabled',
        label: 'AI Strategy Override',
        description:
            'AI synthesis overrides regime-based selection when confidence ≥ 0.65.',
        requiredTrades: 40,
        category: 'strategy',
    },
];

async function fetchFlags(): Promise<Record<string, boolean>> {
    if (!BACKEND_URL) return {};
    const res = await fetch(`${BACKEND_URL}/admin/trading/feature-flags`);
    if (!res.ok) throw new Error('Failed to fetch flags');
    const data = await res.json();
    return data.flags ?? {};
}

async function postFlag(flagKey: string, enabled: boolean): Promise<void> {
    if (!BACKEND_URL) throw new Error('VITE_BACKEND_URL not configured');
    const res = await fetch(`${BACKEND_URL}/admin/trading/feature-flags`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ flag_key: flagKey, enabled }),
    });
    if (!res.ok) throw new Error('Failed to update flag');
}

export function useFeatureFlags() {
    return useQuery({
        queryKey: ['feature-flags'],
        queryFn: fetchFlags,
        refetchInterval: 30_000,
        staleTime: 15_000,
        retry: 2,
    });
}

export function useSetFeatureFlag() {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: ({ flagKey, enabled }: { flagKey: string; enabled: boolean }) =>
            postFlag(flagKey, enabled),
        onSuccess: () => qc.invalidateQueries({ queryKey: ['feature-flags'] }),
    });
}
