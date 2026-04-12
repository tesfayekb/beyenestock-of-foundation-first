/**
 * RW-008: PERMISSION_DEPS drift detection.
 *
 * Verifies the canonical permission-deps.ts matches the two
 * server-side copies in edge functions. Uses file reading + hash comparison.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

/**
 * Extract the PERMISSION_DEPS object literal from a source file.
 * Returns a normalized, sorted JSON string for comparison.
 */
function extractPermissionDeps(filePath: string): Record<string, string[]> {
  const content = readFileSync(resolve(__dirname, '../../', filePath), 'utf-8');

  // Match the object literal after "PERMISSION_DEPS...= {"
  const match = content.match(/PERMISSION_DEPS[^=]*=\s*\{([\s\S]*?)\n\}/);
  if (!match) throw new Error(`Could not extract PERMISSION_DEPS from ${filePath}`);

  const body = match[1];
  const result: Record<string, string[]> = {};

  // Parse each entry: 'key.name': ['dep1', 'dep2', ...],
  const entryRegex = /'([^']+)':\s*\[([^\]]*)\]/g;
  let entryMatch;
  while ((entryMatch = entryRegex.exec(body)) !== null) {
    const key = entryMatch[1];
    const depsStr = entryMatch[2];
    const deps = depsStr
      .split(',')
      .map((d) => d.trim().replace(/'/g, ''))
      .filter(Boolean)
      .sort();
    result[key] = deps;
  }

  return result;
}

function normalize(deps: Record<string, string[]>): string {
  const sorted = Object.keys(deps)
    .sort()
    .reduce((acc, key) => {
      acc[key] = deps[key].sort();
      return acc;
    }, {} as Record<string, string[]>);
  return JSON.stringify(sorted);
}

describe('RW-008: PERMISSION_DEPS drift detection', () => {
  const canonical = extractPermissionDeps('src/config/permission-deps.ts');
  const assignCopy = extractPermissionDeps('supabase/functions/assign-permission-to-role/index.ts');
  const revokeCopy = extractPermissionDeps('supabase/functions/revoke-permission-from-role/index.ts');

  it('canonical source has entries', () => {
    expect(Object.keys(canonical).length).toBeGreaterThan(0);
  });

  it('assign-permission copy matches canonical', () => {
    expect(normalize(assignCopy)).toBe(normalize(canonical));
  });

  it('revoke-permission copy matches canonical', () => {
    expect(normalize(revokeCopy)).toBe(normalize(canonical));
  });

  it('all three have the same entry count', () => {
    const count = Object.keys(canonical).length;
    expect(Object.keys(assignCopy).length).toBe(count);
    expect(Object.keys(revokeCopy).length).toBe(count);
  });
});
