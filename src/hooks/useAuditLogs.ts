import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';

export interface AuditLogEntry {
  id: string;
  actor_id: string | null;
  action: string;
  target_type: string | null;
  target_id: string | null;
  metadata: Record<string, unknown> | null;
  ip_address: string | null;
  user_agent: string | null;
  created_at: string;
}

interface AuditLogsParams {
  actor_id?: string;
  target_id?: string;
  target_type?: string;
  action?: string;
  date_from?: string;
  date_to?: string;
  limit?: number;
  before?: string;
}

interface AuditLogsResponse {
  data: AuditLogEntry[];
  pagination: {
    count: number;
    limit: number;
    next_cursor: string | null;
  };
}

export function useAuditLogs(params: AuditLogsParams = {}, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: ['admin', 'audit-logs', params],
    queryFn: () => apiClient.get<AuditLogsResponse>('query-audit-logs', params as Record<string, string | number | undefined>),
    staleTime: 2 * 60 * 1000,
    enabled: options?.enabled ?? true,
  });
}
