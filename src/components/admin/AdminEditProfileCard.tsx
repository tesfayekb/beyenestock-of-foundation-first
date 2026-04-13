import { useState, useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { isValidAvatarUrl } from '@/lib/validation';
import { CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Pencil, Save, X, Loader2 } from 'lucide-react';
import { toast } from 'sonner';

interface AdminEditProfileCardProps {
  userId: string;
  displayName: string | null;
  avatarUrl: string | null;
  canEdit: boolean;
  isSelf: boolean;
}

export function AdminEditProfileCard({
  userId,
  displayName,
  avatarUrl,
  canEdit,
  isSelf,
}: AdminEditProfileCardProps) {
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(displayName ?? '');
  const [avatar, setAvatar] = useState(avatarUrl ?? '');
  const [submitting, setSubmitting] = useState(false);

  // Sync when props change (e.g. after refetch)
  useEffect(() => {
    if (!editing) {
      setName(displayName ?? '');
      setAvatar(avatarUrl ?? '');
    }
  }, [displayName, avatarUrl, editing]);

  const isDirty = name !== (displayName ?? '') || avatar !== (avatarUrl ?? '');
  const avatarValid = isValidAvatarUrl(avatar);
  const canSubmit = isDirty && avatarValid && name.length <= 255 && !submitting;

  const handleCancel = () => {
    setName(displayName ?? '');
    setAvatar(avatarUrl ?? '');
    setEditing(false);
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;

    setSubmitting(true);
    try {
      await apiClient.patch('update-profile', {
        user_id: userId,
        display_name: name || null,
        avatar_url: avatar || null,
      });
      await queryClient.invalidateQueries({ queryKey: ['admin', 'user', userId] });
      toast.success('Profile updated');
      setEditing(false);
    } catch (err: any) {
      toast.error('Update failed', { description: err.message });
    } finally {
      setSubmitting(false);
    }
  };

  // Don't show edit button for self or without permission
  const showEditButton = canEdit && !isSelf;

  if (!editing) {
    return showEditButton ? (
      <Button variant="outline" size="sm" onClick={() => setEditing(true)}>
        <Pencil className="mr-2 h-3 w-3" />
        Edit Profile
      </Button>
    ) : null;
  }

  return (
    <form onSubmit={handleSave} className="space-y-4 border-t pt-4">
      <div className="space-y-2">
        <Label htmlFor="admin-edit-name">Display Name</Label>
        <Input
          id="admin-edit-name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          maxLength={255}
          placeholder="Display name"
        />
      </div>
      <div className="space-y-2">
        <Label htmlFor="admin-edit-avatar">Avatar URL</Label>
        <Input
          type="url"
          id="admin-edit-avatar"
          value={avatar}
          onChange={(e) => setAvatar(e.target.value)}
          placeholder="https://example.com/avatar.png"
        />
        {avatar && !avatarValid && (
          <p className="text-xs text-destructive">Avatar URL must use HTTPS</p>
        )}
      </div>
      <div className="flex gap-2">
        <Button type="submit" size="sm" disabled={!canSubmit}>
          {submitting && <Loader2 className="mr-2 h-3 w-3 animate-spin" />}
          <Save className="mr-2 h-3 w-3" />
          Save
        </Button>
        <Button type="button" variant="ghost" size="sm" onClick={handleCancel} disabled={submitting}>
          <X className="mr-2 h-3 w-3" />
          Cancel
        </Button>
      </div>
    </form>
  );
}
