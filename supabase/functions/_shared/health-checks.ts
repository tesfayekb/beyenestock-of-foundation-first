/**
 * Shared health check subsystem probes and status derivation.
 *
 * Owner: health-monitoring module
 * Classification: operational
 * Lifecycle: active
 *
 * SOURCE: supabase/functions/_shared/health-checks.ts
 * CONSUMERS: health-check, health-detailed, (future) alert-evaluation
 * SYNC RULE: Threshold or subsystem changes MUST update all consumers.
 */
import { supabaseAdmin } from './supabase-admin.ts'

export interface SubsystemCheck {
  status: 'healthy' | 'degraded' | 'unhealthy'
  latency_ms: number
  error?: string
}

/** DB degraded threshold (ms) */
const DB_DEGRADED_MS = 2000
/** Auth degraded threshold (ms) */
const AUTH_DEGRADED_MS = 3000
/** Audit degraded threshold (ms) */
const AUDIT_DEGRADED_MS = 2000

export async function checkDatabase(): Promise<SubsystemCheck> {
  const start = Date.now()
  try {
    const { error } = await supabaseAdmin.from('profiles').select('id').limit(1)
    const latency = Date.now() - start
    if (error) {
      return { status: 'unhealthy', latency_ms: latency, error: error.message }
    }
    return { status: latency > DB_DEGRADED_MS ? 'degraded' : 'healthy', latency_ms: latency }
  } catch (e) {
    return { status: 'unhealthy', latency_ms: Date.now() - start, error: String(e) }
  }
}

export async function checkAuth(): Promise<SubsystemCheck> {
  const start = Date.now()
  try {
    const { error } = await supabaseAdmin.auth.admin.listUsers({ page: 1, perPage: 1 })
    const latency = Date.now() - start
    if (error) {
      return { status: 'unhealthy', latency_ms: latency, error: error.message }
    }
    return { status: latency > AUTH_DEGRADED_MS ? 'degraded' : 'healthy', latency_ms: latency }
  } catch (e) {
    return { status: 'unhealthy', latency_ms: Date.now() - start, error: String(e) }
  }
}

export async function checkAuditPipeline(): Promise<SubsystemCheck> {
  const start = Date.now()
  try {
    const { error } = await supabaseAdmin.from('audit_logs').select('id').limit(1)
    const latency = Date.now() - start
    if (error) {
      return { status: 'unhealthy', latency_ms: latency, error: error.message }
    }
    return { status: latency > AUDIT_DEGRADED_MS ? 'degraded' : 'healthy', latency_ms: latency }
  } catch (e) {
    return { status: 'unhealthy', latency_ms: Date.now() - start, error: String(e) }
  }
}

export function deriveOverallStatus(
  checks: Record<string, SubsystemCheck>
): 'healthy' | 'degraded' | 'unhealthy' {
  const statuses = Object.values(checks).map(c => c.status)
  if (statuses.includes('unhealthy')) return 'unhealthy'
  if (statuses.includes('degraded')) return 'degraded'
  return 'healthy'
}
