/**
 * useAbComparison — fetches Phase 3B A/B gate status + daily rows.
 *
 * Backs the /trading/ab-comparison page. The shape of `gate` mirrors
 * shadow_engine.get_ab_gate_status() exactly — keep these in sync.
 *
 * BACKEND_URL default mirrors useFeatureFlags.ts and useActivationStatus.ts
 * so the hook works identically when VITE_BACKEND_URL is unset.
 */
import { useQuery } from '@tanstack/react-query';

const BACKEND_URL =
    import.meta.env.VITE_BACKEND_URL ??
    'https://diplomatic-mercy-production-7e61.up.railway.app';

export interface AbGateStatus {
    built: boolean;
    days_elapsed: number;
    days_required: number;
    trades_count?: number;
    trades_required?: number;
    a_total_pnl?: number;
    b_total_pnl?: number;
    a_annualized_pct?: number;
    b_annualized_pct?: number;
    portfolio_b_lead_pct: number | null;
    gate_passed: boolean;
}

export interface AbDailyRow {
    session_date: string;
    a_synthetic_pnl: number | null;
    b_session_pnl: number | null;
    move_pct: number | null;
    a_no_trade: boolean;
    b_no_trade: boolean;
    a_regime: string | null;
}

export interface AbComparisonResponse {
    gate: AbGateStatus;
    daily: AbDailyRow[];
}

async function fetchAbStatus(): Promise<AbComparisonResponse> {
    const res = await fetch(`${BACKEND_URL}/admin/ab/status`);
    if (!res.ok) throw new Error('Failed to fetch A/B status');
    const data = await res.json();
    return {
        gate: data.gate as AbGateStatus,
        daily: (data.daily ?? []) as AbDailyRow[],
    };
}

export function useAbComparison() {
    return useQuery({
        queryKey: ['ab-comparison'],
        queryFn: fetchAbStatus,
        refetchInterval: 5 * 60_000,
        staleTime: 4 * 60_000,
        retry: 2,
    });
}
