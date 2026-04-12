/**
 * useActorSearch — Resolves a free-text actor filter (name/email) to a UUID.
 * If the input is already a valid UUID, it passes through directly.
 * Otherwise, it debounces and searches profiles by display_name or email ILIKE.
 */
import { useQuery } from '@tanstack/react-query';
import { supabase } from '@/integrations/supabase/client';
import { useDebounce } from '@/hooks/useDebounce';

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

interface ActorSearchResult {
  resolvedId: string | undefined;
  resolvedName: string | null;
  isSearching: boolean;
}

export function useActorSearch(input: string): ActorSearchResult {
  const trimmed = input.trim();
  const isUuid = UUID_PATTERN.test(trimmed);
  const debouncedInput = useDebounce(trimmed, 400);

  const shouldSearch = !isUuid && debouncedInput.length >= 2;

  const { data, isLoading } = useQuery({
    queryKey: ['actor-search', debouncedInput],
    queryFn: async () => {
      const pattern = `%${debouncedInput}%`;
      const { data: profiles } = await supabase
        .from('profiles')
        .select('id, display_name, email')
        .or(`display_name.ilike.${pattern},email.ilike.${pattern}`)
        .limit(1);

      if (profiles && profiles.length > 0) {
        const p = profiles[0];
        return { id: p.id, name: p.display_name || p.email || p.id };
      }
      return null;
    },
    enabled: shouldSearch,
    staleTime: 30_000,
  });

  if (isUuid) {
    return { resolvedId: trimmed, resolvedName: null, isSearching: false };
  }

  if (!shouldSearch) {
    return { resolvedId: undefined, resolvedName: null, isSearching: false };
  }

  return {
    resolvedId: data?.id ?? undefined,
    resolvedName: data?.name ?? null,
    isSearching: isLoading,
  };
}