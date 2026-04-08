# Function Index

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-08

## Purpose

Tracks all shared functions/services used by 2+ modules. Required by Constitution Rule 6.

## Scope

All shared functions, utilities, and services.

## Index

| Name | Module | Used By | Impact If Changed |
|------|--------|---------|-------------------|
| `getCurrentUser()` | auth | All modules | HIGH — breaks all authenticated features |
| `requireAuth()` | auth | All protected routes | HIGH — breaks route protection |
| `signOut()` | auth | layout, user-panel | MEDIUM — breaks logout flow |
| `has_role(user_id, role)` | rbac | All RLS policies | HIGH — breaks all authorization |
| `useUserRole()` | rbac | admin-panel, user-panel, layout | HIGH — breaks role-based UI |
| `requireRole(role)` | rbac | Protected routes | HIGH — breaks role gating |
| `checkPermission(permission)` | rbac | All feature modules | HIGH — breaks permission checks |
| `getUserProfile(userId)` | user-management | admin-panel, user-panel | MEDIUM — breaks profile display |
| `updateUserProfile(userId, data)` | user-management | admin-panel, user-panel | MEDIUM — breaks profile editing |
| `listUsers(filters, pagination)` | user-management | admin-panel | MEDIUM — breaks user listing |
| `logAuditEvent(params)` | audit-logging | All modules | HIGH — breaks audit trail |
| `queryAuditLogs(filters)` | audit-logging | admin-panel | MEDIUM — breaks audit viewer |
| `getSystemHealth()` | health-monitoring | admin-panel | LOW — breaks health dashboard |
| `apiError(code, message)` | api | All edge functions | HIGH — breaks error handling |
| `validateRequest(schema, body)` | api | All edge functions | HIGH — breaks input validation |
| `authenticateRequest(req)` | api | All edge functions | HIGH — breaks API auth |
| `executeWithRetry(fn, config)` | jobs-and-scheduler | All jobs | MEDIUM — breaks job retry |

## Rules

- Any function used by 2+ modules MUST be listed here
- When modifying a listed function, check all "Used By" entries
- When adding a new shared function, add it here immediately
- Impact classification guides change control decisions

## Dependencies

- [Constitution](../00-governance/constitution.md) — Rule 6

## Used By / Affects

Change control process, impact assessment.

## Related Documents

- [Dependency Map](../01-architecture/dependency-map.md)
- [Constitution](../00-governance/constitution.md)
