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
 * Enrichment: resolves invited_by → display_name, role_id → role name
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

  const rows = data ?? []

  // Collect unique invited_by UUIDs and role_ids for batch lookup
  const inviterIds = [...new Set(rows.map(r => r.invited_by).filter(Boolean))]
  const roleIds = [...new Set(rows.map(r => r.role_id).filter(Boolean))]

  // Batch resolve inviter names
  const inviterMap = new Map<string, string>()
  if (inviterIds.length > 0) {
    const { data: profiles } = await supabaseAdmin
      .from('profiles')
      .select('id, display_name, last_name, email')
      .in('id', inviterIds)
    for (const p of profiles ?? []) {
      const name = [p.display_name, p.last_name].filter(Boolean).join(' ') || p.email || 'Unknown'
      inviterMap.set(p.id, name)
    }
  }

  // Batch resolve role names
  const roleMap = new Map<string, string>()
  if (roleIds.length > 0) {
    const { data: roles } = await supabaseAdmin
      .from('roles')
      .select('id, name')
      .in('id', roleIds as string[])
    for (const r of roles ?? []) {
      roleMap.set(r.id, r.name)
    }
  }

  // Compute virtual expired status and enrich
  const now = new Date()
  const invitations = rows.map(inv => ({
    ...inv,
    status: inv.status === 'pending' && new Date(inv.expires_at) < now
      ? 'expired'
      : inv.status,
    invited_by_name: inviterMap.get(inv.invited_by) ?? 'Unknown',
    role_name: inv.role_id ? (roleMap.get(inv.role_id) ?? null) : null,
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