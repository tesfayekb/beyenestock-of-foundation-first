import { useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { supabase } from '@/integrations/supabase/client';
import { useAuth } from '@/contexts/AuthContext';
import { useMfaFactors } from '@/hooks/useMfaFactors';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { useToast } from '@/hooks/use-toast';
import { emitMfaEnrolled } from '@/lib/auth-events';
import { ROUTES } from '@/config/routes';

type EnrollStep = 'start' | 'verify' | 'complete';

type ReturnState = {
  returnTo?: string;
};

export default function MfaEnroll() {
  const [step, setStep] = useState<EnrollStep>('start');
  const [qrCode, setQrCode] = useState('');
  const [secret, setSecret] = useState('');
  const [factorId, setFactorId] = useState('');
  const [verifyCode, setVerifyCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [clearingPending, setClearingPending] = useState(false);
  const { toast } = useToast();
  const { checkMfaStatus, mfaStatus, loading: authLoading } = useAuth();
  const { factors, loading: factorsLoading, unenrollFactor } = useMfaFactors();
  const navigate = useNavigate();
  const location = useLocation();

  const locationState = (location.state ?? {}) as ReturnState;
  const hasReturnTarget = typeof locationState.returnTo === 'string' && locationState.returnTo.length > 0;
  const returnTo = hasReturnTarget ? locationState.returnTo! : ROUTES.SETTINGS_SECURITY;
  const isAdminReturn = returnTo.startsWith(ROUTES.ADMIN);

  const verifiedFactors = useMemo(
    () => factors.filter((factor) => factor.status === 'verified'),
    [factors]
  );
  const unverifiedFactors = useMemo(
    () => factors.filter((factor) => factor.status === 'unverified'),
    [factors]
  );

  const hasVerifiedFactor = mfaStatus === 'enrolled' || verifiedFactors.length > 0;
  const hasPendingUnverifiedFactor = unverifiedFactors.length > 0;

  // Auto-redirect: admin user with MFA already set up
  useEffect(() => {
    if (step === 'complete' || (hasReturnTarget && hasVerifiedFactor && step === 'start')) {
      const timeout = window.setTimeout(() => {
        navigate(returnTo, { replace: true });
      }, 2000);
      return () => window.clearTimeout(timeout);
    }
  }, [hasReturnTarget, hasVerifiedFactor, navigate, returnTo, step]);

  const handleEnroll = async () => {
    setLoading(true);

    // Single-factor policy: unenroll any existing verified factors first
    if (verifiedFactors.length > 0) {
      for (const factor of verifiedFactors) {
        const success = await unenrollFactor(factor.id);
        if (!success) {
          toast({
            variant: 'destructive',
            title: 'Could not replace existing factor',
            description: 'Failed to remove the current authenticator. Please try again.',
          });
          setLoading(false);
          return;
        }
      }
    }

    const { data, error } = await supabase.auth.mfa.enroll({
      factorType: 'totp',
      friendlyName: 'Authenticator App',
    });

    if (error) {
      await checkMfaStatus();
      toast({
        variant: 'destructive',
        title: 'Enrollment failed',
        description: error.message,
      });
      setLoading(false);
      return;
    }

    if (data) {
      setQrCode(data.totp.qr_code);
      setSecret(data.totp.secret);
      setFactorId(data.id);
      setStep('verify');
    }
    setLoading(false);
  };

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    const { data: challengeData, error: challengeError } = await supabase.auth.mfa.challenge({
      factorId,
    });

    if (challengeError) {
      toast({ variant: 'destructive', title: 'Challenge failed', description: challengeError.message });
      setLoading(false);
      return;
    }

    const { error: verifyError } = await supabase.auth.mfa.verify({
      factorId,
      challengeId: challengeData.id,
      code: verifyCode,
    });

    if (verifyError) {
      toast({ variant: 'destructive', title: 'Verification failed', description: verifyError.message });
      setLoading(false);
      return;
    }

    await checkMfaStatus();
    const {
      data: { user },
    } = await supabase.auth.getUser();
    if (user) {
      emitMfaEnrolled(user.id, 'totp');
    }
    setStep('complete');
    setLoading(false);
    toast({ title: 'MFA enabled', description: 'Your account is now protected with two-factor authentication.' });
  };

  const handleClearPendingSetup = async () => {
    if (unverifiedFactors.length === 0) return;

    setClearingPending(true);
    try {
      let failed = false;

      for (const factor of unverifiedFactors) {
        const success = await unenrollFactor(factor.id);
        if (!success) {
          failed = true;
        }
      }

      await checkMfaStatus();

      if (failed) {
        toast({
          variant: 'destructive',
          title: 'Could not fully reset MFA setup',
          description: 'Some incomplete authenticator entries could not be removed. Please try again.',
        });
        return;
      }

      toast({
        title: 'Incomplete MFA setup cleared',
        description: 'You can now start MFA enrollment again.',
      });
    } finally {
      setClearingPending(false);
    }
  };

  const continueLabel = isAdminReturn ? 'Continue to Admin Console' : 'Back to Security Settings';
  const continueDescription = isAdminReturn
    ? 'MFA is already active. Redirecting you back to the admin panel.'
    : 'MFA is already active on this account. You can manage factors from Security Settings.';

  if (authLoading || factorsLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background px-4">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <CardTitle className="text-2xl">Checking MFA status</CardTitle>
            <CardDescription>
              Please wait while we verify your authenticator setup.
            </CardDescription>
          </CardHeader>
        </Card>
      </div>
    );
  }

  if (step === 'complete') {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background px-4">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <CardTitle className="text-2xl">MFA Enabled</CardTitle>
            <CardDescription>
              Your account is now protected with two-factor authentication. Redirecting you now.
            </CardDescription>
          </CardHeader>
          <CardFooter>
            <Button className="w-full" onClick={() => navigate(returnTo, { replace: true })}>
              {continueLabel}
            </Button>
          </CardFooter>
        </Card>
      </div>
    );
  }

  if (hasReturnTarget && hasVerifiedFactor) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background px-4">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <CardTitle className="text-2xl">MFA Already Enabled</CardTitle>
            <CardDescription>{continueDescription}</CardDescription>
          </CardHeader>
          <CardFooter className="flex flex-col gap-3">
            <Button className="w-full" onClick={() => navigate(returnTo, { replace: true })}>
              {continueLabel}
            </Button>
            <Button variant="outline" className="w-full" onClick={() => navigate(ROUTES.SETTINGS_SECURITY)}>
              Manage MFA Settings
            </Button>
          </CardFooter>
        </Card>
      </div>
    );
  }

  if (step === 'start' && hasPendingUnverifiedFactor) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background px-4">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <CardTitle className="text-2xl">Incomplete MFA Setup Found</CardTitle>
            <CardDescription>
              An unfinished authenticator setup already exists for this account. Clear it before starting again.
            </CardDescription>
          </CardHeader>
          <CardFooter className="flex flex-col gap-3">
            <Button className="w-full" onClick={handleClearPendingSetup} disabled={clearingPending}>
              {clearingPending ? 'Clearing setup…' : 'Clear incomplete setup'}
            </Button>
            <Button variant="outline" className="w-full" onClick={() => navigate(returnTo)}>
              {continueLabel}
            </Button>
          </CardFooter>
        </Card>
      </div>
    );
  }

  if (step === 'verify') {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background px-4">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <CardTitle className="text-2xl">Set up authenticator</CardTitle>
            <CardDescription>
              Scan the QR code with your authenticator app (Google Authenticator, Authy, etc.), then enter the 6-digit code.
            </CardDescription>
          </CardHeader>
          <form onSubmit={handleVerify}>
            <CardContent className="space-y-6">
              <div className="flex justify-center">
                <img src={qrCode} alt="MFA QR Code" className="h-48 w-48 rounded-lg border border-border" />
              </div>
              <div className="space-y-1 text-center">
                <p className="text-xs text-muted-foreground">Or enter this secret manually:</p>
                <code className="block rounded bg-muted px-3 py-2 text-xs font-mono break-all select-all">
                  {secret}
                </code>
              </div>
              <div className="space-y-2">
                <Label htmlFor="code">Verification code</Label>
                <Input
                  id="code"
                  type="text"
                  inputMode="numeric"
                  pattern="[0-9]{6}"
                  maxLength={6}
                  placeholder="000000"
                  value={verifyCode}
                  onChange={(e) => setVerifyCode(e.target.value.replace(/\D/g, ''))}
                  required
                  autoComplete="one-time-code"
                  className="text-center text-lg tracking-widest"
                />
              </div>
            </CardContent>
            <CardFooter>
              <Button type="submit" className="w-full" disabled={loading || verifyCode.length !== 6}>
                {loading ? 'Verifying...' : 'Verify and enable MFA'}
              </Button>
            </CardFooter>
          </form>
        </Card>
      </div>
    );
  }

  // Default: no MFA yet — show enrollment CTA
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">Enable two-factor authentication</CardTitle>
          <CardDescription>
            Add an extra layer of security to your account using an authenticator app.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button onClick={handleEnroll} className="w-full" disabled={loading}>
            {loading ? 'Setting up...' : 'Set up authenticator app'}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
