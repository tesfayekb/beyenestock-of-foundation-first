import { useLocation, Link } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from '@/components/ui/breadcrumb';
import { Fragment } from 'react';

const labelMap: Record<string, string> = {
  admin: 'Admin',
  users: 'Users',
  roles: 'Roles',
  permissions: 'Permissions',
  audit: 'Audit Logs',
  dashboard: 'Dashboard',
  settings: 'Settings',
  security: 'Security',
};

const UUID_RE = /^[0-9a-f]{8}-/;

/**
 * Resolves a UUID breadcrumb segment to a display name from React Query cache.
 * Read-only — no fetches triggered. Falls back to "Detail" on cache miss.
 */
function resolveEntityName(
  queryClient: ReturnType<typeof useQueryClient>,
  segments: string[],
  uuid: string,
): string {
  // Determine entity type from the segment before the UUID
  const uuidIndex = segments.indexOf(uuid);
  const parentSegment = uuidIndex > 0 ? segments[uuidIndex - 1] : '';

  if (parentSegment === 'users') {
    // useUserDetail uses key ['admin', 'user', id]
    const data = queryClient.getQueryData<any>(['admin', 'user', uuid]);
    if (data?.display_name) return data.display_name;
    if (data?.email) return data.email;
  }

  if (parentSegment === 'roles') {
    // Role detail cache key
    const data = queryClient.getQueryData<any>(['admin', 'role', uuid]);
    if (data?.name) return data.name;
  }

  return 'Detail';
}

export function DashboardBreadcrumbs() {
  const location = useLocation();
  const queryClient = useQueryClient();
  const segments = location.pathname.split('/').filter(Boolean);

  // Suppress single-segment breadcrumbs (root pages like /dashboard, /admin)
  if (segments.length <= 1) return null;

  return (
    <div className="border-b bg-background px-4 py-1.5">
      <Breadcrumb>
        <BreadcrumbList>
          {segments.map((segment, index) => {
            const path = '/' + segments.slice(0, index + 1).join('/');
            const isLast = index === segments.length - 1;
            const isUuid = UUID_RE.test(segment);
            const label = isUuid
              ? resolveEntityName(queryClient, segments, segment)
              : (labelMap[segment] || segment.charAt(0).toUpperCase() + segment.slice(1));

            return (
              <Fragment key={path}>
                {index > 0 && <BreadcrumbSeparator />}
                <BreadcrumbItem>
                  {isLast ? (
                    <BreadcrumbPage>{label}</BreadcrumbPage>
                  ) : (
                    <BreadcrumbLink asChild><Link to={path}>{label}</Link></BreadcrumbLink>
                  )}
                </BreadcrumbItem>
              </Fragment>
            );
          })}
        </BreadcrumbList>
      </Breadcrumb>
    </div>
  );
}
