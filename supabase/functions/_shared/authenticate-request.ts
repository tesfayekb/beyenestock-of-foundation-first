/**
 * authenticateRequest — Server-side JWT validation and user context extraction.
 *
 * Owner: api module
 * Classification: security-critical
 * Fail behavior: fail-secure — throws 401
 * Lifecycle: active
 *
 * Validates the Authorization header, verifies the JWT via Supabase,
 * and returns the authenticated user context.
 */
import { supabaseAdmin } from './supabase-admin.ts'

export interface AuthenticatedUser {
  id: string
  email: string | undefined
  lastSignInAt: string | undefined
}

export interface AuthenticatedContext {
  user: AuthenticatedUser
  token: string
  ipAddress: string | null
  userAgent: string | null
  correlationId: string
}

/**
 * Authenticate an incoming request.
 * Extracts and validates Bearer token, returns authenticated context.
 * Throws structured error data on failure — callers use apiError() to respond.
 */
export async function authenticateRequest(req: Request): Promise<AuthenticatedContext> {
  const authHeader = req.headers.get('Authorization')
  if (!authHeader?.startsWith('Bearer ')) {
    throw new AuthError('Missing or malformed authorization header')
  }

  const token = authHeader.replace('Bearer ', '')

  const { data: { user }, error } = await supabaseAdmin.auth.getUser(token)
  if (error || !user) {
    throw new AuthError('Invalid or expired token')
  }

  return {
    user: {
      id: user.id,
      email: user.email,
      lastSignInAt: user.last_sign_in_at ?? undefined,
    },
    token,
    ipAddress: req.headers.get('x-forwarded-for')?.split(',')[0]?.trim() || null,
    userAgent: req.headers.get('user-agent'),
    correlationId: crypto.randomUUID(),
  }
}

/** Sentinel error class for auth failures — always results in 401 */
export class AuthError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'AuthError'
  }
}
