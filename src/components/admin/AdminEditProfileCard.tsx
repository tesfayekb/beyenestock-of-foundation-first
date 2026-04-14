import { useState, useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { isValidAvatarUrl } from '@/lib/validation';

import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Pencil, Save, X, Loader2 } from 'lucide-react';
import { toast } from 'sonner';

interface AdminEditProfileCardProps {
  userId: string;
  displayName: string | null;
  lastName: string | null;
  avatarUrl: string | null;
  canEdit: boolean;
  isSelf: boolean;
}

export function AdminEditProfileCard({
  userId,
  displayName,
  lastName,
  avatarUrl,
  canEdit,
  isSelf,
}: AdminEditProfileCardProps) {
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [firstName, setFirstName] = useState(displayName ?? '');
  const [lastNameVal, setLastNameVal] = useState(lastName ?? '');
  const [avatar, setAvatar] = useState(avatarUrl ?? '');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!editing) {
      setFirstName(displayName ?? '');
      setLastNameVal(lastName ?? '');
      setAvatar(avatarUrl ?? '');
    }
  }, [displayName, lastName, avatarUrl, editing]);

  const isDirty = firstName !== (displayName ?? '') || lastNameVal !== (lastName ?? '') || avatar !== (avatarUrl ?? '');
  const avatarValid = isValidAvatarUrl(avatar);
  const canSubmit = isDirty && avatarValid && firstName.length <= 255 && lastNameVal.length <= 255 && !submitting;

  const handleCancel = () => {
    setFirstName(displayName ?? '');
    setLastNameVal(lastName ?? '');
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
        display_name: firstName || null,
        last_name: lastNameVal || null,
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
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="admin-edit-first-name">First Name</Label>
          <Input
            id="admin-edit-first-name"
            value={firstName}
            onChange={(e) => setFirstName(e.target.value)}
            maxLength={255}
            placeholder="First name"
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="admin-edit-last-name">Last Name</Label>
          <Input
            id="admin-edit-last-name"
            value={lastNameVal}
            onChange={(e) => setLastNameVal(e.target.value)}
            maxLength={255}
            placeholder="Last name"
          />
        </div>
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
