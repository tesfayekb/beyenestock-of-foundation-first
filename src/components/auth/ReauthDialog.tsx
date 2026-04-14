/**
 * ReauthDialog — requires the user to verify identity via email OTP
 * before performing sensitive actions (MFA removal, password change).
 *
 * Uses supabase.auth.reauthenticate() which sends a nonce to the user's email,
 * then supabase.auth.verifyOtp() with type 'email' to confirm.
 */
import { useState } from 'react';
import { supabase } from '@/integrations/supabase/client';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, ShieldCheck } from 'lucide-react';

type ReauthStep = 'idle' | 'sending' | 'awaiting_code' | 'verifying';

interface ReauthDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title?: string;
  description?: string;
  /** Called after successful OTP verification */
  onVerified: () => void;
}

export function ReauthDialog({
  open,
  onOpenChange,
  title = 'Verify Your Identity',
  description = 'For security, we need to confirm your identity before this action. A verification code will be sent to your email.',
  onVerified,
}: ReauthDialogProps) {
  const [step, setStep] = useState<ReauthStep>('idle');
  const [otp, setOtp] = useState('');
  const [error, setError] = useState<string | null>(null);

  const resetState = () => {
    setStep('idle');
    setOtp('');
    setError(null);
  };

  const handleOpenChange = (open: boolean) => {
    if (!open) resetState();
    onOpenChange(open);
  };

  const handleSendCode = async () => {
    setError(null);
    setStep('sending');
    try {
      const { error: reauthError } = await supabase.auth.reauthenticate();
      if (reauthError) {
        setError(reauthError.message);
        setStep('idle');
        return;
      }
      setStep('awaiting_code');
    } catch (err) {
      setError('Failed to send verification code. Please try again.');
      setStep('idle');
    }
  };

  const handleVerify = async () => {
    if (!otp.trim()) return;
    setError(null);
    setStep('verifying');

    try {
      // Get current user email for OTP verification
      const { data: { user } } = await supabase.auth.getUser();
      if (!user?.email) {
        setError('Unable to determine your email address.');
        setStep('awaiting_code');
        return;
      }

      const { error: verifyError } = await supabase.auth.verifyOtp({
        email: user.email,
        token: otp.trim(),
        type: 'email',
      });

      if (verifyError) {
        setError(verifyError.message);
        setStep('awaiting_code');
        return;
      }

      // Success — close dialog and invoke callback
      resetState();
      onOpenChange(false);
      onVerified();
    } catch (err) {
      setError('Verification failed. Please try again.');
      setStep('awaiting_code');
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <ShieldCheck className="h-5 w-5" />
            {title}
          </DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {(step === 'idle' || step === 'sending') && (
            <p className="text-sm text-muted-foreground">
              Click below to receive a one-time code at your registered email address.
            </p>
          )}

          {(step === 'awaiting_code' || step === 'verifying') && (
            <div className="space-y-2">
              <Label htmlFor="reauth-otp">Verification Code</Label>
              <Input
                id="reauth-otp"
                type="text"
                inputMode="numeric"
                placeholder="Enter the code from your email"
                value={otp}
                onChange={(e) => setOtp(e.target.value)}
                maxLength={8}
                autoComplete="one-time-code"
                autoFocus
              />
              <p className="text-xs text-muted-foreground">
                Check your email for the verification code.
              </p>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => handleOpenChange(false)}>
            Cancel
          </Button>

          {(step === 'idle' || step === 'sending') && (
            <Button onClick={handleSendCode} disabled={step === 'sending'}>
              {step === 'sending' && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Send Code
            </Button>
          )}

          {(step === 'awaiting_code' || step === 'verifying') && (
            <Button onClick={handleVerify} disabled={step === 'verifying' || !otp.trim()}>
              {step === 'verifying' && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Verify
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
