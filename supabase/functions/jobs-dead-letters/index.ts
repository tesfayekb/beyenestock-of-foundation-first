/**
 * jobs-dead-letters — List dead-lettered job executions.
 *
 * GET /jobs-dead-letters?page=1&page_size=20&job_id=optional
 *
 * Requires: jobs.deadletter.manage permission
 * Returns paginated dead_lettered executions from job_executions.
 *
 * Owner: jobs-and-scheduler module
 */
import { createHandler, apiSuccess } from '../_shared/handler.ts'
import { authenticateRequest } from '../_shared/authenticate-request.ts'
import { checkPermissionOrThrow } from '../_shared/authorization.ts'
import { supabaseAdmin } from '../_shared/supabase-admin.ts'

Deno.serve(createHandler(async (req: Request): Promise<Response> => {
  const ctx = await authenticateRequest(req)
  await checkPermissionOrThrow(ctx.user.id, 'jobs.deadletter.manage')

  const url = new URL(req.url)
  const page = Math.max(1, parseInt(url.searchParams.get('page') ?? '1', 10))
  const pageSize = Math.min(100, Math.max(1, parseInt(url.searchParams.get('page_size') ?? '20', 10)))
  const jobIdFilter = url.searchParams.get('job_id')

  let query = supabaseAdmin
    .from('job_executions')
    .select('*', { count: 'exact' })
    .eq('state', 'dead_lettered')
    .order('created_at', { ascending: false })
    .range((page - 1) * pageSize, page * pageSize - 1)

  if (jobIdFilter) {
    query = query.eq('job_id', jobIdFilter)
  }

  const { data, error, count } = await query

  if (error) {
    throw new Error(`Failed to query dead letters: ${error.message}`)
  }

  return apiSuccess({
    data: data ?? [],
    pagination: {
      page,
      page_size: pageSize,
      total: count ?? 0,
      total_pages: Math.ceil((count ?? 0) / pageSize),
    },
  })
}, { rateLimit: 'standard' }))
