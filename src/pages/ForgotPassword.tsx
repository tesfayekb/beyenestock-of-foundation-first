import { useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { useToast } from '@/hooks/use-toast';
import TurnstileWidget, { type TurnstileWidgetHandle } from '@/components/auth/TurnstileWidget';

const SUPABASE_URL = 'https://wbmbsclrgcnqaxmdsgfc.supabase.co';

export default function ForgotPassword() {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [turnstileToken, setTurnstileToken] = useState<string | null>(null);
  const turnstileRef = useRef<TurnstileWidgetHandle | null>(null);
  const { resetPassword } = useAuth();
  const { toast } = useToast();

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

  const verifyTurnstile = async (): Promise<boolean> => {
    const token = await getTurnstileToken();
    if (!token) {
      return false;
    }

    try {
      const res = await fetch(`${SUPABASE_URL}/functions/v1/verify-turnstile`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token }),
      });

      if (!res.ok) {
        toast({
          variant: 'destructive',
          title: 'Verification failed',
          description: 'CAPTCHA verification failed. Please try again.',
        });
        turnstileRef.current?.reset();
        setTurnstileToken(null);
        return false;
      }

      setTurnstileToken(token);
      return true;
    } catch {
      toast({
        variant: 'destructive',
        title: 'Verification error',
        description: 'Could not verify CAPTCHA. Please try again.',
      });
      turnstileRef.current?.reset();
      setTurnstileToken(null);
      return false;
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    const verified = await verifyTurnstile();
    if (!verified) {
      setLoading(false);
      return;
    }

    const { error } = await resetPassword(email);

    if (error) {
      console.error('[ForgotPassword] Reset error:', error.code);
    }
    setSubmitted(true);
    setLoading(false);
  };

  if (submitted) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background px-4">
        <Card className="w-full max-w-md text-center">
          <CardHeader>
            <CardTitle className="text-2xl">Check your email</CardTitle>
            <CardDescription>
              If an account exists for <strong>{email}</strong>, we've sent a password reset link.
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
          <CardTitle className="text-2xl">Reset your password</CardTitle>
          <CardDescription>Enter your email and we'll send a reset link</CardDescription>
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

            <TurnstileWidget
              ref={turnstileRef}
              onVerify={setTurnstileToken}
              onExpire={() => setTurnstileToken(null)}
              onError={() => setTurnstileToken(null)}
            />
          </CardContent>
          <CardFooter className="flex flex-col gap-4">
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? 'Sending…' : 'Send reset link'}
            </Button>
            <Link to="/sign-in" className="text-sm text-muted-foreground hover:text-primary">
              Back to sign in
            </Link>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
}
