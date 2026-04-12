import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';

export interface UserRoleSummary {
  role_key: string;
  role_name: string;
}

export interface UserListItem {
  id: string;
  display_name: string | null;
  avatar_url: string | null;
  email: string | null;
  email_verified: boolean | null;
  status: string;
  created_at: string;
  updated_at: string;
  roles?: UserRoleSummary[];
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

export function useUsers(params: ListUsersParams = {}) {
  return useQuery({
    queryKey: ['admin', 'users', params],
    queryFn: ({ signal }) =>
      apiClient.get<ListUsersResponse>('list-users', {
        limit: params.limit,
        offset: params.offset,
        status: params.status,
        search: params.search,
      }, signal),
    staleTime: 2 * 60 * 1000,
  });
}

export function useUserDetail(userId: string | undefined) {
  return useQuery({
    queryKey: ['admin', 'user', userId],
    queryFn: ({ signal }) =>
      apiClient.get<{ profile: UserListItem }>('get-profile', { user_id: userId }, signal).then((d) => d.profile),
    enabled: !!userId,
    staleTime: 2 * 60 * 1000,
  });
}
