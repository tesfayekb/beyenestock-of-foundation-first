# Authorization Security

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-13

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
| `admin` | Administrative access — provisioned as a seed role during initial setup |
| `user` | Default role with baseline access |

- Base roles cannot be deleted or modified
- `superadmin` automatically inherits all permissions (including newly created ones) via logical enforcement in `has_permission()` — not via seeded permission rows
- `admin` is provisioned during system bootstrap and receives permissions as defined in [permission-index.md](../07-reference/permission-index.md)

### Dynamic Roles

- The schema is dynamic-role-capable: roles can be created, updated, and deleted at runtime
- Phase 2 delivers the foundation; operational dynamic-role CRUD is deferred to Phase 4
- Dynamic roles are assigned permissions explicitly via privileged server-side RPCs
- Role changes are HIGH impact and must be audited

```sql
CREATE TABLE public.roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key TEXT UNIQUE NOT NULL,           -- e.g. 'admin', 'moderator'
    name TEXT NOT NULL,
    description TEXT,
    is_base BOOLEAN NOT NULL DEFAULT false,
    is_immutable BOOLEAN NOT NULL DEFAULT false,
    is_permission_locked BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE public.user_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    role_id UUID REFERENCES public.roles(id) ON DELETE CASCADE NOT NULL,
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    assigned_by UUID REFERENCES auth.users(id),
    UNIQUE (user_id, role_id)
);
```

**Role Rules:**

- Roles MUST be stored in separate authorization tables
- Roles MUST NOT be stored on users or profile tables
- Role assignment and removal are privileged actions and must be audited
- `is_immutable` protects role identity: `key`, `is_base`, `is_immutable`, `is_permission_locked` cannot be changed for immutable roles
- `is_permission_locked` independently protects permission assignments — a role can be identity-immutable but allow permission changes (admin), or both locked (user), or neither (custom roles)
- User role (`is_permission_locked = true`): no permission modifications by any actor under any circumstances
- Admin role (`is_permission_locked = false`, `is_immutable = true`): superadmin can modify permissions with 5-minute reauth
- Superadmin role: no explicit permission rows; inherits all logically; modification blocked entirely

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
    key TEXT UNIQUE NOT NULL,        -- e.g. 'users.view_all'
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE public.role_permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_id UUID REFERENCES public.roles(id) ON DELETE CASCADE NOT NULL,
    permission_id UUID REFERENCES public.permissions(id) ON DELETE CASCADE NOT NULL,
    UNIQUE (role_id, permission_id)
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
CREATE OR REPLACE FUNCTION public.is_superadmin(_user_id UUID)
RETURNS BOOLEAN
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = public
AS $$
  SELECT EXISTS (
    SELECT 1
    FROM public.user_roles ur
    JOIN public.roles r ON r.id = ur.role_id
    WHERE ur.user_id = _user_id AND r.key = 'superadmin'
  )
$$;

CREATE OR REPLACE FUNCTION public.has_role(_user_id UUID, _role_key TEXT)
RETURNS BOOLEAN
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = public
AS $$
  SELECT EXISTS (
    SELECT 1
    FROM public.user_roles ur
    JOIN public.roles r ON r.id = ur.role_id
    WHERE ur.user_id = _user_id AND r.key = _role_key
  )
$$;

CREATE OR REPLACE FUNCTION public.has_permission(_user_id UUID, _permission_key TEXT)
RETURNS BOOLEAN
LANGUAGE plpgsql STABLE SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  IF _user_id IS NULL OR _permission_key IS NULL THEN
    RETURN false;
  END IF;
  -- Superadmin inherits all permissions logically
  IF public.is_superadmin(_user_id) THEN
    RETURN true;
  END IF;
  RETURN EXISTS (
    SELECT 1
    FROM public.user_roles ur
    JOIN public.role_permissions rp ON rp.role_id = ur.role_id
    JOIN public.permissions p ON p.id = rp.permission_id
    WHERE ur.user_id = _user_id AND p.key = _permission_key
  );
END;
$$;
```

**Permission Check Rules:**

- Use security definer helpers where needed to avoid RLS recursion
- Do not query role tables directly inside RLS policies if recursion risk exists
- Client claims alone must never determine authorization

## Privilege Escalation Prevention

The following controls specifically prevent privilege escalation attacks:

| Attack Vector | Prevention Mechanism | Layer |
|---------------|---------------------|-------|
| Admin assigns themselves superadmin | `assign-role` checks `is_superadmin(actor)` before allowing superadmin assignment | API |
| Admin creates superadmin-level custom role with all permissions | `create-role` requires `is_superadmin(actor)` | API |
| Admin modifies their own role's permissions | `assign-permission-to-role` checks `is_superadmin(actor)` for admin role changes | API |
| User manually assigns `user` role to escalate in future | `assign-role` blocks `user` role with `USER_ROLE_AUTO_ASSIGNED` (409) | API |
| Superadmin removes last superadmin (locking out system) | DB trigger `prevent_last_superadmin_delete` + application-layer count check | DB + API |
| Superadmin removes own superadmin (accidental lockout) | `revoke-role` checks `role.key === 'superadmin' && target === actor` | API + UI |
| Race condition on first signup (two users both get superadmin) | `pg_advisory_xact_lock(42)` serializes the superadmin count check in trigger | DB |

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
| `users.reactivate` | Reactivate user accounts | admin, superadmin |
| `roles.assign` | Assign roles to users | admin, superadmin |
| `roles.revoke` | Revoke roles from users | admin, superadmin |
| `roles.view` | View role assignments and definitions | admin, superadmin |
| `roles.create` | Create dynamic roles | superadmin (requires `is_superadmin()` gate) |
| `roles.delete` | Delete dynamic roles (destructive) | superadmin (requires `is_superadmin()` gate) |
| `permissions.assign` | Assign permissions to roles | admin, superadmin |
| `permissions.revoke` | Revoke permissions from roles | admin, superadmin |
| `admin.access` | Access admin panel | admin, superadmin |
| `admin.config` | Modify system configuration | admin, superadmin |
| `audit.view` | View audit logs | admin, superadmin |
| `audit.export` | Export audit data | admin, superadmin |
| `monitoring.view` | View health dashboards | admin, superadmin |
| `monitoring.configure` | Configure alert thresholds | admin, superadmin |
| `jobs.view` | View job status | admin, superadmin |
| `jobs.trigger` | Manually trigger jobs | admin, superadmin |
| `jobs.pause` | Pause scheduled jobs | admin, superadmin |
| `jobs.resume` | Resume paused jobs | admin, superadmin |
| `jobs.retry` | Retry failed jobs | admin, superadmin |
| `jobs.deadletter.manage` | Manage dead-lettered jobs | admin, superadmin |
| `jobs.emergency` | Emergency job controls (kill switch) | superadmin |

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
