import { useUserRoles } from '@/hooks/useUserRoles';
import { checkPermission } from '@/lib/rbac';

interface RequirePermissionProps {
  /** Single permission key or array of keys (all must be satisfied). */
  permission: string | string[];
  children: React.ReactNode;
  /** Optional fallback to render when permission is absent */
  fallback?: React.ReactNode;
}

/**
 * Hides children if the current user lacks the specified permission(s).
 *
 * During loading, renders null — the surrounding layout shell remains visible.
 * This prevents full-page skeleton flashes when used inside an already-rendered layout.
 *
 * UX convenience ONLY — does NOT enforce access.
 * Server-side enforcement (RLS, edge functions, has_permission()) is authoritative.
 */
export function RequirePermission({
  permission,
  children,
  fallback = null,
}: RequirePermissionProps) {
  const { context, loading } = useUserRoles();

  if (loading) {
    return null;
  }

  const permissions = Array.isArray(permission) ? permission : [permission];
  const hasAll = permissions.every((p) => checkPermission(context, p));

  if (!hasAll) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
}
