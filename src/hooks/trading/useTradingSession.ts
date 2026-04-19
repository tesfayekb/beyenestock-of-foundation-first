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
  // P1-14: session_date is the ET trading date, not UTC.
  // Around UTC midnight (which is ~8 PM ET) the UTC date rolls over
  // before the ET trading day ends — using toISOString here loaded
  // tomorrow's (non-existent) session row from 8 PM ET onward, hiding
  // the actual session for the rest of the evening. en-CA locale
  // produces YYYY-MM-DD, matching the session_date column format.
  const today = new Date().toLocaleDateString('en-CA', {
    timeZone: 'America/New_York',
  });

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
