import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { supabase } from '@/integrations/supabase/client';

export interface TradingHealthRow {
  service_name: string;
  status: string;
  last_heartbeat_at: string;
  latency_ms: number | null;
  error_count_1h: number | null;
  last_error_message: string | null;
}

export function useTradingSystemHealth() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['trading', 'system-health'],
    queryFn: async () => {
      const { data: rows, error: err } = await supabase
        .from('trading_system_health')
        .select(
          'service_name, status, last_heartbeat_at, latency_ms, error_count_1h, last_error_message'
        )
        .order('last_heartbeat_at', { ascending: false });
      if (err) throw err;
      return (rows as TradingHealthRow[]) ?? [];
    },
    refetchInterval: 10_000,
    refetchIntervalInBackground: false,
  });

  const serviceMap = useMemo(() => {
    const map = new Map<string, TradingHealthRow>();
    for (const row of data ?? []) {
      if (!map.has(row.service_name)) map.set(row.service_name, row);
    }
    return map;
  }, [data]);

  return { serviceMap, isLoading, error };
}
