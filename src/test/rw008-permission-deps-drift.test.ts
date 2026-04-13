/**
 * RW-008: PERMISSION_DEPS drift detection.
 *
 * Verifies the SSOT permission-deps.json at repo root is valid,
 * and that the canonical client file and both edge functions
 * import from / read from the same JSON source.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const ROOT = resolve(__dirname, '../../');

function readJson(relPath: string): Record<string, string[]> {
  const content = readFileSync(resolve(ROOT, relPath), 'utf-8');
  return JSON.parse(content);
}

function readSource(relPath: string): string {
  return readFileSync(resolve(ROOT, relPath), 'utf-8');
}

describe('RW-008: PERMISSION_DEPS drift detection', () => {
  const ssot = readJson('permission-deps.json');

  it('SSOT JSON has entries', () => {
    expect(Object.keys(ssot).length).toBeGreaterThan(20);
  });

  it('SSOT JSON values are all string arrays', () => {
    for (const [key, deps] of Object.entries(ssot)) {
      expect(Array.isArray(deps), `${key} should be an array`).toBe(true);
      for (const dep of deps) {
        expect(typeof dep).toBe('string');
      }
    }
  });

  it('client config imports from permission-deps.json', () => {
    const src = readSource('src/config/permission-deps.ts');
    expect(src).toContain('permission-deps.json');
  });

  it('assign-permission edge function uses permission-deps shared module', () => {
    const src = readSource('supabase/functions/assign-permission-to-role/index.ts');
    // Must import from the shared TS module (not raw JSON)
    expect(src).toContain("from '../_shared/permission-deps.ts'");
    // Must not have its own inline PERMISSION_DEPS literal
    expect(src).not.toMatch(/const PERMISSION_DEPS\s*=/);
  });

  it('revoke-permission edge function uses permission-deps shared module', () => {
    const src = readSource('supabase/functions/revoke-permission-from-role/index.ts');
    expect(src).toContain("from '../_shared/permission-deps.ts'");
    expect(src).not.toMatch(/const PERMISSION_DEPS\s*=/);
  });

  it('_shared/permission-deps.ts is in sync with permission-deps.json', () => {
    const ssot = readJson('permission-deps.json');
    const sharedSrc = readSource('supabase/functions/_shared/permission-deps.ts');
    // Every key in the SSOT JSON must appear in the shared TS module
    for (const key of Object.keys(ssot)) {
      expect(sharedSrc, `${key} missing from _shared/permission-deps.ts`).toContain(`"${key}"`);
    }
  });

  it('admin.access is a dependency for all admin permissions', () => {
    const adminPerms = Object.entries(ssot).filter(([key]) =>
      key.startsWith('roles.') || key.startsWith('permissions.') ||
      key.startsWith('users.') || key.startsWith('audit.') ||
      key.startsWith('monitoring.') || key.startsWith('jobs.') ||
      key.startsWith('admin.')
    );
    for (const [key, deps] of adminPerms) {
      expect(deps, `${key} should depend on admin.access`).toContain('admin.access');
    }
  });
});
