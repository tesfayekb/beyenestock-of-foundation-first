# Permission Index

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-08 | **Status:** Living Document | **Index Version:** `perm-v1.0`

## Purpose

Central registry and **permission contract governance system** for all permissions in the RBAC system. This document is the single source of truth — it defines what permissions exist, their scope, classification, allowed roles, testing requirements, and audit governance.

**No permission exists unless it is defined in this document.**

## Scope

All permissions across all modules, features, UI panels, and API endpoints.

---

## Enforcement Rule (CRITICAL)

| Rule | Description |
|------|-------------|
| **Completeness** | Every permission MUST be defined here before use. Any permission used but not listed = **INVALID** implementation. |
| **No hardcoding** | Permissions must not be hardcoded outside this registry. |
| **Deny by default** | Absence of a permission MUST be treated as deny. No implicit access. |
| **Change control** | All permission changes must follow change control policy. |
| **Drift prohibition** | DB permissions must match this index. Undocumented DB permission = invalid. Missing DB permission for indexed key = invalid. |
| **Immutable keys** | Permission keys are immutable once active. Rename requires deprecate + successor, not silent overwrite. |
| **UUID governance** | UUIDs must never be recycled. Each permission has a stable UUID at the database level. |
| **Audit mandate** | Adding, removing, or changing any permission semantics must generate an audit event and action tracker entry. |

---

## Permission Classification Model

| Classification | Description | Governance Level |
|---------------|-------------|-----------------|
| **security-critical** | Affects system-wide access, emergency controls, authentication bypass risk | Highest — Lead + Security approval, re-auth required |
| **admin-critical** | Affects administrative capabilities, role management, config | High — Lead approval, audit required |
| **destructive** | Enables irreversible or high-impact state changes | High — approval + audit + re-auth in UI |
| **compliance-sensitive** | Affects audit trails, data export, retention | High — approval + audit |
| **operational** | Affects system behavior, job control, monitoring | Medium — review recommended |
| **read-only** | View/display only, no mutation | Standard |

---

## Permission Scope Model

| Scope | Description | Example |
|-------|-------------|---------|
| **self** | User can act only on their own resources | User editing own profile |
| **resource-scoped** | User can act on specific assigned resources | Managing specific job types |
| **tenant-scoped** | User can act within their tenant/organization | Viewing users within org |
| **system-wide** | User can act across the entire system | Kill switch, config changes |

**Rule:** Every permission must declare its scope. Undeclared scope defaults to most restrictive interpretation.

---

## Permission Entry Schema

Every permission must include:

| Field | Description | Required |
|-------|-------------|----------|
| `key` | Permission key (`resource.action` format) | Yes |
| `module` | Owning module | Yes |
| `description` | Exact semantic definition of what this permission allows | Yes |
| `classification` | From classification model above | Yes |
| `scope` | From scope model above | Yes |
| `default_roles` | Roles that receive this permission by default | Yes |
| `used_by` | UI/API paths that check this permission | Yes |
| `blast_radius` | `small`, `medium`, `large`, `system-wide` | Yes |
| `approval_required` | Whether granting/changing requires approval | Yes |
| `audit_required` | Whether usage generates audit events | Yes |
| `reauth_required` | Whether UI action requires re-authentication | Yes |
| `related_routes` | Routes protected by this permission | If applicable |
| `related_functions` | Shared functions that check this permission | If applicable |
| `related_events` | Events emitted when permission is exercised | If applicable |
| `related_tests` | Tests validating allow/deny paths | If applicable |
| `related_risks` | Risk register items | If applicable |
| `related_watchlist` | Regression watchlist items | If applicable |
| `lifecycle` | `active`, `deprecated`, `pending-removal` | Yes |

---

## Dangerous Permission Rules

Permissions classified as `destructive`, `system-wide`, or `security-critical` require:

| Requirement | Description |
|-------------|-------------|
| **Explicit approval** | Granting requires Lead (or Lead + Security for security-critical) approval |
| **Audit trail** | All exercises of the permission must be audited |
| **Higher test coverage** | Must have allow, deny, wrong-role, and revoked-after-change tests |
| **Re-auth in UI** | UI actions gated by these permissions must require re-authentication |
| **Review cadence** | Quarterly review of who holds these permissions |

