/**
 * OnboardingModeCard — Two switches to control signup/invite modes,
 * plus follow-up settings for pending invitations.
 * Prevents disabling both. Requires reauth confirmation.
 *
 * Owner: user-onboarding module
 */
import { useState, useCallback } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Separator } from '@/components/ui/separator';
import { useSystemConfig, type OnboardingConfig } from '@/hooks/useSystemConfig';
import { LoadingSkeleton } from '@/components/dashboard/LoadingSkeleton';
import { ErrorState } from '@/components/dashboard/ErrorState';
import { ReauthDialog } from '@/components/auth/ReauthDialog';
import { Settings, Clock } from 'lucide-react';

export function OnboardingModeCard() {
  const { config, isLoading, error, updateConfig, isUpdating } = useSystemConfig();
  const [draft, setDraft] = useState<OnboardingConfig | null>(null);
  const [reauthOpen, setReauthOpen] = useState(false);

  const current = draft ?? config;
  const isDirty = draft !== null && config && (
    draft.signup_enabled !== config.signup_enabled ||
    draft.invite_enabled !== config.invite_enabled ||
    draft.followup_days !== config.followup_days ||
    draft.max_followups !== config.max_followups
  );

  const handleToggle = useCallback((field: keyof OnboardingConfig, value: boolean) => {
    const base = draft ?? config;
    if (!base) return;

    const next = { ...base, [field]: value };
    // Prevent disabling both
    if (!next.signup_enabled && !next.invite_enabled) return;
    setDraft(next);
  }, [draft, config]);

  const handleNumberChange = useCallback((field: 'followup_days' | 'max_followups', value: string) => {
    const base = draft ?? config;
    if (!base) return;
    const num = parseInt(value, 10);
    if (isNaN(num) || num < 0) return;
    const clamped = field === 'followup_days'
      ? Math.min(Math.max(num, 1), 30)
      : Math.min(Math.max(num, 0), 10);
    setDraft({ ...base, [field]: clamped });
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

          <Separator />

          {/* Follow-up settings */}
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <Clock className="h-4 w-4 text-muted-foreground" />
              <Label className="text-sm font-medium">Invitation Follow-up</Label>
            </div>
            <p className="text-xs text-muted-foreground">
              Automatically follow up on pending invitations. If invitations are disabled, a signup reminder email is sent instead.
            </p>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label htmlFor="followup-days" className="text-xs text-muted-foreground">
                  Days before follow-up
                </Label>
                <Input
                  id="followup-days"
                  type="number"
                  min={1}
                  max={30}
                  value={current?.followup_days ?? 3}
                  onChange={(e) => handleNumberChange('followup_days', e.target.value)}
                  disabled={isUpdating}
                  className="h-9"
                />
                <p className="text-[11px] text-muted-foreground">Industry standard: 3–7 days</p>
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="max-followups" className="text-xs text-muted-foreground">
                  Maximum follow-ups
                </Label>
                <Input
                  id="max-followups"
                  type="number"
                  min={0}
                  max={10}
                  value={current?.max_followups ?? 2}
                  onChange={(e) => handleNumberChange('max_followups', e.target.value)}
                  disabled={isUpdating}
                  className="h-9"
                />
                <p className="text-[11px] text-muted-foreground">0 = disabled. Standard: 2–3</p>
              </div>
            </div>
          </div>

          {isDirty && (
            <div className="flex justify-end gap-2 pt-2">
              <Button variant="outline" size="sm" onClick={handleCancel} disabled={isUpdating}>
                Cancel
              </Button>
              <Button size="sm" onClick={() => setReauthOpen(true)} disabled={isUpdating}>
                Save Changes
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      <ReauthDialog
        open={reauthOpen}
        onOpenChange={setReauthOpen}
        title="Re-authenticate to Update Config"
        description="Changing onboarding settings is a sensitive action. Please verify your identity."
        onVerified={handleSave}
      />
    </>
  );
}
