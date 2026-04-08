# Audit Logging Module

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-08

## Purpose

Records significant actions for security auditing, compliance, operational visibility, and incident investigation.

## Scope

Audit trail for:

- Auth events
- Privileged/admin actions
- Role and permission changes
- Significant data mutations
- Security-sensitive system events

## Enforcement Rule (CRITICAL)

- Required audit events **MUST** be logged
- Bypassing required audit logging is an **INVALID** implementation
- High-risk actions must not silently proceed without required audit coverage

## Key Rules

- All privileged/admin actions must be logged
- All auth lifecycle events must be logged
- All role/permission changes must be logged
- Significant write operations must be logged
- Logs are **append-only** and immutable from application paths
- No update/delete paths from application logic
- Logs must include: actor, action, target, timestamp, IP, user agent
- Logs must **never** include passwords, tokens, MFA secrets, or unnecessary sensitive data
- Retention: minimum 90 days, configurable by policy
- Archive/retention handling must follow policy — no silent removal

## Standardized Action Naming

Action keys must match the canonical event names defined in [Event Index](../07-reference/event-index.md):

- `auth.signed_in`
- `auth.signed_out`
- `auth.password_reset`
- `rbac.role_assigned`
- `rbac.permission_revoked`
- `admin.config_changed`
- `user.account_deactivated`
- `user.account_reactivated`

## Audit Log Schema

```sql
CREATE TABLE public.audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_id UUID REFERENCES auth.users(id),
    action TEXT NOT NULL,
    target_type TEXT,
    target_id UUID,
    metadata JSONB DEFAULT '{}',
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

**Rules:**

- No update/delete paths from app logic
- Read access restricted by `audit.view` permission; export by `audit.export`
- Append-only behavior must be enforced both by application logic AND database permissions/RLS/policies

## Shared Functions

| Function | Purpose | Used By |
|----------|---------|---------|
| `logAuditEvent(params)` | Writes standardized audit entry | All modules |
| `queryAuditLogs(filters)` | Reads logs with filtering | admin-panel |
| `exportAuditLogs(filters)` | Controlled export path | admin-panel |

## Events

| Event | Emitted When | Consumed By |
|-------|-------------|-------------|
| `audit.logged` | New audit entry created | health-monitoring |
| `audit.write_failed` | Audit write fails | health-monitoring, admin alerts |

## Jobs

| Job | Schedule | Purpose |
|-----|----------|---------|
| `audit_cleanup` | Weekly | Archive or apply retention policy safely |

## Permissions

| Permission | Description |
|-----------|-------------|
| `audit.view` | Can view audit logs |
| `audit.export` | Can export audit logs |

**Rule:** `audit.export` is higher sensitivity than `audit.view`

## Failure Handling (CRITICAL)

- For required auditable high-risk actions, failure to record the audit event must either:
  - **Block completion** of the action, OR
  - **Enter a governed async-fallback path** with guaranteed retry, alerting, and reconciliation
- Audit write failures must emit `audit.write_failed` and be surfaced in health monitoring and admin alerts
- Silent audit drops are an **INVALID** implementation

## Dependencies

- [Auth Module](auth.md)
- [Security Architecture](../02-security/security-architecture.md)

## Used By / Affects

admin-panel, health-monitoring, auth, rbac, user-management, api, jobs-and-scheduler.

## Risks If Modified

HIGH — audit logging is a security, compliance, and incident-response control.

## Related Documents

- [Security Architecture](../02-security/security-architecture.md)
- [Admin Panel](admin-panel.md)
- [Health Monitoring](health-monitoring.md)
- [Authorization Security](../02-security/authorization-security.md)
