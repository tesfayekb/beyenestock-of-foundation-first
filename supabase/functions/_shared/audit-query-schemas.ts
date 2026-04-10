/**
 * audit-query-schemas — Shared Zod schemas for audit log query/export endpoints.
 *
 * Owner: audit-logging module
 * Classification: api-critical
 * Lifecycle: active
 *
 * Centralizes query-param validation for query-audit-logs and export-audit-logs.
 * Both endpoints reuse these schemas via validateRequest().
 */
import { z } from 'https://deno.land/x/zod@v3.22.4/mod.ts'

const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

const uuidString = z.string().trim().regex(uuidRegex, 'Invalid UUID format').optional()

const isoDateString = z.string().trim().refine(
  (v) => !isNaN(Date.parse(v)),
  { message: 'Invalid ISO date format' }
).optional()

/** Schema for query-audit-logs query params */
export const AuditQueryParamsSchema = z.object({
  limit: z.coerce.number().int().min(1).max(100).default(50),
  action: z.string().trim().optional(),
  actor_id: uuidString,
  target_type: z.string().trim().optional(),
  target_id: uuidString,
  date_from: isoDateString,
  date_to: isoDateString,
  before: isoDateString, // cursor
})

/** Schema for export-audit-logs query params */
export const AuditExportParamsSchema = z.object({
  action: z.string().trim().optional(),
  actor_id: uuidString,
  target_type: z.string().trim().optional(),
  date_from: isoDateString,
  date_to: isoDateString,
})

/**
 * Parse URL search params into a plain object for Zod validation.
 * Missing keys become undefined (Zod defaults/optionals handle them).
 */
export function searchParamsToObject(params: URLSearchParams, keys: string[]): Record<string, string | undefined> {
  const obj: Record<string, string | undefined> = {}
  for (const key of keys) {
    const val = params.get(key)
    if (val !== null && val.trim() !== '') {
      obj[key] = val
    }
  }
  return obj
}

/**
 * Metadata allowlist for audit log export.
 * Only these top-level keys are included in exported metadata.
 * Defense-in-depth: even if write-time sanitization missed something,
 * export will not leak sensitive fields.
 */
const EXPORT_METADATA_ALLOWED_KEYS = new Set([
  'correlation_id',
  'filters',
  'max_rows',
  'reason',
  'target_role',
  'target_permission',
  'role_key',
  'permission_key',
  'ip_address',
  'user_agent',
  'action',
  'target_type',
  'target_id',
  'changes',
  'previous_value',
  'new_value',
])

/**
 * Sanitize metadata for export — allowlist-based defense-in-depth.
 * Returns a new object containing only allowed keys.
 * Sensitive fields are excluded even if they somehow exist in stored rows.
 */
export function sanitizeMetadataForExport(
  metadata: Record<string, unknown> | null | undefined
): Record<string, unknown> {
  if (!metadata || typeof metadata !== 'object') return {}
  const sanitized: Record<string, unknown> = {}
  for (const [key, value] of Object.entries(metadata)) {
    if (EXPORT_METADATA_ALLOWED_KEYS.has(key)) {
      sanitized[key] = value
    }
  }
  return sanitized
}
