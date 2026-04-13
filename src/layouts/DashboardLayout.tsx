import { Suspense, useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import { SidebarProvider, SidebarInset } from '@/components/ui/sidebar';
import { DashboardSidebar } from '@/components/dashboard/DashboardSidebar';
import { DashboardHeader } from '@/components/dashboard/DashboardHeader';
import { LoadingSkeleton } from '@/components/dashboard/LoadingSkeleton';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import type { NavSection } from '@/config/navigation.types';

interface DashboardLayoutProps {
  sections: NavSection[];
  /** Label shown in the sidebar header. Defaults to "Foundation First". */
  title?: string;
  /** Optional children to render instead of <Outlet />. Used when layout wraps permission gates. */
  children?: React.ReactNode;
}

const LayoutFallback = () => (
  <div className="p-4 sm:p-6 lg:p-8" role="status" aria-label="Loading content">
    <LoadingSkeleton variant="page" />
    <span className="sr-only">Loading…</span>
  </div>
);

export function DashboardLayout({ sections, title, children }: DashboardLayoutProps) {
  // Clean up body styles that Radix Sheet may leave behind when
  // the layout unmounts during a cross-layout navigation (e.g. admin → user).
  useEffect(() => {
    return () => {
      document.body.style.pointerEvents = '';
      document.body.style.overflow = '';
    };
  }, []);

  return (
    <ErrorBoundary>
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-50 focus:rounded-md focus:bg-primary focus:px-4 focus:py-2 focus:text-primary-foreground focus:shadow-lg"
      >
        Skip to main content
      </a>
      <SidebarProvider>
        <DashboardSidebar sections={sections} title={title} />
        <SidebarInset className="flex flex-col min-w-0">
          <DashboardHeader />
          <main id="main-content" className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8">
            <ErrorBoundary inline>
              <Suspense fallback={<LayoutFallback />}>
                {children ?? <Outlet />}
              </Suspense>
            </ErrorBoundary>
          </main>
        </SidebarInset>
      </SidebarProvider>
    </ErrorBoundary>
  );
}