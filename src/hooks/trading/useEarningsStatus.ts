/**
 * useEarningsStatus — fetches Phase 5A earnings system snapshot.
 *
 * Backs the /trading/earnings page. Direct Supabase queries (no
 * Railway fetch) so this works under the Lovable-hosted CSP, which
 * blocks direct browser calls to the Railway API.
 *
 * The 8:45 AM ET scan now mirrors `earnings:upcoming_events` into
 * the earnings_upcoming_scan Supabase table (one row per scan).
 * The hook reads the most recent row by scanned_at; if no scan has
 * landed yet, the section stays empty and the page shows its
 * empty-state copy.
 *
 * Both earnings_positions and earnings_upcoming_scan are not in the
 * generated Database types yet — we cast the from() argument with
 * `as never` to satisfy the typed supabase-js client without
 * disabling type-checking elsewhere. Same pattern as
 * useAbComparison.
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

interface UpcomingScanRow {
    scanned_at: string;
    payload: EarningsUpcomingEvent[];
}

export function useEarningsStatus() {
    return useQuery<EarningsStatusResponse>({
        queryKey: ['earnings-status'],
        queryFn: async () => {
            const [recentResult, activeResult, scanResult] =
                await Promise.all([
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
                    supabase
                        .from('earnings_upcoming_scan' as never)
                        .select('scanned_at, payload')
                        .order('scanned_at', { ascending: false })
                        .limit(1)
                        .maybeSingle(),
                ]);

            // P1-10: throw on primary-query errors so React Query
            // exposes isError. activeResult uses maybeSingle (null is
            // a valid result), so we still throw on actual errors.
            // scanResult is best-effort — earnings_upcoming_scan may
            // be empty before the first 8:45 AM scan lands.
            if (recentResult.error) throw recentResult.error;
            if (activeResult.error) throw activeResult.error;

            const recent_positions = (recentResult.data ??
                []) as EarningsRecentPosition[];
            const active = (activeResult.data ??
                null) as EarningsActivePosition | null;

            const scanRow = (scanResult.data ?? null) as UpcomingScanRow | null;
            const upcoming = (scanRow?.payload ?? []) as EarningsUpcomingEvent[];
            const last_scan_at = scanRow?.scanned_at ?? null;

            return {
                upcoming,
                active,
                recent_positions,
                last_scan_at,
            };
        },
        refetchInterval: 5 * 60_000,
        staleTime: 4 * 60_000,
        retry: 2,
    });
}
