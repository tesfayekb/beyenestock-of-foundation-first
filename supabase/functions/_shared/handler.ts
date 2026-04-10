/**
 * Edge function request handler — unified pipeline wrapper.
 */
import { corsHeaders } from './cors.ts'
import { apiError } from './api-error.ts'
import { AuthError, PermissionDeniedError, ValidationError } from './errors.ts'

type HandlerFn = (req: Request) => Promise<Response>

/**
 * Wraps an edge function handler with CORS + error classification.
 * Propagates correlation IDs into all error responses when available.
 */
export function createHandler(handler: HandlerFn): (req: Request) => Promise<Response> {
  return async (req: Request): Promise<Response> => {
    if (req.method === 'OPTIONS') {
      return new Response('ok', { headers: corsHeaders })
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
        return apiError(403, 'Permission denied', { correlationId: cid })
      }

      console.error('[HANDLER] Unhandled error:', err, { correlationId: cid })
      return apiError(500, 'Internal server error', { correlationId: cid })
    }
  }
}

/** Build a success JSON response with CORS headers */
export function apiSuccess(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { ...corsHeaders, 'Content-Type': 'application/json' },
  })
}
