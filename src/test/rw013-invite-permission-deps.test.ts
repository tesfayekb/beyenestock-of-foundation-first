/**
 * RW-013: Invitation permission dependency verification.
 *
 * Verifies:
 * - users.invite and users.invite.manage present in permission-deps.json
 * - users.invite and users.invite.manage present in _shared/permission-deps.ts
 * - Dependencies are correct per stage-invitations.md
 * - Both files are in sync for invitation permissions
 *
 * Source: permission-deps.json, supabase/functions/_shared/permission-deps.ts
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

describe('RW-013: Invitation permission dependency verification', () => {
  const ssot = readJson('permission-deps.json');
  const sharedSrc = readSource('supabase/functions/_shared/permission-deps.ts');
  const clientSrc = readSource('src/config/permission-deps.ts');

  // --- permission-deps.json (SSOT) ---

  it('users.invite exists in permission-deps.json', () => {
    expect(ssot).toHaveProperty('users.invite');
  });

  it('users.invite.manage exists in permission-deps.json', () => {
    expect(ssot).toHaveProperty('users.invite.manage');
  });

  it('users.invite depends on users.view_all and admin.access', () => {
    const deps = ssot['users.invite'];
    expect(deps).toContain('users.view_all');
    expect(deps).toContain('admin.access');
  });

  it('users.invite.manage depends on users.invite, users.view_all, and admin.access', () => {
    const deps = ssot['users.invite.manage'];
    expect(deps).toContain('users.invite');
    expect(deps).toContain('users.view_all');
    expect(deps).toContain('admin.access');
  });

  // --- _shared/permission-deps.ts (edge function copy) ---

  it('users.invite exists in _shared/permission-deps.ts', () => {
    expect(sharedSrc).toContain('"users.invite"');
  });

  it('users.invite.manage exists in _shared/permission-deps.ts', () => {
    expect(sharedSrc).toContain('"users.invite.manage"');
  });

  // --- Sync verification ---

  it('_shared/permission-deps.ts has same invitation entries as JSON', () => {
    // Verify every key from JSON appears in shared source
    for (const key of ['users.invite', 'users.invite.manage']) {
      expect(sharedSrc, `${key} missing from _shared/permission-deps.ts`).toContain(`"${key}"`);
      // Verify each dependency value also appears
      for (const dep of ssot[key]) {
        expect(sharedSrc, `dep "${dep}" for ${key} missing from _shared/permission-deps.ts`).toContain(`"${dep}"`);
      }
    }
  });

  it('client config (src/config/permission-deps.ts) imports from permission-deps.json', () => {
    expect(clientSrc).toContain('permission-deps.json');
  });

  // --- Edge function usage verification ---

  it('invite-user checks users.invite permission', () => {
    const src = readSource('supabase/functions/invite-user/index.ts');
    expect(src).toContain("'users.invite'");
  });

  it('invite-users-bulk checks users.invite permission', () => {
    const src = readSource('supabase/functions/invite-users-bulk/index.ts');
    expect(src).toContain("'users.invite'");
  });

  it('list-invitations checks users.invite.manage permission', () => {
    const src = readSource('supabase/functions/list-invitations/index.ts');
    expect(src).toContain("'users.invite.manage'");
  });

  it('revoke-invitation checks users.invite.manage permission', () => {
    const src = readSource('supabase/functions/revoke-invitation/index.ts');
    expect(src).toContain("'users.invite.manage'");
  });

  it('resend-invitation checks users.invite.manage permission', () => {
    const src = readSource('supabase/functions/resend-invitation/index.ts');
    expect(src).toContain("'users.invite.manage'");
  });
});
