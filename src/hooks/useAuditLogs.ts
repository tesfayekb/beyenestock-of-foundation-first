import { useQuery } from '@tanstack/react-query';
import { getAuthHeaders, getProjectUrl } from '@/lib/api-headers';

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

async function fetchAuditLogs(params: AuditLogsParams): Promise<AuditLogsResponse> {
  const searchParams = new URLSearchParams();
  if (params.limit) searchParams.set('limit', String(params.limit));
  if (params.actor_id) searchParams.set('actor_id', params.actor_id);
  if (params.target_id) searchParams.set('target_id', params.target_id);
  if (params.target_type) searchParams.set('target_type', params.target_type);
  if (params.action) searchParams.set('action', params.action);
  if (params.before) searchParams.set('before', params.before);

  const headers = await getAuthHeaders();
  const url = `${getProjectUrl()}/functions/v1/query-audit-logs?${searchParams.toString()}`;

  const res = await fetch(url, { method: 'GET', headers });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error ?? `Failed to fetch audit logs (${res.status})`);
  }

  const json = await res.json();
  return json.data as AuditLogsResponse;
}

export function useAuditLogs(params: AuditLogsParams = {}) {
  return useQuery({
    queryKey: ['admin', 'audit-logs', params],
    queryFn: () => fetchAuditLogs(params),
    staleTime: 30_000,
  });
}
