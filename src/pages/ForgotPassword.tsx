import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { useToast } from '@/hooks/use-toast';
import TurnstileWidget from '@/components/auth/TurnstileWidget';

const SUPABASE_URL = 'https://wbmbsclrgcnqaxmdsgfc.supabase.co';

export default function ForgotPassword() {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [turnstileToken, setTurnstileToken] = useState<string | null>(null);
  const { resetPassword } = useAuth();
  const { toast } = useToast();

  const verifyTurnstile = async (): Promise<boolean> => {
    if (!turnstileToken) {
      toast({
        variant: 'destructive',
        title: 'Verification required',
        description: 'Please complete the CAPTCHA verification.',
      });
      return false;
    }

    try {
      const res = await fetch(`${SUPABASE_URL}/functions/v1/verify-turnstile`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: turnstileToken }),
      });

      if (!res.ok) {
        toast({
          variant: 'destructive',
          title: 'Verification failed',
          description: 'CAPTCHA verification failed. Please try again.',
        });
        setTurnstileToken(null);
        return false;
      }

      return true;
    } catch {
      toast({
        variant: 'destructive',
        title: 'Verification error',
        description: 'Could not verify CAPTCHA. Please try again.',
      });
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
      // Never reveal whether an email exists — always show the same message
      console.error('[ForgotPassword] Reset error:', error.code);
    }
    // Always show "check your email" to prevent user enumeration
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
              onVerify={setTurnstileToken}
              onExpire={() => setTurnstileToken(null)}
              onError={() => setTurnstileToken(null)}
            />
          </CardContent>
          <CardFooter className="flex flex-col gap-4">
            <Button type="submit" className="w-full" disabled={loading || !turnstileToken}>
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
