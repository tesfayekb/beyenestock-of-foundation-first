/**
 * GET /health/detailed — Authenticated detailed health check.
 *
 * Requires Bearer JWT + monitoring.view permission.
 * Returns per-subsystem check results with latency and error details.
 *
 * Owner: health-monitoring module
 * Classification: operational
 * Rate limit: standard
 */
import { createHandler, apiSuccess } from '../_shared/handler.ts'
import { authenticateRequest } from '../_shared/authenticate-request.ts'
import { checkPermissionOrThrow } from '../_shared/authorization.ts'
import { supabaseAdmin } from '../_shared/supabase-admin.ts'

interface SubsystemCheck {
  status: 'healthy' | 'degraded' | 'unhealthy'
  latency_ms: number
  error?: string
}

async function checkDatabase(): Promise<SubsystemCheck> {
  const start = Date.now()
  try {
    const { error } = await supabaseAdmin.from('profiles').select('id').limit(1)
    const latency = Date.now() - start
    if (error) {
      return { status: 'unhealthy', latency_ms: latency, error: error.message }
    }
    return { status: latency > 2000 ? 'degraded' : 'healthy', latency_ms: latency }
  } catch (e) {
    return { status: 'unhealthy', latency_ms: Date.now() - start, error: String(e) }
  }
}

async function checkAuth(): Promise<SubsystemCheck> {
  const start = Date.now()
  try {
    const { error } = await supabaseAdmin.auth.admin.listUsers({ page: 1, perPage: 1 })
    const latency = Date.now() - start
    if (error) {
      return { status: 'unhealthy', latency_ms: latency, error: error.message }
    }
    return { status: latency > 3000 ? 'degraded' : 'healthy', latency_ms: latency }
  } catch (e) {
    return { status: 'unhealthy', latency_ms: Date.now() - start, error: String(e) }
  }
}

async function checkAuditPipeline(): Promise<SubsystemCheck> {
  const start = Date.now()
  try {
    const { error } = await supabaseAdmin.from('audit_logs').select('id').limit(1)
    const latency = Date.now() - start
    if (error) {
      return { status: 'unhealthy', latency_ms: latency, error: error.message }
    }
    return { status: latency > 2000 ? 'degraded' : 'healthy', latency_ms: latency }
  } catch (e) {
    return { status: 'unhealthy', latency_ms: Date.now() - start, error: String(e) }
  }
}

function deriveOverallStatus(checks: Record<string, SubsystemCheck>): 'healthy' | 'degraded' | 'unhealthy' {
  const statuses = Object.values(checks).map(c => c.status)
  if (statuses.includes('unhealthy')) return 'unhealthy'
  if (statuses.includes('degraded')) return 'degraded'
  return 'healthy'
}

Deno.serve(createHandler(async (req: Request): Promise<Response> => {
  // Auth + permission check
  const ctx = await authenticateRequest(req)
  await checkPermissionOrThrow(ctx.user.id, 'monitoring.view')

  // Run all subsystem checks in parallel
  const [db, auth, audit] = await Promise.all([
    checkDatabase(),
    checkAuth(),
    checkAuditPipeline(),
  ])

  const checks = { database: db, auth, audit_pipeline: audit }
  const status = deriveOverallStatus(checks)

  // Detailed response includes per-subsystem data
  return apiSuccess({
    status,
    timestamp: new Date().toISOString(),
    subsystems: checks,
    summary: {
      total: Object.keys(checks).length,
      healthy: Object.values(checks).filter(c => c.status === 'healthy').length,
      degraded: Object.values(checks).filter(c => c.status === 'degraded').length,
      unhealthy: Object.values(checks).filter(c => c.status === 'unhealthy').length,
    },
  })
}))
