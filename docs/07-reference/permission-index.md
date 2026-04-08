# Permission Index

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-08

## Purpose

Central registry of all permissions in the RBAC system.

## Scope

All permissions defined across all modules.

## Permission Map

| Name | Module | Used By | Impact If Changed |
|------|--------|---------|-------------------|
| `roles.assign` | rbac | admin-panel | HIGH — affects role management |
| `roles.revoke` | rbac | admin-panel | HIGH — affects role management |
| `roles.view` | rbac | admin-panel | LOW — display only |
| `users.view_all` | user-management | admin-panel | MEDIUM — affects user listing |
| `users.edit_any` | user-management | admin-panel | HIGH — affects user data |
| `users.deactivate` | user-management | admin-panel | HIGH — affects account lifecycle |
| `admin.access` | admin-panel | admin routes | HIGH — gates admin panel |
| `admin.config` | admin-panel | admin config page | HIGH — affects system config |
| `audit.view` | audit-logging | admin-panel | MEDIUM — affects audit visibility |
| `audit.export` | audit-logging | admin-panel | LOW — export feature |
| `monitoring.view` | health-monitoring | admin-panel | LOW — display only |
| `monitoring.configure` | health-monitoring | admin-panel | MEDIUM — affects alerting |
| `jobs.view` | jobs-and-scheduler | admin-panel | LOW — display only |
| `jobs.trigger` | jobs-and-scheduler | admin-panel | MEDIUM — can trigger execution |

## Dependencies

- [Authorization Security](../02-security/authorization-security.md)
- [RBAC Module](../04-modules/rbac.md)

## Used By / Affects

All permission checks across the application.

## Related Documents

- [RBAC Module](../04-modules/rbac.md)
- [Route Index](route-index.md)
