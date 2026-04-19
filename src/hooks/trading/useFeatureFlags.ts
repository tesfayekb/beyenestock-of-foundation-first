/**
 * useFeatureFlags — read and write trading feature flags.
 *
 * CSP-fix: the Lovable-hosted frontend cannot fetch the Railway API
 * directly. Reads come from the trading_feature_flags Supabase table
 * (mirrored on every backend write). Writes go through the
 * `set-feature-flag` Supabase Edge Function, which forwards to
 * Railway server-side.
 *
 * Polarity:
 *   - Strategy/agent flags (default OFF): absent row = OFF, true = ON.
 *   - Signal flags (default ON):          absent row = ON,  false = OFF.
 * SIGNAL_FLAG_KEYS below MUST match _SIGNAL_FLAGS in backend/main.py.
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { supabase } from '@/integrations/supabase/client';
import { useToast } from '@/hooks/use-toast';

// Signal flags use REVERSE polarity (default ON). Keep this set in
// sync with _SIGNAL_FLAGS in backend/main.py.
// Source of truth: backend/main.py _SIGNAL_FLAGS — if you add a new
// signal flag there, mirror it here AND in the backend
// _SIGNAL_FLAG_DEFAULTS dict in strategy_selector.select().
const SIGNAL_FLAG_KEYS: ReadonlySet<string> = new Set([
    'signal:vix_term_filter:enabled',
    'signal:entry_time_gate:enabled',
    'signal:gex_directional_bias:enabled',
    'signal:market_breadth:enabled',
    'signal:earnings_proximity:enabled',
    'signal:iv_rank_filter:enabled',
]);

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

interface FeatureFlagRow {
    flag_key: string;
    enabled: boolean;
}

async function fetchFlags(): Promise<Record<string, boolean>> {
    // The trading_feature_flags table is not in the generated Database
    // types yet — cast to `never` to satisfy supabase-js without
    // disabling type-checking elsewhere. Same pattern as
    // useAbComparison / useEarningsStatus.
    const { data, error } = await supabase
        .from('trading_feature_flags' as never)
        .select('flag_key, enabled');
    if (error) throw new Error(error.message);
    const flags: Record<string, boolean> = {};
    for (const row of (data ?? []) as FeatureFlagRow[]) {
        flags[row.flag_key] = row.enabled;
    }
    return flags;
}

async function postFlag(
    flagKey: string,
    enabled: boolean,
): Promise<void> {
    // Edge Function forwards to Railway server-side (CSP-allowed).
    const { data, error } = await supabase.functions.invoke(
        'set-feature-flag',
        {
            method: 'POST',
            body: { flag_key: flagKey, enabled },
        },
    );
    if (error) throw new Error(error.message);
    const payload = data as { ok?: boolean; error?: string } | null;
    if (!payload?.ok) {
        throw new Error(payload?.error ?? 'Failed to update flag');
    }
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
    const { toast } = useToast();
    return useMutation({
        mutationFn: ({ flagKey, enabled }: { flagKey: string; enabled: boolean }) =>
            postFlag(flagKey, enabled),
        onSuccess: () => qc.invalidateQueries({ queryKey: ['feature-flags'] }),
        // P1-13: surface failed toggles. Without this, an Edge Function
        // 4xx/5xx silently became a no-op and the optimistic UI made
        // the operator think the flag had flipped.
        onError: (error: Error) => {
            toast({
                title: 'Flag toggle failed',
                description:
                    error.message ?? 'Could not update flag. Check permissions.',
                variant: 'destructive',
            });
        },
    });
}

/**
 * Apply signal-flag default-ON polarity to a raw flag map.
 *
 * Strategy/agent flags: absent = OFF (use `flags[key] ?? false`).
 * Signal flags:         absent = ON  (use `flags[key] ?? true`).
 */
export function isFlagEnabled(
    flags: Record<string, boolean> | undefined,
    key: string,
): boolean {
    const raw = flags?.[key];
    if (raw !== undefined) return raw;
    return SIGNAL_FLAG_KEYS.has(key);
}