---

## Superadmin Rules

| Rule | Description |
|------|-------------|
| **Auto-inherit** | `superadmin` implicitly has ALL permissions listed in this document |
| **Server enforcement** | Inheritance must be server-enforced via `has_role()`, not UI-only |
| **New permissions** | Automatically granted to `superadmin` on creation |
| **Assignment governance** | Superadmin assignment/removal requires strongest governance (Lead + Security approval) |
| **Audit bypass prohibition** | Superadmin must NOT bypass audit logging — all actions are audited |
| **Minimal holders** | Superadmin role should be held by minimum necessary personnel |

---

## Testing Requirements

| Test Type | Applies To | Description |
|-----------|-----------|-------------|
| **Allow test** | All permissions | Verify permission grants access correctly |
| **Deny test** | All permissions | Verify absence of permission blocks access |
| **Wrong-role test** | All permissions | Verify incorrect role is denied |
| **Revoked-after-change test** | Admin-critical, security-critical | Verify revoking permission immediately removes access |
| **UI enforcement test** | Permissions surfaced in UI | Verify UI correctly hides/shows based on permission |
| **Scope boundary test** | Scoped permissions | Verify user cannot exceed their scope |

**Rule:** No new permission is complete until tests exist for both allow and deny paths.

---

## Permission Drift Detection

| Rule | Description |
|------|-------------|
| **Reconciliation** | Periodic comparison between this index and DB permission records |
| **Undocumented DB permission** | Triggers alert + action tracker entry |
| **Missing DB permission** | Indexed key without DB record = implementation gap |
| **Drift frequency** | Reconciliation required at minimum quarterly and before each release |
| **Auto-detection** | System should support automated drift detection in CI |

---

## Permission Lifecycle

| State | Description | Action Required |
|-------|-------------|-----------------|
| **Active** | In use, governed by this index | Standard governance |
| **Deprecated** | Scheduled for removal | `successor_permission` documented + sunset date + migration plan |
| **Pending removal** | Will be removed in next release | All consumers confirmed migrated |

**Additional fields for deprecated permissions:**

| Field | Description |
|-------|-------------|
| `successor_permission` | The permission key that replaces this one |
| `sunset_date` | Date after which permission will be removed |
| `migration_plan` | How consumers should transition |

**Rules:**
- Deprecated permissions must reference successor
- Removal requires all consumers migrated and verified
- Key must not be reused for different semantics

---

## Permission Naming Rules

- Format: `{resource}.{action}`
- Must be lowercase
- Must be descriptive and consistent
- Must not be ambiguous or duplicated
- Examples: `user.read`, `roles.assign`, `jobs.emergency`

---

## Permission Registry

> **Note:** Each entry includes a `Permission UUID` placeholder. Actual UUIDs are assigned at DB creation and must be recorded here for direct traceability.

### RBAC Permissions

#### `roles.assign`

| Field | Value |
|-------|-------|
| **Permission UUID** | `perm-uuid-roles-assign` (actual UUID assigned at DB creation) |
| **Module** | rbac |
| **Description** | Allows assigning roles to users within governance boundaries. Does not imply revoke capability. |
| **Classification** | admin-critical |
| **Scope** | system-wide |
| **Default roles** | admin, superadmin |
| **Used by** | admin-panel (role management UI, API) |
| **Blast radius** | system-wide |
| **Approval required** | Yes — Lead |
| **Audit required** | Yes |
| **Reauth required** | Yes |
| **Related routes** | `/admin/users/:id/roles` |
| **Related functions** | `has_role()`, `checkPermission()` |
| **Related events** | `rbac.role_assigned` |
| **Related risks** | RSK-002 (privilege escalation) |
| **Related watchlist** | RW-001 |
| **Related tests** | Role assignment allow/deny suite |
| **Lifecycle** | active |

#### `roles.revoke`

