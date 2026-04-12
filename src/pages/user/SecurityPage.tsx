import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { PageHeader } from '@/components/dashboard/PageHeader';
import { useAuth } from '@/contexts/AuthContext';
import { useMfaFactors, MfaFactor } from '@/hooks/useMfaFactors';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ROUTES } from '@/config/routes';
import { ShieldCheck, ShieldOff, Trash2, KeyRound, Clock, LogIn, AlertTriangle, Lock, Monitor, LogOut } from 'lucide-react';
import { PasswordChangeCard } from '@/components/user/PasswordChangeCard';
import { ReauthDialog } from '@/components/auth/ReauthDialog';
import { ConfirmActionDialog } from '@/components/dashboard/ConfirmActionDialog';
import { apiClient } from '@/lib/api-client';
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

  const handleRequestUnenroll = (factor: MfaFactor) => {
    setFactorToRemove(factor);
    setShowReauth(true);
  };

  const handleReauthVerified = async () => {
    if (!factorToRemove) return;
    const success = await unenrollFactor(factorToRemove.id);
    if (success) {
      await checkMfaStatus();
    }
    setFactorToRemove(null);
  };

  const verifiedFactors = factors.filter((f) => f.status === 'verified');
  const hasMfa = mfaStatus === 'enrolled' || verifiedFactors.length > 0;

  const handleRevokeSessions = async (scope: 'others' | 'global') => {
    setRevoking(true);
    try {
      await apiClient.post('revoke-sessions', { scope });
      if (scope === 'global') {
        toast.success('All sessions revoked. Redirecting to sign-in…');
        setTimeout(() => navigate(ROUTES.SIGN_IN), 1500);
      } else {
        toast.success('Other sessions have been revoked.');
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to revoke sessions';
      toast.error(msg);
    } finally {
      setRevoking(false);
      setShowRevokeOthers(false);
      setShowRevokeAll(false);
    }
  };

  return (
    <>
      <PageHeader title="Security" subtitle="Manage MFA and account security settings" />

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
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* GAP-2: Recovery codes placeholder */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Lock className="h-4 w-4" />
              Recovery Codes
            </CardTitle>
            <CardDescription>
              Backup codes for account recovery when MFA is unavailable
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="rounded-md border border-dashed p-4 text-center">
              <AlertTriangle className="h-5 w-5 text-muted-foreground mx-auto mb-2" />
              <p className="text-sm text-muted-foreground">
                Recovery codes are not yet available. This feature is planned for a future release (DW-008).
              </p>
            </div>
          </CardContent>
        </Card>

        {/* GAP-1: Session info */}
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
        onConfirm={() => handleRevokeSessions('others')}
        loading={revoking}
      />
      <ConfirmActionDialog
        open={showRevokeAll}
        onOpenChange={setShowRevokeAll}
        title="Sign Out Everywhere"
        description="This will terminate ALL your active sessions, including this one. You will be redirected to the sign-in page."
        confirmLabel="Sign Out Everywhere"
        destructive
        onConfirm={() => handleRevokeSessions('global')}
        loading={revoking}
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
