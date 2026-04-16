import { useQuery } from '@tanstack/react-query';
import { supabase } from '@/integrations/supabase/client';

export interface TradingPositionRow {
  id: string;
  session_id: string;
  position_mode: string;
  instrument: string | null;
  strategy_type: string | null;
  position_type: string | null;
  entry_at: string | null;
  entry_credit: number | null;
  entry_slippage: number | null;
  entry_spx_price: number | null;
  entry_regime: string | null;
  entry_rcs: number | null;
  entry_cv_stress: number | null;
  contracts: number | null;
  current_pnl: number | null;
  peak_pnl: number | null;
  net_pnl: number | null;
  status: string;
  exit_at: string | null;
  exit_reason: string | null;
}

export type PositionStatusFilter = 'open' | 'closed' | 'all';

interface UseTradingPositionsFilter {
  status?: PositionStatusFilter;
}

export function useTradingPositions(filter: UseTradingPositionsFilter = {}) {
  const statusFilter = filter.status ?? 'all';

  const { data, isLoading, error } = useQuery({
    queryKey: ['trading', 'positions', statusFilter],
    queryFn: async () => {
      let query = supabase
        .from('trading_positions')
        .select('*')
        .order('entry_at', { ascending: false })
        .limit(50);

      if (statusFilter !== 'all') {
        query = query.eq('status', statusFilter);
      }

      const { data: rows, error: err } = await query;
      if (err) throw err;
      return (rows as TradingPositionRow[]) ?? [];
    },
    refetchInterval: 15_000,
    refetchIntervalInBackground: false,
  });

  return { data: data ?? null, isLoading, error };
}
