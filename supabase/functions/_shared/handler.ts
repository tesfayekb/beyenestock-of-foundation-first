/**
 * Edge function request handler — unified pipeline wrapper.
 *
 * Wraps the canonical request pipeline:
 *   CORS → authenticate → execute → structured response
 *
 * Handles error classification and returns appropriate responses
 * for AuthError (401), ValidationError (400), PermissionDeniedError (403),
 * and unknown errors (500).
 */
import { corsHeaders } from './cors.ts'
import { apiError } from './api-error.ts'
import { AuthError } from './authenticate-request.ts'
import { ValidationError } from './validate-request.ts'
import { PermissionDeniedError } from './authorization.ts'

type HandlerFn = (req: Request) => Promise<Response>

/**
 * Wraps an edge function handler with:
 * - CORS preflight handling
 * - Error classification (401/400/403/500)
 * - Never exposes internal error details
 */
export function createHandler(handler: HandlerFn): (req: Request) => Promise<Response> {
  return async (req: Request): Promise<Response> => {
    // CORS preflight
    if (req.method === 'OPTIONS') {
      return new Response('ok', { headers: corsHeaders })
    }

    try {
      return await handler(req)
    } catch (err) {
      if (err instanceof AuthError) {
        return apiError(401, err.message)
      }
      if (err instanceof ValidationError) {
        return apiError(400, err.message, {
          code: 'VALIDATION_ERROR',
          field: Object.keys(err.fieldErrors)[0],
        })
      }
      if (err instanceof PermissionDeniedError) {
        return apiError(403, 'Permission denied')
      }

      // Unknown error — never expose details
      console.error('[HANDLER] Unhandled error:', err)
      return apiError(500, 'Internal server error')
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
