import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ROUTES } from '@/config/routes';
import { supabase } from '@/integrations/supabase/client';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { useToast } from '@/hooks/use-toast';
import { emitMfaEnrolled } from '@/lib/auth-events';

type EnrollStep = 'start' | 'verify' | 'complete';

export default function MfaEnroll() {
  const [step, setStep] = useState<EnrollStep>('start');
  const [qrCode, setQrCode] = useState('');
  const [secret, setSecret] = useState('');
  const [factorId, setFactorId] = useState('');
  const [verifyCode, setVerifyCode] = useState('');
  const [loading, setLoading] = useState(false);
  const { toast } = useToast();
  const { checkMfaStatus } = useAuth();

  const handleEnroll = async () => {
    setLoading(true);
    const { data, error } = await supabase.auth.mfa.enroll({
      factorType: 'totp',
      friendlyName: 'Authenticator App',
    });

    if (error) {
      toast({ variant: 'destructive', title: 'Enrollment failed', description: error.message });
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
    // Emit MFA enrolled event
    const { data: { user } } = await supabase.auth.getUser();
    if (user) {
      emitMfaEnrolled(user.id, 'totp');
    }
    setStep('complete');
    setLoading(false);
    toast({ title: 'MFA enabled', description: 'Your account is now protected with two-factor authentication.' });
  };

  if (step === 'complete') {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background px-4">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <CardTitle className="text-2xl">MFA Enabled</CardTitle>
            <CardDescription>
              Your account is now protected with two-factor authentication. You will need your authenticator app to sign in.
            </CardDescription>
          </CardHeader>
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
