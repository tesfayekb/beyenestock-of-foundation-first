import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { PageHeader } from '@/components/dashboard/PageHeader';
import { StatusBadge } from '@/components/dashboard/StatusBadge';
import { LoadingSkeleton } from '@/components/dashboard/LoadingSkeleton';
import { ErrorState } from '@/components/dashboard/ErrorState';
import { ConfirmActionDialog } from '@/components/dashboard/ConfirmActionDialog';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { useUserDetail } from '@/hooks/useUsers';
import { useUserRolesAdmin } from '@/hooks/useUserRolesAdmin';
import { useDeactivateUser, useReactivateUser } from '@/hooks/useUserActions';
import { useAuth } from '@/contexts/AuthContext';
import { ROUTES } from '@/config/routes';
import { format } from 'date-fns';
import { ArrowLeft, ShieldAlert, ShieldCheck, Mail, Calendar, Clock } from 'lucide-react';

export default function UserDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user: currentUser } = useAuth();

  const { data: profile, isLoading, error, refetch } = useUserDetail(id);
  const { data: roles, isLoading: rolesLoading } = useUserRolesAdmin(id);
  const deactivateMutation = useDeactivateUser();
  const reactivateMutation = useReactivateUser();

  const [showDeactivate, setShowDeactivate] = useState(false);
  const [showReactivate, setShowReactivate] = useState(false);

  const isSelf = currentUser?.id === id;

  if (isLoading) {
    return (
      <div className="space-y-6">
        <LoadingSkeleton variant="page" />
      </div>
    );
  }

  if (error || !profile) {
    return (
      <div className="space-y-6">
        <ErrorState message={error?.message ?? 'User not found'} onRetry={() => refetch()} />
      </div>
    );
  }

  const isActive = profile.status === 'active';
  const initials = (profile.display_name ?? '?')
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);

  const handleDeactivate = (reason?: string) => {
    deactivateMutation.mutate(
      { user_id: id!, reason },
      { onSuccess: () => setShowDeactivate(false) },
    );
  };

  const handleReactivate = (reason?: string) => {
    reactivateMutation.mutate(
      { user_id: id!, reason },
      { onSuccess: () => setShowReactivate(false) },
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" onClick={() => navigate(ROUTES.ADMIN_USERS)}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <PageHeader
          title={profile.display_name ?? 'Unknown User'}
          subtitle={profile.email ?? id}
          actions={
            !isSelf && (
              isActive ? (
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => setShowDeactivate(true)}
                >
                  <ShieldAlert className="mr-2 h-4 w-4" />
                  Deactivate
                </Button>
              ) : (
                <Button
                  variant="default"
                  size="sm"
                  onClick={() => setShowReactivate(true)}
                >
                  <ShieldCheck className="mr-2 h-4 w-4" />
                  Reactivate
                </Button>
              )
            )
          }
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Profile Card */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base">Profile Information</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-4">
              <Avatar className="h-16 w-16">
                <AvatarImage src={profile.avatar_url ?? undefined} />
                <AvatarFallback className="text-lg">{initials}</AvatarFallback>
              </Avatar>
              <div className="space-y-1">
                <p className="font-display text-lg font-semibold">
                  {profile.display_name ?? '—'}
                </p>
                <div className="flex items-center gap-2">
                  <StatusBadge status={profile.status as 'active' | 'deactivated'} />
                  <StatusBadge
                    status={profile.email_verified ? 'active' : 'pending'}
                    label={profile.email_verified ? 'Email Verified' : 'Email Unverified'}
                  />
                </div>
              </div>
            </div>

            <div className="grid gap-3 pt-2 sm:grid-cols-2">
              <InfoRow icon={Mail} label="Email" value={profile.email ?? '—'} />
              <InfoRow icon={Calendar} label="Created" value={format(new Date(profile.created_at), 'MMM d, yyyy')} />
              <InfoRow icon={Clock} label="Last Updated" value={format(new Date(profile.updated_at), 'MMM d, yyyy HH:mm')} />
            </div>
          </CardContent>
        </Card>

        {/* Roles Card */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Assigned Roles</CardTitle>
          </CardHeader>
          <CardContent>
            {rolesLoading ? (
              <LoadingSkeleton variant="card" rows={2} />
            ) : roles && roles.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {roles.map((role) => (
                  <Badge key={role.id} variant="secondary" className="text-sm">
                    {role.role_name}
                  </Badge>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No roles assigned</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Deactivate Dialog */}
      <ConfirmActionDialog
        open={showDeactivate}
        onOpenChange={setShowDeactivate}
        title="Deactivate User"
        description={`This will deactivate ${profile.display_name ?? 'this user'}'s account and revoke all active sessions. The user will not be able to sign in until reactivated.`}
        confirmLabel="Deactivate"
        destructive
        requireReason
        reasonLabel="Reason for deactivation (required)"
        onConfirm={handleDeactivate}
        loading={deactivateMutation.isPending}
      />

      {/* Reactivate Dialog */}
      <ConfirmActionDialog
        open={showReactivate}
        onOpenChange={setShowReactivate}
        title="Reactivate User"
        description={`This will reactivate ${profile.display_name ?? 'this user'}'s account, allowing them to sign in again.`}
        confirmLabel="Reactivate"
        destructive={false}
        requireReason
        reasonLabel="Reason for reactivation (required)"
        onConfirm={handleReactivate}
        loading={reactivateMutation.isPending}
      />
    </div>
  );
}

function InfoRow({ icon: Icon, label, value }: { icon: React.ElementType; label: string; value: string }) {
  return (
    <div className="flex items-center gap-2 text-sm">
      <Icon className="h-4 w-4 text-muted-foreground" />
      <span className="text-muted-foreground">{label}:</span>
      <span className="font-medium text-foreground">{value}</span>
    </div>
  );
}
