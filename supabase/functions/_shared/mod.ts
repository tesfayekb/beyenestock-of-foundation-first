/**
 * Shared edge function utilities — barrel export.
 *
 * All edge functions import from this single entry point:
 *   import { ... } from '../_shared/mod.ts'
 */

// CORS
export { corsHeaders } from './cors.ts'

// Supabase admin client
export { supabaseAdmin } from './supabase-admin.ts'

// API error builder
export { apiError } from './api-error.ts'

// Authentication
export {
  authenticateRequest,
  AuthError,
  type AuthenticatedUser,
  type AuthenticatedContext,
} from './authenticate-request.ts'

// Validation
export {
  validateRequest,
  ValidationError,
  z,
} from './validate-request.ts'

// Normalization
export { normalizeRequest } from './normalize-request.ts'

// Authorization
export {
  checkPermissionOrThrow,
  requireSelfScope,
  requireRole,
  requireRecentAuth,
  PermissionDeniedError,
} from './authorization.ts'

// Audit logging
export {
  logAuditEvent,
  type AuditEventParams,
  type AuditWriteResult,
  type AuditWriteSuccess,
  type AuditWriteFailure,
} from './audit.ts'

// Handler wrapper
export { createHandler, apiSuccess } from './handler.ts'
