/**
 * Centralized API client for Edge Function calls.
 * Single source of truth for auth, error handling, and response normalization.
 */
import { supabase } from '@/integrations/supabase/client';

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

async function getAuthHeaders(): Promise<Record<string, string>> {
  const session = (await supabase.auth.getSession()).data.session;
  if (!session) throw new ApiError('Not authenticated', 401);
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
    throw new ApiError(
      body.error ?? `Request failed (${res.status})`,
      res.status,
      body.code,
    );
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
