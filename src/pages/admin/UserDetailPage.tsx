import { useState, useMemo, useCallback } from 'react';
import { AdminEditProfileCard } from '@/components/admin/AdminEditProfileCard';
import { useParams, useNavigate } from 'react-router-dom';
import { PageHeader } from '@/components/dashboard/PageHeader';
import { StatusBadge } from '@/components/dashboard/StatusBadge';
import { LoadingSkeleton } from '@/components/dashboard/LoadingSkeleton';
import { ErrorState } from '@/components/dashboard/ErrorState';
import { ConfirmActionDialog } from '@/components/dashboard/ConfirmActionDialog';
import { AssignRoleDialog } from '@/components/admin/AssignRoleDialog';
import { RequirePermission } from '@/components/auth/RequirePermission';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { useUserDetail } from '@/hooks/useUsers';
import { useUserRolesAdmin } from '@/hooks/useUserRolesAdmin';
import { useAuditLogs, AuditLogEntry } from '@/hooks/useAuditLogs';
import { useDeactivateUser, useReactivateUser } from '@/hooks/useUserActions';
import { useAssignRole, useRevokeRole } from '@/hooks/useRoleActions';
import { useRoles } from '@/hooks/useRoles';
import { useUserRoles } from '@/hooks/useUserRoles';
import { checkPermission } from '@/lib/rbac';
import { useAuth } from '@/contexts/AuthContext';
import { ROUTES } from '@/config/routes';
import { format } from 'date-fns';
import { ArrowLeft, ShieldAlert, ShieldCheck, Mail, Calendar, Clock, FileText, Plus, X, Lock } from 'lucide-react';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';

