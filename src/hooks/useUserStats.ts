import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';

interface UserStats {
  total: number;
  active: number;
  deactivated: number;
}

export const USER_STATS_QUERY_KEY = ['admin', 'user-stats'] as const;

export const userStatsQueryFn = () => apiClient.get<UserStats>('get-user-stats');

export function useUserStats() {
  return useQuery({
    queryKey: [...USER_STATS_QUERY_KEY],
    queryFn: userStatsQueryFn,
    staleTime: 60_000, // 1 minute — counts change infrequently
  });
}
