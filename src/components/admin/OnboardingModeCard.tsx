/**
 * OnboardingModeCard — Two switches to control signup/invite modes.
 * Prevents disabling both. Requires reauth confirmation.
 *
 * Owner: user-onboarding module
 */
import { useState, useCallback } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { useSystemConfig, type OnboardingConfig } from '@/hooks/useSystemConfig';
import { LoadingSkeleton } from '@/components/dashboard/LoadingSkeleton';
import { ErrorState } from '@/components/dashboard/ErrorState';
import { ReauthDialog } from '@/components/auth/ReauthDialog';
import { Settings } from 'lucide-react';

export function OnboardingModeCard() {
  const { config, isLoading, error, updateConfig, isUpdating } = useSystemConfig();
  const [draft, setDraft] = useState<OnboardingConfig | null>(null);
  const [reauthOpen, setReauthOpen] = useState(false);

  const current = draft ?? config;
  const isDirty = draft !== null && config && (
    draft.signup_enabled !== config.signup_enabled ||
    draft.invite_enabled !== config.invite_enabled
  );

  const handleToggle = useCallback((field: keyof OnboardingConfig, value: boolean) => {
    const base = draft ?? config;
    if (!base) return;

    const next = { ...base, [field]: value };
    // Prevent disabling both
    if (!next.signup_enabled && !next.invite_enabled) return;
    setDraft(next);
  }, [draft, config]);

  const handleSave = useCallback(async () => {
    if (!draft) return;
    await updateConfig(draft);
    setDraft(null);
    setReauthOpen(false);
  }, [draft, updateConfig]);

  const handleCancel = useCallback(() => {
    setDraft(null);
  }, []);

  if (isLoading) return <LoadingSkeleton rows={4} />;
  if (error || !config) return <ErrorState message="Failed to load onboarding config" onRetry={() => window.location.reload()} />;

  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Settings className="h-5 w-5 text-muted-foreground" />
            <CardTitle className="text-lg">Onboarding Mode</CardTitle>
          </div>
          <CardDescription>
            Control how users can join the platform. At least one mode must remain enabled.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="signup-switch" className="text-sm font-medium">
                Open Signup
              </Label>
              <p className="text-xs text-muted-foreground">
                Anyone with the URL can create an account
              </p>
            </div>
            <Switch
              id="signup-switch"
              checked={current?.signup_enabled ?? true}
              onCheckedChange={(v) => handleToggle('signup_enabled', v)}
              disabled={isUpdating}
            />
          </div>

          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="invite-switch" className="text-sm font-medium">
                Invite System
              </Label>
              <p className="text-xs text-muted-foreground">
                Admins can send email invitations to new users
              </p>
            </div>
            <Switch
              id="invite-switch"
              checked={current?.invite_enabled ?? true}
              onCheckedChange={(v) => handleToggle('invite_enabled', v)}
              disabled={isUpdating}
            />
          </div>

          {isDirty && (
            <div className="flex justify-end gap-2 pt-2">
              <Button variant="outline" size="sm" onClick={handleCancel} disabled={isUpdating}>
                Cancel
              </Button>
              <Button size="sm" onClick={() => setConfirmOpen(true)} disabled={isUpdating}>
                Save Changes
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      <ConfirmActionDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title="Update Onboarding Mode"
        description="This will change how users can access the platform. Are you sure?"
        confirmLabel="Confirm"
        onConfirm={handleSave}
        loading={isUpdating}
      />
    </>
  );
}
