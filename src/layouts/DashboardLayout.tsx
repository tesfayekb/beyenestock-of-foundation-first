import { Suspense } from 'react';
import { Outlet } from 'react-router-dom';
import { SidebarProvider, SidebarInset } from '@/components/ui/sidebar';
import { DashboardSidebar } from '@/components/dashboard/DashboardSidebar';
import { DashboardHeader } from '@/components/dashboard/DashboardHeader';
import { LoadingSkeleton } from '@/components/dashboard/LoadingSkeleton';
import type { NavSection } from '@/config/navigation.types';

interface DashboardLayoutProps {
  sections: NavSection[];
  /** Label shown in the sidebar header. Defaults to "Foundation First". */
  title?: string;
  /** Optional children to render instead of <Outlet />. Used when layout wraps permission gates. */
  children?: React.ReactNode;
}

const LayoutFallback = () => (
  <div className="p-4 sm:p-6 lg:p-8">
    <LoadingSkeleton variant="page" />
  </div>
);

export function DashboardLayout({ sections, title, children }: DashboardLayoutProps) {
  return (
    <SidebarProvider>
      <DashboardSidebar sections={sections} title={title} />
      <SidebarInset className="flex flex-col min-w-0">
        <DashboardHeader />
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8">
          <Suspense fallback={<LayoutFallback />}>
            {children ?? <Outlet />}
          </Suspense>
        </div>
      </SidebarInset>
    </SidebarProvider>
  );
}
