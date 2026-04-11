/**
 * useProfile — fetch and mutate the authenticated user's own profile.
 * Uses get-profile (GET) and update-profile (PATCH) edge functions.
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { useAuth } from '@/contexts/AuthContext';
import { toast } from 'sonner';

export interface UserProfile {
  id: string;
  display_name: string | null;
  avatar_url: string | null;
  email: string | null;
  email_verified: boolean | null;
  status: string;
  created_at: string;
  updated_at: string;
}

interface ProfileResponse {
  profile: UserProfile;
}

interface UpdateProfilePayload {
  display_name?: string | null;
  avatar_url?: string | null;
}

const PROFILE_KEY = ['profile', 'self'] as const;

export function useProfile() {
  const queryClient = useQueryClient();
  const { user } = useAuth();

  // SCENARIO-5: Only fetch when authenticated
  const query = useQuery({
    queryKey: PROFILE_KEY,
    queryFn: () => apiClient.get<ProfileResponse>('get-profile').then((r) => r.profile),
    staleTime: 30_000,
    enabled: !!user,
  });

  const mutation = useMutation({
    mutationFn: (payload: UpdateProfilePayload) =>
      apiClient.patch<ProfileResponse>('update-profile', payload).then((r) => r.profile),
    onSuccess: (updated) => {
      queryClient.setQueryData(PROFILE_KEY, updated);
      toast.success('Profile updated');
    },
    onError: (err: Error) => {
      toast.error(err.message || 'Failed to update profile');
    },
  });

  return {
    profile: query.data ?? null,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch,
    updateProfile: mutation.mutate,
    isUpdating: mutation.isPending,
  };
}
