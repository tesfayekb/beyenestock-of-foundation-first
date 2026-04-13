import React, { useCallback, useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { NavLink } from '@/components/NavLink';
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
import { Badge } from '@/components/ui/badge';
import { useUserRoles } from '@/hooks/useUserRoles';
import { checkPermission } from '@/lib/rbac';
import { LogOut, Shield, ChevronRight } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import type { NavItem, NavSection } from '@/config/navigation.types';

interface DashboardSidebarProps {
  sections: NavSection[];
  title?: string;
}

export const DashboardSidebar = React.memo(function DashboardSidebar({ sections, title = 'Foundation First' }: DashboardSidebarProps) {
  const { state, isMobile, setOpenMobile } = useSidebar();
  // Item 23: Prevent collapsed icon-mode flash on mobile Sheet
  const collapsed = state === 'collapsed' && !isMobile;
  const location = useLocation();
  const { context, loading } = useUserRoles();
  const { signOut } = useAuth();

  // Close mobile sidebar sheet on navigation
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

      // In collapsed mode, show only parent icon with tooltip — no expand
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
          isActive={isActive}
          renderNavItem={renderNavItem}
        />
      );
    },
    [isItemVisible, isActive, collapsed, renderNavItem],
  );

  return (
    <Sidebar collapsible="icon" variant="inset">
      <SidebarHeader>
        <div className="flex items-center gap-2 px-1 py-1">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <Shield className="h-4 w-4" />
          </div>
          {!collapsed && (
            <span className="truncate font-display text-sm font-semibold">
              {title}
            </span>
          )}
        </div>
      </SidebarHeader>
      <SidebarContent>
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

  // Auto-open when a child becomes active (e.g. navigated via URL)
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
