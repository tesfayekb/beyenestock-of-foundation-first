/**
 * In-memory sliding-window rate limiter for edge functions.
 *
 * Owner: api module
 * Classification: security-infrastructure
 * Lifecycle: active
 *
 * Rate limit classes:
 *   relaxed  — 120 req/min (health checks, public reads)
 *   standard — 60 req/min  (authenticated reads/writes)
 *   strict   — 10 req/min  (destructive/privileged actions)
 *
 * Key derivation: Composite of rate-limit class + IP + authenticated user ID.
 *   - Unauthenticated: keyed by IP only (x-forwarded-for)
 *   - Authenticated: keyed by IP + user sub (from JWT)
 *   This prevents a single user from consuming the entire IP quota in shared-IP
 *   environments (NAT, VPN, corporate proxy).
 *
 * Limitations (documented):
 *   - In-memory only — resets on cold start (acceptable for edge functions)
 *   - Not shared across isolates — each instance maintains its own window
 *   - For distributed rate limiting, upgrade to Redis/Upstash backend
 *
 * Telemetry:
 *   - Rate limit hits are logged to console with structured metadata
 *   - Log format is compatible with Supabase analytics queries
 */

import { corsHeaders } from './cors.ts'

export type RateLimitClass = 'relaxed' | 'standard' | 'strict'

const RATE_LIMITS: Record<RateLimitClass, { maxRequests: number; windowMs: number }> = {
  relaxed:  { maxRequests: 120, windowMs: 60_000 },
  standard: { maxRequests: 60,  windowMs: 60_000 },
  strict:   { maxRequests: 10,  windowMs: 60_000 },
}

/** Sliding window entries: key → timestamps[] */
const windows = new Map<string, number[]>()

/**
 * Derive the rate-limit key from request context.
 * Uses IP + optional authenticated user sub for user-aware limiting.
 */
function deriveKey(req: Request, rateLimitClass: RateLimitClass): string {
  const ip = req.headers.get('x-forwarded-for')?.split(',')[0]?.trim() || 'unknown'

  // Extract user sub from Authorization header if present (lightweight — no full JWT validation)
  let userSub: string | null = null
  const authHeader = req.headers.get('authorization')
  if (authHeader?.startsWith('Bearer ')) {
    try {
      const payload = authHeader.split('.')[1]
      if (payload) {
        const decoded = JSON.parse(atob(payload))
        userSub = decoded.sub ?? null
      }
    } catch {
      // JWT decode failed — fall back to IP-only key
    }
  }

  return userSub
    ? `${rateLimitClass}:${ip}:${userSub}`
    : `${rateLimitClass}:${ip}`
}

/**
 * Check rate limit for a request. Returns null if allowed,
 * or a 429 Response if rate limit exceeded.
 */
export function checkRateLimit(
  req: Request,
  rateLimitClass: RateLimitClass
): Response | null {
  const config = RATE_LIMITS[rateLimitClass]
  const key = deriveKey(req, rateLimitClass)
  const now = Date.now()
  const windowStart = now - config.windowMs

  // Get or create window entries
  let timestamps = windows.get(key) ?? []

  // Prune expired entries
  timestamps = timestamps.filter(t => t > windowStart)

  if (timestamps.length >= config.maxRequests) {
    const retryAfter = Math.ceil((timestamps[0] + config.windowMs - now) / 1000)

    // Telemetry: structured log for rate limit hit
    const ip = req.headers.get('x-forwarded-for')?.split(',')[0]?.trim() || 'unknown'
    console.warn('[RATE_LIMIT] Rate limit exceeded', {
      class: rateLimitClass,
      key,
      ip,
      requests_in_window: timestamps.length,
      max_requests: config.maxRequests,
      retry_after_seconds: retryAfter,
      timestamp: new Date(now).toISOString(),
    })

    return new Response(
      JSON.stringify({
        error: 'Too many requests',
        retry_after_seconds: retryAfter,
      }),
      {
        status: 429,
        headers: {
          ...corsHeaders,
          'Content-Type': 'application/json',
          'Retry-After': String(retryAfter),
        },
      }
    )
  }

  // Record this request
  timestamps.push(now)
  windows.set(key, timestamps)

  // Periodic cleanup: remove stale keys (every ~100 requests)
  if (Math.random() < 0.01) {
    for (const [k, v] of windows.entries()) {
      const filtered = v.filter(t => t > now - 120_000)
      if (filtered.length === 0) {
        windows.delete(k)
      } else {
        windows.set(k, filtered)
      }
    }
  }

  return null
}
