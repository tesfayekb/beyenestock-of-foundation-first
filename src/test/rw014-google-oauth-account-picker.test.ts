import { describe, expect, it } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

describe('RW-014: Google OAuth account picker hardening', () => {
  const signInContent = readFileSync(resolve(__dirname, '../pages/SignIn.tsx'), 'utf-8');
  const signUpContent = readFileSync(resolve(__dirname, '../pages/SignUp.tsx'), 'utf-8');

  it('SignIn forces explicit Google account selection', () => {
    expect(signInContent).toContain('queryParams');
    expect(signInContent).toContain("prompt: 'select_account'");
  });

  it('SignUp forces explicit Google account selection', () => {
    expect(signUpContent).toContain('queryParams');
    expect(signUpContent).toContain("prompt: 'select_account'");
  });

  it('SignIn clears the local session and performs an explicit OAuth redirect handoff', () => {
    expect(signInContent).toContain("signOut({ scope: 'local' })");
    expect(signInContent).toContain('skipBrowserRedirect: true');
    expect(signInContent).toContain('window.location.assign(data.url)');
  });

  it('SignUp clears the local session and performs an explicit OAuth redirect handoff', () => {
    expect(signUpContent).toContain("signOut({ scope: 'local' })");
    expect(signUpContent).toContain('skipBrowserRedirect: true');
    expect(signUpContent).toContain('window.location.assign(data.url)');
  });
});
