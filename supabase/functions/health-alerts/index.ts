/**
 * GET /health-alerts — Query alert history.
 *
 * Requires Bearer JWT + monitoring.view permission.
 * Returns triggered alerts, optionally filtered by severity and resolution status.
 *
 * Owner: health-monitoring module
 * Classification: privileged
 * Rate limit: standard
 */
import { createHandler, apiSuccess } from '../_shared/handler.ts'
import { authenticateRequest } from '../_shared/authenticate-request.ts'
import { checkPermissionOrThrow } from '../_shared/authorization.ts'
import { supabaseAdmin } from '../_shared/supabase-admin.ts'
import { z } from '../_shared/validate-request.ts'

const QuerySchema = z.object({
  severity: z.enum(['info', 'warning', 'critical']).optional(),
  resolved: z.enum(['true', 'false']).optional(),
  limit: z.coerce.number().int().min(1).max(500).default(50),
})

Deno.serve(createHandler(async (req: Request): Promise<Response> => {
  const ctx = await authenticateRequest(req)
  await checkPermissionOrThrow(ctx.user.id, 'monitoring.view')

  const url = new URL(req.url)
  const params = QuerySchema.parse({
    severity: url.searchParams.get('severity') ?? undefined,
    resolved: url.searchParams.get('resolved') ?? undefined,
    limit: url.searchParams.get('limit') ?? 50,
  })

  let query = supabaseAdmin
    .from('alert_history')
    .select('*, alert_configs(metric_key, comparison, enabled)')
    .order('created_at', { ascending: false })
    .limit(params.limit)

  if (params.severity) {
    query = query.eq('severity', params.severity)
  }
  if (params.resolved === 'true') {
    query = query.not('resolved_at', 'is', null)
  } else if (params.resolved === 'false') {
    query = query.is('resolved_at', null)
  }

  const { data, error } = await query

  if (error) {
    throw new Error(`Alerts query failed: ${error.message}`)
  }

  return apiSuccess({
    data: data ?? [],
    count: data?.length ?? 0,
  })
}))
