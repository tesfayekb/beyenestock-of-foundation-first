/**
 * InviteUserDialog — Single invite form modal.
 * Real-time email validation: checks if user already exists before allowing send.
 *
 * Owner: user-onboarding module
 */
import { useState, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useInviteUser } from '@/hooks/useInviteUser';
import { useRoles, type RoleListItem } from '@/hooks/useRoles';
import { useDebounce } from '@/hooks/useDebounce';
import { apiClient } from '@/lib/api-client';
import { Loader2, UserCheck, AlertTriangle } from 'lucide-react';

interface InviteUserDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

interface ExistingUserCheck {
  exists: boolean;
  userId?: string;
  displayName?: string;
}

interface ListUsersResponse {
  users: Array<{ id: string; display_name: string | null; email: string | null }>;
  total: number;
  limit: number;
  offset: number;
}

function isValidEmail(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

export function InviteUserDialog({ open, onOpenChange }: InviteUserDialogProps) {
  const [email, setEmail] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [lastName, setLastName] = useState('');
  const [roleId, setRoleId] = useState<string>('');
  const [existingUser, setExistingUser] = useState<ExistingUserCheck | null>(null);
  const [isChecking, setIsChecking] = useState(false);
  const { inviteUser, isInviting } = useInviteUser();
  const { data: rolesData } = useRoles();
  const navigate = useNavigate();

  const roles = (rolesData as RoleListItem[] | undefined)?.filter(r => r.key !== 'superadmin' && r.key !== 'user') ?? [];
  const debouncedEmail = useDebounce(email.trim().toLowerCase(), 500);

  useEffect(() => {
    if (!open || !debouncedEmail || !isValidEmail(debouncedEmail)) {
      setExistingUser(null);
      setIsChecking(false);
      return;
    }

    let cancelled = false;
    setIsChecking(true);

    (async () => {
      try {
        const res = await apiClient.get<ListUsersResponse>('list-users', {
          search: debouncedEmail,
          limit: 1,
          offset: 0,
        });
        if (cancelled) return;

        const match = res.users.find((u) => u.email?.toLowerCase() === debouncedEmail);
        if (match) {
          setExistingUser({
            exists: true,
            userId: match.id,
            displayName: match.display_name ?? undefined,
          });
        } else {
          setExistingUser({ exists: false });
        }
      } catch {
        if (!cancelled) {
          setExistingUser(null);
        }
      } finally {
        if (!cancelled) {
          setIsChecking(false);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [open, debouncedEmail]);

  const resetForm = useCallback(() => {
    setEmail('');
    setDisplayName('');
    setLastName('');
    setRoleId('');
    setExistingUser(null);
    setIsChecking(false);
  }, []);

  const handleClose = useCallback(() => {
    resetForm();
    onOpenChange(false);
  }, [resetForm, onOpenChange]);

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || existingUser?.exists || isChecking) return;

    const success = await inviteUser({
      email: email.trim().toLowerCase(),
      role_id: roleId || undefined,
      display_name: displayName.trim() || undefined,
      last_name: lastName.trim() || undefined,
    });

    if (!success) return;

    resetForm();
    onOpenChange(false);
  }, [email, displayName, lastName, roleId, inviteUser, onOpenChange, existingUser, isChecking, resetForm]);

  const handleGoToUser = useCallback(() => {
    if (existingUser?.userId) {
      handleClose();
      navigate(`/admin/users/${existingUser.userId}`);
    }
  }, [existingUser, handleClose, navigate]);

  const canSubmit = Boolean(email) && isValidEmail(email) && !isChecking && !existingUser?.exists && !isInviting;

  return (
    <Dialog open={open} onOpenChange={(nextOpen) => (nextOpen ? onOpenChange(true) : handleClose())}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Invite User</DialogTitle>
          <DialogDescription>
            Send an email invitation to a new user. They'll receive a link to set up their account.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="invite-email">Email *</Label>
            <div className="relative">
              <Input
                id="invite-email"
                type="email"
                placeholder="user@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="off"
                className={existingUser?.exists ? 'border-destructive pr-10' : isChecking ? 'pr-10' : ''}
              />
              {isChecking && (
                <Loader2 className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 animate-spin text-muted-foreground" />
              )}
              {existingUser?.exists && !isChecking && (
                <UserCheck className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-destructive" />
              )}
            </div>

            {existingUser?.exists && (
              <Alert variant="destructive" className="py-2">
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription className="flex items-center justify-between gap-3">
                  <span className="text-sm">
                    {existingUser.displayName
                      ? `“${existingUser.displayName}” already has an account with this email.`
                      : 'A user with this email already exists.'}
                  </span>
                  <Button type="button" variant="outline" size="sm" className="shrink-0" onClick={handleGoToUser}>
                    Manage Roles
                  </Button>
                </AlertDescription>
              </Alert>
            )}
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label htmlFor="invite-name">First Name</Label>
              <Input
                id="invite-name"
                type="text"
                placeholder="Jane"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                maxLength={255}
                autoComplete="off"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="invite-lastname">Last Name</Label>
              <Input
                id="invite-lastname"
                type="text"
                placeholder="Doe"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                maxLength={255}
                autoComplete="off"
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="invite-role">Additional Role</Label>
            <p className="text-xs text-muted-foreground">
              All users automatically receive the “User” role. Select an additional role to assign.
            </p>
            <Select value={roleId} onValueChange={setRoleId}>
              <SelectTrigger id="invite-role">
                <SelectValue placeholder="None (user role only)" />
              </SelectTrigger>
              <SelectContent>
                {roles.map((role) => (
                  <SelectItem key={role.id} value={role.id}>
                    {role.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={handleClose} disabled={isInviting}>
              Cancel
            </Button>
            <Button type="submit" disabled={!canSubmit}>
              {isInviting ? 'Sending…' : 'Send Invitation'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
