/**
 * useTradeIntelligence — reads AI agent brief summaries from the backend.
 *
 * Phase 4C — backs the AI Intelligence panel on the War Room. Refreshes
 * every 5 minutes (agents only run on a 5-30 min cadence, so faster
 * polling is wasted work). Stale data (> 8 hr old) is flagged via
 * ``isBriefStale`` so the UI can surface it.
 */
import { useQuery } from '@tanstack/react-query';

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL ?? 'https://diplomatic-mercy-production-7e61.up.railway.app';

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

async function fetchIntelligence(): Promise<TradingIntelligence> {
    if (!BACKEND_URL) return EMPTY_INTEL;
    const res = await fetch(`${BACKEND_URL}/admin/trading/intelligence`);
    if (!res.ok) throw new Error('Failed to fetch intelligence');
    return res.json();
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
