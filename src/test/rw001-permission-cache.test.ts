/**
 * RW-001: Permission cache invalidation.
 *
 * Verifies that the authorization system uses fresh DB queries (no cache)
 * and that role changes are immediately reflected.
 *
 * Note: This is a unit-level test verifying the architecture has no cache.
 * Full E2E verification (assign role → immediate API access) requires
 * deployed edge functions and is covered by Deno integration tests.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

describe('RW-001: No permission cache exists (fresh queries)', () => {
  it('authorization.ts does not contain cache/memo/store patterns', () => {
    const content = readFileSync(
      resolve(__dirname, '../../supabase/functions/_shared/authorization.ts'),
      'utf-8'
    );

    // Should NOT have caching mechanisms
    expect(content).not.toMatch(/Map\s*</);
    expect(content).not.toMatch(/cache/i);
    expect(content).not.toMatch(/memo/i);
    expect(content).not.toMatch(/TTL/i);
    expect(content).not.toMatch(/localStorage/i);
  });

  it('rbac.ts client helper is marked UX-only, not enforcement', () => {
    const content = readFileSync(
      resolve(__dirname, '../../src/lib/rbac.ts'),
      'utf-8'
    );

    expect(content).toContain('UX-only');
    expect(content).toContain('NOT enforcement');
    expect(content).toContain('Server-side enforcement is authoritative');
  });

  it('authorization.ts uses has_permission RPC for each check', () => {
    const content = readFileSync(
      resolve(__dirname, '../../supabase/functions/_shared/authorization.ts'),
      'utf-8'
    );

    expect(content).toContain("supabaseAdmin.rpc('has_permission'");
  });
});