export default function UserDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user: currentUser } = useAuth();
  const { context } = useUserRoles();

  const canViewRoles = checkPermission(context, 'roles.view');
  const canViewAudit = checkPermission(context, 'audit.view');
  const canAssignRoles = checkPermission(context, 'roles.assign');
  const canRevokeRoles = checkPermission(context, 'roles.revoke');
  const canEditProfile = checkPermission(context, 'users.edit_any');
  const canDeactivate = checkPermission(context, 'users.deactivate');
  const canReactivate = checkPermission(context, 'users.reactivate');

  const { data: profile, isLoading, error, refetch } = useUserDetail(id);
  const { data: userRoles, isLoading: rolesLoading, refetch: refetchRoles } = useUserRolesAdmin(canViewRoles ? id : undefined);
  const { data: auditData, isLoading: auditLoading } = useAuditLogs(
    { target_id: id, limit: 10 },
    { enabled: !!id && canViewAudit },
  );
  const { data: allRoles } = useRoles({ enabled: canAssignRoles || canRevokeRoles });

  const deactivateMutation = useDeactivateUser();
  const reactivateMutation = useReactivateUser();
  const assignRoleMutation = useAssignRole();
  const revokeRoleMutation = useRevokeRole();

  const [showDeactivate, setShowDeactivate] = useState(false);
  const [showReactivate, setShowReactivate] = useState(false);
  const [showAssignRole, setShowAssignRole] = useState(false);
  const [revokeRoleTarget, setRevokeRoleTarget] = useState<{ role_id: string; role_name: string } | null>(null);

  const isSelf = currentUser?.id === id;

  // Roles not yet assigned to this user
  const currentUserIsSuperadmin = context?.is_superadmin ?? false;

  // Roles available for assignment: exclude already-assigned, user (auto-assigned),
  // and superadmin (unless current user is superadmin)
  const availableRoles = useMemo(() => {
    if (!allRoles || !userRoles) return [];
    const assignedIds = new Set(userRoles.map((ur) => ur.role_id));
    return allRoles.filter((r) => {
      if (assignedIds.has(r.id)) return false;
      if (r.key === 'user') return false;
      if (r.key === 'superadmin' && !currentUserIsSuperadmin) return false;
      return true;
    });
  }, [allRoles, userRoles, currentUserIsSuperadmin]);

  const handleDeactivate = useCallback((reason?: string) => {
    deactivateMutation.mutate({ user_id: id!, reason }, { onSuccess: () => setShowDeactivate(false) });
  }, [id, deactivateMutation]);

  const handleReactivate = useCallback((reason?: string) => {
    reactivateMutation.mutate({ user_id: id!, reason }, { onSuccess: () => setShowReactivate(false) });
  }, [id, reactivateMutation]);

  const handleAssignRole = useCallback((roleId: string) => {
    assignRoleMutation.mutate(
      { target_user_id: id!, role_id: roleId },
      { onSuccess: () => { setShowAssignRole(false); refetchRoles(); } },
    );
  }, [id, assignRoleMutation, refetchRoles]);

  const handleRevokeRole = useCallback(() => {
    if (!revokeRoleTarget) return;
    revokeRoleMutation.mutate(
      { target_user_id: id!, role_id: revokeRoleTarget.role_id },
      { onSuccess: () => { setRevokeRoleTarget(null); refetchRoles(); } },
    );
  }, [id, revokeRoleTarget, revokeRoleMutation, refetchRoles]);

  if (isLoading) {
    return <div className="space-y-6"><LoadingSkeleton variant="page" /></div>;
  }

  if (error || !profile) {
    return <div className="space-y-6"><ErrorState message={error?.message ?? 'User not found'} onRetry={() => refetch()} /></div>;
  }

  const isActive = profile.status === 'active';
  const initials = (profile.display_name ?? '?').split(' ').map((n) => n[0]).join('').toUpperCase().slice(0, 2);
  const auditEntries: AuditLogEntry[] = auditData?.data ?? [];

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" onClick={() => navigate(ROUTES.ADMIN_USERS)} aria-label="Back to users">
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <PageHeader
          title={profile.display_name ?? 'Unknown User'}
          subtitle={profile.email ?? id}
          actions={
            !isSelf && (
              isActive ? (
                canDeactivate && (
                  <Button variant="destructive" size="sm" onClick={() => setShowDeactivate(true)}>
                    <ShieldAlert className="mr-2 h-4 w-4" />
                    Deactivate
                  </Button>
                )
              ) : (
                canReactivate && (
                  <Button variant="default" size="sm" onClick={() => setShowReactivate(true)}>
                    <ShieldCheck className="mr-2 h-4 w-4" />
                    Reactivate
                  </Button>
                )
              )
            )
          }
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Profile Card */}
        <Card className="lg:col-span-2">
          <CardHeader><CardTitle className="text-base">Profile Information</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-4">
              <Avatar className="h-16 w-16">
                <AvatarImage src={profile.avatar_url ?? undefined} />
                <AvatarFallback className="text-lg">{initials}</AvatarFallback>
              </Avatar>
              <div className="space-y-1">
                <p className="font-display text-lg font-semibold">{profile.display_name ?? '—'}</p>
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
            <AdminEditProfileCard
              userId={id!}
              displayName={profile.display_name}
              avatarUrl={profile.avatar_url}
              canEdit={canEditProfile}
              isSelf={isSelf}
            />
          </CardContent>
        </Card>

        {/* Roles Card — permission-guarded */}
        <RequirePermission permission="roles.view">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-base">Assigned Roles</CardTitle>
                {canAssignRoles && availableRoles.length > 0 && (
                  <Button size="sm" variant="outline" onClick={() => setShowAssignRole(true)}>
                    <Plus className="mr-1 h-3 w-3" />
                    Assign
                  </Button>
                )}
              </div>
            </CardHeader>
            <CardContent>
              {rolesLoading ? (
                <LoadingSkeleton variant="card" rows={2} />
              ) : userRoles && userRoles.length > 0 ? (
                <div className="space-y-2">
                  {userRoles.map((role) => {
                    const isIrrevocableForActor = role.role_key === 'user'
                      || (role.is_base && !context?.is_superadmin)
                      || (role.role_key === 'superadmin' && isSelf);
                    return (
                      <div key={role.id} className="flex items-center justify-between rounded-md border border-border px-3 py-2">
                        <Badge variant="secondary" className="text-sm">{role.role_name}</Badge>
                        {canRevokeRoles && (
                          isIrrevocableForActor ? (
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <span className="inline-flex h-7 w-7 items-center justify-center text-muted-foreground">
                                  <Lock className="h-3 w-3" />
                                </span>
                              </TooltipTrigger>
                              <TooltipContent>Base role — cannot be revoked</TooltipContent>
                            </Tooltip>
                          ) : (
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-7 w-7 text-muted-foreground hover:text-destructive"
                              onClick={() => setRevokeRoleTarget({ role_id: role.role_id, role_name: role.role_name })}
                              aria-label={`Revoke ${role.role_name} role`}
                            >
                              <X className="h-3 w-3" />
                            </Button>
                          )
                        )}
                      </div>
                    );
                  })}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">No roles assigned</p>
              )}
            </CardContent>
          </Card>
        </RequirePermission>
      </div>

      {/* Audit Trail — permission-guarded */}
      <RequirePermission permission="audit.view">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <FileText className="h-4 w-4" />
              Recent Activity
            </CardTitle>
          </CardHeader>
          <CardContent>
            {auditLoading ? (
              <LoadingSkeleton variant="card" rows={3} />
            ) : auditEntries.length > 0 ? (
              <div className="space-y-3">
                {auditEntries.map((entry) => (
                  <div key={entry.id} className="flex items-start justify-between gap-4 border-b border-border pb-3 last:border-0 last:pb-0">
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-foreground">{entry.action}</p>
                      {entry.target_type && (
                        <p className="text-xs text-muted-foreground">
                          {entry.target_type}{entry.target_id ? ` · ${entry.target_display_name ?? entry.target_id.slice(0, 8) + '…'}` : ''}
                        </p>
                      )}
                    </div>
                    <span className="shrink-0 text-xs text-muted-foreground">
                      {format(new Date(entry.created_at), 'MMM d, HH:mm')}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No audit records found for this user.</p>
            )}
          </CardContent>
        </Card>
      </RequirePermission>

      {/* Dialogs */}
      <ConfirmActionDialog
        open={showDeactivate}
        onOpenChange={setShowDeactivate}
        title="Deactivate User"
        description={`This will deactivate ${profile.display_name ?? 'this user'}'s account and revoke all active sessions.`}
        confirmLabel="Deactivate"
        destructive
        requireReason
        reasonLabel="Reason for deactivation (required)"
        onConfirm={handleDeactivate}
        loading={deactivateMutation.isPending}
      />
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
      <AssignRoleDialog
        open={showAssignRole}
        onOpenChange={setShowAssignRole}
        availableRoles={availableRoles}
        onConfirm={handleAssignRole}
        loading={assignRoleMutation.isPending}
      />
      <ConfirmActionDialog
        open={!!revokeRoleTarget}
        onOpenChange={(open) => !open && setRevokeRoleTarget(null)}
        title="Revoke Role"
        description={`Remove "${revokeRoleTarget?.role_name}" from this user? This action is audited.`}
        confirmLabel="Revoke"
        destructive
        onConfirm={handleRevokeRole}
        loading={revokeRoleMutation.isPending}
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
