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

1. **Role assignment** — which roles a user has
2. **Permission assignment** — which permissions a role grants
3. **Policy enforcement** — how access is enforced in APIs and database policies

## Role Structure

```sql
CREATE TYPE public.app_role AS ENUM ('admin', 'moderator', 'user');

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

Authorization must support dynamic permissions.

Recommended structure:

```sql
CREATE TABLE public.permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key TEXT UNIQUE NOT NULL,
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
- Roles are collections of permissions
- Hardcoded permission logic should be minimized and documented
- Permission changes are HIGH impact and must be audited

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

| Capability | admin | moderator | user |
|-----------|-------|-----------|------|
| View own data | ✓ | ✓ | ✓ |
| Edit own data | ✓ | ✓ | ✓ |
| View all users | ✓ | ✓ | ✗ |
| Edit user roles | ✓ | ✗ | ✗ |
| Access admin panel | ✓ | ✗ | ✗ |
| View audit logs | ✓ | ✓ | ✗ |
| Manage system config | ✓ | ✗ | ✗ |

Note: this is an initial baseline only. Long-term enforcement should come from dynamic permissions and `permission-index.md`.

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
