/**
 * ReauthDialog — requires the user to verify identity before sensitive actions.
 *
 * Supports two methods:
 * 1. Email sign-in OTP (supabase.auth.signInWithOtp → verifyOtp)
 * 2. TOTP Authenticator App (if user has enrolled MFA factor)
 *
 * Features:
 * - Resend code on token expired/invalid errors
 * - Method switching between email and authenticator
 * - Shared across all admin/user pages needing reauth
 *
 * Owner: auth module
 */
import { useState, useEffect, useRef } from 'react';
import { supabase } from '@/integrations/supabase/client';
import { invalidateTokenCache } from '@/lib/api-client';
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
import { Loader2, ShieldCheck, Mail, Smartphone, RefreshCw } from 'lucide-react';
import TurnstileWidget, { type TurnstileWidgetHandle } from '@/components/auth/TurnstileWidget';
import { DEV_MODE } from '@/lib/dev-mode';

type ReauthStep = 'idle' | 'sending' | 'awaiting_code' | 'verifying';
type ReauthMethod = 'email' | 'totp';

interface ReauthDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title?: string;
  description?: string;
  /** Called after successful verification */
  onVerified: () => void;
}

function normalizeOtp(value: string, maxLength: number) {
  return value.replace(/\D/g, '').slice(0, maxLength);
}