| Field | Value |
|-------|-------|
| **Module** | rbac |
| **Description** | Allows revoking roles from users. Separate from assign to enable split governance. |
| **Classification** | admin-critical, destructive |
| **Scope** | system-wide |
| **Default roles** | admin, superadmin |
| **Used by** | admin-panel (role management UI, API) |
| **Blast radius** | system-wide |
| **Approval required** | Yes — Lead |
| **Audit required** | Yes |
| **Reauth required** | Yes |
| **Related routes** | `/admin/users/:id/roles` |
| **Related functions** | `has_role()`, `checkPermission()` |
| **Related events** | `rbac.role_revoked` |
| **Related risks** | RSK-002 |
| **Related tests** | Role revocation allow/deny suite |
| **Lifecycle** | active |

#### `roles.view`

| Field | Value |
|-------|-------|
| **Module** | rbac |
| **Description** | Allows viewing role assignments and role definitions |
| **Classification** | read-only |
| **Scope** | system-wide |
| **Default roles** | admin, superadmin |
| **Used by** | admin-panel (role listing UI) |
| **Blast radius** | small |
| **Approval required** | No |
| **Audit required** | No |
| **Reauth required** | No |
| **Related routes** | `/admin/roles` |
| **Related tests** | Role view allow/deny tests |
| **Lifecycle** | active |

#### `roles.create`

| Field | Value |
|-------|-------|
| **Permission UUID** | `perm-uuid-roles-create` (actual UUID assigned at DB creation) |
| **Module** | rbac |
| **Description** | Allows creating new dynamic roles within the RBAC system |
| **Classification** | admin-critical |
| **Scope** | system-wide |
| **Default roles** | admin, superadmin |
| **Used by** | admin-panel (role management UI, API) |
| **Blast radius** | system-wide |
| **Approval required** | Yes — Lead |
| **Audit required** | Yes |
| **Reauth required** | No |
| **Related routes** | `/admin/roles` (POST) |
| **Related functions** | `checkPermission()` |
| **Related events** | `rbac.role_created` |
| **Related risks** | RSK-002 (privilege escalation via new role) |
| **Related tests** | Role creation allow/deny suite |
| **Lifecycle** | active |

#### `roles.delete`

| Field | Value |
|-------|-------|
| **Permission UUID** | `perm-uuid-roles-delete` (actual UUID assigned at DB creation) |
| **Module** | rbac |
| **Description** | Allows deleting dynamic roles. Destructive — removes role and all associated permissions. Base roles (superadmin, user) cannot be deleted. |
| **Classification** | admin-critical, destructive |
| **Scope** | system-wide |
| **Default roles** | admin, superadmin |
| **Used by** | admin-panel (role management UI, API) |
| **Blast radius** | system-wide |
| **Approval required** | Yes — Lead |
| **Audit required** | Yes |
| **Reauth required** | Yes |
| **Related routes** | `/admin/roles/:id` (DELETE) |
| **Related functions** | `checkPermission()` |
| **Related events** | `rbac.role_deleted` |
| **Related risks** | RSK-002 (orphaned users after role deletion) |
| **Related tests** | Role deletion allow/deny suite, base role protection tests |
| **Lifecycle** | active |

### User Management Permissions

#### `users.view_all`

| Field | Value |
|-------|-------|
| **Permission UUID** | `perm-uuid-users-view-all` (actual UUID assigned at DB creation) |
| **Module** | user-management |
| **Description** | Allows viewing all user profiles and account data (non-sensitive fields). Intentionally **system-wide** — this is an admin-only permission for the single-tenant admin panel. If multi-tenancy is introduced, this must be re-scoped to tenant-scoped and a separate `users.view_tenant` created. |
| **Classification** | operational |
| **Scope** | system-wide *(see description for multi-tenancy note)* |
| **Default roles** | admin, superadmin |
| **Used by** | admin-panel (user listing) |
| **Blast radius** | medium |
| **Approval required** | No |
| **Audit required** | No |
| **Reauth required** | No |
| **Related routes** | `/admin/users` |
| **Related functions** | `listUsers()` |
| **Related tests** | User listing allow/deny tests |
| **Lifecycle** | active |

#### `users.edit_any`

| Field | Value |
|-------|-------|
| **Module** | user-management |
| **Description** | Allows editing any user's profile data. Does not include role changes or account lifecycle. |
| **Classification** | admin-critical |
| **Scope** | system-wide |
| **Default roles** | admin, superadmin |
| **Used by** | admin-panel (user edit API) |
| **Blast radius** | large |
| **Approval required** | No |
| **Audit required** | Yes |
| **Reauth required** | No |
| **Related routes** | `/admin/users/:id` |
| **Related functions** | `updateUserProfile()` |
| **Related events** | `user.profile_updated` |
| **Related tests** | User edit allow/deny suite |
| **Lifecycle** | active |

