/**
 * CORS headers — dynamic origin validation using ALLOWED_ORIGINS env var.
 *
 * Restricts Access-Control-Allow-Origin to known app domains.
 * Automatically accepts Lovable preview origins (*.lovableproject.com, *.lovable.app).
 * Falls back to first allowed origin if request origin doesn't match.
 * If ALLOWED_ORIGINS is not set, falls back to wildcard (development only).
 */

const ALLOWED_ORIGINS = (Deno.env.get('ALLOWED_ORIGINS') ?? '')
  .split(',')
  .map(o => o.trim())
  .filter(Boolean);

/** Check if origin is a Lovable preview/published domain */
function isLovableOrigin(origin: string): boolean {
  try {
    const url = new URL(origin);
    return url.hostname.endsWith('.lovableproject.com')
      || url.hostname.endsWith('.lovable.app');
  } catch {
    return false;
  }
}

/**
 * Returns CORS headers with validated origin.
 * If the request origin is in the allow-list or is a Lovable preview origin, it is echoed back.
 * Otherwise, the first allowed origin is returned (browsers will block).
 */
export function getCorsHeaders(requestOrigin: string | null): Record<string, string> {
  let origin: string;

  if (ALLOWED_ORIGINS.length === 0) {
    // No allow-list configured — development fallback
    origin = '*';
  } else {
    const reqOrigin = requestOrigin ?? '';
    origin = (ALLOWED_ORIGINS.includes(reqOrigin) || isLovableOrigin(reqOrigin))
      ? reqOrigin
      : ALLOWED_ORIGINS[0];
  }

  return {
    'Access-Control-Allow-Origin': origin,
    'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type, x-cron-secret, x-supabase-client-platform, x-supabase-client-platform-version, x-supabase-client-runtime, x-supabase-client-runtime-version',
    'Access-Control-Allow-Methods': 'GET, POST, PATCH, OPTIONS',
    'Vary': 'Origin',
  };
}

/** Backward-compatible static export for imports that don't have request context */
export const corsHeaders = getCorsHeaders(null);
