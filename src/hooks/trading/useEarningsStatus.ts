/**
 * useEarningsStatus — fetches Phase 5A earnings system snapshot.
 *
 * Backs the /trading/earnings page. Shape mirrors the
 * /admin/earnings/status response from backend/main.py exactly.
 *
 * Polls every 5 minutes — earnings data changes rarely intraday
 * (the 8:45 AM scan is the main writer). BACKEND_URL fallback
 * mirrors useAbComparison.ts and useActivationStatus.ts so the
 * hook works identically when VITE_BACKEND_URL is unset (Lovable
 * preview).
 */
import { useQuery } from '@tanstack/react-query';

const BACKEND_URL =
    import.meta.env.VITE_BACKEND_URL ??
    'https://diplomatic-mercy-production-7e61.up.railway.app';

export interface EarningsUpcomingEvent {
    ticker: string;
    earnings_date: string;
    announce_time: string;
    entry_date: string | null;
    edge_score: number | null;
    should_enter: boolean;
}

export interface EarningsActivePosition {
    id?: string;
    ticker: string;
    earnings_date: string;
    announce_time?: string;
    entry_date?: string;
    expiry_date?: string;
    call_strike?: number;
    put_strike?: number;
    stock_price_at_entry?: number;
    total_debit?: number;
    contracts?: number;
    implied_move_pct?: number;
    historical_edge_score?: number;
    status?: string;
}

export interface EarningsRecentPosition {
    id: string;
    ticker: string;
    earnings_date: string;
    announce_time: string | null;
    entry_date: string;
    exit_date: string | null;
    status: string;
    exit_reason: string | null;
    contracts: number | null;
    total_debit: number | null;
    exit_value: number | null;
    net_pnl: number | null;
    net_pnl_pct: number | null;
    implied_move_pct: number | null;
    actual_move_pct: number | null;
    historical_edge_score: number | null;
}

export interface EarningsStatusResponse {
    upcoming: EarningsUpcomingEvent[];
    active: EarningsActivePosition | null;
    recent_positions: EarningsRecentPosition[];
    last_scan_at: string | null;
}

async function fetchEarningsStatus(): Promise<EarningsStatusResponse> {
    const res = await fetch(`${BACKEND_URL}/admin/earnings/status`);
    if (!res.ok) throw new Error('Failed to fetch earnings status');
    const data = await res.json();
    return {
        upcoming: (data.upcoming ?? []) as EarningsUpcomingEvent[],
        active: (data.active ?? null) as EarningsActivePosition | null,
        recent_positions: (data.recent_positions ?? []) as EarningsRecentPosition[],
        last_scan_at: (data.last_scan_at ?? null) as string | null,
    };
}

export function useEarningsStatus() {
    return useQuery({
        queryKey: ['earnings-status'],
        queryFn: fetchEarningsStatus,
        refetchInterval: 5 * 60_000,
        staleTime: 4 * 60_000,
        retry: 2,
    });
}
