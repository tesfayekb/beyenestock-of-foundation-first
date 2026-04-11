import { useState, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { PageHeader } from '@/components/dashboard/PageHeader';
import { DataTable, DataTableColumn } from '@/components/dashboard/DataTable';
import { StatusBadge } from '@/components/dashboard/StatusBadge';
import { LoadingSkeleton } from '@/components/dashboard/LoadingSkeleton';
import { ErrorState } from '@/components/dashboard/ErrorState';
import { RequirePermission } from '@/components/auth/RequirePermission';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useUsers, UserListItem } from '@/hooks/useUsers';
import { useUserRoles } from '@/hooks/useUserRoles';
import { checkPermission } from '@/lib/rbac';
import { ROUTES } from '@/config/routes';
import { format } from 'date-fns';
import { Search } from 'lucide-react';
import { useDebounce } from '@/hooks/useDebounce';

const PAGE_SIZE = 50;

export default function AdminUsersPage() {
  const navigate = useNavigate();
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'deactivated'>('all');
  const [page, setPage] = useState(1);
  const { context } = useUserRoles();

  const canViewRoles = checkPermission(context, 'roles.view');

  const debouncedSearch = useDebounce(search, 300);

  const params = useMemo(() => ({
    limit: PAGE_SIZE,
    offset: (page - 1) * PAGE_SIZE,
    status: statusFilter === 'all' ? undefined : statusFilter,
    search: debouncedSearch || undefined,
  }), [page, statusFilter, debouncedSearch]);

  const { data, isLoading, error, refetch } = useUsers(params);

  const handleRowClick = useCallback((row: UserListItem) => {
    navigate(ROUTES.ADMIN_USER_DETAIL.replace(':id', row.id));
  }, [navigate]);

  const columns: DataTableColumn<UserListItem>[] = useMemo(() => {
    const cols: DataTableColumn<UserListItem>[] = [
      {
        key: 'user',
        header: 'User',
        cell: (row) => {
          const initials = (row.display_name ?? '?').split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
          return (
            <div className="flex items-center gap-3">
              <Avatar className="h-8 w-8">
                <AvatarImage src={row.avatar_url ?? undefined} />
                <AvatarFallback className="text-xs">{initials}</AvatarFallback>
              </Avatar>
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-foreground">
                  {row.display_name ?? '—'}
                </p>
                <p className="truncate text-xs text-muted-foreground">
                  {row.email ?? row.id}
                </p>
              </div>
            </div>
          );
        },
      },
    ];

    // Conditionally show roles column based on permission
    if (canViewRoles) {
      cols.push({
        key: 'roles',
        header: 'Roles',
        cell: (row) => (
          <div className="flex flex-wrap gap-1">
            {row.roles && row.roles.length > 0 ? (
              row.roles.map((r) => (
                <Badge key={r.role_key} variant="secondary" className="text-xs">
                  {r.role_name}
                </Badge>
              ))
            ) : (
              <span className="text-xs text-muted-foreground">—</span>
            )}
          </div>
        ),
        className: 'w-40',
      });
    }

    cols.push(
      {
        key: 'status',
        header: 'Status',
        cell: (row) => <StatusBadge status={row.status as 'active' | 'deactivated'} />,
        className: 'w-28',
      },
      {
        key: 'email_verified',
        header: 'Verified',
        cell: (row) => (
          <StatusBadge
            status={row.email_verified ? 'active' : 'pending'}
            label={row.email_verified ? 'Yes' : 'No'}
          />
        ),
        className: 'w-24',
      },
      {
        key: 'created_at',
        header: 'Created',
        cell: (row) => (
          <span className="text-sm text-muted-foreground">
            {format(new Date(row.created_at), 'MMM d, yyyy')}
          </span>
        ),
        className: 'w-32',
      },
    );

    return cols;
  }, [canViewRoles]);

  const handleSearchChange = (value: string) => {
    setSearch(value);
    setPage(1);
  };

  const handleStatusChange = (value: string) => {
    setStatusFilter(value as 'all' | 'active' | 'deactivated');
    setPage(1);
  };

  return (
    <>
      <PageHeader title="Users" subtitle="Manage user accounts, view details, and control access." />

      {/* Filters */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search by name or email…"
            value={search}
            onChange={(e) => handleSearchChange(e.target.value)}
            className="pl-9"
          />
        </div>
        <Select value={statusFilter} onValueChange={handleStatusChange}>
          <SelectTrigger className="w-full sm:w-40">
            <SelectValue placeholder="All statuses" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            <SelectItem value="active">Active</SelectItem>
            <SelectItem value="deactivated">Deactivated</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Content */}
      {isLoading ? (
        <LoadingSkeleton variant="table" rows={8} />
      ) : error ? (
        <ErrorState message={error.message} onRetry={() => refetch()} />
      ) : (
        <DataTable
          columns={columns}
          data={data?.users ?? []}
          total={data?.total ?? 0}
          page={page}
          pageSize={PAGE_SIZE}
          onPageChange={setPage}
          onRowClick={handleRowClick}
          emptyTitle="No users found"
          emptyDescription="No users match your current filters."
        />
      )}
    </>
  );
}
