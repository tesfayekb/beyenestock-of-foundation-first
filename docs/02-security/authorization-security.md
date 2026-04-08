# Authorization Security

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-08

## Purpose

Defines the enforced authorization architecture: how roles, permissions, policies, and access checks are structured and enforced.

## Scope

RBAC system, permission model, RLS policies, and authorization checks across all modules.

## Enforcement Rule (CRITICAL)

- Authorization must be enforced **server-side** and at the **data layer**
- UI visibility is **never** sufficient for access control
- Any bypass of RBAC, RLS, or approved authorization checks is an **INVALID** implementation

## Authorization Model

Authorization is enforced in three layers:

1. **User → Roles** — which roles a user has (base or dynamic)
2. **Roles → Permissions** — which permissions a role grants (resource-based)
3. **Permissions → Resources/Actions** — how access is enforced in APIs and database policies

## Role Structure

### Base Roles (IMMUTABLE)

| Role | Description |
|------|-------------|
| `superadmin` | Full access to all current and future permissions |
| `user` | Default role with baseline access |

- Base roles cannot be deleted or modified
- `superadmin` automatically inherits all permissions (including newly created ones)

### Dynamic Roles

- Additional roles can be created, updated, and deleted at runtime
- Dynamic roles are assigned permissions explicitly
- Role changes are HIGH impact and must be audited

```sql
CREATE TABLE public.user_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    role app_role NOT NULL,
    UNIQUE (user_id, role)
);
```

**Role Rules:**

- Roles MUST be stored in separate authorization tables
- Roles MUST NOT be stored on users or profile tables
- Role assignment and removal are privileged actions and must be audited

## Permission Model

Permissions are **resource-based** and **dynamically generated**.

### Permission Format

```
{resource}.{action}
```

Examples: `user.read`, `user.create`, `user.update`, `user.delete`, `audit.view`, `config.update`

### Permission Tables

```sql
CREATE TABLE public.permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key TEXT UNIQUE NOT NULL,        -- e.g. 'user.read'
    description TEXT
);

CREATE TABLE public.role_permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role app_role NOT NULL,
    permission_id UUID REFERENCES public.permissions(id) ON DELETE CASCADE NOT NULL,
    UNIQUE (role, permission_id)
);
```

**Permission Rules:**

- Permissions are the source of truth for capabilities
- Every resource must define permissions at creation
- Roles are collections of permissions
- `superadmin` bypasses permission checks — all permissions are implicitly granted
- Hardcoded permission logic should be minimized and documented
- Permission changes are HIGH impact and must be audited
- All permissions must be indexed in `permission-index.md`

## Permission Evaluation Rules

- `superadmin` bypasses all permission checks — all permissions are implicitly granted
- Explicit permission grants override absence of role assumptions
- Deny-by-default applies when permission is not explicitly granted
- Business logic must not rely on role names (e.g., `'admin'`) for access decisions
- All access decisions should be permission-driven where possible

## Permission Checking

```sql
CREATE OR REPLACE FUNCTION public.has_role(_user_id UUID, _role app_role)
RETURNS BOOLEAN
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = public
AS $$
  SELECT EXISTS (
    SELECT 1
    FROM public.user_roles
    WHERE user_id = _user_id AND role = _role
  )
$$;
```

Optional future extension:

```sql
CREATE OR REPLACE FUNCTION public.has_permission(_user_id UUID, _permission_key TEXT)
RETURNS BOOLEAN
...
```

**Permission Check Rules:**

- Use security definer helpers where needed to avoid RLS recursion
- Do not query role tables directly inside RLS policies if recursion risk exists
- Client claims alone must never determine authorization

## RLS Rules

- Every application table MUST have RLS enabled
- Every application table MUST have explicit policies
- Default deny applies to all data access
- Policies must use approved helper functions where needed
- Policies must be specific — no overly broad grants
- Every policy must be tested for:
  - Own-data access
  - Forbidden cross-user access
  - Authorized elevated access
  - Denied unauthorized access

## Privileged Authorization Actions

The following are HIGH impact and require strict controls:

- Role assignment
- Permission assignment
- Admin panel access
- Audit log access
- System configuration access

**Requirements:**

- Server-side enforcement
- Audit logging
- Restricted to approved admin permissions

## Permission Levels (initial baseline)

> **Note:** This is a baseline summary only. The authoritative source for all permission definitions, scope, classification, and governance is [`permission-index.md`](../07-reference/permission-index.md).
>
> **Provisional:** The `moderator` role is provisional — see OQ-004. Do not implement until OQ-004 is resolved.

| Permission Key | Description | Default Roles |
|----------------|-------------|---------------|
| `users.view_all` | View all user profiles | admin, superadmin |
| `users.edit_any` | Edit any user's profile | admin, superadmin |
| `users.deactivate` | Deactivate user accounts | admin, superadmin |
| `roles.assign` | Assign roles to users | admin, superadmin |
| `roles.revoke` | Revoke roles from users | admin, superadmin |
| `roles.create` | Create dynamic roles | admin, superadmin |
| `roles.delete` | Delete dynamic roles (destructive) | admin, superadmin |
| `admin.access` | Access admin panel | admin, superadmin |
| `admin.config` | Modify system configuration | admin, superadmin |
| `audit.view` | View audit logs | admin, superadmin |
| `audit.export` | Export audit data | admin, superadmin |
| `monitoring.view` | View health dashboards | admin, superadmin |
| `monitoring.configure` | Configure alert thresholds | admin, superadmin |
| `jobs.view` | View job status | admin, superadmin |
| `jobs.manage` | Manage job lifecycle | admin, superadmin |
| `jobs.emergency` | Emergency job controls | admin, superadmin |

Authorization is **permission-driven**, not role-name-driven. Business logic must check permission keys, not role names.

## Audit Requirements

All authorization changes must log:

- Actor
- Target user/role/permission
- Action performed
- Timestamp
- Before/after state where applicable

## Dependencies

- [Security Architecture](security-architecture.md)
- [Auth Security](auth-security.md)
- [RBAC Module](../04-modules/rbac.md)

## Used By / Affects

Every API, RLS policy, admin action, and data-access path.

## Risks If Changed

HIGH — authorization changes can create privilege escalation, data leakage, or admin compromise.

## Related Documents

- [Security Architecture](security-architecture.md)
- [RBAC Module](../04-modules/rbac.md)
- [Permission Index](../07-reference/permission-index.md)
- [Audit Logging](../04-modules/audit-logging.md)
