/**
 * authenticateRequest — Server-side JWT validation and user context extraction.
 *
 * Owner: api module
 * Classification: security-critical
 * Fail behavior: fail-secure — throws 401
 * Lifecycle: active
 */
import { supabaseAdmin } from './supabase-admin.ts'
import { AuthError } from './errors.ts'

interface FactorLike {
  status?: string
  last_challenged_at?: string | null
}

function getMostRecentAuthTimestamp(user: {
  last_sign_in_at?: string | null
  factors?: unknown[]
}): string | undefined {
  const timestamps: number[] = []

  if (user.last_sign_in_at) {
    const signInAt = new Date(user.last_sign_in_at).getTime()
    if (Number.isFinite(signInAt)) timestamps.push(signInAt)
  }

  const factors = ((user.factors ?? []) as FactorLike[])
    .filter((factor) => factor.status === 'verified' && factor.last_challenged_at)

  for (const factor of factors) {
    const challengedAt = new Date(factor.last_challenged_at as string).getTime()
    if (Number.isFinite(challengedAt)) timestamps.push(challengedAt)
  }

  if (timestamps.length === 0) return undefined
  return new Date(Math.max(...timestamps)).toISOString()
}

export interface AuthenticatedUser {
  id: string
  email: string | undefined
  /** Most recent high-assurance auth timestamp: sign-in or verified MFA challenge. */
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
      lastSignInAt: getMostRecentAuthTimestamp(user),
    },
    token,
    ipAddress: req.headers.get('x-forwarded-for')?.split(',')[0]?.trim() || null,
    userAgent: req.headers.get('user-agent'),
    correlationId: crypto.randomUUID(),
  }
}

// Re-export for convenience
export { AuthError } from './errors.ts'
