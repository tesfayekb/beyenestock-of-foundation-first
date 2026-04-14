import { useRef, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { supabase } from '@/integrations/supabase/client';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { useToast } from '@/hooks/use-toast';
import TurnstileWidget, { type TurnstileWidgetHandle } from '@/components/auth/TurnstileWidget';
import { DEV_MODE, DEV_PASSWORD_MIN_LENGTH, TURNSTILE_ACTIVE } from '@/lib/dev-mode';
import { InviteOnlyMessage } from '@/components/auth/InviteOnlyMessage';
import { useOnboardingMode } from '@/hooks/useOnboardingMode';
import { LoadingSkeleton } from '@/components/dashboard/LoadingSkeleton';

export default function SignUp() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [lastName, setLastName] = useState('');
  const [loading, setLoading] = useState(false);
  const [oauthLoading, setOauthLoading] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(false);
  const [turnstileToken, setTurnstileToken] = useState<string | null>(null);
  const turnstileRef = useRef<TurnstileWidgetHandle | null>(null);
  const { signUp } = useAuth();
  const { toast } = useToast();
  const { data: onboardingMode, isLoading: modeLoading } = useOnboardingMode();

  const getTurnstileToken = useCallback(async (): Promise<string | null> => {
    if (!TURNSTILE_ACTIVE) {
      return null;
    }

    if (turnstileToken) return turnstileToken;
    try {
      return await turnstileRef.current?.execute() ?? null;
    } catch (error) {
      toast({
        variant: 'destructive',
        title: 'Verification required',
        description: error instanceof Error ? error.message : 'Please complete the CAPTCHA check and try again.',
      });
      return null;
    }
  }, [turnstileToken, toast]);

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    const token = await getTurnstileToken();
    if (TURNSTILE_ACTIVE && !token) {
      setLoading(false);
      return;
    }
    const { error } = await signUp(email, password, displayName, token ?? undefined, lastName);
    if (error) {
      toast({ variant: 'destructive', title: 'Sign up failed', description: error.message });
      turnstileRef.current?.reset();
      setTurnstileToken(null);
      setLoading(false);
    } else {
      setSubmitted(true);
      setLoading(false);
    }
  }, [email, password, displayName, lastName, getTurnstileToken, signUp, toast]);

  const handleOAuthSignIn = useCallback(async (provider: 'google') => {
    setOauthLoading(provider);
    const { error } = await supabase.auth.signInWithOAuth({
      provider,
      options: {
        redirectTo: window.location.origin,
        queryParams: { prompt: 'select_account' },
      },
    });
    if (error) {
      toast({ variant: 'destructive', title: 'Sign up failed', description: error.message });
      setOauthLoading(null);
    }
  }, [toast]);

  const handleExpire = useCallback(() => setTurnstileToken(null), []);
  const handleError = useCallback(() => setTurnstileToken(null), []);

  // Check onboarding mode
  if (modeLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background px-4">
        <LoadingSkeleton variant="card" rows={1} />
      </div>
    );
  }

  if (onboardingMode && !onboardingMode.signup_enabled) {
    return <InviteOnlyMessage />;
  }

  if (submitted) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background px-4">
        <Card className="w-full max-w-md text-center">
          <CardHeader>
            <CardTitle className="text-2xl">Check your email</CardTitle>
            <CardDescription>
              We've sent a verification link to <strong>{email}</strong>. Please click it to activate your account.
            </CardDescription>
          </CardHeader>
          <CardFooter className="justify-center">
            <Link to="/sign-in" className="text-sm text-primary hover:underline">
              Back to sign in
            </Link>
          </CardFooter>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">Create an account</CardTitle>
          <CardDescription>Get started with your account</CardDescription>
        </CardHeader>
        <form onSubmit={handleSubmit}>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label htmlFor="displayName">First name</Label>
                <Input
                  id="displayName"
                  type="text"
                  placeholder="First name"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  autoComplete="given-name"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="lastName">Last name</Label>
                <Input
                  id="lastName"
                  type="text"
                  placeholder="Last name"
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                  autoComplete="family-name"
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={DEV_MODE ? DEV_PASSWORD_MIN_LENGTH : 12}
                placeholder={DEV_MODE ? "Minimum 6 characters" : "Minimum 12 characters"}
                autoComplete="new-password"
              />
            </div>

            {TURNSTILE_ACTIVE && (
              <TurnstileWidget
                ref={turnstileRef}
                onVerify={setTurnstileToken}
                onExpire={handleExpire}
                onError={handleError}
              />
            )}

            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? 'Creating account…' : 'Create account'}
            </Button>

            <div className="relative my-2">
              <Separator />
              <span className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 bg-card px-2 text-xs text-muted-foreground">
                or
              </span>
            </div>

            <div className="flex flex-col gap-2">
              <Button
                type="button"
                variant="outline"
                className="w-full"
                onClick={() => handleOAuthSignIn('google')}
                disabled={!!oauthLoading}
              >
                <svg className="mr-2 h-4 w-4" viewBox="0 0 24 24">
                  <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4"/>
                  <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                  <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                  <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
                </svg>
                {oauthLoading === 'google' ? 'Redirecting…' : 'Continue with Google'}
              </Button>
            </div>
          </CardContent>
          <CardFooter className="flex flex-col gap-4">
            <p className="text-sm text-muted-foreground">
              Already have an account?{' '}
              <Link to="/sign-in" className="text-primary hover:underline">
                Sign in
              </Link>
            </p>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
}
