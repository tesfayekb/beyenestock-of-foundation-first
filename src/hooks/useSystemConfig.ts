/**
 * useSystemConfig — Fetch and mutate onboarding mode via get/update-system-config.
 *
 * Owner: user-onboarding module
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { useToast } from '@/hooks/use-toast';

export interface OnboardingConfig {
  signup_enabled: boolean;
  invite_enabled: boolean;
}

interface SystemConfigResponse {
  data: OnboardingConfig;
}

interface UpdateConfigResponse {
  data: { updated: boolean };
}

const SYSTEM_CONFIG_KEY = ['system-config', 'onboarding'] as const;

export function useSystemConfig() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const query = useQuery({
    queryKey: [...SYSTEM_CONFIG_KEY],
    queryFn: async (): Promise<OnboardingConfig> => {
      const res = await apiClient.get<SystemConfigResponse>('get-system-config');
      return res.data;
    },
    staleTime: 60_000,
  });

  const mutation = useMutation({
    mutationFn: async (config: OnboardingConfig) => {
      return apiClient.patch<UpdateConfigResponse>('update-system-config', config);
    },
    onSuccess: (_data, variables) => {
      queryClient.setQueryData([...SYSTEM_CONFIG_KEY], variables);
      toast({ title: 'Onboarding mode updated', description: 'Settings saved successfully.' });
    },
    onError: (error: Error) => {
      toast({ variant: 'destructive', title: 'Update failed', description: error.message });
    },
  });

  return {
    config: query.data,
    isLoading: query.isLoading,
    error: query.error,
    updateConfig: mutation.mutateAsync,
    isUpdating: mutation.isPending,
  };
}
