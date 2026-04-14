/**
 * InviteOnlyMessage — Displayed on SignUp page when self-registration is disabled.
 *
 * Owner: user-onboarding module
 */
import { Link } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { ShieldCheck } from 'lucide-react';

export function InviteOnlyMessage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <Card className="w-full max-w-md text-center">
        <CardHeader>
          <div className="mx-auto mb-2 rounded-full bg-muted p-3">
            <ShieldCheck className="h-8 w-8 text-muted-foreground" />
          </div>
          <CardTitle className="text-2xl">Invitation Only</CardTitle>
          <CardDescription>
            Registration is currently restricted to invited users only.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            If you've received an invitation email, please use the link in that email to create your account.
            Otherwise, contact your administrator to request access.
          </p>
        </CardContent>
        <CardFooter className="justify-center">
          <Link to="/sign-in" className="text-sm text-primary hover:underline">
            Already have an account? Sign in
          </Link>
        </CardFooter>
      </Card>
    </div>
  );
}
