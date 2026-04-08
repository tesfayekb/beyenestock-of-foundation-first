# Admin Panel Module

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-08

## Purpose

Provides a secure administrative control interface for managing users, roles, permissions, system configuration, audit logs, and system health.

## Scope

Admin-only UI and control plane for:

- User management
- Role and permission management
- Audit log access
- System health monitoring
- Configuration management

## Enforcement Rule (CRITICAL)

- Admin panel is a **privileged control surface**
- Access must be strictly enforced via **permissions**
- All actions must be auditable
- Any bypass of RBAC, audit logging, or authentication is an **INVALID** implementation

## Access Control

- Access requires `admin.access` **permission** (not role-based)
- MFA is mandatory for admin access
- Sensitive actions require recent authentication (re-auth)

## Privileged Actions (HIGH IMPACT)

The following actions require strict controls:

- Assigning roles → `roles.assign`
- Revoking roles → `roles.revoke`
- Creating or deleting roles → `roles.create` / `roles.delete`
- Assigning or revoking permissions → `rbac.permission_assigned` / `rbac.permission_revoked`
- Modifying system configuration → `admin.config`
- Deactivating users → `users.deactivate`
- Reactivating users → `users.reactivate`
- Accessing or exporting audit logs → `audit.view` / `audit.export`

**Requirements:**

- Permission checks enforced via `checkPermission()`
- Audit logging required
- Re-authentication required for: role assignment/revocation, config changes, dead-letter management, emergency kill switch, user deactivation/reactivation

## RBAC Management Responsibilities

Admin panel is a **control surface** — it provides the UI for RBAC management, but canonical domain events come from the [RBAC Module](rbac.md), not admin-panel-specific duplicates.

Admin panel must provide:

- Role creation, update, deletion
- Permission assignment and removal
- Role-to-permission mapping visibility
- Safe handling of base roles (`superadmin`, `user`)

All admin RBAC actions must map to: [Permission Index](../07-reference/permission-index.md), [Route Index](../07-reference/route-index.md), [Event Index](../07-reference/event-index.md), and [Function Index](../07-reference/function-index.md).

## Monitoring & Audit Integration

Admin panel must surface:

- System health dashboard
- Alert status and history
- Audit log viewer and filters
- Audit export functionality (permission-controlled)

## Key Rules

- All admin actions must be logged
- No destructive action without confirmation
- No silent failures — errors must be surfaced
- All data must be paginated
- UI must not bypass backend authorization

## Module-Local Components

| Component | Purpose |
|-----------|---------|
| `AdminLayout` | Layout wrapper with admin navigation (module-local, not cross-module shared) |
| `AdminGuard` | Panel-local wrapper around `requireAuth()` + `checkPermission('admin.access')` (module-local) |

## Events

| Event | Emitted When | Consumed By | Notes |
|-------|-------------|-------------|-------|
| `admin.config_changed` | System configuration modified | audit-logging, health-monitoring | |
| `admin.user_action` | Admin performs user operation | audit-logging | |
| `rbac.role_assigned` | Role assigned via admin UI | audit-logging | Owned by RBAC module |
| `rbac.role_revoked` | Role revoked via admin UI | audit-logging | Owned by RBAC module |
| `rbac.permission_assigned` | Permission assigned via admin UI | audit-logging | Owned by RBAC module |
| `rbac.permission_revoked` | Permission revoked via admin UI | audit-logging | Owned by RBAC module |

## Jobs

None owned by this module.

## Permissions

Admin panel consumes the following permissions (defined in [Permission Index](../07-reference/permission-index.md)):

| Permission | Description | Re-Auth |
|-----------|-------------|---------|
| `admin.access` | Gate access to entire admin panel | No |
| `admin.config` | Modify system configuration | Yes |
| `users.view_all` | View all user profiles | No |
| `users.edit_any` | Edit any user profile | No |
| `users.deactivate` | Deactivate user accounts | Yes |
| `users.reactivate` | Reactivate user accounts | Yes |
| `roles.view` | View roles and mappings | No |
| `roles.assign` | Assign roles to users | Yes |
| `roles.revoke` | Revoke roles from users | Yes |
| `roles.create` | Create new roles | No |
| `roles.delete` | Delete roles | Yes |
| `audit.view` | View audit logs | No |
| `audit.export` | Export audit data | No |
| `monitoring.view` | View system health | No |
| `monitoring.configure` | Configure monitoring | No |
| `jobs.view` | View job status | No |
| `jobs.trigger` | Manually trigger jobs | No |
| `jobs.deadletter.manage` | Manage dead-letter queue | Yes |
| `jobs.emergency` | Emergency kill switch | Yes |

## Dependencies

- [Auth Module](auth.md)
- [RBAC Module](rbac.md)
- [User Management Module](user-management.md)
- [Audit Logging Module](audit-logging.md)
- [Health Monitoring Module](health-monitoring.md)

## Used By / Affects

Control surface for:

- RBAC system
- User management
- Audit logging
- Monitoring

## Risks If Modified

HIGH — incorrect admin behavior can lead to privilege escalation or system compromise.

## Related Documents

- [User Panel](user-panel.md)
- [RBAC Module](rbac.md)
- [Audit Logging Module](audit-logging.md)
- [Health Monitoring Module](health-monitoring.md)
