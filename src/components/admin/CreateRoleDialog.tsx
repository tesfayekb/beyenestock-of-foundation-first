/**
 * CreateRoleDialog — dialog for creating a new custom role.
 * Key auto-slugifies from name but remains editable.
 */
import { useState, useEffect, useCallback, useMemo } from 'react';
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
import { apiClient, ApiError } from '@/lib/api-client';
import { ROLES_QUERY_KEY, useRoles } from '@/hooks/useRoles';
import { ROUTES } from '@/config/routes';
import { toast } from 'sonner';
import { ReauthDialog } from '@/components/auth/ReauthDialog';
import { useAuth } from '@/contexts/AuthContext';
import { requiresReauthentication } from '@/lib/auth-guards';

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

interface CreateRolePayload {
  key: string;
  name: string;
  description?: string;
}

interface CreateRoleSuccessResponse {
  id: string;
  key: string;
  name: string;
  correlation_id?: string;
}

interface CreateRoleConflictResponse {
  success: false;
  error: string;
  code: 'CONFLICT';
  correlation_id: string;
}

type CreateRoleResponse = CreateRoleSuccessResponse | CreateRoleConflictResponse;

export function CreateRoleDialog({ open, onOpenChange }: CreateRoleDialogProps) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const { data: roles } = useRoles({ enabled: open });

  const [name, setName] = useState('');
  const [key, setKey] = useState('');
  const [keyManuallyEdited, setKeyManuallyEdited] = useState(false);
  const [description, setDescription] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showReauth, setShowReauth] = useState(false);
  const [pendingPayload, setPendingPayload] = useState<CreateRolePayload | null>(null);

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
    setShowReauth(false);
    setPendingPayload(null);
  }, []);

  const handleOpenChange = useCallback((nextOpen: boolean) => {
    if (!nextOpen) resetForm();
    onOpenChange(nextOpen);
  }, [onOpenChange, resetForm]);

  const normalizedKey = key.trim().toLowerCase();
  const existingRole = useMemo(() => {
    if (!normalizedKey) return null;
    return roles?.find((role) => role.key.toLowerCase() === normalizedKey) ?? null;
  }, [roles, normalizedKey]);

  const keyValid = key.length > 0 && KEY_PATTERN.test(key);
  const canSubmit = name.trim().length > 0 && keyValid && !existingRole && !submitting;

  const createRole = useCallback(async (payload: CreateRolePayload) => {
    setError(null);
    setSubmitting(true);

    try {
      const result = await apiClient.post<CreateRoleResponse>('create-role', payload);

      if ('success' in result && result.success === false) {
        await queryClient.invalidateQueries({ queryKey: ROLES_QUERY_KEY });
        setError(`A role with key "${payload.key}" already exists. Choose another name or open the existing role.`);
        return;
      }

      const created = result as CreateRoleSuccessResponse;
      await queryClient.invalidateQueries({ queryKey: ROLES_QUERY_KEY });
      toast.success(`Role "${created.name}" created`);
      handleOpenChange(false);

      // Navigate to the new role's detail page
      navigate(ROUTES.ADMIN_ROLE_DETAIL.replace(':id', created.id));
    } catch (err: unknown) {
      if (err instanceof ApiError && err.code === 'RECENT_AUTH_REQUIRED') {
        setPendingPayload(payload);
        setShowReauth(true);
        return;
      }

      if (err instanceof ApiError && err.code === 'CONFLICT') {
        await queryClient.invalidateQueries({ queryKey: ROLES_QUERY_KEY });
        setError(`A role with key "${payload.key}" already exists. Choose another name or open the existing role.`);
        return;
      }

      const msg = err instanceof Error ? err.message : 'Failed to create role';
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  }, [handleOpenChange, navigate, queryClient]);

  const openExistingRole = useCallback(() => {
    if (!existingRole) return;
    handleOpenChange(false);
    navigate(ROUTES.ADMIN_ROLE_DETAIL.replace(':id', existingRole.id));
  }, [existingRole, handleOpenChange, navigate]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;

    const payload: CreateRolePayload = {
      key: key.trim(),
      name: name.trim(),
      description: description.trim() || undefined,
    };

    if (existingRole) {
      setError(`A role with key "${existingRole.key}" already exists. Choose another name or open the existing role.`);
      return;
    }

    if (requiresReauthentication(user)) {
      setError(null);
      setPendingPayload(payload);
      setShowReauth(true);
      return;
    }

    await createRole(payload);
  };

  return (
    <>
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

            {!error && existingRole && (
              <Alert variant="destructive">
                <AlertDescription className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                  <span>
                    A role with key "{existingRole.key}" already exists. Choose another name or open the existing role.
                  </span>
                  <Button
                    type="button"
                    variant="link"
                    className="h-auto justify-start p-0"
                    onClick={openExistingRole}
                  >
                    Open role
                  </Button>
                </AlertDescription>
              </Alert>
            )}

            <div className="space-y-2">
              <Label htmlFor="role-name">Role Name</Label>
              <Input
                id="role-name"
                placeholder="e.g. Content Editor"
                value={name}
                onChange={(e) => {
                  if (error) setError(null);
                  setName(e.target.value);
                }}
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
                  if (error) setError(null);
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
                onChange={(e) => {
                  if (error) setError(null);
                  setDescription(e.target.value);
                }}
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

      <ReauthDialog
        open={showReauth}
        onOpenChange={setShowReauth}
        title="Verify before creating a role"
        description="Creating roles requires a recent sign-in. Verify your identity to continue."
        onVerified={() => {
          if (!pendingPayload) return;
          const payload = pendingPayload;
          setPendingPayload(null);
          void createRole(payload);
        }}
      />
    </>
  );
}
