import { useQuery } from '@tanstack/react-query';
import { supabase } from '@/integrations/supabase/client';

export interface TradingPredictionRow {
  id: string;
  session_id: string;
  predicted_at: string;
  direction: string | null;
  confidence: number | null;
  p_bull: number | null;
  p_bear: number | null;
  p_neutral: number | null;
  expected_move_pts: number | null;
  expected_move_pct: number | null;
  regime: string | null;
  regime_hmm: string | null;
  regime_lgbm: string | null;
  regime_agreement: boolean | null;
  rcs: number | null;
  allocation_tier?: string | null;
  cv_stress_score: number | null;
  charm_velocity: number | null;
  vanna_velocity: number | null;
  gex_net: number | null;
  gex_nearest_wall: number | null;
  gex_flip_zone: number | null;
  gex_confidence: number | null;
  spx_price: number | null;
  vix: number | null;
  vvix: number | null;
  vvix_z_score: number | null;
  no_trade_signal: boolean | null;
  no_trade_reason: string | null;
  capital_preservation_mode: boolean | null;
  execution_degraded: boolean | null;
}

export function useTradingPrediction() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['trading', 'prediction', 'latest'],
    queryFn: async () => {
      const { data: rows, error: err } = await supabase
        .from('trading_prediction_outputs')
        .select('*')
        .order('predicted_at', { ascending: false })
        .limit(1);
      if (err) throw err;
      return (rows?.[0] as TradingPredictionRow | undefined) ?? null;
    },
    refetchInterval: 10_000,
    refetchIntervalInBackground: false,
  });

  return { data: data ?? null, isLoading, error };
}
