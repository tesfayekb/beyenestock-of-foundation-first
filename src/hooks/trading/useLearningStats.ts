/**
 * useLearningStats — Section 13 UI-1/UI-3 shared reader.
 *
 * Calls the Supabase Edge Function `get-learning-stats`, which
 * proxies to Railway's GET /admin/trading/learning-stats. Edge
 * Function invoke is the only CSP-allowed path from the Lovable
 * frontend to the Railway API (same pattern as useFeatureFlags —
 * see src/hooks/trading/useFeatureFlags.ts).
 *
 * Every field is optional / nullable because the backend endpoint
 * is fail-open: missing Redis keys become null / defaults, so the
 * UI must render warmup states without assumptions.
 */
import { useQuery } from '@tanstack/react-query';
import { supabase } from '@/integrations/supabase/client';

export interface StrategyMatrixCell {
    regime: string;
    strategy: string;
    trade_count?: number | null;
    win_rate?: number | null;
    avg_pnl?: number | null;
    profit_factor?: number | null;
    // backend may add more fields — keep the shape loose
    [key: string]: unknown;
}

export interface ButterflyThresholds {
    gex_conf: number | null;
    wall_distance: number | null;
    concentration: number | null;
    source: 'calibrated' | 'default' | string;
}

export interface LearningStats {
    realized_vol_20d: number | null;
    vix_current: number | null;
    iv_rv_ratio: number | null;
    realized_vol_last_date: string | null;
    butterfly_gates: Record<string, number>;
    butterfly_allowed_today: number | null;
    strategy_matrix: StrategyMatrixCell[];
    halt_threshold_pct: number | null;
    halt_threshold_source: 'adaptive' | 'default' | string;
    butterfly_thresholds: ButterflyThresholds;
    model_drift_alert: boolean;
    sizing_phase: number;
    sizing_phase_advanced_at: string | null;
    // Edge proxy surfaces this when Railway is unreachable. UI can
    // ignore it for rendering but it is useful for operator triage.
    error?: string;
}

async function fetchLearningStats(): Promise<LearningStats> {
    const { data, error } = await supabase.functions.invoke<LearningStats>(
        'get-learning-stats',
        { method: 'GET' },
    );
    if (error) throw new Error(error.message);
    if (!data) throw new Error('Empty learning-stats response');
    return data;
}

/**
 * Full Learning Dashboard query — 60s refetch, 2 retries.
 * Use on the Learning page.
 */
export function useLearningStats() {
    return useQuery({
        queryKey: ['learning-stats'],
        queryFn: fetchLearningStats,
        refetchInterval: 60_000,
        staleTime: 30_000,
        retry: 2,
    });
}

/**
 * Banner query — slower refetch (120s) and a distinct cache key so
 * navigating between WarRoom / Performance / Learning does not
 * double-fetch or evict each other's data.
 */
export function useLearningStatsBanner() {
    return useQuery({
        queryKey: ['learning-stats-banner'],
        queryFn: fetchLearningStats,
        refetchInterval: 120_000,
        staleTime: 60_000,
        retry: 1,
    });
}
