/**
 * CreateRoleDialog — dialog for creating a new custom role.
 * Key auto-slugifies from name but remains editable.
 */
import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2 } from 'lucide-react';
import { apiClient } from '@/lib/api-client';
import { ROLES_QUERY_KEY } from '@/hooks/useRoles';
import { ROUTES } from '@/config/routes';
import { toast } from 'sonner';

function slugify(name: string): string {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9\s_-]/g, '')
    .replace(/\s+/g, '_')
    .replace(/^[^a-z]+/, '') // must start with letter
    .slice(0, 50);
}

const KEY_PATTERN = /^[a-z][a-z0-9_-]*$/;

interface CreateRoleDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CreateRoleDialog({ open, onOpenChange }: CreateRoleDialogProps) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [name, setName] = useState('');
  const [key, setKey] = useState('');
  const [keyManuallyEdited, setKeyManuallyEdited] = useState(false);
  const [description, setDescription] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Auto-slugify key from name unless user has manually edited it
  useEffect(() => {
    if (!keyManuallyEdited) {
      setKey(slugify(name));
    }
  }, [name, keyManuallyEdited]);

  const resetForm = useCallback(() => {
    setName('');
    setKey('');
    setKeyManuallyEdited(false);
    setDescription('');
    setError(null);
    setSubmitting(false);
  }, []);

  const handleOpenChange = (open: boolean) => {
    if (!open) resetForm();
    onOpenChange(open);
  };

  const keyValid = key.length > 0 && KEY_PATTERN.test(key);
  const canSubmit = name.trim().length > 0 && keyValid && !submitting;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;

    setError(null);
    setSubmitting(true);

    try {
      const result = await apiClient.post<{ id: string; key: string; name: string }>(
        'create-role',
        { key, name: name.trim(), description: description.trim() || undefined },
      );

      queryClient.invalidateQueries({ queryKey: ROLES_QUERY_KEY });
      toast.success(`Role "${result.name}" created`);
      handleOpenChange(false);

      // Navigate to the new role's detail page
      navigate(ROUTES.ADMIN_ROLE_DETAIL.replace(':id', result.id));
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to create role';
      if (msg.includes('re-authenticate') || msg.includes('RECENT_AUTH_REQUIRED')) {
        setError('Your session is too old for this action. Please sign out and sign back in, then try again.');
      } else {
        setError(msg);
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Create Role</DialogTitle>
          <DialogDescription>
            Create a new custom role. You can assign permissions after creation.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4 py-2">
          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <div className="space-y-2">
            <Label htmlFor="role-name">Role Name</Label>
            <Input
              id="role-name"
              placeholder="e.g. Content Editor"
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={100}
              autoFocus
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="role-key">Key</Label>
            <Input
              id="role-key"
              placeholder="e.g. content_editor"
              value={key}
              onChange={(e) => {
                setKey(e.target.value);
                setKeyManuallyEdited(true);
              }}
              maxLength={50}
              className="font-mono text-sm"
            />
            {key && !keyValid && (
              <p className="text-xs text-destructive">
                Key must start with a lowercase letter and contain only lowercase letters, numbers, underscores, and hyphens.
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="role-description">Description (optional)</Label>
            <Textarea
              id="role-description"
              placeholder="Brief description of this role's purpose"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              maxLength={500}
              rows={2}
            />
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => handleOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={!canSubmit}>
              {submitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Create Role
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
