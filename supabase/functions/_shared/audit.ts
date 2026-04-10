/**
 * logAuditEvent — Append-only audit trail writer.
 *
 * Owner: audit-logging module
 * Classification: audit-critical
 * Lifecycle: active
 *
 * Returns structured result:
 *   Success: { success: true, auditId, correlationId }
 *   Failure: { success: false, code, reason, correlationId }
 *
 * Never throws. Callers inspect `success` to decide:
 *   - High-risk actions: abort on { success: false }
 *   - Standard-risk actions: continue, surface alert
 */
import { supabaseAdmin } from './supabase-admin.ts'

export interface AuditEventParams {
  actorId: string
  action: string
  targetType?: string
  targetId?: string
  metadata?: Record<string, unknown>
  ipAddress?: string | null
  userAgent?: string | null
  correlationId: string
}

export interface AuditWriteSuccess {
  success: true
  auditId: string
  correlationId: string
}

export interface AuditWriteFailure {
  success: false
  code: string
  reason: string
  correlationId: string
}

export type AuditWriteResult = AuditWriteSuccess | AuditWriteFailure

export async function logAuditEvent(
  params: AuditEventParams
): Promise<AuditWriteResult> {
  try {
    // Ensure metadata never contains sensitive fields
    const safeMetadata = sanitizeMetadata(params.metadata ?? {})

    // Always include correlation_id in metadata for tracing
    safeMetadata.correlation_id = params.correlationId

    const { data, error } = await supabaseAdmin
      .from('audit_logs')
      .insert({
        actor_id: params.actorId,
        action: params.action,
        target_type: params.targetType ?? null,
        target_id: params.targetId ?? null,
        metadata: safeMetadata,
        ip_address: params.ipAddress ?? null,
        user_agent: params.userAgent ?? null,
      })
      .select('id')
      .single()

    if (error) {
      const failure: AuditWriteFailure = {
        success: false,
        code: 'AUDIT_WRITE_FAILED',
        reason: error.message,
        correlationId: params.correlationId,
      }
      console.error('[AUDIT] Write failed:', error.message, {
        action: params.action,
        correlationId: params.correlationId,
      })
      emitAuditFailureEvent(params, failure)
      return failure
    }

    return {
      success: true,
      auditId: data.id,
      correlationId: params.correlationId,
    }
  } catch (err) {
    const reason = err instanceof Error ? err.message : 'Unknown audit error'
    const failure: AuditWriteFailure = {
      success: false,
      code: 'AUDIT_UNEXPECTED_ERROR',
      reason,
      correlationId: params.correlationId,
    }
    console.error('[AUDIT] Unexpected failure:', reason, {
      action: params.action,
      correlationId: params.correlationId,
    })
    emitAuditFailureEvent(params, failure)
    return failure
  }
}

/** Forbidden keys that must never appear in audit metadata */
const FORBIDDEN_METADATA_KEYS = new Set([
  'password', 'token', 'secret', 'access_token', 'refresh_token',
  'mfa_secret', 'totp_secret', 'api_key', 'service_role_key',
])

function sanitizeMetadata(
  metadata: Record<string, unknown>
): Record<string, unknown> {
  const sanitized: Record<string, unknown> = {}
  for (const [key, value] of Object.entries(metadata)) {
    if (FORBIDDEN_METADATA_KEYS.has(key.toLowerCase())) {
      sanitized[key] = '[REDACTED]'
    } else {
      sanitized[key] = value
    }
  }
  return sanitized
}

// ─── Audit failure event emission ───────────────────────────────────

/** Registered listeners for audit failure events */
type AuditFailureListener = (
  params: AuditEventParams,
  failure: AuditWriteFailure
) => void

const auditFailureListeners: AuditFailureListener[] = []

/**
 * Register a listener for audit.write_failed events.
 * Used by monitoring/alerting infrastructure.
 */
export function onAuditWriteFailure(listener: AuditFailureListener): void {
  auditFailureListeners.push(listener)
}

/**
 * Emit audit.write_failed event to all registered listeners.
 * Never throws — listener errors are logged but do not propagate.
 */
function emitAuditFailureEvent(
  params: AuditEventParams,
  failure: AuditWriteFailure
): void {
  for (const listener of auditFailureListeners) {
    try {
      listener(params, failure)
    } catch (listenerErr) {
      console.error('[AUDIT] Failure listener error:', listenerErr)
    }
  }
}