export function ReauthDialog({
  open,
  onOpenChange,
  title = 'Verify Your Identity',
  description = 'For security, we need to confirm your identity before this action.',
  onVerified,
}: ReauthDialogProps) {
  const [step, setStep] = useState<ReauthStep>('idle');
  const [method, setMethod] = useState<ReauthMethod>('email');
  const [otp, setOtp] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [hasTotpFactor, setHasTotpFactor] = useState(false);
  const [totpFactorId, setTotpFactorId] = useState<string | null>(null);
  const [isTokenError, setIsTokenError] = useState(false);
  const turnstileRef = useRef<TurnstileWidgetHandle>(null);

  useEffect(() => {
    if (!open) return;
    (async () => {
      const { data } = await supabase.auth.mfa.listFactors();
      const verified = data?.totp?.filter((factor) => factor.status === 'verified') ?? [];
      setHasTotpFactor(verified.length > 0);
      setTotpFactorId(verified[0]?.id ?? null);
    })();
  }, [open]);

  const resetState = () => {
    setStep('idle');
    setOtp('');
    setError(null);
    setMethod('email');
    setIsTokenError(false);
  };

  const handleOpenChange = (nextOpen: boolean) => {
    if (!nextOpen) resetState();
    onOpenChange(nextOpen);
  };

  // DEV_MODE: auto-verify immediately when dialog opens
  useEffect(() => {
    if (DEV_MODE && open) {
      console.warn('[ReauthDialog] Dev mode — auto-verifying');
      const timer = setTimeout(() => {
        onOpenChange(false);
        onVerified();
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [open, onOpenChange, onVerified]);

  const getCurrentUserEmail = async () => {
    const { data: { user } } = await supabase.auth.getUser();
    return user?.email ?? null;
  };

  const handleSendCode = async () => {
    setError(null);
    setIsTokenError(false);
    setStep('sending');

    try {
      const email = await getCurrentUserEmail();
      if (!email) {
        setError('Unable to determine your email address.');
        setStep('idle');
        return;
      }

      // Reset turnstile to get a fresh token, then execute
      let captchaToken: string | undefined;
      try {
        turnstileRef.current?.reset();
        captchaToken = await turnstileRef.current?.execute();
      } catch (captchaErr) {
        setError(captchaErr instanceof Error ? captchaErr.message : 'Captcha verification failed.');
        setStep('idle');
        return;
      }

      const { error: sendError } = await supabase.auth.signInWithOtp({
        email,
        options: {
          shouldCreateUser: false,
          captchaToken,
        },
      });

      if (sendError) {
        setError(sendError.message);
        setStep('idle');
        turnstileRef.current?.reset();
        return;
      }

      setStep('awaiting_code');
    } catch {
      setError('Failed to send verification code. Please try again.');
      setStep('idle');
      turnstileRef.current?.reset();
    }
  };

  const handleResendCode = async () => {
    setOtp('');
    setError(null);
    setIsTokenError(false);
    await handleSendCode();
  };

  const handleVerifyEmail = async () => {
    const code = otp.trim();
    if (!code) return;

    setError(null);
    setIsTokenError(false);
    setStep('verifying');

    try {
      const email = await getCurrentUserEmail();
      if (!email) {
        setError('Unable to determine your email address.');
        setStep('awaiting_code');
        return;
      }

      const { error: verifyError } = await supabase.auth.verifyOtp({
        email,
        token: code,
        type: 'email',
      });

      if (verifyError) {
        const msg = verifyError.message.toLowerCase();
        const isExpiredOrInvalid = msg.includes('expired') || msg.includes('invalid');
        setIsTokenError(isExpiredOrInvalid);
        setError(verifyError.message);
        setStep('awaiting_code');
        return;
      }

      invalidateTokenCache();
      resetState();
      onOpenChange(false);
      onVerified();
    } catch {
      setError('Verification failed. Please try again.');
      setStep('awaiting_code');
    }
  };

  const handleVerifyTotp = async () => {
    const code = otp.trim();
    if (!code || !totpFactorId) return;

    setError(null);
    setIsTokenError(false);
    setStep('verifying');

    try {
      const { data: challenge, error: challengeError } = await supabase.auth.mfa.challenge({ factorId: totpFactorId });
      if (challengeError) {
        setError(challengeError.message);
        setStep('awaiting_code');
        return;
      }

      const { error: verifyError } = await supabase.auth.mfa.verify({
        factorId: totpFactorId,
        challengeId: challenge.id,
        code,
      });

      if (verifyError) {
        setError(verifyError.message);
        setStep('awaiting_code');
        return;
      }

      invalidateTokenCache();
      resetState();
      onOpenChange(false);
      onVerified();
    } catch {
      setError('TOTP verification failed. Please try again.');
      setStep('awaiting_code');
    }
  };

  const handleVerify = method === 'totp' ? handleVerifyTotp : handleVerifyEmail;

  const switchMethod = (newMethod: ReauthMethod) => {
    setMethod(newMethod);
    setOtp('');
    setError(null);
    setIsTokenError(false);
    setStep(newMethod === 'totp' ? 'awaiting_code' : 'idle');
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
              <AlertDescription className="flex items-center justify-between gap-2">
                <span>{error}</span>
                {isTokenError && method === 'email' && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleResendCode}
                    className="shrink-0"
                  >
                    <RefreshCw className="mr-1 h-3 w-3" />
                    Resend
                  </Button>
                )}
              </AlertDescription>
            </Alert>
          )}

          {hasTotpFactor && (step === 'idle' || step === 'awaiting_code') && (
            <div className="flex gap-2">
              <Button
                variant={method === 'email' ? 'default' : 'outline'}
                size="sm"
                className="flex-1"
                onClick={() => switchMethod('email')}
              >
                <Mail className="mr-1.5 h-3.5 w-3.5" />
                Email Code
              </Button>
              <Button
                variant={method === 'totp' ? 'default' : 'outline'}
                size="sm"
                className="flex-1"
                onClick={() => switchMethod('totp')}
              >
                <Smartphone className="mr-1.5 h-3.5 w-3.5" />
                Auth App
              </Button>
            </div>
          )}

          {method === 'email' && (step === 'idle' || step === 'sending') && (
            <>
              <p className="text-sm text-muted-foreground">
                Click below to receive a one-time verification code at your registered email address.
              </p>
              <TurnstileWidget
                ref={turnstileRef}
                onVerify={() => {}}
                onError={() => setError('Captcha verification failed. Please try again.')}
              />
            </>
          )}

          {method === 'email' && (step === 'awaiting_code' || step === 'verifying') && (
            <div className="space-y-2">
              <Label htmlFor="reauth-otp">Verification Code</Label>
              <Input
                id="reauth-otp"
                type="text"
                inputMode="numeric"
                placeholder="Enter the code from your email"
                value={otp}
                onChange={(e) => setOtp(normalizeOtp(e.target.value, 8))}
                maxLength={8}
                autoComplete="one-time-code"
                autoFocus
              />
              <p className="text-xs text-muted-foreground">
                Check your email for the latest verification code.
              </p>
            </div>
          )}

          {method === 'totp' && (step === 'awaiting_code' || step === 'verifying') && (
            <div className="space-y-2">
              <Label htmlFor="reauth-totp">Authenticator Code</Label>
              <Input
                id="reauth-totp"
                type="text"
                inputMode="numeric"
                placeholder="Enter 6-digit code from your app"
                value={otp}
                onChange={(e) => setOtp(normalizeOtp(e.target.value, 6))}
                maxLength={6}
                autoComplete="one-time-code"
                autoFocus
              />
              <p className="text-xs text-muted-foreground">
                Open your authenticator app and enter the current code.
              </p>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => handleOpenChange(false)}>
            Cancel
          </Button>

          {method === 'email' && (step === 'idle' || step === 'sending') && (
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
