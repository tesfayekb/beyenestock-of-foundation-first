# Audit Logging Module

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-08

## Purpose

Records all significant actions for security auditing and compliance.

## Scope

Audit trail: who did what, when, from where.

## Key Rules

- All write operations must be logged
- All auth events must be logged
- All admin actions must be logged
- Logs are immutable — no updates or deletes
- Logs include: actor, action, target, timestamp, IP, user agent
- Retention: minimum 90 days, configurable

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
-- RLS: admins and moderators can read; no one can update/delete
```

## Shared Functions

| Function | Purpose | Used By |
|----------|---------|---------|
| `logAuditEvent(params)` | Creates an audit log entry | All modules |
| `queryAuditLogs(filters)` | Queries audit logs with filtering | admin-panel |

## Events

| Event | Emitted When | Consumed By |
|-------|-------------|-------------|
| `audit.logged` | New audit entry created | health-monitoring (metrics) |

## Jobs

| Job | Schedule | Purpose |
|-----|----------|---------|
| `audit_cleanup` | Weekly | Archive logs older than retention period |

## Permissions

| Permission | Description |
|-----------|-------------|
| `audit.view` | Can view audit logs |
| `audit.export` | Can export audit logs |

## Dependencies

- [Auth Module](auth.md) — for actor identity

## Used By / Affects

admin-panel, health-monitoring.

## Risks If Modified

HIGH — audit logging is a compliance and security requirement.

## Related Documents

- [Security Architecture](../02-security/security-architecture.md)
- [Admin Panel](admin-panel.md)
- [Health Monitoring](health-monitoring.md)
