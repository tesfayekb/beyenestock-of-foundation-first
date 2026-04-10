/**
 * validateRequest — Zod-based strict input validation.
 *
 * Owner: api module
 * Classification: api-critical
 * Fail behavior: fail-fast — throws ValidationError (caller returns 400)
 * Lifecycle: active
 *
 * Validates request body against a Zod schema with strict mode
 * (rejects unknown fields). Returns typed, validated data.
 */
import { z } from 'https://deno.land/x/zod@v3.22.4/mod.ts'

export { z }

/**
 * Parse and validate request body against a Zod schema.
 * Throws ValidationError on failure.
 */
export function validateRequest<T extends z.ZodTypeAny>(
  schema: T,
  body: unknown
): z.infer<T> {
  const result = schema.safeParse(body)
  if (!result.success) {
    const flattened = result.error.flatten()
    throw new ValidationError(flattened.fieldErrors, flattened.formErrors)
  }
  return result.data
}

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
