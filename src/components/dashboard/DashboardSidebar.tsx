import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { NavLink } from '@/components/NavLink';
import { AppBrand } from '@/components/AppBrand';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarFooter,
  useSidebar,
} from '@/components/ui/sidebar';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { useUserRoles } from '@/hooks/useUserRoles';
import { checkPermission } from '@/lib/rbac';
import { getAvailableDashboards } from '@/config/dashboards';
import { LogOut, ChevronRight, ChevronsUpDown, Check } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import type { NavItem, NavSection } from '@/config/navigation.types';

interface DashboardSidebarProps {
  sections: NavSection[];
  title?: string;
}

export const DashboardSidebar = React.memo(function DashboardSidebar({ sections, title = "BeyeneQuant" }: DashboardSidebarProps) {
  const { state, isMobile, setOpenMobile } = useSidebar();
  const collapsed = state === 'collapsed' && !isMobile;
  const location = useLocation();
  const navigate = useNavigate();
  const { context, loading } = useUserRoles();
  const { signOut } = useAuth();

  useEffect(() => {
    if (isMobile) {
      setOpenMobile(false);
    }
  }, [location.pathname, isMobile, setOpenMobile]);

  const isActive = useCallback(
    (path: string) => {
      if (path === '/admin' || path === '/dashboard') {
        return location.pathname === path;
      }
      return location.pathname.startsWith(path);
    },
    [location.pathname],
  );

  const handleSignOut = useCallback(() => {
    signOut();
  }, [signOut]);

  const isItemVisible = useCallback(
    (item: NavItem): boolean => {
      if (!item.permission) return true;
      if (loading) return false;
      return checkPermission(context, item.permission);
    },
    [context, loading],
  );

  const availableDashboards = useMemo(
    () => (context ? getAvailableDashboards(context) : []),
    [context],
  );

  const activeDashboard = useMemo(
    () => availableDashboards.find((d) => location.pathname.startsWith(d.basePath)),
    [availableDashboards, location.pathname],
  );

  const handleDashboardSwitch = useCallback(
    (basePath: string) => {
      navigate(basePath);
    },
    [navigate],
  );

  const renderNavItem = useCallback(
    (item: NavItem) => (
      <SidebarMenuItem key={item.url}>
        <SidebarMenuButton
          asChild
          isActive={isActive(item.url)}
          tooltip={item.title}
        >
          <NavLink
            to={item.url}
            end={item.url === '/admin' || item.url === '/dashboard'}
            className="hover:bg-sidebar-accent/50"
            activeClassName="bg-sidebar-accent text-sidebar-accent-foreground font-medium"
          >
            <item.icon className="h-4 w-4 shrink-0" />
            {!collapsed && (
              <>
                <span className="truncate">{item.title}</span>
                {item.badge != null && (
                  <Badge variant="secondary" className="ml-auto text-xs px-1.5 py-0">
                    {item.badge}
                  </Badge>
                )}
              </>
            )}
          </NavLink>
        </SidebarMenuButton>
      </SidebarMenuItem>
    ),
    [isActive, collapsed],
  );

  const renderCollapsibleItem = useCallback(
    (item: NavItem) => {
      const visibleChildren = (item.children ?? []).filter(isItemVisible);
      if (visibleChildren.length === 0) return null;

      const hasActiveChild = visibleChildren.some((child) => isActive(child.url));

      if (collapsed) {
        return (
          <SidebarMenuItem key={item.url}>
            <SidebarMenuButton
              isActive={hasActiveChild}
              tooltip={item.title}
              asChild
            >
              <NavLink
                to={item.url}
                className="hover:bg-sidebar-accent/50"
                activeClassName="bg-sidebar-accent text-sidebar-accent-foreground font-medium"
              >
                <item.icon className="h-4 w-4 shrink-0" />
              </NavLink>
            </SidebarMenuButton>
          </SidebarMenuItem>
        );
      }

      return (
        <CollapsibleNavGroup
          key={item.url}
          item={item}
          visibleChildren={visibleChildren}
          hasActiveChild={hasActiveChild}
          renderNavItem={renderNavItem}
        />
      );
    },
    [isItemVisible, isActive, collapsed, renderNavItem],
  );

  return (
    <Sidebar collapsible="icon" variant="sidebar">
      <SidebarHeader className="p-0">
        {/* Brand row — h-14 to match topbar */}
        <div className="flex h-14 items-center gap-2 px-3">
          <AppBrand appName={title} showName={!collapsed} />
        </div>

        {/* Dashboard switcher */}
        {availableDashboards.length > 1 && (
          <div className="px-2 pb-2">
            <DropdownMenu>
              {collapsed ? (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <DropdownMenuTrigger asChild>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="w-full"
                        aria-label="Switch dashboard"
                      >
                        {activeDashboard ? (
                          <activeDashboard.icon className="h-4 w-4 shrink-0" />
                        ) : (
                          <span className="h-4 w-4 rounded bg-muted animate-pulse" />
                        )}
                      </Button>
                    </DropdownMenuTrigger>
                  </TooltipTrigger>
                  <TooltipContent side="right">Switch dashboard</TooltipContent>
                </Tooltip>
              ) : (
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="outline"
                    size="default"
                    className="w-full justify-between text-left font-normal border-sidebar-border bg-sidebar-accent/30 hover:bg-sidebar-accent/60 text-sidebar-foreground"
                    aria-label="Switch dashboard"
                  >
                    {activeDashboard ? (
                      <>
                        <activeDashboard.icon className="h-4 w-4 shrink-0" />
                        <span className="ml-2 flex-1 truncate text-sm">{activeDashboard.label}</span>
                        <ChevronsUpDown className="ml-auto h-4 w-4 shrink-0 opacity-70" />
                      </>
                    ) : (
                      <span className="h-4 w-4 rounded bg-muted animate-pulse" />
                    )}
                  </Button>
                </DropdownMenuTrigger>
              )}
              <DropdownMenuContent align="start" className="w-56">
                {availableDashboards.map((d) => (
                  <DropdownMenuItem
                    key={d.id}
                    onClick={() => handleDashboardSwitch(d.basePath)}
                    className="gap-2"
                  >
                    <d.icon className="h-4 w-4 shrink-0" />
                    <span className="flex-1">{d.label}</span>
                    {activeDashboard?.id === d.id && (
                      <Check className="h-4 w-4 shrink-0 text-primary" />
                    )}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        )}
      </SidebarHeader>
      <SidebarContent className="flex-1 overflow-y-auto">
        {sections.map((section) => {
          const visibleItems = section.items.filter(isItemVisible);

          if (visibleItems.length === 0) return null;

          return (
            <SidebarGroup key={section.label}>
              <SidebarGroupLabel>{section.label}</SidebarGroupLabel>
              <SidebarGroupContent>
                <SidebarMenu>
                  {visibleItems.map((item) =>
                    item.children && item.children.length > 0
                      ? renderCollapsibleItem(item)
                      : renderNavItem(item),
                  )}
                </SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>
          );
        })}
      </SidebarContent>
      <SidebarFooter>
        <Separator className="mb-2" />
        <Button
          variant="ghost"
          size={collapsed ? 'icon' : 'default'}
          className="w-full justify-start text-muted-foreground hover:text-foreground"
          onClick={handleSignOut}
        >
          <LogOut className="h-4 w-4 shrink-0" />
          {!collapsed && <span className="ml-2">Sign Out</span>}
        </Button>
      </SidebarFooter>
    </Sidebar>
  );
});

/** Extracted collapsible group to manage its own open state */
function CollapsibleNavGroup({
  item,
  visibleChildren,
  hasActiveChild,
  renderNavItem,
}: {
  item: NavItem;
  visibleChildren: NavItem[];
  hasActiveChild: boolean;
  renderNavItem: (item: NavItem) => React.ReactNode;
}) {
  const [open, setOpen] = useState(hasActiveChild);

  useEffect(() => {
    if (hasActiveChild) setOpen(true);
  }, [hasActiveChild]);

  return (
    <SidebarMenuItem>
      <Collapsible open={open} onOpenChange={setOpen}>
        <CollapsibleTrigger asChild>
          <SidebarMenuButton
            isActive={hasActiveChild}
            tooltip={item.title}
            className="hover:bg-sidebar-accent/50"
          >
            <item.icon className="h-4 w-4 shrink-0" />
            <span className="truncate">{item.title}</span>
            {item.badge != null && (
              <Badge variant="secondary" className="ml-auto text-xs px-1.5 py-0">
                {item.badge}
              </Badge>
            )}
            <ChevronRight
              className={`ml-auto h-4 w-4 shrink-0 transition-transform duration-200 ${open ? 'rotate-90' : ''}`}
            />
          </SidebarMenuButton>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <SidebarMenu className="ml-4 border-l border-sidebar-border pl-2">
            {visibleChildren.map(renderNavItem)}
          </SidebarMenu>
        </CollapsibleContent>
      </Collapsible>
    </SidebarMenuItem>
  );
}
