import React, { useCallback, useEffect } from 'react';
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
import { useUserRoles } from '@/hooks/useUserRoles';
import { checkPermission } from '@/lib/rbac';
import { LogOut, Shield } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import type { NavSection } from '@/config/navigation.types';

interface DashboardSidebarProps {
  sections: NavSection[];
  title?: string;
}

export const DashboardSidebar = React.memo(function DashboardSidebar({ sections, title = 'Foundation First' }: DashboardSidebarProps) {
  const { state, isMobile, setOpenMobile } = useSidebar();
  const collapsed = state === 'collapsed';
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
          const visibleItems = section.items.filter((item) => {
            if (!item.permission) return true;
            if (loading) return false;
            return checkPermission(context, item.permission);
          });

          if (visibleItems.length === 0) return null;

          return (
            <SidebarGroup key={section.label}>
              <SidebarGroupLabel>{section.label}</SidebarGroupLabel>
              <SidebarGroupContent>
                <SidebarMenu>
                  {visibleItems.map((item) => (
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
                          {!collapsed && <span className="truncate">{item.title}</span>}
                        </NavLink>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  ))}
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
