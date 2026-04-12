/**
 * get-user-stats — Lightweight user count endpoint (admin).
 *
 * Requires: users.view_all permission.
 *
 * GET /get-user-stats
 *
 * Returns { total, active, deactivated } using COUNT(*) queries only.
 * No auth user enrichment, no email lookup — pure profile counts.
 */
import { createHandler, apiSuccess } from '../_shared/handler.ts'
import { authenticateRequest } from '../_shared/authenticate-request.ts'
import { checkPermissionOrThrow } from '../_shared/authorization.ts'
import { supabaseAdmin } from '../_shared/supabase-admin.ts'

Deno.serve(createHandler(async (req: Request) => {
  if (req.method !== 'GET') {
    const { apiError } = await import('../_shared/api-error.ts')
    return apiError(405, 'Method not allowed', { correlationId: crypto.randomUUID() })
  }

  const ctx = await authenticateRequest(req)
  await checkPermissionOrThrow(ctx.user.id, 'users.view_all')

  // Three lightweight COUNT queries — no joins, no auth enrichment
  const [totalRes, activeRes, deactivatedRes] = await Promise.all([
    supabaseAdmin.from('profiles').select('id', { count: 'exact', head: true }),
    supabaseAdmin.from('profiles').select('id', { count: 'exact', head: true }).eq('status', 'active'),
    supabaseAdmin.from('profiles').select('id', { count: 'exact', head: true }).eq('status', 'deactivated'),
  ])

  return apiSuccess({
    total: totalRes.count ?? 0,
    active: activeRes.count ?? 0,
    deactivated: deactivatedRes.count ?? 0,
  })
}))
