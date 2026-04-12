/**
 * Permission dependency map.
 *
 * When a permission is assigned to a role, all of its dependencies
 * must also be present. The server enforces this by auto-inserting
 * missing dependencies; the client shows a toast listing what was
 * auto-added.
 *
 * Key   = the permission being assigned
 * Value = array of permission keys that MUST also be present
 *
 * NOTE: permissions.assign and permissions.revoke are superadmin-only.
 * They are still listed here for completeness (superadmin auto-inherits).
 */
export const PERMISSION_DEPS: Record<string, string[]> = {
  // RBAC
  'roles.assign':        ['roles.view', 'users.view_all', 'admin.access'],
  'roles.revoke':        ['roles.view', 'users.view_all', 'admin.access'],
  'roles.create':        ['roles.view', 'admin.access'],
  'roles.delete':        ['roles.view', 'admin.access'],
  'roles.edit':          ['roles.view', 'admin.access'],
  'permissions.assign':  ['roles.view', 'permissions.view', 'admin.access'],
  'permissions.revoke':  ['roles.view', 'permissions.view', 'admin.access'],
  'permissions.view':    ['admin.access'],

  // User management
  'users.edit_any':      ['users.view_all', 'admin.access'],
  'users.deactivate':    ['users.view_all', 'admin.access'],
  'users.reactivate':    ['users.view_all', 'admin.access'],

  // Audit
  'audit.export':        ['audit.view', 'admin.access'],
  'audit.view':          ['admin.access'],

  // Monitoring
  'monitoring.configure': ['monitoring.view', 'admin.access'],
  'monitoring.view':      ['admin.access'],

  // Jobs
  'jobs.trigger':            ['jobs.view', 'admin.access'],
  'jobs.pause':              ['jobs.view', 'admin.access'],
  'jobs.resume':             ['jobs.view', 'admin.access'],
  'jobs.retry':              ['jobs.view', 'admin.access'],
  'jobs.deadletter.manage':  ['jobs.view', 'admin.access'],
  'jobs.emergency':          ['admin.access'],
  'jobs.view':               ['admin.access'],

  // Admin
  'admin.config':        ['admin.access'],
};

/**
 * Recursively resolve all transitive dependencies for a permission key.
 * Returns a flat, deduplicated set (excludes the input key itself).
 */
export function resolveAllDeps(key: string): string[] {
  const visited = new Set<string>();
  const queue = PERMISSION_DEPS[key] ?? [];
  for (const dep of queue) {
    if (visited.has(dep)) continue;
    visited.add(dep);
    // Recurse — add transitive deps
    for (const transitive of (PERMISSION_DEPS[dep] ?? [])) {
      if (!visited.has(transitive)) {
        queue.push(transitive);
      }
    }
  }
  return Array.from(visited);
}
