import { useState, useEffect } from 'react';
import { PageHeader } from '@/components/dashboard/PageHeader';
import { LoadingSkeleton } from '@/components/dashboard/LoadingSkeleton';
import { ErrorState } from '@/components/dashboard/ErrorState';
import { useProfile } from '@/hooks/useProfile';
import { isValidAvatarUrl } from '@/lib/validation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Save, Mail, Shield } from 'lucide-react';
import { toast } from 'sonner';

export default function ProfilePage() {
  const { profile, isLoading, isError, refetch, updateProfile, isUpdating } = useProfile();

  const [displayName, setDisplayName] = useState('');
  const [avatarUrl, setAvatarUrl] = useState('');

  // Sync form when profile loads
  useEffect(() => {
    if (profile) {
      setDisplayName(profile.display_name ?? '');
      setAvatarUrl(profile.avatar_url ?? '');
    }
  }, [profile]);

  const isDirty =
    profile &&
    (displayName !== (profile.display_name ?? '') ||
      avatarUrl !== (profile.avatar_url ?? ''));

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!isDirty) return;

    // SCENARIO-2: Validate avatar URL scheme
    if (avatarUrl && !isValidAvatarUrl(avatarUrl)) {
      toast.error('Avatar URL must use HTTPS');
      return;
    }

    const payload: Record<string, string | null> = {};
    if (displayName !== (profile?.display_name ?? '')) {
      // SCENARIO-1: Allow clearing display name by sending null
      payload.display_name = displayName.trim() || null;
    }
    if (avatarUrl !== (profile?.avatar_url ?? ''))
      payload.avatar_url = avatarUrl || null;
    updateProfile(payload as { display_name?: string | null; avatar_url?: string | null });
  };

  if (isLoading) return <LoadingSkeleton />;
  if (isError || !profile) return <ErrorState message="Failed to load profile." onRetry={() => refetch()} />;

  return (
    <>
      <PageHeader title="Profile" subtitle="Manage your account information" />

      <div className="grid gap-6 max-w-2xl">
        {/* Read-only account info */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Account Information</CardTitle>
            <CardDescription>These fields are managed by the system</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-3">
              <Mail className="h-4 w-4 text-muted-foreground" />
              <div>
                <p className="text-sm font-medium">{profile.email ?? '—'}</p>
                <p className="text-xs text-muted-foreground">Email address</p>
              </div>
              {profile.email_verified && (
                <Badge variant="outline" className="ml-auto bg-success/10 text-success border-success/20 text-xs">
                  <Shield className="mr-1 h-3 w-3" />
                  Verified
                </Badge>
              )}
            </div>

            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-muted-foreground text-xs">Account status</p>
                <Badge variant={profile.status === 'active' ? 'default' : 'destructive'} className="mt-1 text-xs">
                  {profile.status}
                </Badge>
              </div>
              <div>
                <p className="text-muted-foreground text-xs">Member since</p>
                <p className="mt-1 font-medium">{new Date(profile.created_at).toLocaleDateString()}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Editable profile */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Edit Profile</CardTitle>
            <CardDescription>Update your display name and avatar</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="display_name">Display Name</Label>
                <Input
                  id="display_name"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  placeholder="Your name (leave empty to clear)"
                  maxLength={255}
                />
                <p className="text-xs text-muted-foreground">
                  Leave empty to remove your display name.
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="avatar_url">Avatar URL</Label>
                <Input
                  id="avatar_url"
                  type="url"
                  value={avatarUrl}
                  onChange={(e) => setAvatarUrl(e.target.value)}
                  placeholder="https://example.com/avatar.png"
                />
                <p className="text-xs text-muted-foreground">
                  Must be an HTTPS URL.
                </p>
              </div>

              <Button type="submit" disabled={!isDirty || isUpdating} size="sm">
                <Save className="mr-2 h-4 w-4" />
                {isUpdating ? 'Saving…' : 'Save Changes'}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </>
  );
}
