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
 * Key derivation: IP address (x-forwarded-for) or 'unknown'.
 * In-memory only — resets on cold start (acceptable for edge functions).
 */

import { apiError } from './api-error.ts'
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
 * Check rate limit for a request. Returns null if allowed,
 * or a 429 Response if rate limit exceeded.
 */
export function checkRateLimit(
  req: Request,
  rateLimitClass: RateLimitClass
): Response | null {
  const config = RATE_LIMITS[rateLimitClass]
  const ip = req.headers.get('x-forwarded-for')?.split(',')[0]?.trim() || 'unknown'
  const key = `${rateLimitClass}:${ip}`
  const now = Date.now()
  const windowStart = now - config.windowMs

  // Get or create window entries
  let timestamps = windows.get(key) ?? []

  // Prune expired entries
  timestamps = timestamps.filter(t => t > windowStart)

  if (timestamps.length >= config.maxRequests) {
    const retryAfter = Math.ceil((timestamps[0] + config.windowMs - now) / 1000)
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
