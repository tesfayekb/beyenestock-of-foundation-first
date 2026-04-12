import { useState, useMemo } from 'react';
import { PageHeader } from '@/components/dashboard/PageHeader';
import { LoadingSkeleton } from '@/components/dashboard/LoadingSkeleton';
import { ErrorState } from '@/components/dashboard/ErrorState';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { usePermissions, PermissionListItem } from '@/hooks/useRoles';
import { useDebounce } from '@/hooks/useDebounce';
import { Search, ChevronDown, ChevronRight } from 'lucide-react';

interface PermissionGroup {
  resource: string;
  label: string;
  permissions: PermissionListItem[];
}

function groupByResource(permissions: PermissionListItem[]): PermissionGroup[] {
  const map = new Map<string, PermissionListItem[]>();
  for (const p of permissions) {
    const dotIdx = p.key.indexOf('.');
    const resource = dotIdx > 0 ? p.key.slice(0, dotIdx) : 'other';
    if (!map.has(resource)) map.set(resource, []);
    map.get(resource)!.push(p);
  }
  return Array.from(map.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([resource, perms]) => ({
      resource,
      label: resource.charAt(0).toUpperCase() + resource.slice(1),
      permissions: perms.sort((a, b) => a.key.localeCompare(b.key)),
    }));
}

export default function AdminPermissionsPage() {
  const { data: permissions, isLoading, error, refetch } = usePermissions();
  const [search, setSearch] = useState('');
  const debouncedSearch = useDebounce(search, 250);
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());

  const filteredPermissions = useMemo(() => {
    if (!permissions) return [];
    if (!debouncedSearch) return permissions;
    const q = debouncedSearch.toLowerCase();
    return permissions.filter(
      (p) =>
        p.key.toLowerCase().includes(q) ||
        (p.description ?? '').toLowerCase().includes(q) ||
        p.role_names.some((r) => r.toLowerCase().includes(q)),
    );
  }, [permissions, debouncedSearch]);

  const groups = useMemo(() => groupByResource(filteredPermissions), [filteredPermissions]);

  const toggleGroup = (resource: string) => {
    setCollapsed((prev) => {
      const next = new Set(prev);
      if (next.has(resource)) next.delete(resource);
      else next.add(resource);
      return next;
    });
  };

  return (
    <>
      <PageHeader
        title="Permissions"
        subtitle={`View all system permissions and their role assignments. ${permissions ? `${permissions.length} total.` : ''}`}
      />

      <div className="relative mb-4">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder="Search permissions…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-9 max-w-sm"
        />
      </div>

      {isLoading ? (
        <LoadingSkeleton variant="table" rows={10} />
      ) : error ? (
        <ErrorState message={error.message} onRetry={() => refetch()} />
      ) : groups.length === 0 ? (
        <div className="py-12 text-center text-sm text-muted-foreground">
          {debouncedSearch ? 'No permissions match your search.' : 'No permissions have been created yet.'}
        </div>
      ) : (
        <div className="space-y-3">
          {groups.map((group) => {
            const isCollapsed = collapsed.has(group.resource);
            return (
              <Card key={group.resource}>
                <CardHeader
                  className="cursor-pointer py-3 px-4"
                  onClick={() => toggleGroup(group.resource)}
                >
                  <CardTitle className="flex items-center justify-between text-sm font-semibold">
                    <span className="flex items-center gap-2">
                      {isCollapsed ? (
                        <ChevronRight className="h-4 w-4 text-muted-foreground" />
                      ) : (
                        <ChevronDown className="h-4 w-4 text-muted-foreground" />
                      )}
                      {group.label}
                      <Badge variant="secondary" className="text-xs font-normal">
                        {group.permissions.length}
                      </Badge>
                    </span>
                  </CardTitle>
                </CardHeader>
                {!isCollapsed && (
                  <CardContent className="pt-0 pb-3 px-4">
                    <div className="space-y-2">
                      {group.permissions.map((perm) => (
                        <div
                          key={perm.id}
                          className="flex items-center justify-between rounded-md border border-border px-3 py-2"
                        >
                          <div className="min-w-0 flex-1">
                            <p className="text-sm font-medium font-mono text-foreground">{perm.key}</p>
                            {perm.description && (
                              <p className="text-xs text-muted-foreground">{perm.description}</p>
                            )}
                          </div>
                          <div className="flex flex-wrap gap-1 ml-4 shrink-0">
                            {perm.role_names.length > 0 ? (
                              perm.role_names.map((name) => (
                                <Badge key={name} variant="secondary" className="text-xs">
                                  {name}
                                </Badge>
                              ))
                            ) : (
                              <span className="text-xs text-muted-foreground">Unassigned</span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                )}
              </Card>
            );
          })}
        </div>
      )}
    </>
  );
}
