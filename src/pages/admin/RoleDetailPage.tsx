import { useState, useMemo, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { PageHeader } from '@/components/dashboard/PageHeader';
import { LoadingSkeleton } from '@/components/dashboard/LoadingSkeleton';
import { ErrorState } from '@/components/dashboard/ErrorState';
import { ConfirmActionDialog } from '@/components/dashboard/ConfirmActionDialog';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useRoleDetail } from '@/hooks/useRoles';
import { usePermissions } from '@/hooks/useRoles';
import { useAssignPermission, useRevokePermission, useDeleteRole } from '@/hooks/useRoleActions';
import { useUserRoles } from '@/hooks/useUserRoles';
import { checkPermission } from '@/lib/rbac';
import { ROUTES } from '@/config/routes';
import { ArrowLeft, Shield, Users, Key, Loader2, Info, Trash2 } from 'lucide-react';


interface PermissionGroup {
  resource: string;
  label: string;
  permissions: { id: string; key: string; description: string | null; assigned: boolean }[];
}

export default function RoleDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { context } = useUserRoles();

  const canAssignPerms = checkPermission(context, 'permissions.assign');
  const canRevokePerms = checkPermission(context, 'permissions.revoke');
  const canModifyPerms = (canAssignPerms || canRevokePerms);
  const canDeleteRole = checkPermission(context, 'roles.delete');

  const { data: role, isLoading, error, refetch } = useRoleDetail(id);
  const { data: allPermissions } = usePermissions();
  const assignPermission = useAssignPermission();
  const revokePermission = useRevokePermission();
  const deleteRole = useDeleteRole();

  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  const isSuperadmin = role?.key === 'superadmin';

  // Track in-flight toggles to show spinners per-permission
  const [pendingToggles, setPendingToggles] = useState<Set<string>>(new Set());

  const handleDeleteRole = useCallback(
    (reason?: string) => {
      if (!id || !reason) return;
      deleteRole.mutate(
        { role_id: id, reason },
        {
          onSuccess: () => {
            setShowDeleteConfirm(false);
            navigate(ROUTES.ADMIN_ROLES);
          },
        },
      );
    },
    [id, deleteRole, navigate],
  );

  // Build grouped permission matrix
  const groups = useMemo<PermissionGroup[]>(() => {
    if (!allPermissions || !role) return [];
    const assignedIds = new Set(role.permissions.map((p) => p.id));
    const map = new Map<string, PermissionGroup['permissions']>();

    for (const p of allPermissions) {
      const dotIdx = p.key.indexOf('.');
      const resource = dotIdx > 0 ? p.key.slice(0, dotIdx) : 'other';
      if (!map.has(resource)) map.set(resource, []);
      map.get(resource)!.push({
        id: p.id,
        key: p.key,
        description: p.description,
        assigned: assignedIds.has(p.id),
      });
    }

    return Array.from(map.entries())
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([resource, perms]) => ({
        resource,
        label: resource.charAt(0).toUpperCase() + resource.slice(1),
        permissions: perms.sort((a, b) => a.key.localeCompare(b.key)),
      }));
  }, [allPermissions, role]);

  const handleToggle = useCallback(
    (permissionId: string, currentlyAssigned: boolean) => {
      if (!id || role?.is_immutable || isSuperadmin) return;
      setPendingToggles((prev) => new Set(prev).add(permissionId));

      const mutation = currentlyAssigned ? revokePermission : assignPermission;
      mutation.mutate(
        { role_id: id, permission_id: permissionId },
        {
          onError: () => {
            refetch();
          },
          onSettled: () => {
            setPendingToggles((prev) => {
              const next = new Set(prev);
              next.delete(permissionId);
              return next;
            });
          },
        },
      );
    },
    [id, role?.is_immutable, isSuperadmin, assignPermission, revokePermission, refetch],
  );

  if (isLoading) {
    return <div className="space-y-6"><LoadingSkeleton variant="page" /></div>;
  }

  if (error || !role) {
    return <div className="space-y-6"><ErrorState message={error?.message ?? 'Role not found'} onRetry={() => refetch()} /></div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" onClick={() => navigate(ROUTES.ADMIN_ROLES)}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <PageHeader title={role.name} subtitle={role.key} />
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

      {/* Superadmin auto-inherit banner */}
      {isSuperadmin && (
        <Alert>
          <Info className="h-4 w-4" />
          <AlertDescription>
            Superadmin inherits <strong>all</strong> permissions automatically. New permissions added to the system are available to superadmin immediately without any configuration. The checkboxes below are read-only and reflect the current full permission set.
          </AlertDescription>
        </Alert>
      )}

      {/* Permission Matrix */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Key className="h-4 w-4" />
            Permissions ({role.permissions.length} / {allPermissions?.length ?? '…'})
          </CardTitle>
          {role.is_immutable && !isSuperadmin && (
            <p className="text-xs text-muted-foreground mt-1">
              This role is immutable — permissions cannot be changed.
            </p>
          )}
        </CardHeader>
        <CardContent>
          {groups.length > 0 ? (
            <div className="space-y-5">
              {groups.map((group) => {
                const assignedCount = group.permissions.filter((p) => p.assigned).length;
                return (
                  <div key={group.resource}>
                    <div className="flex items-center gap-2 mb-2">
                      <h4 className="text-sm font-semibold text-foreground">{group.label}</h4>
                      <Badge variant="secondary" className="text-xs font-normal">
                        {assignedCount}/{group.permissions.length}
                      </Badge>
                    </div>
                    <div className="grid gap-1.5">
                      {group.permissions.map((perm) => {
                        const isPending = pendingToggles.has(perm.id);
                        const isDisabled = role.is_immutable || isSuperadmin || isPending || !canModifyPerms ||
                          (perm.assigned && !canRevokePerms) || (!perm.assigned && !canAssignPerms);
                        return (
                          <label
                            key={perm.id}
                            className={`flex items-start gap-3 rounded-md border border-border px-3 py-2 transition-colors ${
                              isDisabled ? 'opacity-60 cursor-not-allowed' : 'cursor-pointer hover:bg-muted/50'
                            }`}
                          >
                            <div className="pt-0.5">
                              {isPending ? (
                                <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                              ) : (
                                <Checkbox
                                  checked={perm.assigned}
                                  disabled={isDisabled}
                                  onCheckedChange={() => handleToggle(perm.id, perm.assigned)}
                                />
                              )}
                            </div>
                            <div className="min-w-0 flex-1">
                              <p className="text-sm font-mono text-foreground leading-tight">{perm.key}</p>
                              {perm.description && (
                                <p className="text-xs text-muted-foreground mt-0.5">{perm.description}</p>
                              )}
                            </div>
                          </label>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No permissions available.</p>
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
    </div>
  );
}
