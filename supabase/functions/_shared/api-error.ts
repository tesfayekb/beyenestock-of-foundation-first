/**
 * apiError — Structured error response builder.
 *
 * Owner: api module
 * Classification: api-critical
 * Lifecycle: active
 *
 * Returns a Response with structured JSON error body:
 *   { error: string, code: string, field?: string }
 *
 * Never exposes internal details. All edge functions use this
 * for consistent error responses.
 */
import { corsHeaders } from './cors.ts'

export function apiError(
  status: number,
  message: string,
  opts?: { code?: string; field?: string; correlationId?: string }
): Response {
  const body: Record<string, string> = {
    error: message,
    code: opts?.code ?? httpStatusToCode(status),
  }
  if (opts?.field) body.field = opts.field
  if (opts?.correlationId) body.correlation_id = opts.correlationId

  return new Response(JSON.stringify(body), {
    status,
    headers: { ...corsHeaders, 'Content-Type': 'application/json' },
  })
}

function httpStatusToCode(status: number): string {
  switch (status) {
    case 400: return 'BAD_REQUEST'
    case 401: return 'UNAUTHORIZED'
    case 403: return 'FORBIDDEN'
    case 404: return 'NOT_FOUND'
    case 409: return 'CONFLICT'
    case 429: return 'RATE_LIMITED'
    default:  return 'INTERNAL_ERROR'
  }
}
