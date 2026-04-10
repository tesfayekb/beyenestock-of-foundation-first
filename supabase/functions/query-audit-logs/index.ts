/**
 * query-audit-logs — Paginated audit log query endpoint.
 *
 * Permission: audit.view
 * Classification: privileged (read-only)
 * Audit: standard-risk (not audited — read-only)
 *
 * Allowed filters: action, actor_id, target_type, target_id, date_from, date_to
 * Sort: created_at DESC (fixed — no user-controlled sort)
 * Pagination: cursor-based via `before` (created_at of last item)
 * Max page size: 100
 */
import { createHandler, apiSuccess } from '../_shared/handler.ts'
import { authenticateRequest } from '../_shared/authenticate-request.ts'
import { checkPermissionOrThrow } from '../_shared/authorization.ts'
import { validateRequest } from '../_shared/validate-request.ts'
import { supabaseAdmin } from '../_shared/supabase-admin.ts'
import {
  AuditQueryParamsSchema,
  searchParamsToObject,
} from '../_shared/audit-query-schemas.ts'

const QUERY_PARAM_KEYS = ['limit', 'action', 'actor_id', 'target_type', 'target_id', 'date_from', 'date_to', 'before']

Deno.serve(createHandler(async (req: Request): Promise<Response> => {
  if (req.method !== 'GET') {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(405, 'Method not allowed')
  }

  const ctx = await authenticateRequest(req)
  await checkPermissionOrThrow(ctx.user.id, 'audit.view')

  // Schema-based validation via Stage 3A shared primitive
  const url = new URL(req.url)
  const rawParams = searchParamsToObject(url.searchParams, QUERY_PARAM_KEYS)
  const params = validateRequest(AuditQueryParamsSchema, rawParams)

  // Build query
  let query = supabaseAdmin
    .from('audit_logs')
    .select('id, actor_id, action, target_type, target_id, metadata, ip_address, user_agent, created_at')
    .order('created_at', { ascending: false })
    .limit(params.limit)

  if (params.action) query = query.eq('action', params.action)
  if (params.actor_id) query = query.eq('actor_id', params.actor_id)
  if (params.target_type) query = query.eq('target_type', params.target_type)
  if (params.target_id) query = query.eq('target_id', params.target_id)
  if (params.date_from) query = query.gte('created_at', params.date_from)
  if (params.date_to) query = query.lte('created_at', params.date_to)
  if (params.before) query = query.lt('created_at', params.before)

  const { data, error } = await query

  if (error) {
    console.error('[QUERY-AUDIT-LOGS] Query failed:', error.message, { correlationId: ctx.correlationId })
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(500, 'Failed to query audit logs', { correlationId: ctx.correlationId })
  }

  const rows = data ?? []
  const nextCursor = rows.length === params.limit ? rows[rows.length - 1].created_at : null

  return apiSuccess({
    data: rows,
    pagination: {
      count: rows.length,
      limit: params.limit,
      next_cursor: nextCursor,
    },
    correlation_id: ctx.correlationId,
  })
}))
