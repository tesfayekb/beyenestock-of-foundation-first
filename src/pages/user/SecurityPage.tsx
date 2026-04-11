import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { PageHeader } from '@/components/dashboard/PageHeader';
import { useAuth } from '@/contexts/AuthContext';
import { useMfaFactors, MfaFactor } from '@/hooks/useMfaFactors';
import { ConfirmActionDialog } from '@/components/dashboard/ConfirmActionDialog';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ROUTES } from '@/config/routes';
import { ShieldCheck, ShieldOff, Plus, Trash2, KeyRound, Clock } from 'lucide-react';

export default function SecurityPage() {
  const { mfaStatus, checkMfaStatus } = useAuth();
  const { factors, loading, unenrolling, listFactors, unenrollFactor } = useMfaFactors();
  const navigate = useNavigate();
  const [factorToRemove, setFactorToRemove] = useState<MfaFactor | null>(null);

  useEffect(() => {
    listFactors();
  }, [listFactors]);

  const handleUnenroll = async () => {
    if (!factorToRemove) return;
    const success = await unenrollFactor(factorToRemove.id);
    if (success) {
      setFactorToRemove(null);
      await checkMfaStatus();
    }
  };

  const verifiedFactors = factors.filter((f) => f.status === 'verified');
  const hasMfa = mfaStatus === 'enrolled' || verifiedFactors.length > 0;

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
                  <Plus className="mr-2 h-4 w-4" />
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
                      onClick={() => setFactorToRemove(factor)}
                      disabled={unenrolling}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                ))}

                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => navigate(ROUTES.MFA_ENROLL)}
                >
                  <Plus className="mr-2 h-4 w-4" />
                  Add Another Factor
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Password section — informational */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Password</CardTitle>
            <CardDescription>
              Use the password reset flow to change your password
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button
              variant="outline"
              size="sm"
              onClick={() => navigate(ROUTES.FORGOT_PASSWORD)}
            >
              Reset Password
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Unenroll confirmation dialog */}
      <ConfirmActionDialog
        open={!!factorToRemove}
        onOpenChange={(open) => { if (!open) setFactorToRemove(null); }}
        title="Remove MFA Factor"
        description="This will remove the authenticator app from your account. You'll need to set up a new one to re-enable MFA."
        confirmLabel="Remove"
        destructive
        loading={unenrolling}
        onConfirm={handleUnenroll}
      />
    </>
  );
}
