import { useQuery } from '@tanstack/react-query';
import { supabase } from '@/integrations/supabase/client';

export interface TradingSessionRow {
  id: string;
  session_date: string;
  session_status: string;
  regime: string | null;
  day_type: string | null;
  capital_preservation_active: boolean | null;
  consecutive_losses_today: number | null;
  consecutive_loss_sessions: number | null;
  virtual_pnl: number | null;
  virtual_trades_count: number | null;
  virtual_wins: number | null;
  virtual_losses: number | null;
  halt_reason: string | null;
  updated_at: string | null;
}

export function useTradingSession() {
  const today = new Date().toISOString().slice(0, 10);

  const { data, isLoading, error } = useQuery({
    queryKey: ['trading', 'session', today],
    queryFn: async () => {
      const { data: row, error: err } = await supabase
        .from('trading_sessions')
        .select('*')
        .eq('session_date', today)
        .maybeSingle();
      if (err) throw err;
      return (row as TradingSessionRow | null) ?? null;
    },
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });

  return { data: data ?? null, isLoading, error };
}
