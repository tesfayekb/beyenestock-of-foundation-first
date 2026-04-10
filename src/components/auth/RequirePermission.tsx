import { useUserRoles } from '@/hooks/useUserRoles';
import { checkPermission } from '@/lib/rbac';
import { LoadingSkeleton } from '@/components/dashboard/LoadingSkeleton';

interface RequirePermissionProps {
  permission: string;
  children: React.ReactNode;
  /** Optional fallback to render when permission is absent */
  fallback?: React.ReactNode;
}

/**
 * Hides children if the current user lacks the specified permission.
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

  if (!checkPermission(context, permission)) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
}
