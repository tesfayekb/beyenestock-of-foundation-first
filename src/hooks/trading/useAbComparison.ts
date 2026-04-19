/**
 * useAbComparison — fetches Phase 3B A/B gate status + daily rows.
 *
 * Backs the /trading/ab-comparison page. The shape of `gate` mirrors
 * shadow_engine.get_ab_gate_status() exactly — keep these in sync
 * whenever the backend gate logic changes.
 *
 * Direct Supabase queries (no Railway fetch) so this works under the
 * Lovable-hosted CSP, which blocks direct browser calls to the
 * Railway API. All A/B data lives in Supabase tables anyway:
 *   - ab_session_comparison (90 days of synthetic vs real P&L)
 *   - trading_positions     (closed-trade count for the gate)
 * The new tables are not in the generated Database types yet — we
 * cast the from() argument with `as never` to satisfy the typed
 * supabase-js client without disabling type-checking elsewhere.
 */
import { useQuery } from '@tanstack/react-query';
import { supabase } from '@/integrations/supabase/client';

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

const ACCOUNT_NOTIONAL = 100_000;
const TRADING_DAYS_PER_YEAR = 252;

export function useAbComparison() {
    return useQuery<AbComparisonResponse>({
        queryKey: ['ab-comparison'],
        queryFn: async () => {
            // ab_session_comparison + closed-trade count run in parallel.
            // Both tables are in Supabase — no Railway round-trip.
            const [rowsResult, tradesResult] = await Promise.all([
                supabase
                    .from('ab_session_comparison' as never)
                    .select(
                        'session_date, a_synthetic_pnl, b_session_pnl, ' +
                            'move_pct, a_no_trade, b_no_trade, a_regime',
                    )
                    .order('session_date', { ascending: true })
                    .limit(90),
                supabase
                    .from('trading_positions')
                    .select('id', { count: 'exact', head: true })
                    .eq('status', 'closed')
                    .eq('position_mode', 'virtual'),
            ]);

            const rows = (rowsResult.data ?? []) as AbDailyRow[];
            const closedCount = tradesResult.count ?? 0;

            // Days elapsed = today − first session_date in the table.
            // This mirrors shadow_engine.get_ab_gate_status() so the UI
            // shows the same number whether read from API or DB.
            const firstDate = rows[0]?.session_date;
            const daysElapsed = firstDate
                ? Math.floor(
                      (Date.now() - new Date(firstDate).getTime()) /
                          86_400_000,
                  )
                : 0;

            const tradingDays = rows.length;
            const aTotal = rows.reduce(
                (s, r) => s + (r.a_synthetic_pnl ?? 0),
                0,
            );
            const bTotal = rows.reduce(
                (s, r) => s + (r.b_session_pnl ?? 0),
                0,
            );
            const aAnn =
                tradingDays > 0
                    ? ((aTotal / ACCOUNT_NOTIONAL) / tradingDays) *
                      TRADING_DAYS_PER_YEAR *
                      100
                    : 0;
            const bAnn =
                tradingDays > 0
                    ? ((bTotal / ACCOUNT_NOTIONAL) / tradingDays) *
                      TRADING_DAYS_PER_YEAR *
                      100
                    : 0;
            const bLead = bAnn - aAnn;

            const gate: AbGateStatus = {
                // C-7: align with shadow_engine.get_ab_gate_status() —
                // "built" means at least one shadow row exists. The
                // Activation Dashboard reads this and previously
                // disagreed with the A/B page (which always claimed
                // built=true even before the first row landed).
                built: rows.length > 0,
                days_elapsed: daysElapsed,
                days_required: 90,
                trades_count: closedCount,
                trades_required: 100,
                a_total_pnl: Math.round(aTotal * 100) / 100,
                b_total_pnl: Math.round(bTotal * 100) / 100,
                a_annualized_pct: Math.round(aAnn * 100) / 100,
                b_annualized_pct: Math.round(bAnn * 100) / 100,
                portfolio_b_lead_pct:
                    tradingDays > 0 ? Math.round(bLead * 100) / 100 : null,
                gate_passed:
                    daysElapsed >= 90 && closedCount >= 100 && bLead >= 8,
            };

            // Last 30 rows newest-first for the table view.
            const daily = [...rows].slice(-30).reverse();

            return { gate, daily };
        },
        refetchInterval: 5 * 60_000,
        staleTime: 4 * 60_000,
        retry: 2,
    });
}
