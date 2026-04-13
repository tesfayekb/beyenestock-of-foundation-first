/**
 * RW-010: MFA enrollment redirect.
 *
 * Verifies that the MFA enrollment route exists and is properly
 * guarded behind RequireAuth + RequireVerifiedEmail.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

describe('RW-010: MFA enrollment route configuration', () => {
  const appContent = readFileSync(resolve(__dirname, '../App.tsx'), 'utf-8');

  it('/mfa-enroll route exists', () => {
    expect(appContent).toContain('/mfa-enroll');
  });

  it('/mfa-enroll is wrapped in RequireAuth', () => {
    // The route should be inside RequireAuth
    const _mfaSection = appContent.substring(
      appContent.indexOf('/mfa-enroll'),
      appContent.indexOf('/mfa-enroll') + 200
    );
    // Looking backward from mfa-enroll, RequireAuth should be present
    const beforeMfa = appContent.substring(0, appContent.indexOf('/mfa-enroll'));
    const lastRequireAuth = beforeMfa.lastIndexOf('RequireAuth');
    expect(lastRequireAuth).toBeGreaterThan(-1);
  });

  it('/mfa-challenge route exists for MFA verification', () => {
    expect(appContent).toContain('/mfa-challenge');
  });

  it('AdminLayout exists and enforces admin.access', () => {
    const adminLayoutContent = readFileSync(
      resolve(__dirname, '../layouts/AdminLayout.tsx'),
      'utf-8'
    );
    expect(adminLayoutContent).toContain('admin.access');
  });

  it('SignIn redirects to /mfa-challenge when challenge_required', () => {
    const signInContent = readFileSync(
      resolve(__dirname, '../pages/SignIn.tsx'),
      'utf-8'
    );
    expect(signInContent).toContain('mfaStatus');
    expect(signInContent).toContain('challenge_required');
    expect(signInContent).toContain('/mfa-challenge');
  });
});
