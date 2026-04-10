/**
 * Shared Supabase admin client (service-role).
 * Used by all edge functions for privileged operations.
 *
 * SECURITY: This client bypasses RLS. Use only in edge functions,
 * never expose the service role key to clients.
 */
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

export const supabaseAdmin = createClient(
  Deno.env.get('SUPABASE_URL')!,
  Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
)
