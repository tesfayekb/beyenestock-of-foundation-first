import { useAuth } from '@/contexts/AuthContext';
import { isEmailVerified } from '@/lib/auth-guards';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { supabase } from '@/integrations/supabase/client';
import { useToast } from '@/hooks/use-toast';
import { useState } from 'react';

/**
 * Route guard that blocks access for users with unverified email.
 * Implements requireVerifiedEmail() from function-index.md.
 * Fail-secure: denies access if email verification status cannot be determined.
 */
export function RequireVerifiedEmail({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const { toast } = useToast();
  const [resending, setResending] = useState(false);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  if (!isEmailVerified(user)) {
    const handleResend = async () => {
      if (!user?.email) return;
      setResending(true);
      const { error } = await supabase.auth.resend({
        type: 'signup',
        email: user.email,
      });
      if (error) {
        toast({ variant: 'destructive', title: 'Failed to resend', description: error.message });
      } else {
        toast({ title: 'Verification email sent', description: 'Check your inbox.' });
      }
      setResending(false);
    };

    return (
      <div className="flex min-h-screen items-center justify-center bg-background px-4">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <CardTitle className="text-2xl">Email Verification Required</CardTitle>
            <CardDescription>
              Please verify your email address to access this feature.
              Check your inbox for the verification link.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col items-center gap-4">
            <Button onClick={handleResend} disabled={resending} variant="outline">
              {resending ? 'Sending...' : 'Resend verification email'}
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return <>{children}</>;
}
