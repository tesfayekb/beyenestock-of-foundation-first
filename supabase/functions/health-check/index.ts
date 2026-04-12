/**
 * GET /health — Public health check endpoint.
 *
 * Returns minimal system status. No auth required.
 * No sensitive internals exposed.
 *
 * Owner: health-monitoring module
 * Classification: operational
 * Rate limit: standard (public endpoint)
 */
import { createHandler, apiSuccess } from '../_shared/handler.ts'
import { supabaseAdmin } from '../_shared/supabase-admin.ts'
import { logAuditEvent } from '../_shared/audit.ts'

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
    // Lightweight auth service check — list 0 users
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

Deno.serve(createHandler(async (_req: Request): Promise<Response> => {
  const [db, auth, audit] = await Promise.all([
    checkDatabase(),
    checkAuth(),
    checkAuditPipeline(),
  ])

  const checks = { database: db, auth, audit_pipeline: audit }
  const status = deriveOverallStatus(checks)

  // Store snapshot via service role
  const correlationId = crypto.randomUUID()
  await supabaseAdmin.from('system_health_snapshots').insert({
    status,
    checks,
  })

  // If status changed, we'd emit health.status_changed — but we need
  // previous status to compare. Check last snapshot:
  const { data: lastSnapshot } = await supabaseAdmin
    .from('system_health_snapshots')
    .select('status')
    .order('created_at', { ascending: false })
    .range(1, 1) // second-most-recent (index 1), since we just inserted the current one
    .maybeSingle()

  if (lastSnapshot && lastSnapshot.status !== status) {
    await logAuditEvent({
      actorId: null,
      action: 'health.status_changed',
      targetType: 'system',
      metadata: {
        previous_status: lastSnapshot.status,
        new_status: status,
        checks,
      },
      correlationId,
    })
  }

  // Public response: minimal, no internals
  return apiSuccess({
    status,
    timestamp: new Date().toISOString(),
  })
}))
