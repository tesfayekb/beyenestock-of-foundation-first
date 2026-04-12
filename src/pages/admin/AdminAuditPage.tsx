import { useState, useCallback } from 'react';
import { PageHeader } from '@/components/dashboard/PageHeader';
import { DataTable, DataTableColumn } from '@/components/dashboard/DataTable';
import { LoadingSkeleton } from '@/components/dashboard/LoadingSkeleton';
import { ErrorState } from '@/components/dashboard/ErrorState';
import { AuditActionBadge } from '@/components/admin/AuditActionBadge';
import { AuditMetadataViewer } from '@/components/admin/AuditMetadataViewer';
import { useAuditLogs, AuditLogEntry } from '@/hooks/useAuditLogs';
import { useAuditExport } from '@/hooks/useAuditExport';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Download, ChevronLeft, ChevronRight, RotateCcw, Search } from 'lucide-react';
import { format } from 'date-fns';

const PAGE_SIZE = 50;

const ACTION_OPTIONS = [
  { value: '', label: 'All actions' },
  { value: 'user.account_deactivated', label: 'user.account_deactivated' },
  { value: 'user.account_reactivated', label: 'user.account_reactivated' },
  { value: 'user.profile_updated', label: 'user.profile_updated' },
  { value: 'user.deactivation_rolled_back', label: 'user.deactivation_rolled_back' },
  { value: 'rbac.role_assigned', label: 'rbac.role_assigned' },
  { value: 'rbac.role_revoked', label: 'rbac.role_revoked' },
  { value: 'rbac.permission_assigned', label: 'rbac.permission_assigned' },
  { value: 'rbac.permission_revoked', label: 'rbac.permission_revoked' },
  { value: 'audit.exported', label: 'audit.exported' },
  { value: 'auth.permission_denied', label: 'auth.permission_denied' },
];

const TARGET_TYPE_OPTIONS = [
  { value: '', label: 'All targets' },
  { value: 'user', label: 'User' },
  { value: 'role', label: 'Role' },
  { value: 'permission', label: 'Permission' },
  { value: 'audit_logs', label: 'Audit logs' },
];

const columns: DataTableColumn<AuditLogEntry>[] = [
  {
    key: 'created_at',
    header: 'Timestamp',
    className: 'w-44',
    cell: (row) => (
      <span className="text-xs text-muted-foreground whitespace-nowrap">
        {format(new Date(row.created_at), 'yyyy-MM-dd HH:mm:ss')}
      </span>
    ),
  },
  {
    key: 'action',
    header: 'Action',
    className: 'w-48',
    cell: (row) => <AuditActionBadge action={row.action} />,
  },
  {
    key: 'actor_id',
    header: 'Actor',
    className: 'w-40',
    cell: (row) => {
      const displayName = (row as any).actor_display_name;
      return (
        <span className="text-xs text-muted-foreground" title={row.actor_id ?? ''}>
          {displayName && displayName !== row.actor_id
            ? displayName
            : row.actor_id ? row.actor_id.slice(0, 8) + '…' : '—'}
        </span>
      );
    },
  },
  {
    key: 'target',
    header: 'Target',
    cell: (row) => (
      <div className="text-xs">
        {row.target_type && (
          <span className="font-medium text-foreground">{row.target_type}</span>
        )}
        {row.target_id && (
          <span className="ml-1 font-mono text-muted-foreground" title={row.target_id}>
            {row.target_id.slice(0, 8)}…
          </span>
        )}
        {!row.target_type && !row.target_id && (
          <span className="text-muted-foreground">—</span>
        )}
      </div>
    ),
  },
  {
    key: 'metadata',
    header: 'Metadata',
    cell: (row) => <AuditMetadataViewer metadata={row.metadata} />,
  },
  {
    key: 'ip_address',
    header: 'IP',
    className: 'w-28',
    cell: (row) => (
      <span className="font-mono text-xs text-muted-foreground">
        {row.ip_address ?? '—'}
      </span>
    ),
  },
];

