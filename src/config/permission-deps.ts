/**
 * Permission dependency map.
 *
 * SSOT: /permission-deps.json at repo root.
 * This file re-exports from JSON for TypeScript consumers.
 */
import deps from '../../permission-deps.json';

export const PERMISSION_DEPS: Record<string, string[]> = deps;

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
    for (const transitive of (PERMISSION_DEPS[dep] ?? [])) {
      if (!visited.has(transitive)) {
        queue.push(transitive);
      }
    }
  }
  return Array.from(visited);
}
