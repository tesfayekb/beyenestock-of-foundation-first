import { describe, expect, it } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

describe('RW-015: session revocation cleanup', () => {
  const securityPageContent = readFileSync(resolve(__dirname, '../pages/user/SecurityPage.tsx'), 'utf-8');
  const apiClientContent = readFileSync(resolve(__dirname, '../lib/api-client.ts'), 'utf-8');

  it('SecurityPage clears the local session after global revocation', () => {
    expect(securityPageContent).toContain("invalidateTokenCache()");
    expect(securityPageContent).toContain("signOut({ scope: 'local' })");
    expect(securityPageContent).toContain('window.location.replace(ROUTES.SIGN_IN)');
  });

  it('apiClient forces a local logout when a protected edge function returns 401', () => {
    expect(apiClientContent).toContain('res.status === 401');
    expect(apiClientContent).toContain("signOut({ scope: 'local' })");
    expect(apiClientContent).toContain("window.location.replace('/sign-in')");
  });

  it('apiClient also recovers when auth headers cannot be built from a local session', () => {
    expect(apiClientContent).toContain('if (!session) {');
    expect(apiClientContent).toContain('await forceLocalLogout();');
  });
});
