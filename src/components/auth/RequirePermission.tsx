import { useUserRoles } from '@/hooks/useUserRoles';
import { checkPermission } from '@/lib/rbac';
import { LoadingSkeleton } from '@/components/dashboard/LoadingSkeleton';

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
 * During loading, renders a lightweight skeleton inside the already-visible
 * layout shell — prevents the blank content flash on first navigation.
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
    return <LoadingSkeleton variant="page" />;
  }

  const permissions = Array.isArray(permission) ? permission : [permission];
  const hasAll = permissions.every((p) => checkPermission(context, p));

  if (!hasAll) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
}