#### `users.deactivate`

| Field | Value |
|-------|-------|
| **Module** | user-management |
| **Description** | Allows deactivating user accounts. Reversible but high-impact. |
| **Classification** | admin-critical, destructive |
| **Scope** | system-wide |
| **Default roles** | admin, superadmin |
| **Used by** | admin-panel (account lifecycle) |
| **Blast radius** | large |
| **Approval required** | Yes |
| **Audit required** | Yes |
| **Reauth required** | Yes |
| **Related routes** | `/admin/users/:id/deactivate` |
| **Related events** | `user.account_deactivated` |
| **Related risks** | User access disruption |
| **Related tests** | Deactivation allow/deny suite, reactivation tests |
| **Lifecycle** | active |

#### `users.reactivate`

| Field | Value |
|-------|-------|
| **Module** | user-management |
| **Description** | Allows reactivating deactivated user accounts. Distinct from deactivation — separate authority boundary. |
| **Classification** | admin-critical |
| **Scope** | system-wide |
| **Default roles** | admin, superadmin |
| **Used by** | admin-panel (account lifecycle) |
| **Blast radius** | large |
| **Approval required** | Yes |
| **Audit required** | Yes |
| **Reauth required** | Yes |
| **Related routes** | `/admin/users/:id/reactivate` |
| **Related events** | `user.account_reactivated` |
| **Related risks** | Premature access restoration |
| **Related tests** | Reactivation allow/deny suite, post-reactivation access tests |
| **Lifecycle** | active |

### Admin Permissions

#### `admin.access`

| Field | Value |
|-------|-------|
| **Module** | admin-panel |
| **Description** | Gates access to the entire admin panel. Required for all admin routes. |
| **Classification** | security-critical |
| **Scope** | system-wide |
| **Default roles** | admin, superadmin |
| **Used by** | admin routes (UI + API) |
| **Blast radius** | system-wide |
| **Approval required** | Yes |
| **Audit required** | Yes |
| **Reauth required** | No |
| **Related routes** | `/admin/*` |
| **Related functions** | `requireRole()`, `checkPermission()` |
| **Related risks** | RSK-002 (privilege escalation) |
| **Related tests** | Admin access allow/deny suite |
| **Lifecycle** | active |

#### `admin.config`

| Field | Value |
|-------|-------|
| **Module** | admin-panel |
| **Description** | Allows modifying governed system configuration via admin panel. Does not imply secret/env mutation. |
| **Classification** | admin-critical |
| **Scope** | system-wide |
| **Default roles** | admin, superadmin |
| **Used by** | admin config UI/API |
| **Blast radius** | system-wide |
| **Approval required** | Yes — Lead |
| **Audit required** | Yes |
| **Reauth required** | Yes |
| **Related routes** | `/admin/config` |
| **Related events** | `admin.config_changed` |
| **Related tests** | Config change allow/deny suite |
| **Lifecycle** | active |

### Audit Permissions

#### `audit.view`

| Field | Value |
|-------|-------|
| **Module** | audit-logging |
| **Description** | Allows viewing audit log entries in the admin panel |
| **Classification** | read-only |
| **Scope** | system-wide |
| **Default roles** | admin, superadmin |
| **Used by** | admin-panel (audit viewer) |
| **Blast radius** | small |
| **Approval required** | No |
| **Audit required** | No |
| **Reauth required** | No |
| **Related routes** | `/admin/audit` |
| **Related functions** | `queryAuditLogs()` |
| **Related tests** | Audit view allow/deny tests |
| **Lifecycle** | active |

#### `audit.export`

| Field | Value |
|-------|-------|
| **Module** | audit-logging |
| **Description** | Allows exporting audit log data. Compliance-sensitive — exported data may contain PII. |
| **Classification** | compliance-sensitive |
| **Scope** | system-wide |
| **Default roles** | admin, superadmin |
| **Used by** | admin-panel (export feature) |
| **Blast radius** | medium |
| **Approval required** | Yes |
| **Audit required** | Yes |
| **Reauth required** | No |
| **Related routes** | `/admin/audit/export` |
| **Related tests** | Audit export allow/deny suite |
| **Lifecycle** | active |

