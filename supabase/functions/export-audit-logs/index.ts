/**
 * export-audit-logs — CSV export of audit logs.
 *
 * Permission: audit.export
 * Classification: privileged, compliance-sensitive
 * Audit risk: HIGH-RISK (fail-closed — abort if audit write fails)
 *
 * Constraints:
 *   - Max export: 10,000 rows
 *   - Format: CSV (DEC-025)
 *   - Sort: created_at ASC (chronological for compliance)
 *   - The export action itself is audited as high-risk
 *   - Allowed filters: action, actor_id, target_type, date_from, date_to
 *   - Metadata allowlist-sanitized at export time (defense-in-depth)
 */
import { createHandler } from '../_shared/handler.ts'
import { authenticateRequest } from '../_shared/authenticate-request.ts'
import { checkPermissionOrThrow } from '../_shared/authorization.ts'
import { validateRequest } from '../_shared/validate-request.ts'
import { logAuditEvent } from '../_shared/audit.ts'
import { apiError } from '../_shared/api-error.ts'
import { supabaseAdmin } from '../_shared/supabase-admin.ts'
import { corsHeaders } from '../_shared/cors.ts'
import {
  AuditExportParamsSchema,
  searchParamsToObject,
  sanitizeMetadataForExport,
} from '../_shared/audit-query-schemas.ts'

const MAX_EXPORT_ROWS = 10_000
const EXPORT_PARAM_KEYS = ['action', 'actor_id', 'target_type', 'date_from', 'date_to']

Deno.serve(createHandler(async (req: Request): Promise<Response> => {
  if (req.method !== 'GET') {
    return apiError(405, 'Method not allowed', { correlationId: crypto.randomUUID() })
  }

  const ctx = await authenticateRequest(req)
  await checkPermissionOrThrow(ctx.user.id, 'audit.export')

  // Schema-based validation via Stage 3A shared primitive
  const url = new URL(req.url)
  const rawParams = searchParamsToObject(url.searchParams, EXPORT_PARAM_KEYS)
  const params = validateRequest(AuditExportParamsSchema, rawParams)

  // ─── HIGH-RISK AUDIT: Log the export action BEFORE executing ───
  const auditResult = await logAuditEvent({
    actorId: ctx.user.id,
    action: 'audit.exported',
    targetType: 'audit_logs',
    metadata: {
      filters: {
        action: params.action ?? null,
        actor_id: params.actor_id ?? null,
        target_type: params.target_type ?? null,
        date_from: params.date_from ?? null,
        date_to: params.date_to ?? null,
      },
      max_rows: MAX_EXPORT_ROWS,
    },
    ipAddress: ctx.ipAddress,
    userAgent: ctx.userAgent,
    correlationId: ctx.correlationId,
  })

  // FAIL-CLOSED: Abort export if audit write failed
  if (!auditResult.success) {
    console.error('[EXPORT-AUDIT-LOGS] Audit write failed — aborting export (fail-closed)', {
      code: auditResult.code,
      reason: auditResult.reason,
      correlationId: ctx.correlationId,
    })
    return apiError(503, 'Export unavailable: audit integrity check failed', {
      code: 'AUDIT_INTEGRITY_FAILURE',
      correlationId: ctx.correlationId,
    })
  }

  // Build query — chronological for compliance
  let query = supabaseAdmin
    .from('audit_logs')
    .select('id, actor_id, action, target_type, target_id, metadata, ip_address, user_agent, created_at')
    .order('created_at', { ascending: true })
    .limit(MAX_EXPORT_ROWS)

  if (params.action) query = query.eq('action', params.action)
  if (params.actor_id) query = query.eq('actor_id', params.actor_id)
  if (params.target_type) query = query.eq('target_type', params.target_type)
  if (params.date_from) query = query.gte('created_at', params.date_from)
  if (params.date_to) query = query.lte('created_at', params.date_to)

  const { data, error } = await query

  if (error) {
    console.error('[EXPORT-AUDIT-LOGS] Query failed:', error.message, { correlationId: ctx.correlationId })
    return apiError(500, 'Failed to export audit logs', { correlationId: ctx.correlationId })
  }

  const rows = data ?? []

  // Build CSV with allowlist-sanitized metadata (defense-in-depth)
  const csvHeader = 'id,actor_id,action,target_type,target_id,ip_address,user_agent,created_at,metadata'
  const csvRows = rows.map(r => [
    r.id,
    r.actor_id ?? '',
    escapeCsv(r.action),
    escapeCsv(r.target_type ?? ''),
    r.target_id ?? '',
    r.ip_address ?? '',
    escapeCsv(r.user_agent ?? ''),
    r.created_at,
    escapeCsv(JSON.stringify(sanitizeMetadataForExport(r.metadata as Record<string, unknown>))),
  ].join(','))

  const csv = [csvHeader, ...csvRows].join('\n')

  return new Response(csv, {
    status: 200,
    headers: {
      ...corsHeaders,
      'Content-Type': 'text/csv; charset=utf-8',
      'Content-Disposition': `attachment; filename="audit-logs-${new Date().toISOString().slice(0, 10)}.csv"`,
      'X-Correlation-Id': ctx.correlationId,
      'X-Row-Count': String(rows.length),
      'X-Max-Rows': String(MAX_EXPORT_ROWS),
    },
  })
}))

/** Escape a value for CSV — wrap in quotes if it contains comma, quote, or newline */
function escapeCsv(value: string): string {
  if (value.includes(',') || value.includes('"') || value.includes('\n')) {
    return `"${value.replace(/"/g, '""')}"`
  }
  return value
}
