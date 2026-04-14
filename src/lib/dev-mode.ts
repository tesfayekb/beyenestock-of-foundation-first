/**
 * Dev-mode utilities.
 *
 * When VITE_DEV_MODE=true, security friction is reduced for faster development:
 * - Turnstile CAPTCHA bypassed (dummy token)
 * - Reauth dialog auto-verifies
 * - Email verification gate skipped
 * - Inactivity timeout extended to 24h
 * - Password minimum reduced to 6 chars
 *
 * ⚠️ MUST be removed before production (see preproduction-checklist.md PP-006).
 *
 * Owner: governance
 * Classification: dev-only
 */

export const DEV_MODE = import.meta.env.VITE_DEV_MODE === 'true';

export const DEV_PASSWORD_MIN_LENGTH = 6;
export const DEV_INACTIVITY_TIMEOUT_MS = 24 * 60 * 60 * 1000; // 24 hours

if (DEV_MODE) {
  console.warn(
    '%c⚠️ DEV MODE ACTIVE — Security measures bypassed. Do NOT ship to production.',
    'color: #f59e0b; font-weight: bold; font-size: 14px;'
  );
}
