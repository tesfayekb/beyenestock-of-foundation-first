/**
 * list-invitations — List invitations with pagination and status filtering.
 *
 * Owner: user-onboarding module
 * Classification: api-standard
 * Lifecycle: active
 *
 * GET /list-invitations?status=pending&page=1&per_page=20
 *
 * Authorization: users.invite.manage
 * Virtual status: pending invitations past expires_at are returned as "expired"
 */
import { createHandler, apiSuccess } from '../_shared/handler.ts'
import { authenticateRequest } from '../_shared/authenticate-request.ts'
import { checkPermissionOrThrow } from '../_shared/authorization.ts'
import { supabaseAdmin } from '../_shared/supabase-admin.ts'

const VALID_STATUSES = ['all', 'pending', 'accepted', 'expired', 'revoked'] as const
const MAX_PER_PAGE = 100
const DEFAULT_PER_PAGE = 20

Deno.serve(createHandler(async (req: Request) => {
  if (req.method !== 'GET') {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(405, 'Method not allowed', { correlationId: crypto.randomUUID() })
  }

  const ctx = await authenticateRequest(req)
  await checkPermissionOrThrow(ctx.user.id, 'users.invite.manage')

  const url = new URL(req.url)
  const statusFilter = (url.searchParams.get('status') || 'all') as typeof VALID_STATUSES[number]
  const page = Math.max(1, parseInt(url.searchParams.get('page') || '1', 10))
  const perPage = Math.min(MAX_PER_PAGE, Math.max(1, parseInt(url.searchParams.get('per_page') || String(DEFAULT_PER_PAGE), 10)))

  if (!VALID_STATUSES.includes(statusFilter)) {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(400, `Invalid status filter. Must be one of: ${VALID_STATUSES.join(', ')}`, {
      correlationId: ctx.correlationId,
    })
  }

  const offset = (page - 1) * perPage

  // Build query
  let query = supabaseAdmin
    .from('invitations')
    .select('id, email, status, role_id, invited_by, expires_at, accepted_at, accepted_by, created_at', { count: 'exact' })

  // For "expired" filter, we need to get pending ones past TTL + actual expired
  if (statusFilter === 'expired') {
    // Get both DB-expired and virtually-expired (pending + past TTL)
    query = query.or(`status.eq.expired,and(status.eq.pending,expires_at.lt.${new Date().toISOString()})`)
  } else if (statusFilter !== 'all') {
    query = query.eq('status', statusFilter)
  }

  const { data, error, count } = await query
    .order('created_at', { ascending: false })
    .range(offset, offset + perPage - 1)

  if (error) {
    console.error('[LIST-INVITATIONS] Query failed:', error)
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(500, 'Failed to list invitations', { correlationId: ctx.correlationId })
  }

  // Compute virtual expired status for pending invitations past TTL
  const now = new Date()
  const invitations = (data ?? []).map(inv => ({
    ...inv,
    // Virtual status: if pending and past expires_at, show as "expired"
    status: inv.status === 'pending' && new Date(inv.expires_at) < now
      ? 'expired'
      : inv.status,
  }))

  // If filtering for "pending", exclude virtually expired ones
  const filtered = statusFilter === 'pending'
    ? invitations.filter(inv => inv.status === 'pending')
    : invitations

  return apiSuccess({
    invitations: filtered,
    pagination: {
      page,
      per_page: perPage,
      total: count ?? 0,
    },
    correlation_id: ctx.correlationId,
  })
}))
