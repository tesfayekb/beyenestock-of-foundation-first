/**
 * useEarningsStatus — fetches Phase 5A earnings system snapshot.
 *
 * Backs the /trading/earnings page. Direct Supabase queries (no
 * Railway fetch) so this works under the Lovable-hosted CSP, which
 * blocks direct browser calls to the Railway API.
 *
 * KNOWN GAP: the upcoming-events list is written to Redis by the
 * 8:45 AM ET scan and is NOT mirrored into Supabase yet. Until
 * Phase 5A-2 adds a persisted events table, the upcoming section
 * stays empty in the UI and the existing empty-state copy carries
 * the message ("Earnings scan runs at 8:45 AM ET …").
 *
 * The earnings_positions table is not in the generated Database
 * types yet — we cast the from() argument with `as never` to
 * satisfy the typed supabase-js client without disabling
 * type-checking elsewhere. Same pattern as useAbComparison.
 */
import { useQuery } from '@tanstack/react-query';
import { supabase } from '@/integrations/supabase/client';

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

export function useEarningsStatus() {
    return useQuery<EarningsStatusResponse>({
        queryKey: ['earnings-status'],
        queryFn: async () => {
            const [recentResult, activeResult] = await Promise.all([
                supabase
                    .from('earnings_positions' as never)
                    .select(
                        'id, ticker, earnings_date, announce_time, ' +
                            'entry_date, exit_date, status, exit_reason, ' +
                            'contracts, total_debit, exit_value, ' +
                            'net_pnl, net_pnl_pct, implied_move_pct, ' +
                            'actual_move_pct, historical_edge_score',
                    )
                    .order('entry_date', { ascending: false })
                    .limit(30),
                supabase
                    .from('earnings_positions' as never)
                    .select('*')
                    .eq('status', 'open')
                    .eq('position_mode', 'virtual')
                    .limit(1)
                    .maybeSingle(),
            ]);

            const recent_positions = (recentResult.data ??
                []) as EarningsRecentPosition[];
            const active = (activeResult.data ??
                null) as EarningsActivePosition | null;

            return {
                // Upcoming events live in Redis (written by the 8:45 AM
                // scan). Until Phase 5A-2 mirrors them to Supabase, this
                // stays empty and the page shows its empty-state copy.
                upcoming: [],
                active,
                recent_positions,
                last_scan_at: null,
            };
        },
        refetchInterval: 5 * 60_000,
        staleTime: 4 * 60_000,
        retry: 2,
    });
}
