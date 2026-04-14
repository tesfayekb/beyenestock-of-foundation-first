import { describe, expect, it } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

describe('RW-014: Google OAuth account picker hardening', () => {
  const signInContent = readFileSync(resolve(__dirname, '../pages/SignIn.tsx'), 'utf-8');
  const signUpContent = readFileSync(resolve(__dirname, '../pages/SignUp.tsx'), 'utf-8');

  it('SignIn forces explicit Google account selection', () => {
    expect(signInContent).toContain("queryParams");
    expect(signInContent).toContain("prompt: 'select_account'");
  });

  it('SignUp forces explicit Google account selection', () => {
    expect(signUpContent).toContain("queryParams");
    expect(signUpContent).toContain("prompt: 'select_account'");
  });
});
