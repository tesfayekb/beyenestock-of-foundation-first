/**
 * normalizeRequest — Per-field input canonicalization.
 *
 * Owner: api module
 * Classification: api-critical
 * Lifecycle: active
 *
 * Canonicalizes approved fields only:
 * - Trims all string values
 * - Lowercases email fields
 *
 * No silent alteration of arbitrary user content.
 * Normalization rules are explicit per-field, not global character stripping.
 */

/** Fields that should be lowercased after trimming */
const LOWERCASE_FIELDS = new Set(['email', 'email_address'])

/**
 * Normalize a plain object's string fields.
 * Returns a shallow copy with normalized values.
 * Non-string values are passed through unchanged.
 */
export function normalizeRequest<T extends Record<string, unknown>>(input: T): T {
  const result = { ...input }

  for (const [key, value] of Object.entries(result)) {
    if (typeof value !== 'string') continue

    let normalized = value.trim()

    if (LOWERCASE_FIELDS.has(key)) {
      normalized = normalized.toLowerCase()
    }

    ;(result as Record<string, unknown>)[key] = normalized
  }

  return result
}
