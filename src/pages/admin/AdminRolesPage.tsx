import { useState, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { PageHeader } from '@/components/dashboard/PageHeader';
import { DataTable, DataTableColumn } from '@/components/dashboard/DataTable';
import { LoadingSkeleton } from '@/components/dashboard/LoadingSkeleton';
import { ErrorState } from '@/components/dashboard/ErrorState';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useRoles, RoleListItem } from '@/hooks/useRoles';
import { useUserRoles } from '@/hooks/useUserRoles';
import { checkPermission } from '@/lib/rbac';
import { useDebounce } from '@/hooks/useDebounce';
import { ROUTES } from '@/config/routes';
import { Search, Plus } from 'lucide-react';
import { CreateRoleDialog } from '@/components/admin/CreateRoleDialog';

export default function AdminRolesPage() {
  const navigate = useNavigate();
  const { data: roles, isLoading, error, refetch } = useRoles();
  const { context } = useUserRoles();
  const [search, setSearch] = useState('');
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const debouncedSearch = useDebounce(search, 250);

  const canCreateRole = checkPermission(context, 'roles.create');

  const filteredRoles = useMemo(() => {
    if (!roles) return [];
    if (!debouncedSearch) return roles;
    const q = debouncedSearch.toLowerCase();
    return roles.filter(
      (r) =>
        r.name.toLowerCase().includes(q) ||
        r.key.toLowerCase().includes(q) ||
        (r.description ?? '').toLowerCase().includes(q),
    );
  }, [roles, debouncedSearch]);

  const handleRowClick = useCallback((row: RoleListItem) => {
    navigate(ROUTES.ADMIN_ROLE_DETAIL.replace(':id', row.id));
  }, [navigate]);

  const columns: DataTableColumn<RoleListItem>[] = useMemo(() => [
    {
      key: 'name',
      header: 'Role',
      cell: (row) => (
        <div className="min-w-0">
          <p className="text-sm font-medium text-foreground">{row.name}</p>
          <p className="text-xs text-muted-foreground font-mono">{row.key}</p>
        </div>
      ),
    },
    {
      key: 'flags',
      header: 'Type',
      cell: (row) => (
        <div className="flex flex-wrap gap-1">
          {row.is_base && <Badge variant="secondary" className="text-xs">Base</Badge>}
          {row.is_immutable && <Badge variant="outline" className="text-xs">Immutable</Badge>}
          {!row.is_base && !row.is_immutable && <span className="text-xs text-muted-foreground">Custom</span>}
        </div>
      ),
      className: 'w-32',
    },
    {
      key: 'permissions',
      header: 'Permissions',
      cell: (row) => (
        <span className="text-sm text-muted-foreground">{row.permission_count}</span>
      ),
      className: 'w-28',
    },
    {
      key: 'users',
      header: 'Users',
      cell: (row) => (
        <span className="text-sm text-muted-foreground">{row.user_count}</span>
      ),
      className: 'w-24',
    },
  ], []);

  return (
    <>
      <PageHeader
        title="Roles"
        subtitle="View and manage system roles and their permissions."
        actions={
          canCreateRole ? (
            <Button size="sm" onClick={() => setShowCreateDialog(true)}>
              <Plus className="mr-2 h-4 w-4" />
              Create Role
            </Button>
          ) : undefined
        }
      />

      <div className="relative mb-4">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder="Search roles…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-9 max-w-sm"
        />
      </div>

      {isLoading ? (
        <LoadingSkeleton variant="table" rows={6} />
      ) : error ? (
        <ErrorState message={error.message} onRetry={() => refetch()} />
      ) : (
        <DataTable
          columns={columns}
          data={filteredRoles}
          onRowClick={handleRowClick}
          emptyTitle="No roles found"
          emptyDescription={debouncedSearch ? 'No roles match your search.' : 'No roles have been created yet.'}
        />
      )}

      <CreateRoleDialog open={showCreateDialog} onOpenChange={setShowCreateDialog} />
    </>
  );
}
