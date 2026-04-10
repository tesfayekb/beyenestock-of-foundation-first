import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { LoadingSkeleton } from '@/components/dashboard/LoadingSkeleton';

export function RequireAuth({ children }: { children: React.ReactNode }) {
  const { user, loading, mfaStatus } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background p-8">
        <LoadingSkeleton variant="page" />
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/sign-in" state={{ from: location }} replace />;
  }

  // User has MFA enrolled but hasn't completed the challenge yet
  if (mfaStatus === 'challenge_required') {
    return <Navigate to="/mfa-challenge" replace />;
  }

  return <>{children}</>;
}
