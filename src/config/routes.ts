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
  ADMIN_USER_DETAIL: '/admin/users/:id',
  ADMIN_ROLES: '/admin/roles',
  ADMIN_ROLE_DETAIL: '/admin/roles/:id',
  ADMIN_PERMISSIONS: '/admin/permissions',
  ADMIN_AUDIT: '/admin/audit',
  ADMIN_HEALTH: '/admin/health',
  ADMIN_JOBS: '/admin/jobs',
  ADMIN_ONBOARDING: '/admin/onboarding',

  // Trading (Phase 1+) — privileged, separate from foundation /admin/health
  ADMIN_TRADING: '/admin/trading',
  ADMIN_TRADING_WARROOM: '/admin/trading/warroom',
  ADMIN_TRADING_POSITIONS: '/admin/trading/positions',
  ADMIN_TRADING_SIGNALS: '/admin/trading/signals',
  ADMIN_TRADING_PERFORMANCE: '/admin/trading/performance',
  ADMIN_TRADING_HEALTH: '/admin/trading/health',
  ADMIN_TRADING_CONFIG: '/admin/trading/config',

  // ── Trading Console ──────────────────────────────────────────────────────
  // Dedicated dashboard at /trading/* — separate from /admin/*
  // All trading pages moved here from /admin/trading/* in Phase 4C.
  // Old /admin/trading/* routes redirect here for backward compatibility.
  TRADING: '/trading',
  TRADING_WARROOM: '/trading/warroom',
  TRADING_POSITIONS: '/trading/positions',
  TRADING_SIGNALS: '/trading/signals',
  TRADING_PERFORMANCE: '/trading/performance',
  TRADING_HEALTH: '/trading/health',
  TRADING_CONFIG: '/trading/config',
  TRADING_INTELLIGENCE: '/trading/intelligence',
  TRADING_FLAGS: '/trading/flags',
  TRADING_STRATEGIES: '/trading/strategies',
  TRADING_MILESTONES: '/trading/milestones',
  TRADING_SUBSCRIPTIONS: '/trading/subscriptions',
  TRADING_ACTIVATION: '/trading/activation',
  TRADING_AB_COMPARISON: '/trading/ab-comparison',
} as const;
