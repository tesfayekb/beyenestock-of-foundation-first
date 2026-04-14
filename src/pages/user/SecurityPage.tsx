import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { PageHeader } from '@/components/dashboard/PageHeader';
import { useAuth } from '@/contexts/AuthContext';
import { supabase } from '@/integrations/supabase/client';
import { useMfaFactors, MfaFactor } from '@/hooks/useMfaFactors';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ROUTES } from '@/config/routes';
import { ShieldCheck, ShieldOff, Trash2, KeyRound, Clock, LogIn, Lock, Monitor, LogOut, Copy, RefreshCw, Link2, Unlink } from 'lucide-react';
import { PasswordChangeCard } from '@/components/user/PasswordChangeCard';
import { ReauthDialog } from '@/components/auth/ReauthDialog';
import { ConfirmActionDialog } from '@/components/dashboard/ConfirmActionDialog';
import { apiClient, invalidateTokenCache } from '@/lib/api-client';
import { toast } from 'sonner';

export default function SecurityPage() {
  const { user, mfaStatus, checkMfaStatus } = useAuth();
  const { factors, loading, unenrolling, unenrollFactor } = useMfaFactors();
  const navigate = useNavigate();
  const [factorToRemove, setFactorToRemove] = useState<MfaFactor | null>(null);
  const [showReauth, setShowReauth] = useState(false);
  const [showRevokeOthers, setShowRevokeOthers] = useState(false);
  const [showRevokeAll, setShowRevokeAll] = useState(false);
  const [revoking, setRevoking] = useState(false);

  // Recovery codes state
  const [recoveryCodes, setRecoveryCodes] = useState<string[] | null>(null);
  const [generatingCodes, setGeneratingCodes] = useState(false);
  const [showRegenerateConfirm, setShowRegenerateConfirm] = useState(false);

  // OAuth linking state
  const [linkingProvider, setLinkingProvider] = useState<string | null>(null);

  const handleRequestUnenroll = useCallback((factor: MfaFactor) => {
    setFactorToRemove(factor);
    setShowReauth(true);
  }, []);

  const handleReauthVerified = useCallback(async () => {
    if (!factorToRemove) return;
    const success = await unenrollFactor(factorToRemove.id);
    if (success) {
      await checkMfaStatus();
    }
    setFactorToRemove(null);
  }, [factorToRemove, unenrollFactor, checkMfaStatus]);

  const verifiedFactors = factors.filter((f) => f.status === 'verified');
  const hasMfa = mfaStatus === 'enrolled' || verifiedFactors.length > 0;

  const handleRevokeSessions = useCallback(async (scope: 'others' | 'global') => {
    setRevoking(true);
    try {
      await apiClient.post('revoke-sessions', { scope });
      if (scope === 'global') {
        toast.success('All sessions revoked. Signing out…');
        invalidateTokenCache();
        await supabase.auth.signOut({ scope: 'local' });
        window.location.replace(ROUTES.SIGN_IN);
        return;
      }
      toast.success('Other sessions have been revoked.');
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to revoke sessions';
      toast.error(msg);
    } finally {
      setRevoking(false);
      setShowRevokeOthers(false);
      setShowRevokeAll(false);
    }
  }, []);

  const handleGenerateRecoveryCodes = useCallback(async () => {
    setGeneratingCodes(true);
    try {
      const result = await apiClient.post<{ codes: string[]; message: string }>('mfa-recovery-generate');
      setRecoveryCodes(result.codes);
      toast.success('Recovery codes generated. Save them now — they won\'t be shown again.');
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to generate recovery codes';
      toast.error(msg);
    } finally {
      setGeneratingCodes(false);
      setShowRegenerateConfirm(false);
    }
  }, []);

  const handleCopyRecoveryCodes = useCallback(() => {
    if (!recoveryCodes) return;
    navigator.clipboard.writeText(recoveryCodes.join('\n'));
    toast.success('Recovery codes copied to clipboard');
  }, [recoveryCodes]);

  // OAuth identity helpers
  const identities = user?.identities ?? [];
  const linkedProviders = identities.map(i => i.provider);
  const hasGoogle = linkedProviders.includes('google');
  const canUnlink = identities.length > 1; // must keep at least one auth method

  const handleLinkProvider = useCallback(async (provider: 'google') => {
    setLinkingProvider(provider);
    const { error } = await supabase.auth.linkIdentity({
      provider,
      options: { redirectTo: `${window.location.origin}/settings/security` },
    });
    if (error) {
      toast.error(error.message);
      setLinkingProvider(null);
    }
  }, []);

  const handleUnlinkProvider = useCallback(async (identityId: string, provider: string) => {
    if (!canUnlink) {
      toast.error('Cannot unlink — you must keep at least one authentication method.');
      return;
    }
    setLinkingProvider(provider);
    const { error } = await supabase.auth.unlinkIdentity({ provider, id: identityId } as any);
    if (error) {
      toast.error(error.message);
    } else {
      toast.success(`${provider} account unlinked.`);
    }
    setLinkingProvider(null);
  }, [canUnlink]);

  const handleRevokeOthers = useCallback(() => handleRevokeSessions('others'), [handleRevokeSessions]);
  const handleRevokeAll = useCallback(() => handleRevokeSessions('global'), [handleRevokeSessions]);

  return (
    <>
      <PageHeader title="Security" subtitle="Manage MFA, recovery codes, linked accounts, and session security" />

      <div className="grid gap-6 max-w-2xl">
        {/* MFA Status */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-base flex items-center gap-2">
                  <KeyRound className="h-4 w-4" />
                  Multi-Factor Authentication
                </CardTitle>
                <CardDescription className="mt-1">
                  Add an extra layer of security to your account
                </CardDescription>
              </div>
              <Badge
                variant="outline"
                className={hasMfa
                  ? 'bg-success/10 text-success border-success/20'
                  : 'bg-warning/10 text-warning border-warning/20'
                }
              >
                {hasMfa ? (
                  <><ShieldCheck className="mr-1 h-3 w-3" /> Enabled</>
                ) : (
                  <><ShieldOff className="mr-1 h-3 w-3" /> Disabled</>
                )}
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {loading ? (
              <p className="text-sm text-muted-foreground">Loading factors…</p>
            ) : verifiedFactors.length === 0 ? (
              <div className="rounded-md border border-dashed p-4 text-center">
                <p className="text-sm text-muted-foreground mb-3">
                  No authenticator app configured. Enable TOTP to secure your account.
                </p>
                <Button size="sm" onClick={() => navigate(ROUTES.MFA_ENROLL)}>
                  Set Up TOTP
                </Button>
              </div>
            ) : (
              <div className="space-y-3">
                {verifiedFactors.map((factor) => (
                  <div
                    key={factor.id}
                    className="flex items-center justify-between rounded-md border p-3"
                  >
                    <div className="flex items-center gap-3">
                      <ShieldCheck className="h-5 w-5 text-success" />
                      <div>
                        <p className="text-sm font-medium">
                          {factor.friendly_name || 'Authenticator App'}
                        </p>
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                          <Clock className="h-3 w-3" />
                          Added {new Date(factor.created_at).toLocaleDateString()}
                        </div>
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 text-destructive hover:text-destructive"
                      onClick={() => handleRequestUnenroll(factor)}
                      disabled={unenrolling}
                      aria-label={`Remove MFA factor ${factor.friendly_name ?? factor.id}`}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Recovery Codes (DW-008) */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Lock className="h-4 w-4" />
              Recovery Codes
            </CardTitle>
            <CardDescription>
              Backup codes for account recovery when your authenticator is unavailable
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {recoveryCodes ? (
              <div className="space-y-3">
                <div className="rounded-md border bg-muted p-4">
                  <div className="grid grid-cols-2 gap-2 font-mono text-sm">
                    {recoveryCodes.map((code, i) => (
                      <div key={i} className="rounded bg-background px-2 py-1 text-center">
                        {code}
                      </div>
                    ))}
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button size="sm" variant="outline" onClick={handleCopyRecoveryCodes}>
                    <Copy className="mr-2 h-3 w-3" />
                    Copy all
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => setShowRegenerateConfirm(true)}>
                    <RefreshCw className="mr-2 h-3 w-3" />
                    Regenerate
                  </Button>
                </div>
                <p className="text-xs text-destructive font-medium">
                  Save these codes in a safe place. They will not be shown again after you leave this page.
                </p>
              </div>
            ) : (
              <div className="rounded-md border border-dashed p-4 text-center space-y-3">
                <p className="text-sm text-muted-foreground">
                  {hasMfa
                    ? 'Generate backup codes in case you lose access to your authenticator app. Each code can only be used once.'
                    : 'Enable MFA first to generate recovery codes.'}
                </p>
                <Button
                  size="sm"
                  onClick={handleGenerateRecoveryCodes}
                  disabled={!hasMfa || generatingCodes}
                >
                  {generatingCodes ? 'Generating…' : 'Generate Recovery Codes'}
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Linked Accounts (DW-001, DW-002) */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Link2 className="h-4 w-4" />
              Linked Accounts
            </CardTitle>
            <CardDescription>
              Connect external accounts for faster sign-in
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {/* Google */}
            <div className="flex items-center justify-between rounded-md border p-3">
              <div className="flex items-center gap-3">
                <svg className="h-5 w-5" viewBox="0 0 24 24">
                  <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4"/>
                  <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                  <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                  <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
                </svg>
                <div>
                  <p className="text-sm font-medium">Google</p>
                  <p className="text-xs text-muted-foreground">
                    {hasGoogle ? 'Connected' : 'Not connected'}
                  </p>
                </div>
              </div>
              {hasGoogle ? (
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={!canUnlink || linkingProvider === 'google'}
                  onClick={() => {
                    const identity = identities.find(i => i.provider === 'google');
                    if (identity) handleUnlinkProvider(identity.id, 'google');
                  }}
                >
                  <Unlink className="mr-1 h-3 w-3" />
                  Unlink
                </Button>
              ) : (
                <Button
                  size="sm"
                  variant="outline"
                  disabled={!!linkingProvider}
                  onClick={() => handleLinkProvider('google')}
                >
                  <Link2 className="mr-1 h-3 w-3" />
                  {linkingProvider === 'google' ? 'Redirecting…' : 'Link'}
                </Button>
              )}
            </div>

            {!canUnlink && identities.length === 1 && (
              <p className="text-xs text-muted-foreground">
                You must keep at least one authentication method linked.
              </p>
            )}
          </CardContent>
        </Card>

        {/* Session info */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <LogIn className="h-4 w-4" />
              Session Information
            </CardTitle>
            <CardDescription>
              Details about your current session
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-muted-foreground text-xs">Last sign-in</p>
                <p className="mt-1 font-medium">
                  {user?.last_sign_in_at
                    ? new Date(user.last_sign_in_at).toLocaleString()
                    : '—'}
                </p>
              </div>
              <div>
                <p className="text-muted-foreground text-xs">Auth provider</p>
                <p className="mt-1 font-medium">
                  {user?.app_metadata?.provider ?? 'email'}
                </p>
              </div>
              <div>
                <p className="text-muted-foreground text-xs">Assurance level</p>
                <Badge variant="outline" className="mt-1 text-xs">
                  {mfaStatus === 'enrolled' ? 'AAL2 (MFA)' : 'AAL1 (Password)'}
                </Badge>
              </div>
              <div>
                <p className="text-muted-foreground text-xs">Account created</p>
                <p className="mt-1 font-medium">
                  {user?.created_at
                    ? new Date(user.created_at).toLocaleDateString()
                    : '—'}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Session Management (DW-019) */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Monitor className="h-4 w-4" />
              Active Sessions
            </CardTitle>
            <CardDescription>
              Manage your active sessions across devices
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex flex-col gap-3 sm:flex-row">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowRevokeOthers(true)}
                disabled={revoking}
              >
                <LogOut className="mr-2 h-4 w-4" />
                Sign out other devices
              </Button>
              <Button
                variant="destructive"
                size="sm"
                onClick={() => setShowRevokeAll(true)}
                disabled={revoking}
              >
                <LogOut className="mr-2 h-4 w-4" />
                Sign out everywhere
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">
              "Sign out other devices" keeps your current session. "Sign out everywhere" terminates all sessions including this one.
            </p>
          </CardContent>
        </Card>

        {/* Password change */}
        <PasswordChangeCard />
      </div>

      {/* Session revocation confirmations */}
      <ConfirmActionDialog
        open={showRevokeOthers}
        onOpenChange={setShowRevokeOthers}
        title="Sign Out Other Devices"
        description="This will terminate all your other active sessions. Your current session will remain active."
        confirmLabel="Sign Out Others"
        destructive={false}
        onConfirm={handleRevokeOthers}
        loading={revoking}
      />
      <ConfirmActionDialog
        open={showRevokeAll}
        onOpenChange={setShowRevokeAll}
        title="Sign Out Everywhere"
        description="This will terminate ALL your active sessions, including this one. You will be redirected to the sign-in page."
        confirmLabel="Sign Out Everywhere"
        destructive
        onConfirm={handleRevokeAll}
        loading={revoking}
      />

      {/* Recovery code regeneration confirm */}
      <ConfirmActionDialog
        open={showRegenerateConfirm}
        onOpenChange={setShowRegenerateConfirm}
        title="Regenerate Recovery Codes"
        description="This will invalidate all existing recovery codes and generate new ones. Any unused codes will stop working."
        confirmLabel="Regenerate"
        destructive
        onConfirm={handleGenerateRecoveryCodes}
        loading={generatingCodes}
      />

      {/* Re-authentication dialog for MFA removal */}
      <ReauthDialog
        open={showReauth}
        onOpenChange={(open) => {
          setShowReauth(open);
          if (!open) setFactorToRemove(null);
        }}
        title="Verify Identity to Remove MFA"
        description="Removing MFA is a critical security action. Please verify your identity by entering the code sent to your email."
        onVerified={handleReauthVerified}
      />
    </>
  );
}
