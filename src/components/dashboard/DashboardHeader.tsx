import { SidebarTrigger, useSidebar } from '@/components/ui/sidebar';
import { UserMenu } from './UserMenu';
import { ThemeToggle } from './ThemeToggle';
import { DashboardBreadcrumbs } from './DashboardBreadcrumbs';
import { AppBrand } from '@/components/AppBrand';
import { Separator } from '@/components/ui/separator';

export function DashboardHeader() {
  const { state, isMobile } = useSidebar();
  const collapsed = state === 'collapsed' && !isMobile;

  return (
    <>
      <header className="sticky top-0 z-30 flex h-14 shrink-0 items-center gap-2 border-b bg-background px-4">
        <SidebarTrigger className="-ml-1" aria-label="Toggle sidebar" />
        <Separator orientation="vertical" className="mr-2 h-4" />
        {/* On mobile: show full brand (sidebar is hidden). On desktop collapsed: show only the name (icon stays in sidebar rail). */}
        {isMobile ? (
          <AppBrand className="mr-2" />
        ) : collapsed ? (
          <span className="mr-2 truncate font-display text-sm font-semibold">BeyeneQuant</span>
        ) : null}
        <div className="ml-auto flex items-center gap-2">
          <ThemeToggle />
          <UserMenu />
        </div>
      </header>
      <DashboardBreadcrumbs />
    </>
  );
}
