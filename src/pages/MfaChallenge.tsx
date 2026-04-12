import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { supabase } from '@/integrations/supabase/client';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { useToast } from '@/hooks/use-toast';
import { apiClient } from '@/lib/api-client';

export default function MfaChallenge() {
  const [code, setCode] = useState('');
  const [factorId, setFactorId] = useState('');
  const [loading, setLoading] = useState(false);
  const [initializing, setInitializing] = useState(true);
  const [useRecovery, setUseRecovery] = useState(false);
  const [recoveryCode, setRecoveryCode] = useState('');
  const { completeMfaChallenge } = useAuth();
  const navigate = useNavigate();
  const { toast } = useToast();

  useEffect(() => {
    supabase.auth.mfa.listFactors().then(({ data, error }) => {
      if (error || !data) {
        toast({ variant: 'destructive', title: 'MFA error', description: 'Could not load MFA factors.' });
        setInitializing(false);
        return;
      }

      const totpFactor = data.totp.find(f => f.status === 'verified');
      if (totpFactor) {
        setFactorId(totpFactor.id);
      }
      setInitializing(false);
    });
  }, [toast]);

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!factorId) return;
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
      code,
    });

    if (verifyError) {
      toast({ variant: 'destructive', title: 'Invalid code', description: 'Please check your authenticator app and try again.' });
      setCode('');
      setLoading(false);
      return;
    }

    completeMfaChallenge();
    navigate('/', { replace: true });
  };

  const handleRecoveryVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const result = await apiClient.post<{ success: boolean; remaining_codes: number; message: string }>(
        'mfa-recovery-verify',
        { code: recoveryCode.toUpperCase().replace(/\s/g, '') }
      );

      if (result.success) {
        toast({
          title: 'Recovery code accepted',
          description: result.message,
        });
        completeMfaChallenge();
        navigate('/', { replace: true });
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Invalid recovery code';
      toast({ variant: 'destructive', title: 'Recovery failed', description: msg });
      setRecoveryCode('');
      setLoading(false);
    }
  };

  if (initializing) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  if (useRecovery) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background px-4">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <CardTitle className="text-2xl">Use a recovery code</CardTitle>
            <CardDescription>Enter one of your 8-character recovery codes</CardDescription>
          </CardHeader>
          <form onSubmit={handleRecoveryVerify}>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="recovery-code">Recovery code</Label>
                <Input
                  id="recovery-code"
                  type="text"
                  maxLength={8}
                  placeholder="XXXXXXXX"
                  value={recoveryCode}
                  onChange={(e) => setRecoveryCode(e.target.value.replace(/\s/g, '').toUpperCase())}
                  required
                  autoFocus
                  className="text-center text-lg tracking-widest font-mono"
                />
              </div>
            </CardContent>
            <CardFooter className="flex flex-col gap-3">
              <Button type="submit" className="w-full" disabled={loading || recoveryCode.length !== 8}>
                {loading ? 'Verifying...' : 'Verify recovery code'}
              </Button>
              <Button
                type="button"
                variant="ghost"
                className="w-full text-sm"
                onClick={() => { setUseRecovery(false); setRecoveryCode(''); }}
              >
                Back to authenticator code
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
          <CardTitle className="text-2xl">Two-factor authentication</CardTitle>
          <CardDescription>Enter the 6-digit code from your authenticator app</CardDescription>
        </CardHeader>
        <form onSubmit={handleVerify}>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="mfa-code">Authentication code</Label>
              <Input
                id="mfa-code"
                type="text"
                inputMode="numeric"
                pattern="[0-9]{6}"
                maxLength={6}
                placeholder="000000"
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
                required
                autoComplete="one-time-code"
                autoFocus
                className="text-center text-lg tracking-widest"
              />
            </div>
          </CardContent>
          <CardFooter className="flex flex-col gap-3">
            <Button type="submit" className="w-full" disabled={loading || code.length !== 6}>
              {loading ? 'Verifying...' : 'Verify'}
            </Button>
            <Button
              type="button"
              variant="ghost"
              className="w-full text-sm text-muted-foreground"
              onClick={() => setUseRecovery(true)}
            >
              Lost your authenticator? Use a recovery code
            </Button>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
}
