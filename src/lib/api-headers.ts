/**
 * Shared auth header helper for Edge Function calls.
 * Single source of truth — used by all admin hooks.
 */
import { supabase } from '@/integrations/supabase/client';

export async function getAuthHeaders(): Promise<Record<string, string>> {
  const session = (await supabase.auth.getSession()).data.session;
  if (!session) throw new Error('Not authenticated');
  return {
    'Authorization': `Bearer ${session.access_token}`,
    'apikey': import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY,
  };
}

export function getProjectUrl(): string {
  return import.meta.env.VITE_SUPABASE_URL;
}
