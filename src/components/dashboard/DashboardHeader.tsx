import { SidebarTrigger } from '@/components/ui/sidebar';
import { UserMenu } from './UserMenu';
import { ThemeToggle } from './ThemeToggle';
import { DashboardBreadcrumbs } from './DashboardBreadcrumbs';
import { Separator } from '@/components/ui/separator';

export function DashboardHeader() {
  return (
    <header className="sticky top-0 z-30 flex h-14 shrink-0 items-center gap-2 border-b bg-background px-4">
      <SidebarTrigger className="-ml-1" />
      <Separator orientation="vertical" className="mr-2 h-4" />
      <DashboardBreadcrumbs />
      <div className="ml-auto flex items-center gap-2">
        <ThemeToggle />
        <UserMenu />
      </div>
    </header>
  );
}
