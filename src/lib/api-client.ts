/**
 * Centralized API client for Edge Function calls.
 * Single source of truth for auth, error handling, and response normalization.
 */
import * as Sentry from '@sentry/react';
import { SUPABASE_PUBLISHABLE_KEY, SUPABASE_URL, supabase } from '@/integrations/supabase/client';

class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public code?: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

/**
 * Cached auth header to avoid redundant getSession() calls.
 * The Supabase SDK caches sessions in memory, but this avoids
 * even the synchronous localStorage read on rapid sequential calls.
 */
let _cachedToken: string | null = null;
let _tokenExpiry = 0;
let _unauthorizedRecoveryInProgress = false;

/** Force the next API call to fetch a fresh session token. */
export function invalidateTokenCache() {
  _cachedToken = null;
  _tokenExpiry = 0;
}

async function forceLocalLogout() {
  if (_unauthorizedRecoveryInProgress) return;
  _unauthorizedRecoveryInProgress = true;

  invalidateTokenCache();

  try {
    await supabase.auth.signOut({ scope: 'local' });
  } catch {
    // Best-effort local cleanup only — redirect still proceeds.
  }

  if (typeof window !== 'undefined' && window.location.pathname !== '/sign-in') {
    window.location.replace('/sign-in');
  }
}

// Clear cache on auth state change (sign-out, token refresh)
const { data: { subscription: _authSubscription } } = supabase.auth.onAuthStateChange((_event, session) => {
  if (session) {
    _cachedToken = session.access_token;
    _tokenExpiry = (session.expires_at ?? 0) * 1000 - 60_000; // 60s before expiry
  } else {
    _cachedToken = null;
    _tokenExpiry = 0;
    _unauthorizedRecoveryInProgress = false;
  }
});

// Cleanup on HMR to prevent memory leaks in development
if (import.meta.hot) {
  import.meta.hot.dispose(() => _authSubscription.unsubscribe());
}

async function getAuthHeaders(): Promise<Record<string, string>> {
  // Use cached token if still valid (60s buffer before JWT expiry)
  if (_cachedToken && Date.now() < _tokenExpiry) {
    return {
      'Authorization': `Bearer ${_cachedToken}`,
      'apikey': import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY,
    };
  }

  const session = (await supabase.auth.getSession()).data.session;
  if (!session) {
    await forceLocalLogout();
    throw new ApiError('Not authenticated', 401);
  }

  _cachedToken = session.access_token;
  _tokenExpiry = (session.expires_at ?? 0) * 1000 - 60_000;

  return {
    'Authorization': `Bearer ${session.access_token}`,
    'apikey': import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY,
  };
}

function getBaseUrl(): string {
  return `${import.meta.env.VITE_SUPABASE_URL}/functions/v1`;
}

function buildUrl(path: string, params?: Record<string, string | number | undefined | null>): string {
  const url = new URL(`${getBaseUrl()}/${path}`);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value != null && value !== '') {
        url.searchParams.set(key, String(value));
      }
    }
  }
  return url.toString();
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const error = new ApiError(
      body.error ?? `Request failed (${res.status})`,
      res.status,
      body.code,
    );

    if (res.status === 401) {
      await forceLocalLogout();
    }

    if (res.status >= 500) {
      Sentry.captureException(error, {
        contexts: {
          api: {
            status: res.status,
            code: body.code,
            correlation_id: body.correlation_id,
          },
        },
      });
    }

    throw error;
  }
  const json = await res.json();
  return json as T;
}

export const apiClient = {
  async get<T>(path: string, params?: Record<string, string | number | undefined | null>, signal?: AbortSignal): Promise<T> {
    const headers = await getAuthHeaders();
    const res = await fetch(buildUrl(path, params), { method: 'GET', headers, signal });
    return handleResponse<T>(res);
  },

  async post<T>(path: string, body?: object, signal?: AbortSignal): Promise<T> {
    const headers = await getAuthHeaders();
    const res = await fetch(buildUrl(path), {
      method: 'POST',
      headers: { ...headers, 'Content-Type': 'application/json' },
      body: body ? JSON.stringify(body) : undefined,
      signal,
    });
    return handleResponse<T>(res);
  },

  async patch<T>(path: string, body?: object, signal?: AbortSignal): Promise<T> {
    const headers = await getAuthHeaders();
    const res = await fetch(buildUrl(path), {
      method: 'PATCH',
      headers: { ...headers, 'Content-Type': 'application/json' },
      body: body ? JSON.stringify(body) : undefined,
      signal,
    });
    return handleResponse<T>(res);
  },
};

export { ApiError };
