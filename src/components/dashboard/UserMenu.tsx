import { useAuth } from '@/contexts/AuthContext';
import { useNavigate, useLocation } from 'react-router-dom';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Button } from '@/components/ui/button';
import { UserCircle, ShieldCheck, LogOut, LayoutDashboard, Shield } from 'lucide-react';
import { useUserRoles } from '@/hooks/useUserRoles';
import { checkPermission } from '@/lib/rbac';
import { ROUTES } from '@/config/routes';
import { formatFullName, getInitials } from '@/lib/format-name';

export function UserMenu() {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const { context } = useUserRoles();

  const isInAdmin = location.pathname.startsWith('/admin');
  const hasAdminAccess = checkPermission(context, 'admin.access');

  const firstName = user?.user_metadata?.display_name;
  const lastName = user?.user_metadata?.last_name;
  const displayName = formatFullName(firstName, lastName, user?.email || 'User');
  const initials = getInitials(firstName, lastName);

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" className="relative h-8 w-8 rounded-full">
          <Avatar className="h-8 w-8">
            <AvatarFallback className="bg-primary text-primary-foreground text-xs font-medium">
              {initials}
            </AvatarFallback>
          </Avatar>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent className="w-56" align="end" forceMount>
        <DropdownMenuLabel className="font-normal">
          <div className="flex flex-col space-y-1">
            <p className="text-sm font-medium leading-none truncate">{displayName}</p>
            <p className="text-xs leading-none text-muted-foreground truncate">
              {user?.email}
            </p>
          </div>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={() => navigate(ROUTES.SETTINGS)}>
          <UserCircle className="mr-2 h-4 w-4" />
          Profile
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => navigate(ROUTES.SETTINGS_SECURITY)}>
          <ShieldCheck className="mr-2 h-4 w-4" />
          Security
        </DropdownMenuItem>
        {hasAdminAccess && (
          <>
            <DropdownMenuSeparator />
            {isInAdmin ? (
              <DropdownMenuItem onClick={() => navigate(ROUTES.DASHBOARD)}>
                <LayoutDashboard className="mr-2 h-4 w-4" />
                My Dashboard
              </DropdownMenuItem>
            ) : (
              <DropdownMenuItem onClick={() => navigate(ROUTES.ADMIN)}>
                <Shield className="mr-2 h-4 w-4" />
                Admin Console
              </DropdownMenuItem>
            )}
          </>
        )}
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={() => signOut()}>
          <LogOut className="mr-2 h-4 w-4" />
          Sign Out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
