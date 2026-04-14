/**
 * formatFullName — Consistently formats first + last name across the app.
 * Returns "First Last" if both present, otherwise whichever is available,
 * or the fallback string.
 */
export function formatFullName(
  displayName: string | null | undefined,
  lastName: string | null | undefined,
  fallback = '—',
): string {
  const parts = [displayName, lastName].filter(Boolean);
  return parts.length > 0 ? parts.join(' ') : fallback;
}

/**
 * getInitials — Extracts up to 2 initials from a full name string.
 */
export function getInitials(
  displayName: string | null | undefined,
  lastName: string | null | undefined,
): string {
  const full = formatFullName(displayName, lastName, '?');
  return full
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
}
