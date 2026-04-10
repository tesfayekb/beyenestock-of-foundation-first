/**
 * Shared error classes for edge function error classification.
 * These are pure classes with no external dependencies,
 * safe to import in any context including tests.
 */

/** Authentication failure — always results in 401 */
export class AuthError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'AuthError'
  }
}

/**
 * Permission/authorization failure — always results in 403.
 *
 * Enforcement rule: Any authorization guard MUST throw this error
 * for denials. Returning apiError(403, ...) from authorization logic
 * is a governance violation.
 */
export class PermissionDeniedError extends Error {
  permissionKey: string
  /** Authoritative actor identity — set at throw site with validated user ID */
  userId: string | null
  /** Denial reason category for audit analytics */
  reason: string

  constructor(
    message: string,
    permissionKey: string,
    options?: { userId?: string; reason?: string }
  ) {
    super(message)
    this.name = 'PermissionDeniedError'
    this.permissionKey = permissionKey
    this.userId = options?.userId ?? null
    this.reason = options?.reason ?? 'missing_permission'
  }
}

/** Input validation failure — always results in 400 */
export class ValidationError extends Error {
  fieldErrors: Record<string, string[] | undefined>
  formErrors: string[]

  constructor(
    fieldErrors: Record<string, string[] | undefined>,
    formErrors: string[]
  ) {
    const firstField = Object.keys(fieldErrors)[0]
    const firstMsg = firstField
      ? `${firstField}: ${fieldErrors[firstField]?.[0]}`
      : formErrors[0] ?? 'Validation failed'
    super(firstMsg)
    this.name = 'ValidationError'
    this.fieldErrors = fieldErrors
    this.formErrors = formErrors
  }
}
