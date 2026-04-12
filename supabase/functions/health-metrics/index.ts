/**
 * GET /health-metrics — Query system metrics time-series.
 *
 * Requires Bearer JWT + monitoring.view permission.
 * Returns paginated metrics, optionally filtered by metric_key and time range.
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
  metric_key: z.string().optional(),
  from: z.string().datetime().optional(),
  to: z.string().datetime().optional(),
  limit: z.coerce.number().int().min(1).max(500).default(100),
})

Deno.serve(createHandler(async (req: Request): Promise<Response> => {
  const ctx = await authenticateRequest(req)
  await checkPermissionOrThrow(ctx.user.id, 'monitoring.view')

  const url = new URL(req.url)
  const params = QuerySchema.parse({
    metric_key: url.searchParams.get('metric_key') ?? undefined,
    from: url.searchParams.get('from') ?? undefined,
    to: url.searchParams.get('to') ?? undefined,
    limit: url.searchParams.get('limit') ?? 100,
  })

  let query = supabaseAdmin
    .from('system_metrics')
    .select('*')
    .order('recorded_at', { ascending: false })
    .limit(params.limit)

  if (params.metric_key) {
    query = query.eq('metric_key', params.metric_key)
  }
  if (params.from) {
    query = query.gte('recorded_at', params.from)
  }
  if (params.to) {
    query = query.lte('recorded_at', params.to)
  }

  const { data, error } = await query

  if (error) {
    throw new Error(`Metrics query failed: ${error.message}`)
  }

  return apiSuccess({
    data: data ?? [],
    count: data?.length ?? 0,
  })
}))
