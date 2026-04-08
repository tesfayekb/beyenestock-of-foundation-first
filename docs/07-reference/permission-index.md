# Permission Index

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-08

## Purpose

Central registry and **single source of truth** for all permissions in the RBAC system.

**No permission exists unless it is defined in this document.**

## Scope

All permissions across all modules and features.

## Enforcement Rule (CRITICAL)

- Every permission **MUST** be defined here before use
- Any permission used but not listed here is an **INVALID** implementation
- Permissions must not be hardcoded outside this registry
- All changes must follow the change control policy

## Permission Naming Rules

- Format: `{resource}.{action}`
- Must be lowercase
- Must be descriptive and consistent
- Must not be ambiguous or duplicated

Examples:

- `user.read`
- `user.update`
- `audit.view`
- `config.update`

### Identity Rules

- Each permission has a stable identifier (UUID) at the database level
- The `key` is the human-readable reference, not the primary identifier
- Absence of a permission **MUST** be treated as deny (no implicit access)

## Permission Map

| Permission | Module | Used By | Impact If Changed |
|-----------|--------|---------|-------------------|
| `roles.assign` | rbac | admin-panel (role management UI, API) | HIGH — affects role assignment |
| `roles.revoke` | rbac | admin-panel (role management UI, API) | HIGH — affects role removal |
| `roles.view` | rbac | admin-panel (role listing UI) | LOW — display only |
| `users.view_all` | user-management | admin-panel (user listing) | MEDIUM — affects visibility |
| `users.edit_any` | user-management | admin-panel (user edit API) | HIGH — affects user data |
| `users.deactivate` | user-management | admin-panel (account lifecycle) | HIGH — affects access |
| `admin.access` | admin-panel | admin routes | HIGH — gates admin panel |
| `admin.config` | admin-panel | admin config UI/API | HIGH — affects system config |
| `audit.view` | audit-logging | admin-panel (audit viewer) | MEDIUM — affects visibility |
| `audit.export` | audit-logging | admin-panel (export feature) | LOW — export feature |
| `monitoring.view` | health-monitoring | admin-panel (dashboard) | LOW — display only |
| `monitoring.configure` | health-monitoring | admin-panel (alerts config) | MEDIUM — affects alerting |
| `jobs.view` | jobs-and-scheduler | admin-panel (jobs dashboard) | LOW — display only |
| `jobs.trigger` | jobs-and-scheduler | admin-panel (manual trigger) | MEDIUM — affects execution |

## Superadmin Rule

- `superadmin` implicitly has **ALL** permissions listed in this document
- New permissions are automatically granted to `superadmin`

## Permission Lifecycle Rules

- New permissions **MUST** be added here before implementation
- Permission removal **MUST** be documented and reviewed
- Deprecated permissions must be marked (not silently removed)
- Changes are HIGH impact and require audit

## Dependency Rules

- Each permission must map to a module
- Each permission must have at least one usage path
- All usage must be traceable to:
  - Module
  - UI/API path

## Dependencies

- [Authorization Security](../02-security/authorization-security.md)
- [RBAC Module](../04-modules/rbac.md)

## Used By / Affects

All permission checks, RBAC enforcement, API guards, and UI access controls.

## Risks If Changed

HIGH — incorrect permission definitions lead to access control failures or privilege escalation.

## Related Documents

- [RBAC Module](../04-modules/rbac.md)
- [Route Index](route-index.md)
- [Dependency Map](../01-architecture/dependency-map.md)
