/**
 * InviteUserDialog — Single invite form modal.
 *
 * Owner: user-onboarding module
 */
import { useState, useCallback } from 'react';
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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useInviteUser } from '@/hooks/useInviteUser';
import { useRoles, type RoleListItem } from '@/hooks/useRoles';

interface InviteUserDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function InviteUserDialog({ open, onOpenChange }: InviteUserDialogProps) {
  const [email, setEmail] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [roleId, setRoleId] = useState<string>('');
  const { inviteUser, isInviting } = useInviteUser();
  const { data: rolesData } = useRoles();

  const roles = (rolesData as RoleListItem[] | undefined)?.filter(r => r.key !== 'superadmin' && r.key !== 'user') ?? [];

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;

    try {
      await inviteUser({
        email: email.trim().toLowerCase(),
        role_id: roleId || undefined,
        display_name: displayName.trim() || undefined,
      });

      setEmail('');
      setDisplayName('');
      setRoleId('');
      onOpenChange(false);
    } catch {
      // Error is already handled by useInviteUser's onError (toast).
      // Catch here to prevent unhandled rejection → ErrorBoundary.
    }
  }, [email, displayName, roleId, inviteUser, onOpenChange]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
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
            <Input
              id="invite-email"
              type="email"
              placeholder="user@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="off"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="invite-name">Display Name</Label>
            <Input
              id="invite-name"
              type="text"
              placeholder="Jane Doe"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              maxLength={255}
              autoComplete="off"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="invite-role">Additional Role</Label>
            <p className="text-xs text-muted-foreground">
              All users automatically receive the "User" role. Select an additional role to assign.
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
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={isInviting}>
              Cancel
            </Button>
            <Button type="submit" disabled={isInviting || !email}>
              {isInviting ? 'Sending…' : 'Send Invitation'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
