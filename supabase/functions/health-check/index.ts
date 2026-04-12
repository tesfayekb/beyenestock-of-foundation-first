/**
 * GET /health-check — Public health check endpoint.
 *
 * Returns minimal system status. No auth required.
 * No sensitive internals exposed.
 *
 * Owner: health-monitoring module
 * Classification: operational
 * Rate limit: relaxed (public, hit by load balancers/monitors)
 */
import { createHandler, apiSuccess } from '../_shared/handler.ts'
import { supabaseAdmin } from '../_shared/supabase-admin.ts'
import { logAuditEvent } from '../_shared/audit.ts'
import {
  checkDatabase,
  checkAuth,
  checkAuditPipeline,
  deriveOverallStatus,
} from '../_shared/health-checks.ts'

Deno.serve(createHandler(async (_req: Request): Promise<Response> => {
  // Query previous snapshot BEFORE inserting — avoids race condition
  const { data: previousSnapshot } = await supabaseAdmin
    .from('system_health_snapshots')
    .select('status')
    .order('created_at', { ascending: false })
    .limit(1)
    .maybeSingle()

  // Run all subsystem checks in parallel
  const [db, auth, audit] = await Promise.all([
    checkDatabase(),
    checkAuth(),
    checkAuditPipeline(),
  ])

  const checks = { database: db, auth, audit_pipeline: audit }
  const status = deriveOverallStatus(checks)

  // Store snapshot via service role
  await supabaseAdmin.from('system_health_snapshots').insert({
    status,
    checks,
  })

  // Emit health.status_changed on transition
  if (previousSnapshot && previousSnapshot.status !== status) {
    const correlationId = crypto.randomUUID()
    await logAuditEvent({
      actorId: null,
      action: 'health.status_changed',
      targetType: 'system',
      metadata: {
        previous_status: previousSnapshot.status,
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
}, { rateLimit: 'relaxed' }))
