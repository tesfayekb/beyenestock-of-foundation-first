import { useQuery } from '@tanstack/react-query';
import { supabase } from '@/integrations/supabase/client';

export interface UserListItem {
  id: string;
  display_name: string | null;
  avatar_url: string | null;
  email: string | null;
  email_verified: boolean | null;
  status: string;
  created_at: string;
  updated_at: string;
}

interface ListUsersParams {
  limit?: number;
  offset?: number;
  status?: 'active' | 'deactivated';
  search?: string;
}

interface ListUsersResponse {
  users: UserListItem[];
  total: number;
  limit: number;
  offset: number;
}

async function fetchUsers(params: ListUsersParams): Promise<ListUsersResponse> {
  const searchParams = new URLSearchParams();
  if (params.limit) searchParams.set('limit', String(params.limit));
  if (params.offset != null) searchParams.set('offset', String(params.offset));
  if (params.status) searchParams.set('status', params.status);
  if (params.search) searchParams.set('search', params.search);

  const { data, error } = await supabase.functions.invoke('list-users', {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
    body: undefined,
  });

  // list-users is GET, but supabase.functions.invoke doesn't support query params natively
  // We need to use the full URL approach instead
  const session = (await supabase.auth.getSession()).data.session;
  if (!session) throw new Error('Not authenticated');

  const projectUrl = import.meta.env.VITE_SUPABASE_URL;
  const url = `${projectUrl}/functions/v1/list-users?${searchParams.toString()}`;

  const res = await fetch(url, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${session.access_token}`,
      'apikey': import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY,
    },
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error ?? `Failed to list users (${res.status})`);
  }

  const json = await res.json();
  return json.data as ListUsersResponse;
}

export function useUsers(params: ListUsersParams = {}) {
  return useQuery({
    queryKey: ['admin', 'users', params],
    queryFn: () => fetchUsers(params),
    staleTime: 30_000,
  });
}

/** Fetch a single user profile for admin detail view */
async function fetchUserDetail(userId: string): Promise<UserListItem> {
  const session = (await supabase.auth.getSession()).data.session;
  if (!session) throw new Error('Not authenticated');

  const projectUrl = import.meta.env.VITE_SUPABASE_URL;
  const url = `${projectUrl}/functions/v1/get-profile?user_id=${userId}`;

  const res = await fetch(url, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${session.access_token}`,
      'apikey': import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY,
    },
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error ?? `Failed to fetch user (${res.status})`);
  }

  const json = await res.json();
  const profile = json.data.profile;

  // Enrich with email from auth (admin has list-users which does this, but get-profile doesn't)
  // We'll fetch email separately if needed from list-users cache or accept null
  return profile as UserListItem;
}

export function useUserDetail(userId: string | undefined) {
  return useQuery({
    queryKey: ['admin', 'user', userId],
    queryFn: () => fetchUserDetail(userId!),
    enabled: !!userId,
    staleTime: 30_000,
  });
}
