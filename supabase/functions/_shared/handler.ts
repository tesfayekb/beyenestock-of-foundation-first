/**
 * Edge function request handler — unified pipeline wrapper.
 *
 * Provides: CORS preflight, rate limiting, error classification,
 * correlation ID propagation, and centralized denial audit logging.
 *
 * Enforcement rule: ALL denial audit logging occurs here.
 * No endpoint-level denial logging is permitted.
 */
import { corsHeaders } from './cors.ts'
import { apiError } from './api-error.ts'
import { AuthError, PermissionDeniedError, ValidationError } from './errors.ts'
import { checkRateLimit, type RateLimitClass } from './rate-limit.ts'
import { logAuditEvent } from './audit.ts'

type HandlerFn = (req: Request) => Promise<Response>

export interface HandlerOptions {
  /** Rate limit class for this endpoint. Default: 'standard' */
  rateLimit?: RateLimitClass
}

/**
 * Wraps an edge function handler with CORS + rate limiting + error classification.
 * Propagates correlation IDs into all error responses when available.
 * Centralized denial audit logging: intercepts PermissionDeniedError and
 * writes auth.permission_denied audit event (fire-and-forget).
 */
export function createHandler(
  handler: HandlerFn,
  options?: HandlerOptions
): (req: Request) => Promise<Response> {
  const rateLimitClass = options?.rateLimit ?? 'standard'

  return async (req: Request): Promise<Response> => {
    if (req.method === 'OPTIONS') {
      return new Response('ok', { headers: corsHeaders })
    }

    // Rate limit check (before any auth or processing)
    const rateLimitResponse = checkRateLimit(req, rateLimitClass)
    if (rateLimitResponse) {
      return rateLimitResponse
    }

    // Generate a correlation ID for the request lifecycle
    const correlationId = crypto.randomUUID()

    try {
      return await handler(req)
    } catch (err) {
      // Extract correlation ID from authenticated context if available
      const cid = (err as Record<string, unknown>)?.correlationId as string ?? correlationId

      if (err instanceof AuthError) {
        return apiError(401, err.message, { correlationId: cid })
      }
      if (err instanceof ValidationError) {
        return apiError(400, err.message, {
          code: 'VALIDATION_ERROR',
          field: Object.keys(err.fieldErrors)[0],
          correlationId: cid,
        })
      }
      if (err instanceof PermissionDeniedError) {
        // ── Centralized denial audit logging (fire-and-forget) ──
        // Actor extraction: err.userId is authoritative.
        // JWT fallback is best-effort enrichment only — never affects
        // authorization logic, only audit metadata.
        let actorId = err.userId
        if (!actorId) {
          actorId = extractActorFromRequest(req)
        }

        const endpoint = new URL(req.url).pathname

        // Fire-and-forget: audit failure must NOT block the 403 response
        logDenialAudit(actorId, err.permissionKey, err.reason, endpoint, cid)

        // Distinguish re-auth requirement from permission denial
        if (err.reason === 'recent_auth_required') {
          return apiError(403, 'Session too old for this action — please re-authenticate', {
            code: 'RECENT_AUTH_REQUIRED',
            correlationId: cid,
          })
        }

        return apiError(403, 'Permission denied', { correlationId: cid })
      }

      console.error('[HANDLER] Unhandled error:', err, { correlationId: cid })
      return apiError(500, 'Internal server error', { correlationId: cid })
    }
  }
}

/**
 * Best-effort actor extraction from request JWT.
 * This is enrichment only — not trusted identity derivation.
 * If decode fails, returns null (event still recorded with null actor).
 */
function extractActorFromRequest(req: Request): string | null {
  try {
    const authHeader = req.headers.get('Authorization')
    if (!authHeader?.startsWith('Bearer ')) return null
    const token = authHeader.replace('Bearer ', '')
    const payloadB64 = token.split('.')[1]
    if (!payloadB64) return null
    const payload = JSON.parse(atob(payloadB64))
    return typeof payload.sub === 'string' ? payload.sub : null
  } catch {
    return null
  }
}

/**
 * Fire-and-forget denial audit write.
 * Failure is logged to console.error only — never blocks the 403 response.
 */
function logDenialAudit(
  actorId: string | null,
  permissionKey: string,
  reason: string,
  endpoint: string,
  correlationId: string
): void {
  // actorId can be null — preserves audit truth (unknown ≠ fake)
  logAuditEvent({
    actorId,
    action: 'auth.permission_denied',
    targetType: 'permission',
    metadata: {
      permission_key: permissionKey,
      reason,
      endpoint,
      actor_known: actorId !== null,
      correlation_id: correlationId,
    },
    correlationId,
  }).catch((e) => {
    console.error('[HANDLER] Denial audit write failed (non-blocking):', e)
  })
}

/** Build a success JSON response with CORS headers */
export function apiSuccess(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { ...corsHeaders, 'Content-Type': 'application/json' },
  })
}
