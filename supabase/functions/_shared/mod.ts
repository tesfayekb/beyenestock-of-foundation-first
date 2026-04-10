/**
 * Shared edge function utilities — barrel export.
 */

// CORS
export { corsHeaders } from './cors.ts'

// Supabase admin client
export { supabaseAdmin } from './supabase-admin.ts'

// Error classes (no external deps — safe to import anywhere)
export { AuthError, PermissionDeniedError, ValidationError } from './errors.ts'

// API error builder
export { apiError } from './api-error.ts'

// Authentication
export {
  authenticateRequest,
  type AuthenticatedUser,
  type AuthenticatedContext,
} from './authenticate-request.ts'

// Validation
export { validateRequest, z } from './validate-request.ts'

// Normalization
export { normalizeRequest } from './normalize-request.ts'

// Authorization
export {
  checkPermissionOrThrow,
  requireSelfScope,
  requireRole,
  requireRecentAuth,
} from './authorization.ts'

// Audit logging
export {
  logAuditEvent,
  type AuditEventParams,
  type AuditWriteResult,
  type AuditWriteSuccess,
  type AuditWriteFailure,
} from './audit.ts'

// Audit query schemas
export {
  AuditQueryParamsSchema,
  AuditExportParamsSchema,
  searchParamsToObject,
  sanitizeMetadataForExport,
} from './audit-query-schemas.ts'

// Rate limiting
export { checkRateLimit, type RateLimitClass } from './rate-limit.ts'

// Handler wrapper
export { createHandler, apiSuccess, type HandlerOptions } from './handler.ts'