export default function AdminAuditPage() {
  // Filters
  const [actionFilter, setActionFilter] = useState('');
  const [targetTypeFilter, setTargetTypeFilter] = useState('');
  const [actorIdFilter, setActorIdFilter] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  // Cursor history for Prev/Next navigation
  const [cursorStack, setCursorStack] = useState<string[]>([]);
  const [currentCursor, setCurrentCursor] = useState<string | undefined>(undefined);

  const params = {
    limit: PAGE_SIZE,
    action: actionFilter || undefined,
    target_type: targetTypeFilter || undefined,
    actor_id: actorIdFilter || undefined,
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
    before: currentCursor,
  };

  const { data, isLoading, isError, refetch } = useAuditLogs(params);
  const { exportCsv, exporting } = useAuditExport();

  const entries = data?.data ?? [];
  const nextCursor = data?.pagination?.next_cursor ?? null;
  const hasPrev = cursorStack.length > 0;
  const hasNext = nextCursor !== null;

  const handleNext = useCallback(() => {
    if (!nextCursor) return;
    setCursorStack((prev) => [...prev, currentCursor ?? '__first__']);
    setCurrentCursor(nextCursor);
  }, [nextCursor, currentCursor]);

  const handlePrev = useCallback(() => {
    setCursorStack((prev) => {
      const newStack = [...prev];
      const prevCursor = newStack.pop();
      setCurrentCursor(prevCursor === '__first__' ? undefined : prevCursor);
      return newStack;
    });
  }, []);

  const resetFilters = useCallback(() => {
    setActionFilter('');
    setTargetTypeFilter('');
    setActorIdFilter('');
    setDateFrom('');
    setDateTo('');
    setCursorStack([]);
    setCurrentCursor(undefined);
  }, []);

  const handleExport = useCallback(() => {
    exportCsv({
      action: actionFilter || undefined,
      target_type: targetTypeFilter || undefined,
      actor_id: actorIdFilter || undefined,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
    });
  }, [exportCsv, actionFilter, targetTypeFilter, actorIdFilter, dateFrom, dateTo]);

  return (
    <>
      <PageHeader
        title="Audit Logs"
        subtitle="Compliance event log — all security-relevant actions"
        actions={
          <Button
            variant="outline"
            size="sm"
            onClick={handleExport}
            disabled={exporting}
          >
            <Download className="mr-2 h-4 w-4" />
            {exporting ? 'Exporting…' : 'Export CSV'}
          </Button>
        }
      />

      {/* Filters */}
      <div className="mb-4 flex flex-wrap items-end gap-3">
        <div className="space-y-1">
          <label className="text-xs font-medium text-muted-foreground">Action</label>
          <Select value={actionFilter || '__all__'} onValueChange={(v) => { setActionFilter(v === '__all__' ? '' : v); setCursorStack([]); setCurrentCursor(undefined); }}>
            <SelectTrigger className="w-44 h-9 text-xs">
              <SelectValue placeholder="All actions" />
            </SelectTrigger>
            <SelectContent>
              {ACTION_OPTIONS.map((o) => (
                <SelectItem key={o.value || '__all__'} value={o.value || '__all__'}>{o.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-1">
          <label className="text-xs font-medium text-muted-foreground">Target Type</label>
          <Select value={targetTypeFilter || '__all__'} onValueChange={(v) => { setTargetTypeFilter(v === '__all__' ? '' : v); setCursorStack([]); setCurrentCursor(undefined); }}>
            <SelectTrigger className="w-36 h-9 text-xs">
              <SelectValue placeholder="All targets" />
            </SelectTrigger>
            <SelectContent>
              {TARGET_TYPE_OPTIONS.map((o) => (
                <SelectItem key={o.value || '__all__'} value={o.value || '__all__'}>{o.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-1">
          <label className="text-xs font-medium text-muted-foreground">Actor ID</label>
          <div className="relative">
            <Search className="absolute left-2 top-2 h-4 w-4 text-muted-foreground" />
            <Input
              className="h-9 w-52 pl-8 text-xs"
              placeholder="UUID prefix…"
              value={actorIdFilter}
              onChange={(e) => { setActorIdFilter(e.target.value); setCursorStack([]); setCurrentCursor(undefined); }}
            />
          </div>
        </div>

        <div className="space-y-1">
          <label className="text-xs font-medium text-muted-foreground">From</label>
          <Input
            type="date"
            className="h-9 w-36 text-xs"
            value={dateFrom}
            onChange={(e) => { setDateFrom(e.target.value); setCursorStack([]); setCurrentCursor(undefined); }}
          />
        </div>

        <div className="space-y-1">
          <label className="text-xs font-medium text-muted-foreground">To</label>
          <Input
            type="date"
            className="h-9 w-36 text-xs"
            value={dateTo}
            onChange={(e) => { setDateTo(e.target.value); setCursorStack([]); setCurrentCursor(undefined); }}
          />
        </div>

        <Button variant="ghost" size="sm" className="h-9" onClick={resetFilters}>
          <RotateCcw className="mr-1 h-3.5 w-3.5" />
          Reset
        </Button>
      </div>

      {/* Table */}
      {isLoading ? (
        <LoadingSkeleton />
      ) : isError ? (
        <ErrorState message="Failed to load audit logs." onRetry={() => refetch()} />
      ) : (
        <>
          <DataTable
            columns={columns}
            data={entries}
            emptyTitle="No audit logs"
            emptyDescription="No events match the current filters."
          />

          {/* Cursor-based pagination controls */}
          {(hasPrev || hasNext) && (
            <div className="mt-3 flex items-center justify-between">
              <p className="text-xs text-muted-foreground">
                Showing {entries.length} entries{cursorStack.length > 0 ? ` · Page ${cursorStack.length + 1}` : ''}
              </p>
              <div className="flex items-center gap-1">
                <Button
                  variant="outline"
                  size="icon"
                  className="h-8 w-8"
                  disabled={!hasPrev}
                  onClick={handlePrev}
                  aria-label="Previous page"
                >
                  <ChevronLeft className="h-4 w-4" />
                </Button>
                <Button
                  variant="outline"
                  size="icon"
                  className="h-8 w-8"
                  disabled={!hasNext}
                  onClick={handleNext}
                  aria-label="Next page"
                >
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
          )}
        </>
      )}
    </>
  );
}
