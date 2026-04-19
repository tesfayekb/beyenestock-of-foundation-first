/**
 * useTradeIntelligence — reads AI agent brief summaries directly
 * from Supabase.
 *
 * CSP-fix: agent briefs are mirrored from Redis into the
 * trading_ai_briefs table by each agent on every write. The hook
 * reads the table directly so this works under the Lovable-hosted
 * CSP (which blocks browser fetches to the Railway API).
 *
 * Brief kinds correspond 1:1 to the previous Railway response:
 *   calendar  ← economic_calendar
 *   macro     ← macro_agent
 *   flow      ← flow_agent
 *   sentiment ← sentiment_agent
 *   synthesis ← synthesis_agent (also updated by surprise_detector)
 *
 * The trading_ai_briefs table is not in the generated Database
 * types yet — cast the from() argument with `as never`. Same
 * pattern as useAbComparison / useEarningsStatus.
 */
import { useQuery } from '@tanstack/react-query';
import { supabase } from '@/integrations/supabase/client';

export interface CalendarIntel {
    day_classification?: string;
    recommended_posture?: string;
    events?: Array<{ event: string; is_major: boolean; time?: string }>;
    earnings?: Array<{ ticker: string }>;
}

export interface SynthesisIntel {
    direction?: string;
    confidence?: number;
    strategy?: string;
    rationale?: string;
    risk_level?: number;
    sizing_modifier?: number;
    confluence_score?: number;
    flow_direction?: string;
    sentiment_direction?: string;
    generated_at?: string;
    source?: string;
}

export interface FlowIntel {
    flow_score?: number;
    flow_direction?: string;
    flow_confidence?: number;
    put_call_ratio?: number;
    unusual_activity_count?: number;
    generated_at?: string;
}

export interface SentimentIntel {
    sentiment_score?: number;
    sentiment_direction?: string;
    fear_greed_index?: number;
    fear_greed_label?: string;
    overnight_gap_pct?: number;
    top_headlines?: string[];
    generated_at?: string;
}

export interface TradingIntelligence {
    calendar: CalendarIntel;
    macro: Record<string, unknown>;
    synthesis: SynthesisIntel;
    flow: FlowIntel;
    sentiment: SentimentIntel;
    flags: Record<string, boolean>;
}

const EMPTY_INTEL: TradingIntelligence = {
    calendar: {},
    macro: {},
    synthesis: {},
    flow: {},
    sentiment: {},
    flags: {},
};

interface BriefRow {
    brief_kind: string;
    payload: Record<string, unknown>;
    generated_at: string;
}

interface FlagRow {
    flag_key: string;
    enabled: boolean;
}

async function fetchIntelligence(): Promise<TradingIntelligence> {
    const [briefsResult, flagsResult] = await Promise.all([
        supabase
            .from('trading_ai_briefs' as never)
            .select('brief_kind, payload, generated_at'),
        supabase
            .from('trading_feature_flags' as never)
            .select('flag_key, enabled'),
    ]);

    // C-6: throw on query errors so React Query exposes isError.
    // Previously these were silently coerced to empty arrays — the
    // page rendered as "no agents ran today" instead of showing an
    // error state when RLS / Supabase actually failed.
    if (briefsResult.error) throw briefsResult.error;
    if (flagsResult.error) throw flagsResult.error;

    const briefs = (briefsResult.data ?? []) as BriefRow[];
    const flagRows = (flagsResult.data ?? []) as FlagRow[];

    const byKind = (kind: string): Record<string, unknown> => {
        const row = briefs.find((b) => b.brief_kind === kind);
        return row?.payload ?? {};
    };

    const flags: Record<string, boolean> = {};
    for (const row of flagRows) {
        flags[row.flag_key] = row.enabled;
    }

    return {
        ...EMPTY_INTEL,
        calendar: byKind('calendar') as CalendarIntel,
        macro: byKind('macro'),
        flow: byKind('flow') as FlowIntel,
        sentiment: byKind('sentiment') as SentimentIntel,
        synthesis: byKind('synthesis') as SynthesisIntel,
        flags,
    };
}

export function useTradeIntelligence() {
    return useQuery({
        queryKey: ['trade-intelligence'],
        queryFn: fetchIntelligence,
        refetchInterval: 5 * 60_000,
        staleTime: 4 * 60_000,
        retry: 2,
    });
}

/** Minutes since the brief was generated. -1 if no timestamp available. */
export function briefAgeMinutes(generatedAt?: string): number {
    if (!generatedAt) return -1;
    return (Date.now() - new Date(generatedAt).getTime()) / 60_000;
}

/** True when the brief is missing a timestamp or older than 8 hours. */
export function isBriefStale(generatedAt?: string): boolean {
    const age = briefAgeMinutes(generatedAt);
    return age < 0 || age > 480;
}
