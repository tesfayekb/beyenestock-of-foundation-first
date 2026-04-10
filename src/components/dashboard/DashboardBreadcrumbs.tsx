import { useLocation } from 'react-router-dom';
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

export function DashboardBreadcrumbs() {
  const location = useLocation();
  const segments = location.pathname.split('/').filter(Boolean);

  if (segments.length === 0) return null;

  return (
    <Breadcrumb>
      <BreadcrumbList>
        {segments.map((segment, index) => {
          const path = '/' + segments.slice(0, index + 1).join('/');
          const isLast = index === segments.length - 1;
          // Skip UUID-like segments for display, show "Detail" instead
          const isUuid = /^[0-9a-f]{8}-/.test(segment);
          const label = isUuid ? 'Detail' : (labelMap[segment] || segment.charAt(0).toUpperCase() + segment.slice(1));

          return (
            <Fragment key={path}>
              {index > 0 && <BreadcrumbSeparator />}
              <BreadcrumbItem>
                {isLast ? (
                  <BreadcrumbPage>{label}</BreadcrumbPage>
                ) : (
                  <BreadcrumbLink href={path}>{label}</BreadcrumbLink>
                )}
              </BreadcrumbItem>
            </Fragment>
          );
        })}
      </BreadcrumbList>
    </Breadcrumb>
  );
}
