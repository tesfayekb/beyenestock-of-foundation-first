# Authorization Security

> **Owner:** Project Lead | **Last Reviewed:** 2026-04-08

## Purpose

Defines authorization architecture: how permissions are structured, checked, and enforced.

## Scope

RBAC system, RLS policies, permission checking.

## Authorization Model

### Role Structure

```sql
-- Roles stored in separate table (NEVER on profile/users table)
CREATE TYPE public.app_role AS ENUM ('admin', 'moderator', 'user');

CREATE TABLE public.user_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    role app_role NOT NULL,
    UNIQUE (user_id, role)
);
```

### Permission Checking

```sql
-- Security definer function (bypasses RLS, prevents recursion)
CREATE OR REPLACE FUNCTION public.has_role(_user_id UUID, _role app_role)
RETURNS BOOLEAN
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = public
AS $$
  SELECT EXISTS (
    SELECT 1 FROM public.user_roles
    WHERE user_id = _user_id AND role = _role
  )
$$;
```

### RLS Rules

1. Every table MUST have RLS enabled
2. Every table MUST have at least one RLS policy
3. Default deny — no access without explicit policy
4. Use `has_role()` function in policies (never query `user_roles` directly in RLS)
5. Test every policy: ensure users can only access their own data unless explicitly granted

## Permission Levels

| Permission | admin | moderator | user |
|-----------|-------|-----------|------|
| View own data | ✓ | ✓ | ✓ |
| Edit own data | ✓ | ✓ | ✓ |
| View all users | ✓ | ✓ | ✗ |
| Edit user roles | ✓ | ✗ | ✗ |
| Access admin panel | ✓ | ✗ | ✗ |
| View audit logs | ✓ | ✓ | ✗ |
| Manage system config | ✓ | ✗ | ✗ |

## Dependencies

- [Security Architecture](security-architecture.md)
- [Auth Security](auth-security.md)
- [RBAC Module](../04-modules/rbac.md)

## Used By / Affects

Every data-access operation in the application.

## Risks If Changed

HIGH — authorization changes can cause privilege escalation.

## Related Documents

- [Security Architecture](security-architecture.md)
- [RBAC Module](../04-modules/rbac.md)
- [Permission Index](../07-reference/permission-index.md)