### Monitoring Permissions

#### `monitoring.view`

| Field | Value |
|-------|-------|
| **Module** | health-monitoring |
| **Description** | Allows viewing health dashboards and system status |
| **Classification** | read-only |
| **Scope** | system-wide |
| **Default roles** | admin, superadmin |
| **Used by** | admin-panel (dashboard) |
| **Blast radius** | small |
| **Approval required** | No |
| **Audit required** | No |
| **Reauth required** | No |
| **Related routes** | `/admin/monitoring` |
| **Related functions** | `getSystemHealth()` |
| **Related tests** | Monitoring view allow/deny tests |
| **Lifecycle** | active |

#### `monitoring.configure`

| Field | Value |
|-------|-------|
| **Module** | health-monitoring |
| **Description** | Allows configuring alert thresholds and monitoring parameters |
| **Classification** | operational |
| **Scope** | system-wide |
| **Default roles** | admin, superadmin |
| **Used by** | admin-panel (alerts config) |
| **Blast radius** | medium |
| **Approval required** | No |
| **Audit required** | Yes |
| **Reauth required** | No |
| **Related routes** | `/admin/monitoring/config` |
| **Related tests** | Monitoring config allow/deny tests |
| **Lifecycle** | active |

### Job Permissions

#### `jobs.view`

| Field | Value |
|-------|-------|
| **Module** | jobs-and-scheduler |
| **Description** | Allows viewing job status, history, and queue state |
| **Classification** | read-only |
| **Scope** | system-wide |
| **Default roles** | admin, superadmin |
| **Used by** | admin-panel (jobs dashboard) |
| **Blast radius** | small |
| **Approval required** | No |
| **Audit required** | No |
| **Reauth required** | No |
| **Related routes** | `/admin/jobs` |
| **Related tests** | Jobs view allow/deny tests |
| **Lifecycle** | active |

#### `jobs.trigger`

| Field | Value |
|-------|-------|
| **Module** | jobs-and-scheduler |
| **Description** | Allows manually triggering job execution |
| **Classification** | operational |
| **Scope** | system-wide |
| **Default roles** | admin, superadmin |
| **Used by** | admin-panel (manual trigger) |
| **Blast radius** | medium |
| **Approval required** | No |
| **Audit required** | Yes |
| **Reauth required** | No |
| **Related routes** | `/admin/jobs/:id/trigger` |
| **Related events** | `job.started` |
| **Related tests** | Job trigger allow/deny suite |
| **Lifecycle** | active |

#### `jobs.pause`

| Field | Value |
|-------|-------|
| **Module** | jobs-and-scheduler |
| **Description** | Allows pausing scheduled job execution |
| **Classification** | operational |
| **Scope** | system-wide |
| **Default roles** | admin, superadmin |
| **Used by** | admin-panel (job control) |
| **Blast radius** | medium |
| **Approval required** | No |
| **Audit required** | Yes |
| **Reauth required** | No |
| **Related routes** | `/admin/jobs/:id/pause` |
| **Related events** | `job.paused` |
| **Related tests** | Job pause allow/deny suite |
| **Lifecycle** | active |

#### `jobs.resume`

| Field | Value |
|-------|-------|
| **Module** | jobs-and-scheduler |
| **Description** | Allows resuming paused job execution |
| **Classification** | operational |
| **Scope** | system-wide |
| **Default roles** | admin, superadmin |
| **Used by** | admin-panel (job control) |
| **Blast radius** | medium |
| **Approval required** | No |
| **Audit required** | Yes |
| **Reauth required** | No |
| **Related routes** | `/admin/jobs/:id/resume` |
| **Related tests** | Job resume allow/deny suite |
| **Lifecycle** | active |

#### `jobs.retry`

| Field | Value |
|-------|-------|
| **Module** | jobs-and-scheduler |
| **Description** | Allows manually retrying failed jobs |
| **Classification** | operational |
| **Scope** | system-wide |
| **Default roles** | admin, superadmin |
| **Used by** | admin-panel (failure management) |
| **Blast radius** | medium |
| **Approval required** | No |
| **Audit required** | Yes |
| **Reauth required** | No |
| **Related routes** | `/admin/jobs/:id/retry` |
| **Related events** | `job.retry_scheduled` |
| **Related tests** | Job retry allow/deny suite |
| **Lifecycle** | active |

