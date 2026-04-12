/**
 * GET /health-detailed — Authenticated detailed health check.
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
import {
  checkDatabase,
  checkAuth,
  checkAuditPipeline,
  deriveOverallStatus,
} from '../_shared/health-checks.ts'

Deno.serve(createHandler(async (req: Request): Promise<Response> => {
  const ctx = await authenticateRequest(req)
  await checkPermissionOrThrow(ctx.user.id, 'monitoring.view')

  const [db, auth, audit] = await Promise.all([
    checkDatabase(),
    checkAuth(),
    checkAuditPipeline(),
  ])

  const checks = { database: db, auth, audit_pipeline: audit }
  const status = deriveOverallStatus(checks)

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
