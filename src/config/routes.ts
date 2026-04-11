/**
 * Centralized route constants — single source of truth.
 * Used by navigation configs AND route definitions to prevent drift.
 */
export const ROUTES = {
  // Public
  SIGN_IN: '/sign-in',
  SIGN_UP: '/sign-up',
  FORGOT_PASSWORD: '/forgot-password',
  RESET_PASSWORD: '/reset-password',
  MFA_CHALLENGE: '/mfa-challenge',
  MFA_ENROLL: '/mfa-enroll',

  // User
  HOME: '/',
  DASHBOARD: '/dashboard',
  SETTINGS: '/settings',
  SETTINGS_SECURITY: '/settings/security',

  // Admin
  ADMIN: '/admin',
  ADMIN_USERS: '/admin/users',
  ADMIN_ROLES: '/admin/roles',
  ADMIN_PERMISSIONS: '/admin/permissions',
  ADMIN_AUDIT: '/admin/audit',
} as const;