#### `jobs.deadletter.manage`

| Field | Value |
|-------|-------|
| **Module** | jobs-and-scheduler |
| **Description** | Allows managing dead-lettered jobs: replay, discard, investigate |
| **Classification** | admin-critical, destructive |
| **Scope** | system-wide |
| **Default roles** | admin, superadmin |
| **Used by** | admin-panel (dead-letter management) |
| **Blast radius** | large |
| **Approval required** | Yes |
| **Audit required** | Yes |
| **Reauth required** | Yes |
| **Related routes** | `/admin/jobs/deadletter` |
| **Related events** | `job.replayed`, `job.dead_lettered` |
| **Related risks** | RSK-007 (job failure cascade) |
| **Related tests** | Dead-letter management allow/deny suite |
| **Lifecycle** | active |

#### `jobs.emergency`

| Field | Value |
|-------|-------|
| **Module** | jobs-and-scheduler |
| **Description** | Allows activating the job kill switch — halts all job execution system-wide. Emergency use only. |
| **Classification** | security-critical, destructive |
| **Scope** | system-wide |
| **Default roles** | superadmin |
| **Used by** | admin-panel (kill switch UI, API) |
| **Blast radius** | system-wide |
| **Approval required** | Yes — Lead + Security |
| **Audit required** | Yes |
| **Reauth required** | Yes |
| **Related routes** | `/admin/jobs/emergency` |
| **Related functions** | Kill switch function |
| **Related events** | `job.kill_switch_activated` |
| **Related risks** | RSK-007 (job failure cascade) |
| **Related tests** | Kill switch allow/deny suite, emergency flow tests |
| **Lifecycle** | active |

---

## Critical Permission Summary

### Highest-Risk Permissions (Strongest Governance)

| Permission | Classification | Blast Radius | Why Critical |
|-----------|---------------|--------------|--------------|
| `jobs.emergency` | security-critical, destructive | system-wide | Halts all job processing |
| `admin.access` | security-critical | system-wide | Gates entire admin panel |
| `roles.assign` | admin-critical | system-wide | Can escalate privilege |
| `roles.revoke` | admin-critical, destructive | system-wide | Can remove access |
| `admin.config` | admin-critical | system-wide | Can alter system behavior |
| `users.deactivate` | admin-critical, destructive | large | Can remove user access |

### Destructive Permissions (Require Re-Auth)

| Permission | Description |
|-----------|-------------|
| `roles.revoke` | Irreversible access removal |
| `users.deactivate` | Account deactivation |
| `jobs.deadletter.manage` | Dead-letter manipulation |
| `jobs.emergency` | System-wide job halt |

### Quarterly Review Required

All permissions classified as `security-critical`, `admin-critical`, or `destructive` must be reviewed quarterly to confirm:
- Holders still appropriate
- No drift from baseline
- Tests still passing
- Scope still correct

---

## Action Tracker Integration

The following must create Action Tracker entries:

| Trigger | Action Required |
|---------|----------------|
| New critical permission added | Entry with classification + impact assessment |
| Permission removed | Entry with migration confirmation |
| Permission drift detected | Entry with reconciliation plan |
| Permission semantics changed | Entry with consumer impact review |
| Undocumented permission discovered | Entry with investigation + remediation |

---

## Dependencies

- [Authorization Security](../02-security/authorization-security.md)
- [RBAC Module](../04-modules/rbac.md)
- [Change Control Policy](../00-governance/change-control-policy.md) — permission changes follow change control
- [Action Tracker](../06-tracking/action-tracker.md) — permission changes create entries
- [Risk Register](../06-tracking/risk-register.md) — permission-related risks tracked
- [Regression Watchlist](../06-tracking/regression-watchlist.md) — permission fragility monitored

## Related Documents

- [Route Index](route-index.md)
- [Function Index](function-index.md)
- [Event Index](event-index.md)
- [Config Index](config-index.md)
- [Dependency Map](../01-architecture/dependency-map.md)
