import { useState, useEffect, useRef } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { supabase } from '@/integrations/supabase/client';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { useToast } from '@/hooks/use-toast';
import { safeRedirectPath } from '@/lib/safe-redirect';
import TurnstileWidget, { type TurnstileWidgetHandle } from '@/components/auth/TurnstileWidget';


export default function SignIn() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [oauthLoading, setOauthLoading] = useState<string | null>(null);
  const [turnstileToken, setTurnstileToken] = useState<string | null>(null);
  const turnstileRef = useRef<TurnstileWidgetHandle | null>(null);
  const { signIn, user, mfaStatus } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const { toast } = useToast();

  const from = safeRedirectPath(
    (location.state as { from?: { pathname: string } })?.from?.pathname,
    '/'
  );

  useEffect(() => {
    if (user) {
      if (mfaStatus === 'challenge_required') {
        navigate('/mfa-challenge', { replace: true });
      } else {
        navigate(from, { replace: true });
      }
    }
  }, [user, mfaStatus, from, navigate]);

  const getTurnstileToken = async (): Promise<string | null> => {
    if (turnstileToken) {
      return turnstileToken;
    }

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
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    const token = await getTurnstileToken();
    if (!token) {
      setLoading(false);
      return;
    }

    const { error } = await signIn(email, password, token);

    if (error) {
      toast({
        variant: 'destructive',
        title: 'Sign in failed',
        description: error.message,
      });
      turnstileRef.current?.reset();
      setTurnstileToken(null);
      setLoading(false);
    }
  };

  const handleOAuthSignIn = async (provider: 'google' | 'apple') => {
    setOauthLoading(provider);
    const { error } = await supabase.auth.signInWithOAuth({
      provider,
      options: {
        redirectTo: window.location.origin,
      },
    });
    if (error) {
      toast({
        variant: 'destructive',
        title: 'Sign in failed',
        description: error.message,
      });
      setOauthLoading(null);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">Welcome back</CardTitle>
          <CardDescription>Sign in to your account</CardDescription>
        </CardHeader>
        <form onSubmit={handleSubmit}>
          <CardContent className="space-y-4">
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
              <div className="flex items-center justify-between">
                <Label htmlFor="password">Password</Label>
                <Link to="/forgot-password" tabIndex={-1} className="text-sm text-muted-foreground hover:text-primary">
                  Forgot password?
                </Link>
              </div>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={12}
                autoComplete="current-password"
              />
            </div>

            <TurnstileWidget
              ref={turnstileRef}
              onVerify={setTurnstileToken}
              onExpire={() => setTurnstileToken(null)}
              onError={() => setTurnstileToken(null)}
            />

            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? 'Signing in...' : 'Sign in'}
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
              <Button
                type="button"
                variant="outline"
                className="w-full"
                onClick={() => handleOAuthSignIn('apple')}
                disabled={!!oauthLoading}
              >
                <svg className="mr-2 h-4 w-4" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M17.05 20.28c-.98.95-2.05.88-3.08.4-1.09-.5-2.08-.48-3.24 0-1.44.62-2.2.44-3.06-.4C2.79 15.25 3.51 7.59 9.05 7.31c1.35.07 2.29.74 3.08.8 1.18-.24 2.31-.93 3.57-.84 1.51.12 2.65.72 3.4 1.8-3.12 1.87-2.38 5.98.48 7.13-.57 1.5-1.31 2.99-2.54 4.09zM12.03 7.25c-.15-2.23 1.66-4.07 3.74-4.25.29 2.58-2.34 4.5-3.74 4.25z"/>
                </svg>
                {oauthLoading === 'apple' ? 'Redirecting…' : 'Continue with Apple'}
              </Button>
            </div>
          </CardContent>
          <CardFooter className="flex flex-col gap-4">
            <p className="text-sm text-muted-foreground">
              Don't have an account?{' '}
              <Link to="/sign-up" className="text-primary hover:underline">
                Sign up
              </Link>
            </p>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
}
