import { useAuth } from '@/contexts/AuthContext';
import { useProfile } from '@/hooks/useProfile';
import { useMfaFactors } from '@/hooks/useMfaFactors';
import { PageHeader } from '@/components/dashboard/PageHeader';
import { LoadingSkeleton } from '@/components/dashboard/LoadingSkeleton';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Link } from 'react-router-dom';
import { ROUTES } from '@/config/routes';
import { UserCircle, ShieldCheck, ShieldOff, ArrowRight } from 'lucide-react';

export default function UserDashboard() {
  const { user } = useAuth();
  const { profile, isLoading } = useProfile();
  const { factors } = useMfaFactors();

  if (isLoading) return <LoadingSkeleton />;

  const greeting = profile?.display_name
    ? `Welcome back, ${profile.display_name}`
    : 'Welcome back';

  // FINDING-3 FIX: Use verifiedFactors.length > 0 (consistent with SecurityPage)
  const verifiedFactors = factors.filter((f) => f.status === 'verified');
  const hasMfa = verifiedFactors.length > 0;

  return (
    <>
      <PageHeader title="Dashboard" subtitle={greeting} />

      <div className="grid gap-6 md:grid-cols-2 max-w-3xl">
        {/* Profile card */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <UserCircle className="h-4 w-4" />
              Your Profile
            </CardTitle>
            <CardDescription>Account overview</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="text-sm">
              <p className="text-muted-foreground text-xs">Email</p>
              <p className="font-medium">{user?.email ?? '—'}</p>
            </div>
            <div className="text-sm">
              <p className="text-muted-foreground text-xs">Display Name</p>
              <p className="font-medium">{profile?.display_name ?? '—'}</p>
            </div>
            <div className="text-sm">
              <p className="text-muted-foreground text-xs">Status</p>
              <Badge variant={profile?.status === 'active' ? 'default' : 'destructive'} className="text-xs">
                {profile?.status ?? 'unknown'}
              </Badge>
            </div>
            <Button variant="outline" size="sm" asChild className="mt-2">
              <Link to={ROUTES.SETTINGS}>
                Edit Profile
                <ArrowRight className="ml-2 h-3.5 w-3.5" />
              </Link>
            </Button>
          </CardContent>
        </Card>

        {/* Security card */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              {hasMfa ? (
                <ShieldCheck className="h-4 w-4 text-success" />
              ) : (
                <ShieldOff className="h-4 w-4 text-warning" />
              )}
              Security
            </CardTitle>
            <CardDescription>
              {hasMfa ? 'Your account is protected with MFA' : 'MFA is not enabled'}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {!hasMfa && (
              <p className="text-sm text-muted-foreground mb-3">
                Enable multi-factor authentication to add an extra layer of security.
              </p>
            )}
            <Button variant="outline" size="sm" asChild>
              <Link to={ROUTES.SETTINGS_SECURITY}>
                {hasMfa ? 'Manage MFA' : 'Enable MFA'}
                <ArrowRight className="ml-2 h-3.5 w-3.5" />
              </Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    </>
  );
}
