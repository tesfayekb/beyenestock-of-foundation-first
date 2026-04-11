import { useState, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { PageHeader } from '@/components/dashboard/PageHeader';
import { LoadingSkeleton } from '@/components/dashboard/LoadingSkeleton';
import { ErrorState } from '@/components/dashboard/ErrorState';
import { ConfirmActionDialog } from '@/components/dashboard/ConfirmActionDialog';
import { ManagePermissionsDialog } from '@/components/admin/ManagePermissionsDialog';
import { RequirePermission } from '@/components/auth/RequirePermission';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useRoleDetail } from '@/hooks/useRoles';
import { usePermissions } from '@/hooks/useRoles';
import { useAssignPermission, useRevokePermission } from '@/hooks/useRoleActions';
import { useUserRoles } from '@/hooks/useUserRoles';
import { checkPermission } from '@/lib/rbac';
import { ROUTES } from '@/config/routes';
import { ArrowLeft, Plus, X, Shield, Users, Key } from 'lucide-react';

export default function RoleDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { context } = useUserRoles();

  const canAssignPerms = checkPermission(context, 'permissions.assign');
  const canRevokePerms = checkPermission(context, 'permissions.revoke');

  const { data: role, isLoading, error, refetch } = useRoleDetail(id);
  const { data: allPermissions } = usePermissions();
  const assignPermission = useAssignPermission();
  const revokePermission = useRevokePermission();

  const [showAddPermission, setShowAddPermission] = useState(false);
  const [revokeTarget, setRevokeTarget] = useState<{ id: string; key: string } | null>(null);

  // Permissions not yet assigned to this role
  const availablePermissions = useMemo(() => {
    if (!allPermissions || !role) return [];
    const assignedIds = new Set(role.permissions.map((p) => p.id));
    return allPermissions.filter((p) => !assignedIds.has(p.id));
  }, [allPermissions, role]);

  if (isLoading) {
    return <div className="space-y-6"><LoadingSkeleton variant="page" /></div>;
  }

  if (error || !role) {
    return <div className="space-y-6"><ErrorState message={error?.message ?? 'Role not found'} onRetry={() => refetch()} /></div>;
  }

  const handleAssignPermission = (permissionId: string) => {
    assignPermission.mutate(
      { role_id: id!, permission_id: permissionId },
      { onSuccess: () => { setShowAddPermission(false); refetch(); } },
    );
  };

  const handleRevokePermission = () => {
    if (!revokeTarget) return;
    revokePermission.mutate(
      { role_id: id!, permission_id: revokeTarget.id },
      { onSuccess: () => { setRevokeTarget(null); refetch(); } },
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" onClick={() => navigate(ROUTES.ADMIN_ROLES)}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <PageHeader
          title={role.name}
          subtitle={role.key}
        />
      </div>

      {/* Role Info */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Shield className="h-4 w-4" />
            Role Details
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {role.description && (
            <p className="text-sm text-muted-foreground">{role.description}</p>
          )}
          <div className="flex flex-wrap gap-2">
            {role.is_base && <Badge variant="secondary">Base Role</Badge>}
            {role.is_immutable && <Badge variant="outline">Immutable</Badge>}
          </div>
        </CardContent>
      </Card>

      {/* Permissions */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-base">
              <Key className="h-4 w-4" />
              Permissions ({role.permissions.length})
            </CardTitle>
            {canAssignPerms && !role.is_immutable && availablePermissions.length > 0 && (
              <Button size="sm" variant="outline" onClick={() => setShowAddPermission(true)}>
                <Plus className="mr-1 h-3 w-3" />
                Add
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {role.permissions.length > 0 ? (
            <div className="space-y-2">
              {role.permissions.map((perm) => (
                <div key={perm.id} className="flex items-center justify-between rounded-md border border-border px-3 py-2">
                  <div className="min-w-0">
                    <p className="text-sm font-medium font-mono text-foreground">{perm.key}</p>
                    {perm.description && (
                      <p className="text-xs text-muted-foreground">{perm.description}</p>
                    )}
                  </div>
                  {canRevokePerms && !role.is_immutable && (
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7 text-muted-foreground hover:text-destructive"
                      onClick={() => setRevokeTarget({ id: perm.id, key: perm.key })}
                    >
                      <X className="h-3 w-3" />
                    </Button>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No permissions assigned to this role.</p>
          )}
        </CardContent>
      </Card>

      {/* Users with this role */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Users className="h-4 w-4" />
            Users with this Role ({role.users.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {role.users.length > 0 ? (
            <div className="space-y-2">
              {role.users.map((user) => (
                <div
                  key={user.id}
                  className="flex items-center justify-between rounded-md border border-border px-3 py-2 cursor-pointer hover:bg-muted/50"
                  onClick={() => navigate(ROUTES.ADMIN_USER_DETAIL.replace(':id', user.id))}
                >
                  <p className="text-sm font-medium text-foreground">
                    {user.display_name ?? user.id.slice(0, 8) + '…'}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No users have this role.</p>
          )}
        </CardContent>
      </Card>

      {/* Add Permission Dialog */}
      <ManagePermissionsDialog
        open={showAddPermission}
        onOpenChange={setShowAddPermission}
        availablePermissions={availablePermissions}
        onConfirm={handleAssignPermission}
        loading={assignPermission.isPending}
      />

      {/* Revoke Permission Confirm */}
      <ConfirmActionDialog
        open={!!revokeTarget}
        onOpenChange={(open) => !open && setRevokeTarget(null)}
        title="Revoke Permission"
        description={`Remove "${revokeTarget?.key}" from role "${role.name}"? This action is audited.`}
        confirmLabel="Revoke"
        destructive
        onConfirm={handleRevokePermission}
        loading={revokePermission.isPending}
      />
    </div>
  );
}
