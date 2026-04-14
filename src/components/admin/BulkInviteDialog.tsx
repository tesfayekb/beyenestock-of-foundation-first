/**
 * BulkInviteDialog — Textarea bulk invite modal (up to 50 emails).
 * Format: email, first name, last name (one per line)
 *
 * Owner: user-onboarding module
 */
import { useState, useCallback, useMemo } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { useInviteUser } from '@/hooks/useInviteUser';
import { useRoles, type RoleListItem } from '@/hooks/useRoles';
import { CheckCircle2, XCircle, AlertTriangle } from 'lucide-react';

interface BulkInviteDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

interface BulkResult {
  succeeded: string[];
  failed: { email: string; reason: string }[];
  skipped_existing: string[];
}

interface ParsedEntry {
  email: string;
  display_name?: string;
  last_name?: string;
}

function parseEntries(text: string): ParsedEntry[] {
  return text
    .split('\n')
    .map(line => {
      const parts = line.split(',').map(p => p.trim());
      const email = parts[0]?.toLowerCase() || '';
      if (!email || !email.includes('@')) return null;
      return {
        email,
        display_name: parts[1] || undefined,
        last_name: parts[2] || undefined,
      };
    })
    .filter((e): e is ParsedEntry => e !== null);
}

export function BulkInviteDialog({ open, onOpenChange }: BulkInviteDialogProps) {
  const [emailsText, setEmailsText] = useState('');
  const [roleId, setRoleId] = useState<string>('');
  const [result, setResult] = useState<BulkResult | null>(null);
  const { bulkInvite, isBulkInviting } = useInviteUser();
  const { data: rolesData } = useRoles();

  const roles = (rolesData as RoleListItem[] | undefined)?.filter(r => r.key !== 'superadmin' && r.key !== 'user') ?? [];

  const entries = useMemo(() => parseEntries(emailsText), [emailsText]);

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    if (entries.length === 0) return;

    try {
      const res = await bulkInvite({
        entries: entries.slice(0, 50),
        role_id: roleId || undefined,
      });

      const data = res as unknown as BulkResult;
      setResult(data);
    } catch {
      // Error handled by useInviteUser's onError (toast).
    }
  }, [entries, roleId, bulkInvite]);

  const handleClose = useCallback(() => {
    setEmailsText('');
    setRoleId('');
    setResult(null);
    onOpenChange(false);
  }, [onOpenChange]);

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Bulk Invite</DialogTitle>
          <DialogDescription>
            Enter one entry per line: email, first name, last name. Only email is required.
          </DialogDescription>
        </DialogHeader>

        {result ? (
          <div className="space-y-3">
            {result.succeeded.length > 0 && (
              <Alert>
                <CheckCircle2 className="h-4 w-4 text-success" />
                <AlertTitle>Sent ({result.succeeded.length})</AlertTitle>
                <AlertDescription className="text-xs mt-1 max-h-24 overflow-y-auto">
                  {result.succeeded.join(', ')}
                </AlertDescription>
              </Alert>
            )}
            {result.skipped_existing.length > 0 && (
              <Alert>
                <AlertTriangle className="h-4 w-4 text-warning" />
                <AlertTitle>Skipped — already registered ({result.skipped_existing.length})</AlertTitle>
                <AlertDescription className="text-xs mt-1 max-h-24 overflow-y-auto">
                  {result.skipped_existing.join(', ')}
                </AlertDescription>
              </Alert>
            )}
            {result.failed.length > 0 && (
              <Alert variant="destructive">
                <XCircle className="h-4 w-4" />
                <AlertTitle>Failed ({result.failed.length})</AlertTitle>
                <AlertDescription className="text-xs mt-1 max-h-24 overflow-y-auto">
                  {result.failed.map(f => `${f.email}: ${f.reason}`).join(', ')}
                </AlertDescription>
              </Alert>
            )}
            <DialogFooter>
              <Button onClick={handleClose}>Done</Button>
            </DialogFooter>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="bulk-emails">Email Addresses *</Label>
              <p className="text-xs text-muted-foreground">
                Enter one email per line (up to 50).
              </p>
              <div className="relative rounded-md border border-input bg-background">
                <div className="flex">
                  {/* Line numbers */}
                  <div
                    className="select-none border-r border-border bg-muted/50 px-2 py-2 text-right font-mono text-xs text-muted-foreground leading-[1.625rem]"
                    aria-hidden="true"
                  >
                    {(emailsText || ' ').split('\n').map((_, i) => (
                      <div key={i}>{i + 1}</div>
                    ))}
                  </div>
                  <Textarea
                    id="bulk-emails"
                    placeholder={"user1@example.com\nuser2@example.com\nuser3@example.com"}
                    value={emailsText}
                    onChange={(e) => setEmailsText(e.target.value)}
                    rows={8}
                    className="border-0 font-mono text-sm leading-[1.625rem] resize-none focus-visible:ring-0 focus-visible:ring-offset-0 rounded-l-none"
                  />
                </div>
              </div>
              <p className="text-xs text-muted-foreground">
                {emails.length} valid email{emails.length !== 1 ? 's' : ''} detected
                {emails.length > 50 && ' — only first 50 will be sent'}
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="bulk-role">Additional role for all invitees</Label>
              <p className="text-xs text-muted-foreground">
                All users automatically receive the "User" role. Select an additional role to assign.
              </p>
              <Select value={roleId} onValueChange={setRoleId}>
                <SelectTrigger id="bulk-role">
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
              <Button type="button" variant="outline" onClick={handleClose} disabled={isBulkInviting}>
                Cancel
              </Button>
              <Button type="submit" disabled={isBulkInviting || emails.length === 0}>
                {isBulkInviting ? 'Sending…' : `Send ${Math.min(emails.length, 50)} Invitation${emails.length !== 1 ? 's' : ''}`}
              </Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}
