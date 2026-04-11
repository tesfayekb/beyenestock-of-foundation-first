/**
 * Shared input validation utilities.
 * SSOT for validation logic used across multiple components.
 */

/**
 * Validates that a URL uses HTTPS protocol.
 * Empty string is valid (allows clearing the field).
 */
export function isValidAvatarUrl(url: string): boolean {
  if (!url) return true;
  try {
    const parsed = new URL(url);
    return parsed.protocol === 'https:';
  } catch {
    return false;
  }
}
